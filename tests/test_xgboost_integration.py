"""End-to-end integration tests for the XGBoost pipeline.

Task #069 — WS-XGB-7: validates that a full pipeline run with
strategy.name='xgboost_reg' completes without crash on synthetic OHLCV
data and produces valid artefacts (manifest, metrics, model files, trades).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tests.conftest import build_ohlcv_df, write_config, write_parquet

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_N_BARS = 500
_SEED = 42


def _make_xgboost_config_dict(tmp_path: Path) -> dict:
    """Build a raw config dict for XGBoost E2E integration testing.

    Uses small parameters for CI speed: n_estimators=10, max_depth=3,
    n_folds=2 (via small train/test windows).
    """
    raw_dir = tmp_path / "data" / "raw"
    output_dir = tmp_path / "runs"
    output_dir.mkdir(parents=True, exist_ok=True)

    ohlcv = build_ohlcv_df(n=_N_BARS)
    write_parquet(ohlcv, raw_dir, "BTCUSDT")

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
            "train_days": 5,
            "test_days": 2,
            "step_days": 2,
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
            "strategy_type": "model",
            "name": "xgboost_reg",
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
                "max_depth": 3,
                "n_estimators": 10,
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
            "save_trades": True,
        },
    }


# ---------------------------------------------------------------------------
# TestXGBoostE2E
# ---------------------------------------------------------------------------


class TestXGBoostE2E:
    """#069 — E2E integration: full pipeline run with xgboost_reg strategy."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        self.cfg_dict = _make_xgboost_config_dict(tmp_path)
        self.cfg_path = write_config(tmp_path, self.cfg_dict)

    def _run(self) -> Path:
        """Load config and run the pipeline, returning the run directory."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        return run_pipeline(config)

    # -- AC: Run E2E sans crash ------------------------------------------

    def test_run_completes_without_crash(self):
        """#069 — Pipeline run with xgboost_reg completes and returns a dir."""
        run_dir = self._run()
        assert isinstance(run_dir, Path)
        assert run_dir.is_dir()

    # -- AC: manifest.json valid, strategy fields correct ----------------

    def test_manifest_exists_and_valid_schema(self):
        """#069 — manifest.json exists and passes JSON Schema validation."""
        from ai_trading.artifacts.validation import validate_manifest

        run_dir = self._run()
        manifest_path = run_dir / "manifest.json"
        assert manifest_path.is_file()
        manifest = json.loads(manifest_path.read_text())
        validate_manifest(manifest)  # raises on invalid

    def test_manifest_strategy_name(self):
        """#069 — manifest strategy.name == 'xgboost_reg'."""
        run_dir = self._run()
        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["strategy"]["name"] == "xgboost_reg"

    def test_manifest_strategy_framework(self):
        """#069 — manifest strategy.framework == 'xgboost'."""
        run_dir = self._run()
        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["strategy"]["framework"] == "xgboost"

    # -- AC: metrics.json valid, prediction metrics non-null -------------

    def test_metrics_exists_and_valid_schema(self):
        """#069 — metrics.json exists and passes JSON Schema validation."""
        from ai_trading.artifacts.validation import validate_metrics

        run_dir = self._run()
        metrics_path = run_dir / "metrics.json"
        assert metrics_path.is_file()
        metrics = json.loads(metrics_path.read_text())
        validate_metrics(metrics)  # raises on invalid

    def test_prediction_metrics_non_null(self):
        """#069 — Prediction metrics MAE > 0, RMSE > 0, DA in [0,1]."""
        run_dir = self._run()
        metrics = json.loads((run_dir / "metrics.json").read_text())
        assert len(metrics["folds"]) >= 1
        for fold in metrics["folds"]:
            pred = fold["prediction"]
            assert pred["mae"] > 0
            assert pred["rmse"] > 0
            assert 0.0 <= pred["directional_accuracy"] <= 1.0

    # -- AC: trading metrics present and coherent -----------------------

    def test_trading_metrics_present(self):
        """#069 — Trading metrics present in each fold."""
        run_dir = self._run()
        metrics = json.loads((run_dir / "metrics.json").read_text())
        for fold in metrics["folds"]:
            trading = fold["trading"]
            assert trading["net_pnl"] is not None
            assert trading["n_trades"] is not None
            assert trading["max_drawdown"] is not None

    # -- AC: at least 1 fold completed ----------------------------------

    def test_at_least_one_fold(self):
        """#069 — At least 1 fold directory exists."""
        run_dir = self._run()
        folds_dir = run_dir / "folds"
        assert folds_dir.is_dir()
        fold_dirs = sorted(folds_dir.iterdir())
        assert len(fold_dirs) >= 1

    # -- AC: xgboost model file present in each fold --------------------

    def test_xgboost_model_file_in_each_fold(self):
        """#069 — XGBoost model file present in model_artifacts of each fold.

        The trainer saves to ``model_artifacts/model``. The XGBoost _resolve_path
        treats this as a file path (not a directory), so the artifact is saved
        as ``model`` (no extension).
        """
        run_dir = self._run()
        fold_dirs = sorted((run_dir / "folds").iterdir())
        assert len(fold_dirs) >= 1
        for fd in fold_dirs:
            model_file = fd / "model_artifacts" / "model"
            assert model_file.is_file(), (
                f"XGBoost model file missing in {fd.name}"
            )

    # -- AC: trades.csv present in each fold ----------------------------

    def test_trades_csv_in_each_fold(self):
        """#069 — trades.csv present in each fold."""
        run_dir = self._run()
        fold_dirs = sorted((run_dir / "folds").iterdir())
        assert len(fold_dirs) >= 1
        for fd in fold_dirs:
            assert (fd / "trades.csv").is_file(), (
                f"trades.csv missing in {fd.name}"
            )

    # -- AC: seed fixed, test deterministic -----------------------------

    def test_deterministic_across_two_runs(self):
        """#069 — Two runs with same config/seed produce identical metrics."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config1 = load_config(str(self.cfg_path))
        run_dir1 = run_pipeline(config1)
        metrics1 = json.loads((run_dir1 / "metrics.json").read_text())

        config2 = load_config(str(self.cfg_path))
        run_dir2 = run_pipeline(config2)
        metrics2 = json.loads((run_dir2 / "metrics.json").read_text())

        # Compare fold-level prediction metrics
        for f1, f2 in zip(metrics1["folds"], metrics2["folds"], strict=True):
            assert f1["prediction"]["mae"] == pytest.approx(
                f2["prediction"]["mae"]
            )
            assert f1["prediction"]["rmse"] == pytest.approx(
                f2["prediction"]["rmse"]
            )
            assert f1["trading"]["net_pnl"] == pytest.approx(
                f2["trading"]["net_pnl"]
            )
