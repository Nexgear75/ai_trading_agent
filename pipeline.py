#!/usr/bin/env python3
"""pipeline.py — AI Trading Pipeline orchestrator.

Thin orchestrator that wires together the modules in ``lib/``.

Usage:
    python pipeline.py --config configs/default.yaml
    python pipeline.py --config configs/default.yaml --strategy dummy
    python pipeline.py --config configs/default.yaml --output-dir /tmp/runs
    python pipeline.py --help
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ── lib imports ──────────────────────────────────────────────────────────
from lib.config import (  # noqa: F401 — re-exported for backward compat
    VALID_STRATEGIES,
    PipelineConfig,
    load_config,
)
from lib.timeframes import TIMEFRAME_DELTA, parse_timeframe  # noqa: F401
from lib.seed import set_global_seed  # noqa: F401
from lib.qa import run_qa_checks  # noqa: F401
from lib.features import (  # noqa: F401
    FEATURE_REGISTRY,
    resolve_features,
    compute_features,
    apply_warmup,
    VALID_OUTPUT_TYPES,
)
from lib.data import (  # noqa: F401
    compute_labels,
    compute_valid_mask,
    build_samples,
    flatten_seq_to_tab,
)
from lib.splitter import (  # noqa: F401
    FoldInfo,
    WalkForwardSplitter,
    apply_purge,
)
from lib.scaler import create_scaler  # noqa: F401
from lib.models import (  # noqa: F401
    MODEL_REGISTRY,
    get_model_class,
)
from lib.trainer import FoldTrainer  # noqa: F401
from lib.backtest import (  # noqa: F401
    validate_cost_rates,
    apply_cost_model,
    execute_trades,
    build_equity_curve,
    export_trade_journal,
)
from lib.calibration import (  # noqa: F401
    calibrate_threshold,
    apply_threshold,
)
from lib.metrics import (  # noqa: F401
    compute_prediction_metrics,
    compute_trading_metrics,
    aggregate_fold_metrics,
    stitch_equity_curves,
    check_acceptance_criteria,
    derive_comparison_type,
    PREDICTION_METRICS,
)
from lib.artifacts import (  # noqa: F401
    STRATEGY_FRAMEWORK_MAP,
    get_git_commit,
    build_manifest,
    write_manifest,
    build_metrics,
    write_metrics,
    write_fold_metrics,
    generate_run_id,
    save_config_snapshot,
    create_run_dir,
    validate_manifest,
    validate_metrics,
)

logger = logging.getLogger(__name__)

__version__ = "1.0.0"


# 
# PIPELINE HELPERS
# 


def _load_raw_ohlcv(config: PipelineConfig) -> tuple[pd.DataFrame, Path]:
    symbol = config.dataset.symbols[0]
    timeframe = config.dataset.timeframe
    raw_dir = Path(config.dataset.raw_dir)
    parquet_path = raw_dir / f"{symbol}_{timeframe}.parquet"
    if not parquet_path.is_file():
        raise FileNotFoundError(
            f"Raw OHLCV file not found: {parquet_path}. Run data ingestion first."
        )
    df = pd.read_parquet(parquet_path)
    logger.info("Loaded raw OHLCV: %d rows from %s", len(df), parquet_path)
    return df, parquet_path


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _prepare_ohlcv_indexed(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.copy()
    if "timestamp_utc" in df.columns:
        df = df.set_index("timestamp_utc")
    df.index = pd.DatetimeIndex(df.index)
    df = df.sort_index()
    return df


def _setup_file_logging(run_dir: Path) -> logging.FileHandler:
    log_path = run_dir / "pipeline.log"
    handler = logging.FileHandler(str(log_path), encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    logger.info("File logging started: %s", log_path)
    return handler


def _timeframe_to_hours(timeframe: str) -> float:
    delta = TIMEFRAME_DELTA[timeframe]
    return delta.total_seconds() / 3600.0


def _write_predictions_csv(
    timestamps: pd.DatetimeIndex,
    y_true: np.ndarray,
    y_hat: np.ndarray,
    path: Path,
) -> None:
    df = pd.DataFrame({
        "timestamp": timestamps,
        "y_true": y_true.astype(np.float64),
        "y_hat": y_hat.astype(np.float64),
    })
    df.to_csv(path, index=False)


def _get_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _get_platform() -> str:
    import platform
    return platform.platform()


def run_pipeline(config: PipelineConfig) -> Path:
    """Execute the full pipeline and return the run directory path."""
    strategy_name = config.strategy.name

    # 1. Registry check
    registry_keys = set(MODEL_REGISTRY.keys())
    valid_keys = set(VALID_STRATEGIES.keys())
    if not registry_keys <= valid_keys:
        extra = registry_keys - valid_keys
        raise ValueError(
            f"MODEL_REGISTRY contains keys not in VALID_STRATEGIES: {sorted(extra)}."
        )

    # 2. Fix global seed
    set_global_seed(
        seed=config.reproducibility.global_seed,
        deterministic_torch=config.reproducibility.deterministic_torch,
    )
    logger.info("Global seed set to %d", config.reproducibility.global_seed)

    # 3. Load and verify raw data + QA
    raw_df, parquet_path = _load_raw_ohlcv(config)
    qa_report = run_qa_checks(
        df=raw_df,
        timeframe=config.dataset.timeframe,
        zero_volume_min_streak=config.qa.zero_volume_min_streak,
    )
    logger.info("QA report: passed=%s", qa_report.passed)

    # 4. Prepare indexed OHLCV
    ohlcv = _prepare_ohlcv_indexed(raw_df)
    logger.info("OHLCV indexed: %d bars, %s to %s", len(ohlcv), ohlcv.index[0], ohlcv.index[-1])

    # 5. Compute features
    features_df = compute_features(ohlcv, config)
    logger.info("Features computed: %s", list(features_df.columns))

    # 6. Compute labels
    candle_mask = np.ones(len(ohlcv), dtype=bool)
    y, label_mask = compute_labels(ohlcv, config.label, candle_mask)

    # 7. Valid mask (missing candles)
    timestamps_series = pd.Series(ohlcv.index)
    valid_mask = compute_valid_mask(
        timestamps=timestamps_series,
        timeframe=config.dataset.timeframe,
        seq_len=config.window.L,
        horizon=config.label.horizon_H_bars,
    )

    # 8. Warmup
    feature_instances = resolve_features(config)
    params_dict = config.features.params.model_dump()
    final_mask = apply_warmup(
        features_df=features_df,
        valid_mask=valid_mask & label_mask,
        min_warmup=config.window.min_warmup,
        feature_instances=feature_instances,
        params=params_dict,
    )

    # 9. Build samples
    x_seq, y_out, sample_timestamps = build_samples(
        features_df=features_df, y=y, final_mask=final_mask, config=config.window,
    )
    logger.info("Samples built: X_seq=%s, y=%s", x_seq.shape, y_out.shape)

    # 10. Walk-forward split
    splitter = WalkForwardSplitter(config.splits, config.dataset.timeframe)
    folds = splitter.split(sample_timestamps)
    delta = parse_timeframe(config.dataset.timeframe)
    purged_folds = [
        apply_purge(
            fold=fold, timestamps=sample_timestamps,
            horizon_H_bars=config.label.horizon_H_bars,
            embargo_bars=config.splits.embargo_bars, delta=delta,
        )
        for fold in folds
    ]
    n_folds = len(purged_folds)
    logger.info("Walk-forward: %d folds after purge", n_folds)

    # 11. Create run_dir
    run_dir = create_run_dir(config, strategy_name, n_folds)
    logger.info("Run directory: %s", run_dir)

    # 12. File logging
    file_handler = _setup_file_logging(run_dir)

    # 13. Get model class
    model_cls = get_model_class(strategy_name)
    model_output_type: str = model_cls.output_type

    # 14. Per-fold loop
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
            k, n_folds - 1, fold.n_train, fold.n_val, fold.n_test,
        )

        x_train = x_seq[fold.train_indices]
        y_train = y_out[fold.train_indices]
        x_val = x_seq[fold.val_indices]
        y_val = y_out[fold.val_indices]
        x_test = x_seq[fold.test_indices]
        y_test = y_out[fold.test_indices]

        ts_train = sample_timestamps[fold.train_indices]
        ts_val = sample_timestamps[fold.val_indices]
        ts_test = sample_timestamps[fold.test_indices]

        meta_train = {"decision_time": ts_train}
        meta_val = {"decision_time": ts_val}
        meta_test = {"decision_time": ts_test}

        if strategy_name == "dummy":
            model = model_cls(seed=config.reproducibility.global_seed)
        else:
            model = model_cls()

        fold_model_dir = fold_dir / "model_artifacts"
        fold_model_dir.mkdir(parents=True, exist_ok=True)
        trainer_result = trainer.train_fold(
            model=model,
            X_train=x_train, y_train=y_train,
            X_val=x_val, y_val=y_val,
            X_test=x_test, run_dir=fold_model_dir,
            meta_train=meta_train, meta_val=meta_val,
            meta_test=meta_test, ohlcv=ohlcv,
        )

        y_hat_val = trainer_result["y_hat_val"]
        y_hat_test = trainer_result["y_hat_test"]
        output_type: str = model.output_type
        execution_mode: str = model.execution_mode

        ohlcv_val = ohlcv.loc[ts_val]

        cal_result: dict = calibrate_threshold(
            y_hat_val=y_hat_val, ohlcv_val=ohlcv_val,
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
            signals_test = y_hat_test.astype(np.int32)
        else:
            theta = cal_result["theta"]
            if theta is not None:
                signals_test = apply_threshold(y_hat_test, theta)
            else:
                signals_test = np.zeros(len(y_hat_test), dtype=np.int32)

        test_start = ts_test[0]
        test_end = ts_test[-1]
        ohlcv_test_mask = (ohlcv.index >= test_start) & (ohlcv.index <= test_end)
        ohlcv_test = ohlcv.loc[ohlcv_test_mask]

        signals_series = pd.Series(signals_test, index=ts_test)
        signals_full = np.asarray(
            signals_series.reindex(ohlcv_test.index, fill_value=0), dtype=np.int32,
        )

        trades = execute_trades(
            signals=signals_full, ohlcv=ohlcv_test,
            horizon=config.label.horizon_H_bars,
            execution_mode=execution_mode,
        )
        enriched_trades = apply_cost_model(
            trades=trades,
            fee_rate_per_side=config.costs.fee_rate_per_side,
            slippage_rate_per_side=config.costs.slippage_rate_per_side,
        )

        y_true_map = dict(zip(ts_test, y_test, strict=True))
        y_hat_map = dict(zip(ts_test, y_hat_test, strict=True))
        for trade in enriched_trades:
            sig_t = trade["signal_time"]
            trade["y_true"] = float(y_true_map[sig_t])
            trade["y_hat"] = float(y_hat_map[sig_t])

        equity_df = build_equity_curve(
            trades=enriched_trades, ohlcv=ohlcv_test,
            initial_equity=config.backtest.initial_equity,
            position_fraction=config.backtest.position_fraction,
        )

        if config.artifacts.save_predictions:
            _write_predictions_csv(ts_val, y_val, y_hat_val, fold_dir / "preds_val.csv")
            _write_predictions_csv(ts_test, y_test, y_hat_test, fold_dir / "preds_test.csv")

        if config.artifacts.save_equity_curve:
            equity_df.to_csv(fold_dir / "equity_curve.csv", index=False)
            fold_equities.append(equity_df)

        if config.artifacts.save_trades:
            export_trade_journal(
                trades=enriched_trades, path=fold_dir / "trades.csv",
                fee_rate_per_side=config.costs.fee_rate_per_side,
                slippage_rate_per_side=config.costs.slippage_rate_per_side,
            )

        if not config.artifacts.save_model:
            model_dir = fold_model_dir
            if model_dir.is_dir():
                for file in model_dir.iterdir():
                    if file.is_file():
                        file.unlink()

        pred_metrics = compute_prediction_metrics(
            y_true=y_test.astype(np.float64),
            y_hat=y_hat_test.astype(np.float64),
            output_type=output_type,
        )
        trading_metrics = compute_trading_metrics(
            equity_curve=equity_df, trades=enriched_trades,
            sharpe_epsilon=config.metrics.sharpe_epsilon,
            sharpe_annualized=config.metrics.sharpe_annualized,
            timeframe_hours=timeframe_hours,
        )

        fold_trading_for_agg.append({**trading_metrics, **pred_metrics})
        fold_prediction_for_agg.append(pred_metrics)

        raw_theta = cal_result["theta"]
        json_theta = None if (raw_theta is None or not np.isfinite(raw_theta)) else raw_theta
        raw_method = cal_result["method"]
        schema_method = raw_method

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
        write_fold_metrics(fold_data, fold_dir)
        logger.info(
            "Fold %d: n_trades=%d, net_pnl=%.6f",
            k, trading_metrics["n_trades"], trading_metrics["net_pnl"],
        )

    # 15. Aggregate
    aggregate = aggregate_fold_metrics(fold_trading_for_agg)
    notes_list = check_acceptance_criteria(aggregate, mdd_cap=config.thresholding.mdd_cap)
    notes = "; ".join(notes_list) if notes_list else ""
    comparison_type = derive_comparison_type(strategy_name)

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

    # 16. Write metrics.json
    strategy_info = {
        "strategy_type": config.strategy.strategy_type,
        "name": strategy_name,
        "output_type": model_output_type,
    }
    run_id = run_dir.name
    metrics_data = build_metrics(
        run_id=run_id, strategy_info=strategy_info,
        folds_data=folds_data_for_metrics, aggregate_data=aggregate_data,
    )
    write_metrics(metrics_data, run_dir)

    # 17. Stitch equity curves
    if config.artifacts.save_equity_curve and len(fold_equities) > 0:
        stitched = stitch_equity_curves(fold_equities)
        stitched.to_csv(run_dir / "equity_curve.csv", index=False)

    # 18. Manifest
    git_commit = get_git_commit()
    framework = STRATEGY_FRAMEWORK_MAP[strategy_name]

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
        if config.artifacts.save_trades:
            fold_files["trades_csv"] = str(fold_dir / "trades.csv")
        if config.artifacts.save_model:
            fold_files["model_artifacts_dir"] = str(fold_dir / "model_artifacts")
        per_fold_artifacts.append({"fold_id": k, "files": fold_files})

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
            "raw_files": [{
                "path": str(parquet_path),
                "sha256": _sha256_file(parquet_path),
                "n_rows": len(raw_df),
            }],
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
            "output_type": model_output_type,
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
        pipeline_version=__version__,
    )
    write_manifest(manifest_data, run_dir)

    # 19. Validate JSON schemas
    manifest_json = json.loads((run_dir / "manifest.json").read_text())
    validate_manifest(manifest_json)
    logger.info("manifest.json validated against schema")

    metrics_json = json.loads((run_dir / "metrics.json").read_text())
    validate_metrics(metrics_json)
    logger.info("metrics.json validated against schema")

    # 20. Cleanup
    logging.getLogger().removeHandler(file_handler)
    file_handler.close()

    logger.info("Pipeline run complete: %s", run_dir)
    return run_dir


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════


def main() -> None:
    """CLI entry point for the AI Trading Pipeline."""
    parser = argparse.ArgumentParser(
        description="AI Trading Pipeline — standalone runner",
    )
    parser.add_argument(
        "--config", required=True,
        help="Path to the YAML configuration file.",
    )
    parser.add_argument(
        "--strategy", default=None,
        help="Override strategy name (e.g. 'dummy', 'xgboost_reg').",
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Override output directory for artefacts.",
    )

    args = parser.parse_args()

    # Build overrides
    overrides: list[str] = []
    if args.strategy:
        overrides.append(f"strategy.name={args.strategy}")
        if args.strategy in VALID_STRATEGIES:
            overrides.append(
                f"strategy.strategy_type={VALID_STRATEGIES[args.strategy]}"
            )
    if args.output_dir:
        overrides.append(f"artifacts.output_dir={args.output_dir}")

    config = load_config(args.config, overrides=overrides if overrides else None)

    # Setup basic console logging
    log_level = getattr(logging, config.logging.level.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    run_dir = run_pipeline(config)
    print(f"Pipeline complete. Run directory: {run_dir}")


if __name__ == "__main__":
    main()
