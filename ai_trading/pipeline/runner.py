"""Pipeline runner — end-to-end orchestration of a pipeline run.

Loads config, fixes seeds, verifies data, computes features, builds
datasets, runs per-fold train/predict/calibrate/backtest/metrics, aggregates
inter-fold, writes artefacts, and validates JSON schemas.

Task #049 — WS-12.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

import ai_trading
import ai_trading.baselines  # noqa: F401
import ai_trading.features  # noqa: F401
import ai_trading.models  # noqa: F401
from ai_trading.artifacts.manifest import (
    STRATEGY_FRAMEWORK_MAP,
    build_manifest,
    get_git_commit,
    write_manifest,
)
from ai_trading.artifacts.metrics_builder import (
    build_metrics,
    write_fold_metrics,
    write_metrics,
)
from ai_trading.artifacts.run_dir import create_run_dir
from ai_trading.artifacts.validation import validate_manifest, validate_metrics
from ai_trading.backtest.costs import apply_cost_model
from ai_trading.backtest.engine import build_equity_curve, execute_trades
from ai_trading.calibration.threshold import apply_threshold, calibrate_threshold
from ai_trading.config import VALID_STRATEGIES, PipelineConfig
from ai_trading.data.dataset import build_samples
from ai_trading.data.labels import compute_labels
from ai_trading.data.missing import compute_valid_mask
from ai_trading.data.qa import run_qa_checks
from ai_trading.data.splitter import WalkForwardSplitter, apply_purge
from ai_trading.data.timeframes import TIMEFRAME_DELTA, parse_timeframe
from ai_trading.features.pipeline import compute_features, resolve_features
from ai_trading.features.warmup import apply_warmup
from ai_trading.metrics.aggregation import (
    PREDICTION_METRICS,
    aggregate_fold_metrics,
    check_acceptance_criteria,
    derive_comparison_type,
    stitch_equity_curves,
)
from ai_trading.metrics.prediction import compute_prediction_metrics
from ai_trading.metrics.trading import compute_trading_metrics
from ai_trading.models.base import MODEL_REGISTRY, get_model_class
from ai_trading.training.trainer import FoldTrainer
from ai_trading.utils.seed import set_global_seed

logger = logging.getLogger(__name__)

# Re-export for test imports
__all__ = [
    "run_pipeline",
    "VALID_STRATEGIES",
    "STRATEGY_FRAMEWORK_MAP",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_raw_ohlcv(config: PipelineConfig) -> tuple[pd.DataFrame, Path]:
    """Load raw OHLCV parquet file for the first (MVP) symbol.

    Returns
    -------
    tuple[pd.DataFrame, Path]
        The loaded DataFrame and the path to the parquet file.

    Raises
    ------
    FileNotFoundError
        If the parquet file does not exist.
    """
    symbol = config.dataset.symbols[0]
    timeframe = config.dataset.timeframe
    raw_dir = Path(config.dataset.raw_dir)
    parquet_path = raw_dir / f"{symbol}_{timeframe}.parquet"
    if not parquet_path.is_file():
        raise FileNotFoundError(
            f"Raw OHLCV file not found: {parquet_path}. "
            f"Run data ingestion first."
        )
    df = pd.read_parquet(parquet_path)
    logger.info("Loaded raw OHLCV: %d rows from %s", len(df), parquet_path)
    return df, parquet_path


def _sha256_file(path: Path) -> str:
    """Compute hex SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _prepare_ohlcv_indexed(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Convert raw OHLCV DataFrame to DatetimeIndex-based format for pipeline.

    The ingestion stores timestamps in ``timestamp_utc`` column. The
    feature pipeline and downstream modules expect a DatetimeIndex.
    """
    df = raw_df.copy()
    if "timestamp_utc" in df.columns:
        df = df.set_index("timestamp_utc")
    df.index = pd.DatetimeIndex(df.index)
    df = df.sort_index()
    return df


def _setup_file_logging(run_dir: Path) -> logging.FileHandler:
    """Add a FileHandler to the root logger pointing to run_dir/pipeline.log."""
    log_path = run_dir / "pipeline.log"
    handler = logging.FileHandler(str(log_path), encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    logger.info("File logging started: %s", log_path)
    return handler


def _timeframe_to_hours(timeframe: str) -> float:
    """Convert a timeframe string to hours."""
    delta = TIMEFRAME_DELTA[timeframe]
    return delta.total_seconds() / 3600.0


def _write_predictions_csv(
    timestamps: pd.DatetimeIndex,
    y_true: np.ndarray,
    y_hat: np.ndarray,
    path: Path,
) -> None:
    """Write predictions to CSV."""
    df = pd.DataFrame({
        "timestamp": timestamps,
        "y_true": y_true.astype(np.float64),
        "y_hat": y_hat.astype(np.float64),
    })
    df.to_csv(path, index=False)


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------


def run_pipeline(config: PipelineConfig) -> Path:
    """Execute the full pipeline and return the run directory path.

    Parameters
    ----------
    config : PipelineConfig
        Fully validated pipeline configuration.

    Returns
    -------
    Path
        Path to the created run directory containing all artefacts.

    Raises
    ------
    FileNotFoundError
        If raw data files are missing.
    ValueError
        If registry is inconsistent or other validation fails.
    """
    strategy_name = config.strategy.name

    # --- 1. Verify registry consistency ---
    registry_keys = set(MODEL_REGISTRY.keys())
    valid_keys = set(VALID_STRATEGIES.keys())
    if not registry_keys <= valid_keys:
        extra = registry_keys - valid_keys
        raise ValueError(
            f"MODEL_REGISTRY contains keys not in VALID_STRATEGIES: {sorted(extra)}. "
            f"Fix the registry or update VALID_STRATEGIES."
        )

    # --- 2. Fix global seed ---
    set_global_seed(
        seed=config.reproducibility.global_seed,
        deterministic_torch=config.reproducibility.deterministic_torch,
    )
    logger.info("Global seed set to %d", config.reproducibility.global_seed)

    # --- 3. Load and verify raw data + QA ---
    raw_df, parquet_path = _load_raw_ohlcv(config)

    qa_report = run_qa_checks(
        df=raw_df,
        timeframe=config.dataset.timeframe,
        zero_volume_min_streak=config.qa.zero_volume_min_streak,
    )
    logger.info("QA report: passed=%s", qa_report.passed)

    # --- 4. Prepare indexed OHLCV ---
    ohlcv = _prepare_ohlcv_indexed(raw_df)
    logger.info("OHLCV indexed: %d bars, %s to %s", len(ohlcv), ohlcv.index[0], ohlcv.index[-1])

    # --- 5. Compute features ---
    features_df = compute_features(ohlcv, config)
    logger.info("Features computed: %s", list(features_df.columns))

    # --- 6. Compute labels ---
    candle_mask = np.ones(len(ohlcv), dtype=bool)
    y, label_mask = compute_labels(ohlcv, config.label, candle_mask)

    # --- 7. Compute valid mask (missing candles policy) ---
    timestamps_series = pd.Series(ohlcv.index)
    valid_mask = compute_valid_mask(
        timestamps=timestamps_series,
        timeframe=config.dataset.timeframe,
        seq_len=config.window.L,
        horizon=config.label.horizon_H_bars,
    )

    # --- 8. Apply warmup ---
    feature_instances = resolve_features(config)
    params_dict = config.features.params.model_dump()
    final_mask = apply_warmup(
        features_df=features_df,
        valid_mask=valid_mask & label_mask,
        min_warmup=config.window.min_warmup,
        feature_instances=feature_instances,
        params=params_dict,
    )

    # --- 9. Build samples ---
    x_seq, y_out, sample_timestamps = build_samples(
        features_df=features_df,
        y=y,
        final_mask=final_mask,
        config=config.window,
    )
    logger.info("Samples built: X_seq=%s, y=%s", x_seq.shape, y_out.shape)

    # --- 10. Walk-forward split ---
    splitter = WalkForwardSplitter(config.splits, config.dataset.timeframe)
    folds = splitter.split(sample_timestamps)
    delta = parse_timeframe(config.dataset.timeframe)
    purged_folds = [
        apply_purge(
            fold=fold,
            timestamps=sample_timestamps,
            horizon_H_bars=config.label.horizon_H_bars,
            embargo_bars=config.splits.embargo_bars,
            delta=delta,
        )
        for fold in folds
    ]
    n_folds = len(purged_folds)
    logger.info("Walk-forward: %d folds after purge", n_folds)

    # --- 11. Create run_dir ---
    run_dir = create_run_dir(config, strategy_name, n_folds)
    logger.info("Run directory: %s", run_dir)

    # --- 12. Setup file logging (phase 2) ---
    file_handler = _setup_file_logging(run_dir)

    # --- 13. Resolve model class and instantiate ---
    model_cls = get_model_class(strategy_name)

    # --- 14. Per-fold loop ---
    trainer = FoldTrainer(config)
    timeframe_hours = _timeframe_to_hours(config.dataset.timeframe)

    fold_trading_for_agg: list[dict] = []
    fold_prediction_for_agg: list[dict] = []
    fold_equities: list[pd.DataFrame] = []
    folds_data_for_metrics: list[dict] = []

    for k, fold in enumerate(purged_folds):
        fold_id = k
        fold_dir = run_dir / "folds" / f"fold_{k:02d}"
        fold_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Fold %d/%d: train=%d, val=%d, test=%d",
            k, n_folds - 1,
            fold.n_train, fold.n_val, fold.n_test,
        )

        # --- Extract fold data ---
        x_train = x_seq[fold.train_indices]
        y_train = y_out[fold.train_indices]
        x_val = x_seq[fold.val_indices]
        y_val = y_out[fold.val_indices]
        x_test = x_seq[fold.test_indices]
        y_test = y_out[fold.test_indices]

        ts_train = sample_timestamps[fold.train_indices]
        ts_val = sample_timestamps[fold.val_indices]
        ts_test = sample_timestamps[fold.test_indices]

        # Build meta dicts for models that need decision_time
        meta_train = {"decision_time": ts_train}
        meta_val = {"decision_time": ts_val}
        meta_test = {"decision_time": ts_test}

        # --- Instantiate model ---
        # DummyModel requires seed; all other models use no-arg constructors.
        # MVP: only DummyModel has this signature quirk.
        if strategy_name == "dummy":
            model = model_cls(seed=config.reproducibility.global_seed)  # type: ignore[call-arg]
        else:
            model = model_cls()

        # --- Trainer: scale → fit → predict → save ---
        fold_model_dir = fold_dir / "model_artifacts"
        fold_model_dir.mkdir(parents=True, exist_ok=True)
        trainer_result = trainer.train_fold(
            model=model,
            X_train=x_train,
            y_train=y_train,
            X_val=x_val,
            y_val=y_val,
            X_test=x_test,
            run_dir=fold_model_dir,
            meta_train=meta_train,
            meta_val=meta_val,
            meta_test=meta_test,
            ohlcv=ohlcv,
        )

        y_hat_val = trainer_result["y_hat_val"]
        y_hat_test = trainer_result["y_hat_test"]

        output_type: str = model.output_type  # type: ignore[attr-defined]
        execution_mode: str = model.execution_mode

        # --- Calibrate θ ---
        if output_type == "signal":
            logger.info(
                "Fold %d: output_type='signal' — bypassing θ calibration", k
            )

        # Calibrate on validation OHLCV (or bypass for signal models)
        val_start = ts_val[0]
        val_end = ts_val[-1]
        ohlcv_val_mask = (ohlcv.index >= val_start) & (ohlcv.index <= val_end)
        ohlcv_val = ohlcv.loc[ohlcv_val_mask]

        cal_result: dict = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv_val,
            q_grid=config.thresholding.q_grid,
            horizon=config.label.horizon_H_bars,
            fee_rate_per_side=config.costs.fee_rate_per_side,
            slippage_rate_per_side=config.costs.slippage_rate_per_side,
            initial_equity=config.backtest.initial_equity,
            position_fraction=config.backtest.position_fraction,
            objective=config.thresholding.objective,
            mdd_cap=config.thresholding.mdd_cap,
            min_trades=config.thresholding.min_trades,
            output_type=output_type,
        )

        if output_type == "signal":
            # For signal models, predictions are already binary signals
            signals_test = y_hat_test.astype(np.int32)
        else:
            theta = cal_result["theta"]
            if theta is not None:
                signals_test = apply_threshold(y_hat_test, theta)
            else:
                signals_test = np.zeros(len(y_hat_test), dtype=np.int32)

        # --- Backtest on test period ---
        test_start = ts_test[0]
        test_end = ts_test[-1]
        ohlcv_test_mask = (ohlcv.index >= test_start) & (ohlcv.index <= test_end)
        ohlcv_test = ohlcv.loc[ohlcv_test_mask]

        # Align signals to OHLCV test slice
        # signals_test has one entry per sample in the test set.
        # We need one signal per bar in ohlcv_test.
        signals_series = pd.Series(signals_test, index=ts_test)
        signals_full = np.asarray(
            signals_series.reindex(ohlcv_test.index, fill_value=0),
            dtype=np.int32,
        )

        trades = execute_trades(
            signals=signals_full,
            ohlcv=ohlcv_test,
            horizon=config.label.horizon_H_bars,
            execution_mode=execution_mode,
        )

        # Apply cost model
        enriched_trades = apply_cost_model(
            trades=trades,
            fee_rate_per_side=config.costs.fee_rate_per_side,
            slippage_rate_per_side=config.costs.slippage_rate_per_side,
        )

        # Build equity curve
        equity_df = build_equity_curve(
            trades=enriched_trades,
            ohlcv=ohlcv_test,
            initial_equity=config.backtest.initial_equity,
            position_fraction=config.backtest.position_fraction,
        )

        # --- Save conditional artifacts ---
        if config.artifacts.save_predictions:
            _write_predictions_csv(ts_val, y_val, y_hat_val, fold_dir / "preds_val.csv")
            _write_predictions_csv(ts_test, y_test, y_hat_test, fold_dir / "preds_test.csv")

        if config.artifacts.save_equity_curve:
            equity_df.to_csv(fold_dir / "equity_curve.csv", index=False)
            fold_equities.append(equity_df)

        # Model already saved by trainer if save_model would be used.
        # The trainer always calls model.save(); the flag controls whether
        # we keep the artefact or remove it.
        if not config.artifacts.save_model:
            model_dir = fold_model_dir
            if model_dir.is_dir():
                for f in model_dir.iterdir():
                    if f.is_file():
                        f.unlink()

        # --- Compute metrics ---
        pred_metrics = compute_prediction_metrics(
            y_true=y_test.astype(np.float64),
            y_hat=y_hat_test.astype(np.float64),
            output_type=output_type,
        )

        trading_metrics = compute_trading_metrics(
            equity_curve=equity_df,
            trades=enriched_trades,
            sharpe_epsilon=config.metrics.sharpe_epsilon,
            sharpe_annualized=config.metrics.sharpe_annualized,
            timeframe_hours=timeframe_hours,
        )

        fold_trading_for_agg.append({**trading_metrics, **pred_metrics})
        fold_prediction_for_agg.append(pred_metrics)

        # --- Build fold data for metrics.json ---
        # Sanitize theta for JSON serialization (inf → null)
        raw_theta = cal_result["theta"]
        json_theta = None if (raw_theta is None or not np.isfinite(raw_theta)) else raw_theta

        # Normalize method for schema compliance: fallback_no_trade → none
        raw_method = cal_result["method"]
        schema_method = "none" if raw_method == "fallback_no_trade" else raw_method

        threshold_info = {
            "method": schema_method,
            "theta": json_theta,
            "selected_quantile": cal_result["quantile"],
        }

        fold_data = {
            "fold_id": fold_id,
            "period_test": {
                "start_utc": str(fold.test_start.isoformat()),
                "end_utc": str(fold.test_end.isoformat()),
            },
            "threshold": threshold_info,
            "prediction": pred_metrics,
            "n_samples_train": fold.n_train,
            "n_samples_val": fold.n_val,
            "n_samples_test": fold.n_test,
            "trading": trading_metrics,
        }
        folds_data_for_metrics.append(fold_data)

        # Write per-fold metrics
        write_fold_metrics(fold_data, fold_dir)
        logger.info(
            "Fold %d: n_trades=%d, net_pnl=%.6f",
            k, trading_metrics["n_trades"], trading_metrics["net_pnl"],
        )

    # --- 15. Aggregate inter-fold ---
    aggregate = aggregate_fold_metrics(fold_trading_for_agg)
    notes_list = check_acceptance_criteria(
        aggregate,
        mdd_cap=config.thresholding.mdd_cap,
    )
    # Schema expects notes as a string, not list
    notes = "; ".join(notes_list) if notes_list else ""

    comparison_type = derive_comparison_type(strategy_name)

    # Split aggregate into prediction/trading for metrics builder
    pred_agg_mean: dict = {}
    pred_agg_std: dict = {}
    trad_agg_mean: dict = {}
    trad_agg_std: dict = {}
    for key, val in aggregate.items():
        if key.endswith("_mean"):
            base = key[: -len("_mean")]
            if base in PREDICTION_METRICS:
                pred_agg_mean[base] = val
            else:
                trad_agg_mean[base] = val
        elif key.endswith("_std"):
            base = key[: -len("_std")]
            if base in PREDICTION_METRICS:
                pred_agg_std[base] = val
            else:
                trad_agg_std[base] = val

    aggregate_data = {
        "prediction": {"mean": pred_agg_mean, "std": pred_agg_std},
        "trading": {"mean": trad_agg_mean, "std": trad_agg_std},
        "notes": notes,
        "comparison_type": comparison_type,
    }

    # --- 16. Write metrics.json ---
    strategy_info = {
        "strategy_type": config.strategy.strategy_type,
        "name": strategy_name,
    }
    run_id = run_dir.name

    metrics_data = build_metrics(
        run_id=run_id,
        strategy_info=strategy_info,
        folds_data=folds_data_for_metrics,
        aggregate_data=aggregate_data,
    )
    write_metrics(metrics_data, run_dir)

    # --- 17. Stitch equity curves (if saved) ---
    if config.artifacts.save_equity_curve and len(fold_equities) > 0:
        stitched = stitch_equity_curves(fold_equities)
        stitched.to_csv(run_dir / "equity_curve.csv", index=False)

    # --- 18. Build and write manifest.json ---
    git_commit = get_git_commit()

    framework = STRATEGY_FRAMEWORK_MAP[strategy_name]

    # Build folds metadata for manifest
    folds_manifest = []
    for k, fold in enumerate(purged_folds):
        folds_manifest.append({
            "fold_id": k,
            "train": {
                "start_utc": fold.train_start.isoformat(),
                "end_utc": fold.train_only_end.isoformat(),
            },
            "val": {
                "start_utc": fold.val_start.isoformat(),
                "end_utc": fold.train_val_end.isoformat(),
            },
            "test": {
                "start_utc": fold.test_start.isoformat(),
                "end_utc": fold.test_end.isoformat(),
            },
        })

    # Build per-fold artifact metadata
    per_fold_artifacts = []
    for k in range(n_folds):
        fold_dir = run_dir / "folds" / f"fold_{k:02d}"
        fold_files: dict[str, str] = {
            "metrics_fold_json": str(fold_dir / "metrics_fold.json"),
        }
        if config.artifacts.save_predictions:
            fold_files["preds_val_csv"] = str(fold_dir / "preds_val.csv")
            fold_files["preds_test_csv"] = str(fold_dir / "preds_test.csv")
        if config.artifacts.save_equity_curve:
            fold_files["equity_curve_csv"] = str(fold_dir / "equity_curve.csv")
        if config.artifacts.save_model:
            fold_files["model_artifacts_dir"] = str(
                fold_dir / "model_artifacts"
            )
        per_fold_artifacts.append({"fold_id": k, "files": fold_files})

    # Build file-level artifact metadata
    files_meta: dict[str, str] = {
        "manifest_json": str(run_dir / "manifest.json"),
        "metrics_json": str(run_dir / "metrics.json"),
        "config_yaml": str(run_dir / "config_snapshot.yaml"),
        "pipeline_log": str(run_dir / "pipeline.log"),
    }
    if config.artifacts.save_equity_curve and len(fold_equities) > 0:
        files_meta["equity_curve_csv"] = str(run_dir / "equity_curve.csv")

    manifest_data = build_manifest(
        run_id=run_id,
        config_snapshot=config.model_dump(),
        dataset_info={
            "exchange": config.dataset.exchange,
            "symbols": config.dataset.symbols,
            "timeframe": config.dataset.timeframe,
            "start": config.dataset.start,
            "end": config.dataset.end,
            "timezone": config.dataset.timezone,
            "raw_files": [
                {
                    "path": str(parquet_path),
                    "sha256": _sha256_file(parquet_path),
                    "n_rows": len(raw_df),
                }
            ],
        },
        label_info={
            "horizon_H_bars": config.label.horizon_H_bars,
            "target_type": config.label.target_type,
        },
        window_info={
            "L": config.window.L,
            "min_warmup": config.window.min_warmup,
        },
        features_info={
            "feature_list": config.features.feature_list,
            "feature_version": config.features.feature_version,
        },
        splits_info={
            "scheme": config.splits.scheme,
            "train_days": config.splits.train_days,
            "test_days": config.splits.test_days,
            "step_days": config.splits.step_days,
            "val_frac_in_train": config.splits.val_frac_in_train,
            "embargo_bars": config.splits.embargo_bars,
            "folds": folds_manifest,
        },
        strategy_info={
            "strategy_type": config.strategy.strategy_type,
            "name": strategy_name,
            "framework": framework,
        },
        costs_info={
            "cost_model": config.costs.cost_model,
            "fee_rate_per_side": config.costs.fee_rate_per_side,
            "slippage_rate_per_side": config.costs.slippage_rate_per_side,
        },
        environment_info={
            "python_version": _get_python_version(),
            "platform": _get_platform(),
        },
        artifacts_info={
            "run_dir": str(run_dir),
            "files": files_meta,
            "per_fold": per_fold_artifacts,
        },
        git_commit=git_commit,
        pipeline_version=ai_trading.__version__,
    )
    write_manifest(manifest_data, run_dir)

    # --- 19. Validate JSON schemas ---
    manifest_json = json.loads((run_dir / "manifest.json").read_text())
    validate_manifest(manifest_json)
    logger.info("manifest.json validated against schema")

    metrics_json = json.loads((run_dir / "metrics.json").read_text())
    validate_metrics(metrics_json)
    logger.info("metrics.json validated against schema")

    # --- 20. Cleanup file logging ---
    logging.getLogger().removeHandler(file_handler)
    file_handler.close()

    logger.info("Pipeline run complete: %s", run_dir)
    return run_dir


def _get_python_version() -> str:
    """Return Python version string."""
    import sys
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _get_platform() -> str:
    """Return platform string."""
    import platform
    return platform.platform()
