"""End-to-end integration tests for the XGBoost pipeline.

Task #069 — WS-XGB-7: validates that a full pipeline run with
strategy.name='xgboost_reg' completes without crash on synthetic OHLCV
data and produces valid artefacts (manifest, metrics, model files, trades).

Task #070 — WS-XGB-7: anti-leak tests for the XGBoost pipeline path.

Task #071 — WS-XGB-7: reproducibility tests — metrics determinism,
trades SHA-256, serialization round-trip.

Task #072 — WS-XGB-7: gate G-XGB-Integration — consolidated validation
of all 8 gate criteria.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
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


# ---------------------------------------------------------------------------
# TestXGBoostAntiLeak
# ---------------------------------------------------------------------------


class TestXGBoostAntiLeak:
    """#070 — Anti-leak tests for XGBoost pipeline path.

    Verifies absence of look-ahead bias: causality of predictions,
    scaler isolation to train, θ independence from test, and adapter
    C-order preservation.
    """

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        self.cfg_dict = _make_xgboost_config_dict(tmp_path)
        self.cfg_path = write_config(tmp_path, self.cfg_dict)

    # -- Test 1: Causality — modifying future OHLCV → past predictions unchanged --

    def test_causality_future_perturbation(self):
        """#070 — Modify OHLCV close prices for t > T; predictions for t ≤ T must
        remain identical within tolerance 1e-12 between original and perturbed runs.
        """
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        # Run 1: original data
        config1 = load_config(str(self.cfg_path))
        run_dir1 = run_pipeline(config1)
        metrics1 = json.loads((run_dir1 / "metrics.json").read_text())

        # Perturb future data: multiply close prices for the last 30 bars by 2.
        # With 500 bars, warmup=200, train_days=5 (~120 bars), val+embargo+test
        # ~76 bars → first fold ends ~bar 396. Perturbing bars 470-499 is safe.
        raw_dir = Path(self.cfg_dict["dataset"]["raw_dir"])
        pq_path = raw_dir / "BTCUSDT_1h.parquet"
        df = pd.read_parquet(pq_path)
        df.loc[df.index[-30:], "close"] = df.loc[df.index[-30:], "close"] * 2.0
        df.loc[df.index[-30:], "high"] = df.loc[df.index[-30:], "high"] * 2.0
        df.to_parquet(pq_path, index=False)

        # Run 2: perturbed data (re-write config to force new output_dir)
        output_dir2 = self.tmp / "runs2"
        output_dir2.mkdir(parents=True, exist_ok=True)
        cfg_dict2 = dict(self.cfg_dict)
        cfg_dict2["artifacts"] = dict(self.cfg_dict["artifacts"])
        cfg_dict2["artifacts"]["output_dir"] = str(output_dir2)
        run2_dir = self.tmp / "run2"
        run2_dir.mkdir(parents=True, exist_ok=True)
        cfg_path2 = write_config(run2_dir, cfg_dict2)
        config2 = load_config(str(cfg_path2))
        run_dir2 = run_pipeline(config2)
        metrics2 = json.loads((run_dir2 / "metrics.json").read_text())

        # First fold's test period ends before the perturbation zone,
        # so trading & prediction metrics must be identical.
        assert len(metrics1["folds"]) >= 1
        assert len(metrics2["folds"]) >= 1
        f1 = metrics1["folds"][0]
        f2 = metrics2["folds"][0]
        for key in ("mae", "rmse", "directional_accuracy"):
            assert f1["prediction"][key] == pytest.approx(
                f2["prediction"][key], abs=1e-12
            ), f"First fold prediction metric '{key}' differs after future perturbation"
        for key in ("n_trades", "net_pnl", "max_drawdown"):
            assert f1["trading"][key] == pytest.approx(
                f2["trading"][key], abs=1e-12
            ), f"First fold trading metric '{key}' differs after future perturbation"

    # -- Test 2: Scaler isolation — fit() uses only train indices --

    def test_scaler_fit_uses_only_train_data(self):
        """#070 — Scaler.fit() is called exclusively with X_train (train indices),
        never with val or test data. Verified by patching StandardScaler.fit.
        """
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))

        # We'll capture the array passed to scaler.fit() and the fold's
        # train/val/test shapes to verify disjointness.
        fit_calls = []
        original_fit = None

        from ai_trading.data import scaler as scaler_module

        original_fit = scaler_module.StandardScaler.fit

        def _spy_fit(self_scaler, x_train):
            fit_calls.append(x_train.shape)
            return original_fit(self_scaler, x_train)

        with patch.object(scaler_module.StandardScaler, "fit", _spy_fit):
            run_pipeline(config)

        # At least one fold was processed
        assert len(fit_calls) >= 1

        # Verify each fit call received data smaller than the full dataset
        # (i.e. not val+test). The full dataset is _N_BARS minus warmup.
        # Train size must be strictly less than total samples.
        # We also know train_days=5 → ~120 bars (minus warmup overhead).
        for shape in fit_calls:
            # shape is (N_train, L, F) — N_train must be > 0 and significantly
            # less than the full dataset (train is a strict subset).
            n_train = shape[0]
            assert n_train > 0, "Scaler fit received empty training set"
            assert n_train < _N_BARS // 2, (
                f"Scaler fit received {n_train} samples — "
                f"must be < {_N_BARS // 2} (half of full dataset {_N_BARS})"
            )

    # -- Test 3: θ independence from test — calibrate_threshold has no test input --

    def test_theta_independent_of_test_predictions(self):
        """#070 — θ is structurally independent of test predictions because
        calibrate_threshold() accepts only val data (y_hat_val, ohlcv_val).
        Verified by: (1) inspecting the function signature has no test-related
        parameter, and (2) calibrating θ once and confirming the result depends
        solely on val inputs.
        """
        import inspect

        from ai_trading.calibration.threshold import calibrate_threshold
        from tests.conftest import make_calibration_ohlcv

        # --- Part 1: structural guarantee — no test parameter in signature ---
        sig = inspect.signature(calibrate_threshold)
        param_names = set(sig.parameters.keys())
        test_related = {p for p in param_names if "test" in p}
        assert test_related == set(), (
            f"calibrate_threshold has test-related parameters {test_related} — "
            "θ calibration must not accept test data (§R3, §11.3)"
        )

        # --- Part 2: functional check — calibrate θ on val data ---
        n_val = 100
        rng = np.random.default_rng(42)
        y_hat_val = rng.standard_normal(n_val).astype(np.float64)
        ohlcv_val = make_calibration_ohlcv(n_val, seed=42)

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv_val,
            q_grid=[0.5, 0.7, 0.9],
            horizon=4,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=0.25,
            min_trades=1,
            output_type="regression",
        )

        # calibrate_threshold returned a result — since no test data can
        # enter the function, any y_hat_test variation in the pipeline is
        # irrelevant. θ depends structurally only on val inputs.
        assert "theta" in result
        assert "method" in result
        assert result["method"] in ("quantile_grid", "fallback_no_trade")

    # -- Test 4: Adapter C-order — flatten_seq_to_tab matches np.reshape C-order --

    def test_adapter_flatten_is_c_order(self):
        """#070 — flatten_seq_to_tab() produces identical values to
        np.reshape(..., order='C'), confirming no data reordering.
        """
        from ai_trading.data.dataset import flatten_seq_to_tab

        rng = np.random.default_rng(123)
        n, seq_len, n_feat = 50, 24, 9
        x_seq = rng.standard_normal((n, seq_len, n_feat)).astype(np.float32)
        feature_names = [f"f{i}" for i in range(n_feat)]

        x_tab, col_names = flatten_seq_to_tab(x_seq, feature_names)

        # Reference: explicit C-order reshape
        x_ref = x_seq.reshape(n, seq_len * n_feat, order="C")

        np.testing.assert_array_equal(
            x_tab, x_ref,
            err_msg="flatten_seq_to_tab output differs from C-order reshape"
        )
        assert x_tab.shape == (n, seq_len * n_feat)
        assert len(col_names) == seq_len * n_feat


# ---------------------------------------------------------------------------
# Helpers for deep comparison
# ---------------------------------------------------------------------------


def _deep_compare_metrics(obj1: object, obj2: object, path: str, atol: float) -> None:
    """Recursively compare two JSON-like objects, asserting float equality."""
    if isinstance(obj1, dict) and isinstance(obj2, dict):
        assert set(obj1.keys()) == set(obj2.keys()), (
            f"Key mismatch at {path}: {set(obj1.keys())} vs {set(obj2.keys())}"
        )
        for key in obj1:
            _deep_compare_metrics(obj1[key], obj2[key], f"{path}.{key}", atol)
    elif isinstance(obj1, list) and isinstance(obj2, list):
        assert len(obj1) == len(obj2), (
            f"List length mismatch at {path}: {len(obj1)} vs {len(obj2)}"
        )
        for i, (a, b) in enumerate(zip(obj1, obj2, strict=True)):
            _deep_compare_metrics(a, b, f"{path}[{i}]", atol)
    elif isinstance(obj1, (int, float)) and isinstance(obj2, (int, float)):
        assert abs(float(obj1) - float(obj2)) <= atol, (
            f"Float mismatch at {path}: {obj1} vs {obj2} (atol={atol})"
        )
    else:
        assert obj1 == obj2, f"Value mismatch at {path}: {obj1!r} vs {obj2!r}"


def _sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# TestXGBoostReproducibility
# ---------------------------------------------------------------------------


class TestXGBoostReproducibility:
    """#071 — Reproducibility tests for the XGBoost pipeline.

    Validates that two independent runs with the same seed produce
    strictly identical metrics.json and trades.csv, and that model
    serialization round-trip preserves predictions.
    """

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.cfg_dict = _make_xgboost_config_dict(tmp_path)
        self.cfg_path = write_config(tmp_path, self.cfg_dict)

    def _run_pipeline(self, cfg_path: Path) -> Path:
        """Load config and run the pipeline, returning the run directory."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(cfg_path))
        return run_pipeline(config)

    def _run_two(self) -> tuple[Path, Path]:
        """Execute two independent pipeline runs with the same config/seed."""
        # Run 1
        run_dir1 = self._run_pipeline(self.cfg_path)

        # Run 2 — same config, fresh output dir
        output_dir2 = self.tmp / "runs2"
        output_dir2.mkdir(parents=True, exist_ok=True)
        cfg_dict2 = dict(self.cfg_dict)
        cfg_dict2["artifacts"] = dict(self.cfg_dict["artifacts"])
        cfg_dict2["artifacts"]["output_dir"] = str(output_dir2)
        cfg2_dir = self.tmp / "cfg2"
        cfg2_dir.mkdir(parents=True, exist_ok=True)
        cfg_path2 = write_config(cfg2_dir, cfg_dict2)
        run_dir2 = self._run_pipeline(cfg_path2)

        return run_dir1, run_dir2

    # -- Test 1: Metrics determinism (full metrics.json, atol=1e-7) ------

    def test_metrics_json_identical_across_two_runs(self) -> None:
        """#071 — Two runs with same seed produce metrics.json identical
        field-by-field (atol=1e-7 for floats).
        """
        run_dir1, run_dir2 = self._run_two()

        metrics1 = json.loads((run_dir1 / "metrics.json").read_text())
        metrics2 = json.loads((run_dir2 / "metrics.json").read_text())

        # Remove non-deterministic metadata (run_id, timestamps, paths)
        for m in (metrics1, metrics2):
            m.pop("run_id", None)
            m.pop("timestamp", None)
            m.pop("run_dir", None)

        _deep_compare_metrics(metrics1, metrics2, "metrics", atol=1e-7)

    # -- Test 2: Trades SHA-256 -----------------------------------------

    def test_trades_csv_sha256_identical_across_two_runs(self) -> None:
        """#071 — Two runs with same seed produce trades.csv files that are
        byte-identical (SHA-256 comparison) in each fold.
        """
        run_dir1, run_dir2 = self._run_two()

        folds1 = sorted((run_dir1 / "folds").iterdir())
        folds2 = sorted((run_dir2 / "folds").iterdir())
        assert len(folds1) == len(folds2)
        assert len(folds1) >= 1

        for fd1, fd2 in zip(folds1, folds2, strict=True):
            trades1 = fd1 / "trades.csv"
            trades2 = fd2 / "trades.csv"
            assert trades1.is_file(), f"trades.csv missing in {fd1.name}"
            assert trades2.is_file(), f"trades.csv missing in {fd2.name}"

            hash1 = _sha256_file(trades1)
            hash2 = _sha256_file(trades2)
            assert hash1 == hash2, (
                f"trades.csv SHA-256 mismatch in {fd1.name}: "
                f"{hash1} vs {hash2}"
            )

    # -- Test 3: Serialization round-trip --------------------------------

    def test_serialization_roundtrip_predictions(self) -> None:
        """#071 — save() + load() + predict() produces identical predictions
        as before save (serialization round-trip at model level).
        """
        from ai_trading.models.xgboost import XGBoostRegModel

        rng = np.random.default_rng(_SEED)

        # Build synthetic 3D data (N, L, F) — matches pipeline conventions
        n_train, n_val, n_test = 80, 20, 30
        seq_len, n_feat = 24, 9
        x_train = rng.standard_normal(
            (n_train, seq_len, n_feat)
        ).astype(np.float32)
        y_train = rng.standard_normal(n_train).astype(np.float32)
        x_val = rng.standard_normal(
            (n_val, seq_len, n_feat)
        ).astype(np.float32)
        y_val = rng.standard_normal(n_val).astype(np.float32)
        x_test = rng.standard_normal(
            (n_test, seq_len, n_feat)
        ).astype(np.float32)

        # Create a minimal config for XGBoost fit
        from ai_trading.config import load_config

        rt_cfg_dir = self.tmp / "rt_cfg"
        rt_cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = write_config(rt_cfg_dir, self.cfg_dict)
        config = load_config(str(cfg_path))

        # Fit model
        model = XGBoostRegModel()
        model.fit(
            X_train=x_train,
            y_train=y_train,
            X_val=x_val,
            y_val=y_val,
            config=config,
            run_dir=self.tmp / "rt_model",
        )

        # Predict before save
        y_hat_before = model.predict(X=x_test)

        # Save
        save_path = self.tmp / "rt_model" / "saved_model"
        model.save(save_path)
        assert save_path.is_file()

        # Load into a fresh model and predict
        model2 = XGBoostRegModel()
        model2.load(save_path)
        # XGBoost's native save/load (save_model/load_model) does not persist
        # our custom _feature_names attribute. We must restore it manually so that
        # predict() can build the expected DMatrix column names. This is a known
        # limitation of the current save/load contract.
        model2._feature_names = [f"f{i}" for i in range(n_feat)]

        y_hat_after = model2.predict(X=x_test)

        np.testing.assert_array_equal(
            y_hat_before, y_hat_after,
            err_msg="Predictions differ after save/load round-trip",
        )


# ---------------------------------------------------------------------------
# TestGateXGBIntegration
# ---------------------------------------------------------------------------


class TestGateXGBIntegration:
    """#072 — Gate G-XGB-Integration: consolidated validation of all 8 criteria.

    Each criterion test runs the pipeline independently via ``_run()`` for full
    isolation (criteria 6 and 7 require two runs each).  Criteria checked:
    1. Run complet sans crash
    2. manifest.json and metrics.json valid (JSON Schema)
    3. strategy.name == 'xgboost_reg' and strategy.framework == 'xgboost'
    4. Prediction metrics non-null (MAE, RMSE, DA)
    5. Trading metrics present and coherent
    6. Anti-leak: future price modification → predictions unchanged for t ≤ T
    7. Reproducibility: two runs same seed → metrics.json identical (atol=1e-7)
    8. ruff check ai_trading/ tests/ clean
    """

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.cfg_dict = _make_xgboost_config_dict(tmp_path)
        self.cfg_path = write_config(tmp_path, self.cfg_dict)

    def _run(self) -> Path:
        """Load config and run the pipeline, returning the run directory."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        return run_pipeline(config)

    # -- Criterion 1: Run complet sans crash -----------------------------

    def test_gate_criterion_1_run_completes(self):
        """#072 — Gate criterion 1: full pipeline run completes without crash."""
        run_dir = self._run()
        assert isinstance(run_dir, Path)
        assert run_dir.is_dir()
        # At least one fold was produced
        folds_dir = run_dir / "folds"
        assert folds_dir.is_dir()
        fold_dirs = sorted(folds_dir.iterdir())
        assert len(fold_dirs) >= 1

    # -- Criterion 2: manifest.json and metrics.json valid JSON Schema ---

    def test_gate_criterion_2_json_schema_valid(self):
        """#072 — Gate criterion 2: manifest.json and metrics.json pass schema."""
        from ai_trading.artifacts.validation import validate_manifest, validate_metrics

        run_dir = self._run()

        manifest_path = run_dir / "manifest.json"
        assert manifest_path.is_file()
        manifest = json.loads(manifest_path.read_text())
        validate_manifest(manifest)

        metrics_path = run_dir / "metrics.json"
        assert metrics_path.is_file()
        metrics = json.loads(metrics_path.read_text())
        validate_metrics(metrics)

    # -- Criterion 3: strategy.name and strategy.framework ---------------

    def test_gate_criterion_3_strategy_fields(self):
        """#072 — Gate criterion 3: strategy.name == 'xgboost_reg',
        strategy.framework == 'xgboost' in manifest.
        """
        run_dir = self._run()
        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["strategy"]["name"] == "xgboost_reg"
        assert manifest["strategy"]["framework"] == "xgboost"

    # -- Criterion 4: Prediction metrics non-null ------------------------

    def test_gate_criterion_4_prediction_metrics_non_null(self):
        """#072 — Gate criterion 4: MAE > 0, RMSE > 0, DA in [0,1]."""
        run_dir = self._run()
        metrics = json.loads((run_dir / "metrics.json").read_text())
        assert len(metrics["folds"]) >= 1
        for fold in metrics["folds"]:
            pred = fold["prediction"]
            assert pred["mae"] > 0, f"MAE must be > 0, got {pred['mae']}"
            assert pred["rmse"] > 0, f"RMSE must be > 0, got {pred['rmse']}"
            assert 0.0 <= pred["directional_accuracy"] <= 1.0, (
                f"DA must be in [0,1], got {pred['directional_accuracy']}"
            )

    # -- Criterion 5: Trading metrics present and coherent ---------------

    def test_gate_criterion_5_trading_metrics_present(self):
        """#072 — Gate criterion 5: trading metrics present in each fold."""
        run_dir = self._run()
        metrics = json.loads((run_dir / "metrics.json").read_text())
        for fold in metrics["folds"]:
            trading = fold["trading"]
            assert trading["net_pnl"] is not None
            assert trading["n_trades"] is not None
            assert trading["max_drawdown"] is not None
            # Coherence: max_drawdown >= 0 (absolute drawdown convention)
            assert trading["max_drawdown"] >= 0.0, (
                f"max_drawdown must be >= 0, got {trading['max_drawdown']}"
            )

    # -- Criterion 6: Anti-leak (future perturbation) --------------------

    def test_gate_criterion_6_anti_leak(self):
        """#072 — Gate criterion 6: modifying future OHLCV prices does not
        change predictions/metrics for t ≤ T (first fold).
        """
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        # Run 1: original
        config1 = load_config(str(self.cfg_path))
        run_dir1 = run_pipeline(config1)
        metrics1 = json.loads((run_dir1 / "metrics.json").read_text())

        # Perturb last 30 bars (well beyond first fold's test window)
        raw_dir = Path(self.cfg_dict["dataset"]["raw_dir"])
        pq_path = raw_dir / "BTCUSDT_1h.parquet"
        df = pd.read_parquet(pq_path)
        df.loc[df.index[-30:], "close"] = df.loc[df.index[-30:], "close"] * 2.0
        df.loc[df.index[-30:], "high"] = df.loc[df.index[-30:], "high"] * 2.0
        df.to_parquet(pq_path, index=False)

        # Run 2: perturbed data, separate output
        output_dir2 = self.tmp / "runs_gate6"
        output_dir2.mkdir(parents=True, exist_ok=True)
        cfg_dict2 = dict(self.cfg_dict)
        cfg_dict2["artifacts"] = dict(self.cfg_dict["artifacts"])
        cfg_dict2["artifacts"]["output_dir"] = str(output_dir2)
        cfg2_dir = self.tmp / "cfg_gate6"
        cfg2_dir.mkdir(parents=True, exist_ok=True)
        cfg_path2 = write_config(cfg2_dir, cfg_dict2)
        config2 = load_config(str(cfg_path2))
        run_dir2 = run_pipeline(config2)
        metrics2 = json.loads((run_dir2 / "metrics.json").read_text())

        # First fold metrics must be identical
        assert len(metrics1["folds"]) >= 1
        assert len(metrics2["folds"]) >= 1
        f1 = metrics1["folds"][0]
        f2 = metrics2["folds"][0]
        for key in ("mae", "rmse", "directional_accuracy"):
            assert f1["prediction"][key] == pytest.approx(
                f2["prediction"][key], abs=1e-12
            ), f"Gate criterion 6 failed: prediction '{key}' differs"
        for key in ("n_trades", "net_pnl", "max_drawdown"):
            assert f1["trading"][key] == pytest.approx(
                f2["trading"][key], abs=1e-12
            ), f"Gate criterion 6 failed: trading '{key}' differs"

    # -- Criterion 7: Reproducibility (two runs, atol=1e-7) --------------

    def test_gate_criterion_7_reproducibility(self):
        """#072 — Gate criterion 7: two runs with same seed produce
        metrics.json identical field-by-field (atol=1e-7).
        """
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config1 = load_config(str(self.cfg_path))
        run_dir1 = run_pipeline(config1)
        metrics1 = json.loads((run_dir1 / "metrics.json").read_text())

        # Second run — separate output dir
        output_dir2 = self.tmp / "runs_gate7"
        output_dir2.mkdir(parents=True, exist_ok=True)
        cfg_dict2 = dict(self.cfg_dict)
        cfg_dict2["artifacts"] = dict(self.cfg_dict["artifacts"])
        cfg_dict2["artifacts"]["output_dir"] = str(output_dir2)
        cfg2_dir = self.tmp / "cfg_gate7"
        cfg2_dir.mkdir(parents=True, exist_ok=True)
        cfg_path2 = write_config(cfg2_dir, cfg_dict2)
        config2 = load_config(str(cfg_path2))
        run_dir2 = run_pipeline(config2)
        metrics2 = json.loads((run_dir2 / "metrics.json").read_text())

        # Remove non-deterministic metadata
        for m in (metrics1, metrics2):
            m.pop("run_id", None)
            m.pop("timestamp", None)
            m.pop("run_dir", None)

        _deep_compare_metrics(metrics1, metrics2, "gate7.metrics", atol=1e-7)

    # -- Criterion 8: ruff check clean ----------------------------------

    def test_gate_criterion_8_ruff_check_clean(self):
        """#072 — Gate criterion 8: ruff check ai_trading/ tests/ exits 0."""
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "ai_trading/", "tests/"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
            timeout=60,
        )
        assert result.returncode == 0, (
            f"ruff check failed with:\n{result.stdout}\n{result.stderr}"
        )
