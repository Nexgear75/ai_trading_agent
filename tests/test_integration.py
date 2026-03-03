"""Integration tests — full pipeline on synthetic data.

Task #051 — WS-12: Dockerfile & CI integration.
Covers:
- Full pipeline with DummyModel → arborescence §15.1, valid JSON, metrics
- Full pipeline with no_trade baseline → θ bypass, net_pnl=0, n_trades=0
- synthetic_ohlcv fixture validation (500 candles, GBM, §4.1 columns)
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_parquet(ohlcv_df: pd.DataFrame, raw_dir: Path, symbol: str) -> None:
    """Write OHLCV DataFrame to parquet matching the ingestion convention."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{symbol}_1h.parquet"
    ohlcv_df.to_parquet(path, index=False)


def _make_integration_config(
    tmp_path: Path,
    ohlcv_df: pd.DataFrame,
    *,
    strategy_name: str = "dummy",
    strategy_type: str = "model",
) -> Path:
    """Build a YAML config for integration testing and return its path.

    Uses short windows and few folds to keep tests fast.
    """
    raw_dir = tmp_path / "data" / "raw"
    output_dir = tmp_path / "runs"
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_parquet(ohlcv_df, raw_dir, "BTCUSDT")

    start_ts = ohlcv_df["timestamp_utc"].iloc[0]
    end_ts = ohlcv_df["timestamp_utc"].iloc[-1] + pd.Timedelta(hours=1)

    cfg = {
        "logging": {"level": "WARNING", "format": "text", "file": "pipeline.log"},
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
        "window": {"L": 24, "min_warmup": 80},
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
            "train_days": 10,
            "test_days": 3,
            "step_days": 3,
            "val_frac_in_train": 0.2,
            "embargo_bars": 4,
            "min_samples_train": 10,
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
            "save_model": True,
            "save_equity_curve": True,
            "save_predictions": True,
        },
    }

    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump(cfg, default_flow_style=False), encoding="utf-8")
    return cfg_path


# ---------------------------------------------------------------------------
# 1. synthetic_ohlcv fixture validation
# ---------------------------------------------------------------------------


class TestSyntheticOhlcvFixture:
    """#051 — AC: synthetic_ohlcv generates a valid OHLCV DataFrame."""

    def test_row_count(self, synthetic_ohlcv):
        assert len(synthetic_ohlcv) == 500

    def test_columns_conform_to_spec(self, synthetic_ohlcv):
        """§4.1: open, high, low, close, volume, timestamp_utc."""
        expected = {"timestamp_utc", "open", "high", "low", "close", "volume"}
        assert set(synthetic_ohlcv.columns) == expected

    def test_timestamps_utc_aware(self, synthetic_ohlcv):
        ts = synthetic_ohlcv["timestamp_utc"]
        assert ts.dt.tz is not None
        assert str(ts.dt.tz) == "UTC"

    def test_timestamps_contiguous_hourly(self, synthetic_ohlcv):
        ts = synthetic_ohlcv["timestamp_utc"]
        diffs = ts.diff().dropna()
        assert (diffs == pd.Timedelta(hours=1)).all()

    def test_prices_positive(self, synthetic_ohlcv):
        for col in ("open", "high", "low", "close"):
            assert (synthetic_ohlcv[col] > 0).all(), f"{col} has non-positive values"

    def test_volume_positive(self, synthetic_ohlcv):
        assert (synthetic_ohlcv["volume"] > 0).all()

    def test_high_ge_low(self, synthetic_ohlcv):
        assert (synthetic_ohlcv["high"] >= synthetic_ohlcv["low"]).all()

    def test_deterministic(self, synthetic_ohlcv):
        """Two calls produce identical DataFrames (seed=42)."""
        # The fixture is called once per test, but we verify the seed
        # produces a known first close value.
        assert synthetic_ohlcv["close"].iloc[0] == pytest.approx(100.0, rel=1e-6)

    def test_no_nan(self, synthetic_ohlcv):
        assert not synthetic_ohlcv.isna().any().any()


# ---------------------------------------------------------------------------
# 2. Full pipeline — DummyModel on synthetic_ohlcv
# ---------------------------------------------------------------------------


class TestIntegrationDummy:
    """#051 — AC: DummyModel on synthetic data → arborescence §15.1, valid JSON."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path, synthetic_ohlcv):
        self.cfg_path = _make_integration_config(
            tmp_path, synthetic_ohlcv, strategy_name="dummy", strategy_type="model"
        )

    def test_run_completes(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        assert isinstance(run_dir, Path)
        assert run_dir.is_dir()

    def test_arborescence_section_15_1(self):
        """§15.1: run_dir contains manifest.json, metrics.json, config_snapshot.yaml,
        pipeline.log, and folds/ directory."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)

        assert (run_dir / "manifest.json").is_file()
        assert (run_dir / "metrics.json").is_file()
        assert (run_dir / "config_snapshot.yaml").is_file()
        assert (run_dir / "pipeline.log").is_file()
        assert (run_dir / "folds").is_dir()

        # At least one fold directory
        fold_dirs = sorted((run_dir / "folds").iterdir())
        assert len(fold_dirs) >= 1

        # Each fold has metrics_fold.json
        for fd in fold_dirs:
            assert (fd / "metrics_fold.json").is_file()

    def test_manifest_json_valid(self):
        from ai_trading.artifacts.validation import validate_manifest
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        manifest = json.loads((run_dir / "manifest.json").read_text())
        validate_manifest(manifest)  # raises on invalid
        assert manifest["strategy"]["name"] == "dummy"

    def test_metrics_json_valid(self):
        from ai_trading.artifacts.validation import validate_metrics
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        metrics = json.loads((run_dir / "metrics.json").read_text())
        validate_metrics(metrics)  # raises on invalid
        assert "folds" in metrics
        assert len(metrics["folds"]) >= 1

    def test_metrics_non_null(self):
        """Trading metrics must be populated (non-null) for DummyModel."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        metrics = json.loads((run_dir / "metrics.json").read_text())
        for fold in metrics["folds"]:
            assert fold["trading"]["net_pnl"] is not None
            assert fold["trading"]["n_trades"] is not None
            assert fold["prediction"]["mae"] is not None
            assert fold["prediction"]["rmse"] is not None


# ---------------------------------------------------------------------------
# 3. Full pipeline — no_trade baseline on synthetic_ohlcv
# ---------------------------------------------------------------------------


class TestIntegrationNoTrade:
    """#051 — AC: no_trade → θ bypass, net_pnl=0, n_trades=0."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path, synthetic_ohlcv):
        self.cfg_path = _make_integration_config(
            tmp_path,
            synthetic_ohlcv,
            strategy_name="no_trade",
            strategy_type="baseline",
        )

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

    def test_no_trade_theta_bypass(self):
        """no_trade output_type='signal' → θ bypass (method='none', theta=None)."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        metrics = json.loads((run_dir / "metrics.json").read_text())
        for fold in metrics["folds"]:
            assert fold["threshold"]["method"] == "none"
            assert fold["threshold"]["theta"] is None

    def test_no_trade_arborescence(self):
        """§15.1 arborescence also valid for baselines."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        assert (run_dir / "manifest.json").is_file()
        assert (run_dir / "metrics.json").is_file()
        assert (run_dir / "config_snapshot.yaml").is_file()

    def test_no_trade_json_schema_valid(self):
        from ai_trading.artifacts.validation import validate_manifest, validate_metrics
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        validate_manifest(json.loads((run_dir / "manifest.json").read_text()))
        validate_metrics(json.loads((run_dir / "metrics.json").read_text()))


# ---------------------------------------------------------------------------
# 4. Error scenarios
# ---------------------------------------------------------------------------


class TestIntegrationErrors:
    """#051 — AC: error scenarios for integration tests."""

    def test_missing_parquet_raises(self, tmp_path, synthetic_ohlcv):
        """Pipeline raises FileNotFoundError when raw parquet file is missing."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        cfg_path = _make_integration_config(
            tmp_path, synthetic_ohlcv, strategy_name="dummy", strategy_type="model"
        )
        config = load_config(str(cfg_path))

        # Delete the parquet file that _make_integration_config created
        raw_dir = Path(config.dataset.raw_dir)
        for f in raw_dir.glob("*.parquet"):
            f.unlink()

        with pytest.raises(FileNotFoundError, match="Raw OHLCV file not found"):
            run_pipeline(config)

    def test_invalid_strategy_name_raises(self, tmp_path, synthetic_ohlcv):
        """Pipeline raises ValueError for an unknown strategy name."""
        from pydantic import ValidationError

        from ai_trading.config import load_config

        cfg_path = _make_integration_config(
            tmp_path, synthetic_ohlcv, strategy_name="dummy", strategy_type="model"
        )

        # Patch config YAML to use an invalid strategy name
        cfg_text = cfg_path.read_text(encoding="utf-8")
        cfg_text = cfg_text.replace("name: dummy", "name: nonexistent_model_xyz")
        cfg_path.write_text(cfg_text, encoding="utf-8")

        with pytest.raises(ValidationError):
            load_config(str(cfg_path))
