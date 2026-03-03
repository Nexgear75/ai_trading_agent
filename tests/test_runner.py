"""Tests for the pipeline runner / orchestrator.

Task #049 — WS-12: complete pipeline orchestration.
Covers:
- Module importability
- Full run with DummyModel → valid artefact tree, JSON conformance, non-null metrics
- Full run with NoTradeBaseline → θ bypass, net_pnl=0, n_trades=0
- §14.4 acceptance warnings
- θ bypass for output_type="signal" logged at INFO
- STRATEGY_FRAMEWORK_MAP correctness
- config_snapshot.yaml always written (unconditional)
- JSON schema validation at end of run
- Conditional artefacts (save_predictions, save_equity_curve, save_model)
- Causality test: modifying future OHLCV → past signals unchanged
- Error paths: missing raw data, registry inconsistency
"""

from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

# ---------------------------------------------------------------------------
# Helpers — synthetic OHLCV on disk
# ---------------------------------------------------------------------------

_N_BARS = 3000  # Enough for walk-forward with short windows
_SEED = 42


def _build_ohlcv_df(n: int = _N_BARS, seed: int = _SEED) -> pd.DataFrame:
    """Synthetic OHLCV (UTC-aware, hourly, positive prices)."""
    rng = np.random.default_rng(seed)
    ts = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    close = 100.0 + np.cumsum(rng.standard_normal(n) * 0.3)
    close = np.abs(close) + 50.0
    opens = close + rng.standard_normal(n) * 0.05
    opens = np.abs(opens) + 50.0
    high = np.maximum(opens, close) + rng.uniform(0.01, 0.5, n)
    low = np.minimum(opens, close) - rng.uniform(0.01, 0.5, n)
    volume = rng.uniform(100, 10000, n)
    return pd.DataFrame(
        {
            "timestamp_utc": ts,
            "open": opens,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
    )


def _write_parquet(ohlcv_df: pd.DataFrame, raw_dir: Path, symbol: str) -> None:
    """Write a parquet file matching the ingestion convention."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{symbol}_1h.parquet"
    ohlcv_df.to_parquet(path, index=False)


def _make_config_dict(
    tmp_path: Path,
    *,
    strategy_name: str = "dummy",
    strategy_type: str = "model",
    save_predictions: bool = True,
    save_equity_curve: bool = True,
    save_model: bool = True,
    save_trades: bool = True,
    n_bars: int = _N_BARS,
) -> dict:
    """Build a raw config dict adapted for fast integration testing.

    Short windows, small horizons, few folds to keep tests fast.
    """
    raw_dir = tmp_path / "data" / "raw"
    output_dir = tmp_path / "runs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write OHLCV parquet
    ohlcv = _build_ohlcv_df(n=n_bars)
    _write_parquet(ohlcv, raw_dir, "BTCUSDT")

    # Compute dataset date range from OHLCV timestamps
    start_ts = ohlcv["timestamp_utc"].iloc[0]
    end_ts = ohlcv["timestamp_utc"].iloc[-1] + pd.Timedelta(hours=1)

    return {
        "logging": {"level": "INFO", "format": "text", "file": "pipeline.log"},
        "dataset": {
            "exchange": "binance",
            "symbols": ["BTCUSDT"],
            "timeframe": "1h",
            "start": start_ts.strftime("%Y-%m-%d"),
            "end": end_ts.strftime("%Y-%m-%d"),
            "timezone": "UTC",
            "raw_dir": str(raw_dir),
            "ingestion": {
                "page_limit": 1000,
                "max_retries": 3,
                "base_backoff_s": 1.0,
            },
        },
        "qa": {"zero_volume_min_streak": 2},
        "label": {"horizon_H_bars": 4, "target_type": "log_return_trade"},
        "window": {"L": 24, "min_warmup": 200},
        "features": {
            "feature_version": "mvp_v1",
            "feature_list": [
                "logret_1", "logret_2", "logret_4",
                "vol_24", "vol_72", "logvol", "dlogvol",
                "rsi_14", "ema_ratio_12_26",
            ],
            "params": {
                "rsi_period": 14,
                "rsi_epsilon": 1e-12,
                "ema_fast": 12,
                "ema_slow": 26,
                "vol_windows": [24, 72],
                "logvol_epsilon": 1e-8,
                "volatility_ddof": 0,
            },
        },
        "splits": {
            "scheme": "walk_forward_rolling",
            "train_days": 60,
            "test_days": 15,
            "step_days": 15,
            "val_frac_in_train": 0.2,
            "embargo_bars": 4,
            "min_samples_train": 50,
            "min_samples_test": 1,
        },
        "scaling": {
            "method": "standard",
            "epsilon": 1e-12,
            "robust_quantile_low": 0.005,
            "robust_quantile_high": 0.995,
            "rolling_window": 720,
        },
        "strategy": {
            "strategy_type": strategy_type,
            "name": strategy_name,
        },
        "thresholding": {
            "method": "quantile_grid",
            "q_grid": [0.5, 0.7, 0.9],
            "objective": "max_net_pnl_with_mdd_cap",
            "mdd_cap": 0.25,
            "min_trades": 1,
        },
        "costs": {
            "cost_model": "per_side_multiplicative",
            "fee_rate_per_side": 0.0005,
            "slippage_rate_per_side": 0.00025,
        },
        "backtest": {
            "mode": "one_at_a_time",
            "direction": "long_only",
            "initial_equity": 1.0,
            "position_fraction": 1.0,
        },
        "baselines": {"sma": {"fast": 20, "slow": 50}},
        "training": {
            "loss": "mse",
            "optimizer": "adam",
            "learning_rate": 1e-3,
            "batch_size": 64,
            "max_epochs": 100,
            "early_stopping_patience": 10,
        },
        "models": {
            "xgboost": {
                "max_depth": 5,
                "n_estimators": 500,
                "learning_rate": 0.05,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_alpha": 0.0,
                "reg_lambda": 1.0,
            },
            "cnn1d": {
                "n_conv_layers": 2,
                "filters": 64,
                "kernel_size": 3,
                "dropout": 0.2,
                "pool": "global_avg",
            },
            "gru": {
                "hidden_size": 64,
                "num_layers": 1,
                "bidirectional": False,
                "dropout": 0.2,
            },
            "lstm": {
                "hidden_size": 64,
                "num_layers": 1,
                "bidirectional": False,
                "dropout": 0.2,
            },
            "patchtst": {
                "patch_size": 16,
                "stride": 8,
                "d_model": 64,
                "n_heads": 4,
                "n_layers": 2,
                "ff_dim": 128,
                "dropout": 0.2,
            },
            "rl_ppo": {
                "hidden_sizes": [64, 64],
                "clip_epsilon": 0.2,
                "gamma": 0.99,
                "gae_lambda": 0.95,
                "n_epochs_ppo": 4,
                "max_episodes": 200,
                "rollout_steps": 512,
                "value_loss_coeff": 0.5,
                "entropy_coeff": 0.01,
                "learning_rate": 3e-4,
                "deterministic_eval": True,
            },
        },
        "metrics": {"sharpe_annualized": False, "sharpe_epsilon": 1e-12},
        "reproducibility": {"global_seed": 42, "deterministic_torch": False},
        "artifacts": {
            "output_dir": str(output_dir),
            "save_model": save_model,
            "save_equity_curve": save_equity_curve,
            "save_predictions": save_predictions,
            "save_trades": save_trades,
        },
    }


def _write_config(tmp_path: Path, cfg_dict: dict) -> Path:
    """Write config dict to a YAML file and return its path."""
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump(cfg_dict, default_flow_style=False), encoding="utf-8")
    return cfg_path


# ---------------------------------------------------------------------------
# 1. Module importability
# ---------------------------------------------------------------------------


class TestModuleImport:
    """#049 — AC: module exists and is importable."""

    def test_import_runner_module(self):
        mod = importlib.import_module("ai_trading.pipeline.runner")
        assert hasattr(mod, "run_pipeline")

    def test_import_valid_strategies(self):
        from ai_trading.pipeline.runner import VALID_STRATEGIES
        assert isinstance(VALID_STRATEGIES, dict)
        assert len(VALID_STRATEGIES) > 0

    def test_import_strategy_framework_map(self):
        from ai_trading.pipeline.runner import STRATEGY_FRAMEWORK_MAP
        assert isinstance(STRATEGY_FRAMEWORK_MAP, dict)
        assert len(STRATEGY_FRAMEWORK_MAP) > 0


# ---------------------------------------------------------------------------
# 2. STRATEGY_FRAMEWORK_MAP correctness
# ---------------------------------------------------------------------------


class TestStrategyFrameworkMap:
    """#049 — AC: strategy.framework derived automatically for each MVP strategy."""

    def test_all_valid_strategies_have_framework(self):
        from ai_trading.config import VALID_STRATEGIES
        from ai_trading.pipeline.runner import STRATEGY_FRAMEWORK_MAP
        for name in VALID_STRATEGIES:
            assert name in STRATEGY_FRAMEWORK_MAP, (
                f"Strategy '{name}' missing from STRATEGY_FRAMEWORK_MAP"
            )

    def test_dummy_framework(self):
        from ai_trading.pipeline.runner import STRATEGY_FRAMEWORK_MAP
        assert STRATEGY_FRAMEWORK_MAP["dummy"] == "internal"

    def test_baseline_frameworks(self):
        from ai_trading.pipeline.runner import STRATEGY_FRAMEWORK_MAP
        assert STRATEGY_FRAMEWORK_MAP["no_trade"] == "baseline"
        assert STRATEGY_FRAMEWORK_MAP["buy_hold"] == "baseline"
        assert STRATEGY_FRAMEWORK_MAP["sma_rule"] == "baseline"

    def test_model_frameworks(self):
        from ai_trading.pipeline.runner import STRATEGY_FRAMEWORK_MAP
        assert STRATEGY_FRAMEWORK_MAP["xgboost_reg"] == "xgboost"
        for name in ("cnn1d_reg", "gru_reg", "lstm_reg", "patchtst_reg", "rl_ppo"):
            assert STRATEGY_FRAMEWORK_MAP[name] == "pytorch"


# ---------------------------------------------------------------------------
# 3. Full pipeline DummyModel run
# ---------------------------------------------------------------------------


class TestFullRunDummy:
    """#049 — AC: Run with DummyModel → correct arborescence, valid JSON, non-null metrics."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        self.cfg_dict = _make_config_dict(tmp_path, strategy_name="dummy")
        self.cfg_path = _write_config(tmp_path, self.cfg_dict)

    def test_run_returns_path(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        assert isinstance(run_dir, Path)
        assert run_dir.is_dir()

    def test_config_snapshot_exists(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        assert (run_dir / "config_snapshot.yaml").is_file()

    def test_manifest_json_valid(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        manifest_path = run_dir / "manifest.json"
        assert manifest_path.is_file()
        manifest = json.loads(manifest_path.read_text())
        assert "run_id" in manifest
        assert "strategy" in manifest

    def test_metrics_json_valid(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        metrics_path = run_dir / "metrics.json"
        assert metrics_path.is_file()
        metrics = json.loads(metrics_path.read_text())
        assert "folds" in metrics
        assert len(metrics["folds"]) >= 1
        # non-null trading metrics for dummy (regression model)
        fold0 = metrics["folds"][0]
        assert fold0["trading"]["net_pnl"] is not None
        assert fold0["trading"]["n_trades"] is not None

    def test_fold_dirs_exist(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        folds_dir = run_dir / "folds"
        assert folds_dir.is_dir()
        fold_dirs = sorted(folds_dir.iterdir())
        assert len(fold_dirs) >= 1

    def test_pipeline_log_exists(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        assert (run_dir / "pipeline.log").is_file()

    def test_predictions_saved_when_flag_true(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        fold_dirs = sorted((run_dir / "folds").iterdir())
        # At least one fold should have preds_test.csv
        found_preds = any(
            (fd / "preds_test.csv").is_file() for fd in fold_dirs
        )
        assert found_preds

    def test_equity_curve_saved_when_flag_true(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        fold_dirs = sorted((run_dir / "folds").iterdir())
        found_ec = any(
            (fd / "equity_curve.csv").is_file() for fd in fold_dirs
        )
        assert found_ec

    def test_model_saved_when_flag_true(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        fold_dirs = sorted((run_dir / "folds").iterdir())
        # model_artifacts dir should have content
        found_model = any(
            (fd / "model_artifacts").is_dir()
            and any((fd / "model_artifacts").iterdir())
            for fd in fold_dirs
        )
        assert found_model

    def test_trades_csv_saved_when_flag_true(self):
        """W-1: trades.csv exported per fold when save_trades=True."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        fold_dirs = sorted((run_dir / "folds").iterdir())
        found_trades = any(
            (fd / "trades.csv").is_file() for fd in fold_dirs
        )
        assert found_trades


# ---------------------------------------------------------------------------
# 4. Full pipeline no_trade run
# ---------------------------------------------------------------------------


class TestFullRunNoTrade:
    """#049 — AC: no_trade → θ bypass, net_pnl=0, n_trades=0."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        self.cfg_dict = _make_config_dict(
            tmp_path, strategy_name="no_trade", strategy_type="baseline"
        )
        self.cfg_path = _write_config(tmp_path, self.cfg_dict)

    def test_no_trade_run_completes(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        assert run_dir.is_dir()

    def test_no_trade_zero_pnl_zero_trades(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        metrics = json.loads((run_dir / "metrics.json").read_text())
        for fold in metrics["folds"]:
            assert fold["trading"]["n_trades"] == 0
            assert fold["trading"]["net_pnl"] == pytest.approx(0.0, abs=1e-12)

    def test_no_trade_bypass_theta(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        metrics = json.loads((run_dir / "metrics.json").read_text())
        for fold in metrics["folds"]:
            assert fold["threshold"]["method"] == "none"
            assert fold["threshold"]["theta"] is None


# ---------------------------------------------------------------------------
# 5. θ bypass for signal models — INFO log
# ---------------------------------------------------------------------------


class TestThetaBypassInfoLog:
    """#049 — AC: bypass θ for output_type='signal' is logged at INFO level."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        self.cfg_dict = _make_config_dict(
            tmp_path, strategy_name="no_trade", strategy_type="baseline"
        )
        self.cfg_path = _write_config(tmp_path, self.cfg_dict)

    def test_theta_bypass_logged_info(self, caplog):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        with caplog.at_level(logging.INFO, logger="ai_trading.pipeline.runner"):
            run_pipeline(config)
        # Check that the bypass is logged
        bypass_msgs = [r for r in caplog.records if "bypass" in r.message.lower()]
        assert len(bypass_msgs) >= 1, "Expected at least one INFO log about θ bypass"
        assert all(r.levelno == logging.INFO for r in bypass_msgs)


# ---------------------------------------------------------------------------
# 6. §14.4 Acceptance warnings
# ---------------------------------------------------------------------------


class TestAcceptanceWarnings:
    """#049 — AC: §14.4 warnings emitted if thresholds exceeded."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        # no_trade → net_pnl=0 → triggers §14.4 warning net_pnl_mean <= 0
        self.cfg_dict = _make_config_dict(
            tmp_path, strategy_name="no_trade", strategy_type="baseline"
        )
        self.cfg_path = _write_config(tmp_path, self.cfg_dict)

    def test_warnings_emitted(self, caplog):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        with caplog.at_level(logging.WARNING):
            run_pipeline(config)
        # net_pnl_mean=0 for no_trade → warning
        warning_texts = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        found_pnl_warning = any("net_pnl_mean" in msg for msg in warning_texts)
        assert found_pnl_warning, "Expected §14.4 warning for net_pnl_mean <= 0"


# ---------------------------------------------------------------------------
# 7. Conditional artifacts — flags False
# ---------------------------------------------------------------------------


class TestConditionalArtifactsFalse:
    """#049 — AC: conditional artefacts not written when save_* = False."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        self.cfg_dict = _make_config_dict(
            tmp_path,
            strategy_name="dummy",
            save_predictions=False,
            save_equity_curve=False,
            save_model=False,
            save_trades=False,
        )
        self.cfg_path = _write_config(tmp_path, self.cfg_dict)

    def test_no_predictions_when_flag_false(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        fold_dirs = sorted((run_dir / "folds").iterdir())
        for fd in fold_dirs:
            assert not (fd / "preds_test.csv").is_file()
            assert not (fd / "preds_val.csv").is_file()

    def test_no_equity_curve_when_flag_false(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        fold_dirs = sorted((run_dir / "folds").iterdir())
        for fd in fold_dirs:
            assert not (fd / "equity_curve.csv").is_file()
        # No stitched equity curve either
        assert not (run_dir / "equity_curve.csv").is_file()

    def test_no_trades_csv_when_flag_false(self):
        """W-1: trades.csv NOT exported when save_trades=False."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        fold_dirs = sorted((run_dir / "folds").iterdir())
        for fd in fold_dirs:
            assert not (fd / "trades.csv").is_file()

    def test_unconditional_artifacts_always_present(self):
        """manifest.json, metrics.json, config_snapshot.yaml always written."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        assert (run_dir / "manifest.json").is_file()
        assert (run_dir / "metrics.json").is_file()
        assert (run_dir / "config_snapshot.yaml").is_file()


# ---------------------------------------------------------------------------
# 8. JSON Schema validation at end of run
# ---------------------------------------------------------------------------


class TestJsonSchemaValidation:
    """#049 — AC: JSON schema validation is executed at end of run."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        self.cfg_dict = _make_config_dict(tmp_path, strategy_name="dummy")
        self.cfg_path = _write_config(tmp_path, self.cfg_dict)

    def test_manifest_passes_schema(self):
        from ai_trading.artifacts.validation import validate_manifest
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        manifest = json.loads((run_dir / "manifest.json").read_text())
        # Should not raise
        validate_manifest(manifest)

    def test_metrics_passes_schema(self):
        from ai_trading.artifacts.validation import validate_metrics
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        metrics = json.loads((run_dir / "metrics.json").read_text())
        # Should not raise
        validate_metrics(metrics)


# ---------------------------------------------------------------------------
# 9. Error paths
# ---------------------------------------------------------------------------


class TestErrorPaths:
    """#049 — AC: error if raw data absent, registry inconsistent."""

    def test_error_missing_raw_data(self, tmp_path):
        """Raise if raw data parquet file does not exist."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        cfg_dict = _make_config_dict(tmp_path, strategy_name="dummy")
        # Remove the parquet file
        raw_dir = Path(cfg_dict["dataset"]["raw_dir"])
        for f in raw_dir.glob("*.parquet"):
            f.unlink()
        cfg_path = _write_config(tmp_path, cfg_dict)
        config = load_config(str(cfg_path))
        with pytest.raises(FileNotFoundError):
            run_pipeline(config)

    def test_error_registry_inconsistency(self, tmp_path):
        """Raise if MODEL_REGISTRY has keys not in VALID_STRATEGIES."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        cfg_dict = _make_config_dict(tmp_path, strategy_name="dummy")
        cfg_path = _write_config(tmp_path, cfg_dict)
        config = load_config(str(cfg_path))

        # Temporarily inject a bogus entry into MODEL_REGISTRY
        from ai_trading.models.base import MODEL_REGISTRY

        class _FakeModel:
            output_type = "regression"

        MODEL_REGISTRY["__bogus_test_model__"] = _FakeModel  # type: ignore[assignment]
        try:
            with pytest.raises(ValueError, match="registry"):
                run_pipeline(config)
        finally:
            MODEL_REGISTRY.pop("__bogus_test_model__", None)


# ---------------------------------------------------------------------------
# 10. Causality test
# ---------------------------------------------------------------------------


class TestCausality:
    """#049 — AC: modifying future OHLCV prices → past signals unchanged.

    Uses SMA baseline (data-dependent, causal) instead of DummyModel.
    SMA signals depend on historical close prices — modifying future bars
    must not alter signals for earlier bars.
    """

    def test_causality_sma_baseline(self, tmp_path):
        """Modify last 200 bars of OHLCV close prices.

        Signals for the first fold's test period must be identical between
        the original and perturbed runs, because SMA is backward-looking.
        """
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        # Run 1: original data
        cfg_dict_1 = _make_config_dict(
            tmp_path / "run1", strategy_name="sma_rule", strategy_type="baseline"
        )
        cfg_path_1 = _write_config(tmp_path / "run1", cfg_dict_1)
        config_1 = load_config(str(cfg_path_1))
        run_dir_1 = run_pipeline(config_1)

        # Run 2: perturbed future data (last 200 bars)
        cfg_dict_2 = _make_config_dict(
            tmp_path / "run2", strategy_name="sma_rule", strategy_type="baseline"
        )
        raw_dir_2 = Path(cfg_dict_2["dataset"]["raw_dir"])
        pq_path = raw_dir_2 / "BTCUSDT_1h.parquet"
        df = pd.read_parquet(pq_path)
        rng = np.random.default_rng(999)
        df.loc[df.index[-200:], "close"] = df.loc[df.index[-200:], "close"] * (
            1.0 + rng.uniform(-0.1, 0.1, 200)
        )
        df.to_parquet(pq_path, index=False)
        cfg_path_2 = _write_config(tmp_path / "run2", cfg_dict_2)
        config_2 = load_config(str(cfg_path_2))
        run_dir_2 = run_pipeline(config_2)

        # Compare first fold metrics — must be identical since SMA is
        # backward-looking and perturbation only affects the last 200 bars
        m1 = json.loads((run_dir_1 / "metrics.json").read_text())
        m2 = json.loads((run_dir_2 / "metrics.json").read_text())
        assert len(m1["folds"]) >= 1
        assert len(m2["folds"]) >= 1

        # First fold's test period ends well before the perturbation zone,
        # so trading metrics (including signals) must be strictly identical.
        t1 = m1["folds"][0]["trading"]
        t2 = m2["folds"][0]["trading"]
        for key in ("n_trades", "net_pnl", "net_return", "max_drawdown"):
            assert t1[key] == pytest.approx(t2[key], abs=1e-12), (
                f"First fold trading metric '{key}' differs: {t1[key]} vs {t2[key]}"
            )


# ---------------------------------------------------------------------------
# 10b. Edge cases: few folds
# ---------------------------------------------------------------------------


class TestEdgeCaseFolds:
    """#049 — Edge cases: very large windows → 0 or 1 fold."""

    def test_single_fold(self, tmp_path):
        """Reduced dataset that produces exactly 1 fold."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        # With 2200 bars (~92 raw days), warmup+window eats ~228 bars,
        # leaving ~83 days of samples → only 1 fold with default split params.
        cfg_dict = _make_config_dict(tmp_path, strategy_name="dummy", n_bars=2200)
        cfg_path = _write_config(tmp_path, cfg_dict)
        config = load_config(str(cfg_path))
        run_dir = run_pipeline(config)
        metrics = json.loads((run_dir / "metrics.json").read_text())
        assert len(metrics["folds"]) == 1

    def test_zero_folds_raises(self, tmp_path):
        """Dataset too small for any fold → pipeline raises."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        # 500 bars (~21 days) with train_days=60 → 0 folds
        cfg_dict = _make_config_dict(tmp_path, strategy_name="dummy", n_bars=500)
        cfg_path = _write_config(tmp_path, cfg_dict)
        config = load_config(str(cfg_path))
        with pytest.raises((ValueError, IndexError)):
            run_pipeline(config)


# ---------------------------------------------------------------------------
# 11. Buy-hold baseline run
# ---------------------------------------------------------------------------


class TestFullRunBuyHold:
    """#049 — Run with buy_hold baseline → single_trade execution, θ bypass."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        self.cfg_dict = _make_config_dict(
            tmp_path, strategy_name="buy_hold", strategy_type="baseline"
        )
        self.cfg_path = _write_config(tmp_path, self.cfg_dict)

    def test_buy_hold_completes(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        assert run_dir.is_dir()
        metrics = json.loads((run_dir / "metrics.json").read_text())
        for fold in metrics["folds"]:
            # buy_hold produces exactly 1 trade per fold
            assert fold["trading"]["n_trades"] == 1
            assert fold["threshold"]["method"] == "none"
