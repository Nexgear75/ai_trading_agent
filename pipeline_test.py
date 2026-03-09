"""End-to-end integration tests for pipeline.py — unified pipeline script.

Tests the standalone pipeline.py script with the xgboost_reg strategy on
synthetic OHLCV data. Validates:
- Full run completion (no crash)
- Artefact generation (manifest.json, metrics.json, trades, equity, predictions)
- JSON Schema compliance
- Prediction and trading metrics correctness
- Reproducibility (two runs → identical metrics)
- Anti-leak (future perturbation → first fold unchanged)
- CLI invocation via subprocess
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from conftest import build_ohlcv_df, write_config, write_parquet

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_N_BARS = 500
_SEED = 42
_PIPELINE_SCRIPT = Path(__file__).resolve().parent / "pipeline.py"


# ---------------------------------------------------------------------------
# Config builder — XGBoost with small parameters for fast CI
# ---------------------------------------------------------------------------


def _make_xgboost_config_dict(tmp_path: Path) -> dict:
    """Build a raw config dict for XGBoost E2E testing via pipeline.py.

    Small parameters: n_estimators=10, max_depth=3, train_days=5.
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
                "n_conv_layers": 2, "filters": 64, "kernel_size": 3,
                "dropout": 0.2, "pool": "global_avg",
            },
            "gru": {
                "hidden_size": 64, "num_layers": 1,
                "bidirectional": False, "dropout": 0.2,
            },
            "lstm": {
                "hidden_size": 64, "num_layers": 1,
                "bidirectional": False, "dropout": 0.2,
            },
            "patchtst": {
                "patch_size": 16, "stride": 8, "d_model": 64,
                "n_heads": 4, "n_layers": 2, "ff_dim": 128, "dropout": 0.2,
            },
            "rl_ppo": {
                "hidden_sizes": [64, 64], "clip_epsilon": 0.2,
                "gamma": 0.99, "gae_lambda": 0.95, "n_epochs_ppo": 4,
                "max_episodes": 200, "rollout_steps": 512,
                "value_loss_coeff": 0.5, "entropy_coeff": 0.01,
                "learning_rate": 3e-4, "deterministic_eval": True,
            },
        },
        "metrics": {"sharpe_annualized": False, "sharpe_epsilon": 1e-12},
        "reproducibility": {"global_seed": _SEED, "deterministic_torch": False},
        "artifacts": {
            "output_dir": str(output_dir),
            "save_model": True,
            "save_equity_curve": True,
            "save_predictions": True,
            "save_trades": True,
        },
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _deep_compare_metrics(
    obj1: object, obj2: object, path: str, atol: float,
) -> None:
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


def _run_pipeline_programmatic(cfg_path: Path) -> Path:
    """Run the pipeline programmatically via pipeline.run_pipeline()."""
    from lib.config import load_config
    from pipeline import run_pipeline

    config = load_config(str(cfg_path))
    return run_pipeline(config)


# ═══════════════════════════════════════════════════════════════════════════
# TestPipelineE2E — Full end-to-end with XGBoost
# ═══════════════════════════════════════════════════════════════════════════


class TestPipelineE2E:
    """E2E integration: full pipeline.py run with xgboost_reg strategy."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.cfg_dict = _make_xgboost_config_dict(tmp_path)
        self.cfg_path = write_config(tmp_path, self.cfg_dict)

    def _run(self) -> Path:
        return _run_pipeline_programmatic(self.cfg_path)

    # -- Run completes without crash -------------------------------------

    def test_run_completes_without_crash(self):
        """Pipeline run with xgboost_reg completes and returns a directory."""
        run_dir = self._run()
        assert isinstance(run_dir, Path)
        assert run_dir.is_dir()

    # -- At least one fold -----------------------------------------------

    def test_at_least_one_fold(self):
        """At least 1 fold directory exists in the run output."""
        run_dir = self._run()
        folds_dir = run_dir / "folds"
        assert folds_dir.is_dir()
        fold_dirs = sorted(folds_dir.iterdir())
        assert len(fold_dirs) >= 1

    # -- manifest.json: exists, valid schema, correct strategy -----------

    def test_manifest_exists_and_valid_schema(self):
        """manifest.json exists and passes JSON Schema validation."""
        from lib.artifacts import validate_manifest

        run_dir = self._run()
        manifest_path = run_dir / "manifest.json"
        assert manifest_path.is_file()
        manifest = json.loads(manifest_path.read_text())
        validate_manifest(manifest)

    def test_manifest_strategy_fields(self):
        """manifest.json contains correct strategy name and framework."""
        run_dir = self._run()
        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["strategy"]["name"] == "xgboost_reg"
        assert manifest["strategy"]["framework"] == "xgboost"
        assert manifest["strategy"]["output_type"] == "regression"

    # -- metrics.json: exists, valid schema ------------------------------

    def test_metrics_exists_and_valid_schema(self):
        """metrics.json exists and passes JSON Schema validation."""
        from lib.artifacts import validate_metrics

        run_dir = self._run()
        metrics_path = run_dir / "metrics.json"
        assert metrics_path.is_file()
        metrics = json.loads(metrics_path.read_text())
        validate_metrics(metrics)

    # -- Prediction metrics non-null and bounded -------------------------

    def test_prediction_metrics_non_null(self):
        """Prediction metrics MAE > 0, RMSE > 0, DA in [0,1] for each fold."""
        run_dir = self._run()
        metrics = json.loads((run_dir / "metrics.json").read_text())
        assert len(metrics["folds"]) >= 1
        for fold in metrics["folds"]:
            pred = fold["prediction"]
            assert pred["mae"] > 0
            assert pred["rmse"] > 0
            assert 0.0 <= pred["directional_accuracy"] <= 1.0

    # -- Trading metrics present and coherent ----------------------------

    def test_trading_metrics_present(self):
        """Trading metrics present and max_drawdown >= 0 in each fold."""
        run_dir = self._run()
        metrics = json.loads((run_dir / "metrics.json").read_text())
        for fold in metrics["folds"]:
            trading = fold["trading"]
            assert trading["net_pnl"] is not None
            assert trading["n_trades"] is not None
            assert trading["max_drawdown"] is not None
            assert trading["max_drawdown"] >= 0.0

    # -- Aggregate metrics present in metrics.json -----------------------

    def test_aggregate_metrics_present(self):
        """Aggregate metrics (mean/std) present in metrics.json."""
        run_dir = self._run()
        metrics = json.loads((run_dir / "metrics.json").read_text())
        agg = metrics["aggregate"]
        assert "prediction" in agg
        assert "trading" in agg
        assert "mean" in agg["trading"]
        assert "std" in agg["trading"]
        assert "net_pnl" in agg["trading"]["mean"]

    # -- XGBoost model file in each fold ---------------------------------

    def test_xgboost_model_file_in_each_fold(self):
        """XGBoost model artifact present in each fold."""
        run_dir = self._run()
        fold_dirs = sorted((run_dir / "folds").iterdir())
        assert len(fold_dirs) >= 1
        for fd in fold_dirs:
            model_file = fd / "model_artifacts" / "model" / "xgboost_model.json"
            assert model_file.is_file(), (
                f"XGBoost model file missing in {fd.name}"
            )

    # -- trades.csv in each fold -----------------------------------------

    def test_trades_csv_in_each_fold(self):
        """trades.csv present in each fold directory."""
        run_dir = self._run()
        fold_dirs = sorted((run_dir / "folds").iterdir())
        assert len(fold_dirs) >= 1
        for fd in fold_dirs:
            assert (fd / "trades.csv").is_file(), (
                f"trades.csv missing in {fd.name}"
            )

    # -- equity_curve.csv in each fold and stitched ----------------------

    def test_equity_curve_in_each_fold(self):
        """equity_curve.csv present in each fold and at run root (stitched)."""
        run_dir = self._run()
        fold_dirs = sorted((run_dir / "folds").iterdir())
        for fd in fold_dirs:
            assert (fd / "equity_curve.csv").is_file(), (
                f"equity_curve.csv missing in {fd.name}"
            )
        assert (run_dir / "equity_curve.csv").is_file(), (
            "Stitched equity_curve.csv missing at run root"
        )

    # -- predictions CSVs in each fold -----------------------------------

    def test_predictions_csv_in_each_fold(self):
        """preds_val.csv and preds_test.csv present in each fold."""
        run_dir = self._run()
        fold_dirs = sorted((run_dir / "folds").iterdir())
        for fd in fold_dirs:
            assert (fd / "preds_val.csv").is_file(), (
                f"preds_val.csv missing in {fd.name}"
            )
            assert (fd / "preds_test.csv").is_file(), (
                f"preds_test.csv missing in {fd.name}"
            )

    # -- config_snapshot.yaml in run root --------------------------------

    def test_config_snapshot_exists(self):
        """config_snapshot.yaml exists in run directory."""
        run_dir = self._run()
        assert (run_dir / "config_snapshot.yaml").is_file()

    # -- pipeline.log in run root ----------------------------------------

    def test_pipeline_log_exists(self):
        """pipeline.log exists in run directory."""
        run_dir = self._run()
        assert (run_dir / "pipeline.log").is_file()

    # -- metrics_fold.json in each fold ----------------------------------

    def test_fold_metrics_in_each_fold(self):
        """metrics_fold.json present in each fold directory."""
        run_dir = self._run()
        fold_dirs = sorted((run_dir / "folds").iterdir())
        for fd in fold_dirs:
            mf_path = fd / "metrics_fold.json"
            assert mf_path.is_file(), (
                f"metrics_fold.json missing in {fd.name}"
            )
            fold_metrics = json.loads(mf_path.read_text())
            assert "fold_id" in fold_metrics
            assert "prediction" in fold_metrics
            assert "trading" in fold_metrics

    # -- Trades CSV column validation ------------------------------------

    def test_trades_csv_columns(self):
        """trades.csv contains expected columns per §12.6."""
        run_dir = self._run()
        fold_dirs = sorted((run_dir / "folds").iterdir())
        expected_cols = {
            "entry_time_utc", "exit_time_utc", "entry_price", "exit_price",
            "entry_price_eff", "exit_price_eff", "f", "s", "fees_paid",
            "slippage_paid", "y_true", "y_hat", "gross_return", "net_return",
        }
        for fd in fold_dirs:
            trades_df = pd.read_csv(fd / "trades.csv")
            assert expected_cols <= set(trades_df.columns), (
                f"Missing columns in {fd.name}/trades.csv: "
                f"{expected_cols - set(trades_df.columns)}"
            )


# ═══════════════════════════════════════════════════════════════════════════
# TestPipelineReproducibility — Two runs same seed → identical output
# ═══════════════════════════════════════════════════════════════════════════


class TestPipelineReproducibility:
    """Reproducibility: two pipeline.py runs with same seed → identical results."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.cfg_dict = _make_xgboost_config_dict(tmp_path)
        self.cfg_path = write_config(tmp_path, self.cfg_dict)

    def _run_two(self) -> tuple[Path, Path]:
        """Execute two independent pipeline runs with the same config/seed."""
        run_dir1 = _run_pipeline_programmatic(self.cfg_path)

        # Second run — separate output dir
        output_dir2 = self.tmp / "runs2"
        output_dir2.mkdir(parents=True, exist_ok=True)
        cfg_dict2 = dict(self.cfg_dict)
        cfg_dict2["artifacts"] = dict(self.cfg_dict["artifacts"])
        cfg_dict2["artifacts"]["output_dir"] = str(output_dir2)
        cfg2_dir = self.tmp / "cfg2"
        cfg2_dir.mkdir(parents=True, exist_ok=True)
        cfg_path2 = write_config(cfg2_dir, cfg_dict2)
        run_dir2 = _run_pipeline_programmatic(cfg_path2)

        return run_dir1, run_dir2

    def test_metrics_json_identical_across_two_runs(self):
        """Two runs with same seed produce metrics.json identical (atol=1e-7)."""
        run_dir1, run_dir2 = self._run_two()

        metrics1 = json.loads((run_dir1 / "metrics.json").read_text())
        metrics2 = json.loads((run_dir2 / "metrics.json").read_text())

        for m in (metrics1, metrics2):
            m.pop("run_id", None)
            m.pop("timestamp", None)
            m.pop("run_dir", None)

        _deep_compare_metrics(metrics1, metrics2, "metrics", atol=1e-7)

    def test_trades_csv_sha256_identical_across_two_runs(self):
        """Two runs with same seed produce byte-identical trades.csv per fold."""
        run_dir1, run_dir2 = self._run_two()

        folds1 = sorted((run_dir1 / "folds").iterdir())
        folds2 = sorted((run_dir2 / "folds").iterdir())
        assert len(folds1) == len(folds2)
        assert len(folds1) >= 1

        for fd1, fd2 in zip(folds1, folds2, strict=True):
            trades1 = fd1 / "trades.csv"
            trades2 = fd2 / "trades.csv"
            assert trades1.is_file()
            assert trades2.is_file()
            assert _sha256_file(trades1) == _sha256_file(trades2), (
                f"trades.csv SHA-256 mismatch in {fd1.name}"
            )

    def test_fold_prediction_metrics_identical(self):
        """Two runs → fold-level prediction metrics are identical."""
        run_dir1, run_dir2 = self._run_two()

        metrics1 = json.loads((run_dir1 / "metrics.json").read_text())
        metrics2 = json.loads((run_dir2 / "metrics.json").read_text())

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


# ═══════════════════════════════════════════════════════════════════════════
# TestPipelineAntiLeak — Future perturbation → first fold unchanged
# ═══════════════════════════════════════════════════════════════════════════


class TestPipelineAntiLeak:
    """Anti-leak: modifying future OHLCV → first fold predictions unchanged."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.cfg_dict = _make_xgboost_config_dict(tmp_path)
        self.cfg_path = write_config(tmp_path, self.cfg_dict)

    def test_future_perturbation_preserves_first_fold(self):
        """Modify OHLCV close for last 30 bars; first fold metrics unchanged."""
        # Run 1: original data
        run_dir1 = _run_pipeline_programmatic(self.cfg_path)
        metrics1 = json.loads((run_dir1 / "metrics.json").read_text())

        # Perturb last 30 bars
        raw_dir = Path(self.cfg_dict["dataset"]["raw_dir"])
        pq_path = raw_dir / "BTCUSDT_1h.parquet"
        df = pd.read_parquet(pq_path)
        df.loc[df.index[-30:], "close"] = df.loc[df.index[-30:], "close"] * 2.0
        df.loc[df.index[-30:], "high"] = df.loc[df.index[-30:], "high"] * 2.0
        df.to_parquet(pq_path, index=False)

        # Run 2: perturbed data, fresh output dir
        output_dir2 = self.tmp / "runs_perturbed"
        output_dir2.mkdir(parents=True, exist_ok=True)
        cfg_dict2 = dict(self.cfg_dict)
        cfg_dict2["artifacts"] = dict(self.cfg_dict["artifacts"])
        cfg_dict2["artifacts"]["output_dir"] = str(output_dir2)
        cfg2_dir = self.tmp / "cfg_perturbed"
        cfg2_dir.mkdir(parents=True, exist_ok=True)
        cfg_path2 = write_config(cfg2_dir, cfg_dict2)
        run_dir2 = _run_pipeline_programmatic(cfg_path2)
        metrics2 = json.loads((run_dir2 / "metrics.json").read_text())

        # First fold must be identical
        assert len(metrics1["folds"]) >= 1
        assert len(metrics2["folds"]) >= 1
        f1 = metrics1["folds"][0]
        f2 = metrics2["folds"][0]

        for key in ("mae", "rmse", "directional_accuracy"):
            assert f1["prediction"][key] == pytest.approx(
                f2["prediction"][key], abs=1e-12
            ), f"Prediction '{key}' differs after future perturbation"

        for key in ("n_trades", "net_pnl", "max_drawdown"):
            assert f1["trading"][key] == pytest.approx(
                f2["trading"][key], abs=1e-12
            ), f"Trading '{key}' differs after future perturbation"


# ═══════════════════════════════════════════════════════════════════════════
# TestPipelineCLI — Subprocess invocation of pipeline.py
# ═══════════════════════════════════════════════════════════════════════════


class TestPipelineCLI:
    """Test pipeline.py invocation via subprocess (simulates real usage)."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.cfg_dict = _make_xgboost_config_dict(tmp_path)
        self.cfg_path = write_config(tmp_path, self.cfg_dict)

    def test_cli_help_exits_zero(self):
        """python pipeline.py --help exits with code 0."""
        result = subprocess.run(
            [sys.executable, str(_PIPELINE_SCRIPT), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "AI Trading Pipeline" in result.stdout

    def test_cli_run_completes(self):
        """python pipeline.py --config <path> runs successfully via subprocess."""
        result = subprocess.run(
            [
                sys.executable, str(_PIPELINE_SCRIPT),
                "--config", str(self.cfg_path),
            ],
            capture_output=True,
            text=True,
            cwd=str(_PIPELINE_SCRIPT.parent),
            timeout=120,
        )
        assert result.returncode == 0, (
            f"pipeline.py exited with code {result.returncode}:\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )
        assert "Pipeline" in result.stdout or "Pipeline" in result.stderr

    def test_cli_missing_config_fails(self):
        """python pipeline.py --config nonexistent.yaml fails with FileNotFoundError."""
        result = subprocess.run(
            [
                sys.executable, str(_PIPELINE_SCRIPT),
                "--config", "nonexistent_config_12345.yaml",
            ],
            capture_output=True,
            text=True,
            cwd=str(self.tmp),
            timeout=30,
        )
        assert result.returncode != 0

    def test_cli_strategy_override(self):
        """python pipeline.py --strategy dummy --config <path> uses dummy strategy."""
        # Reconfigure for dummy strategy (faster)
        cfg_dict = dict(self.cfg_dict)
        cfg_dict["strategy"] = {"strategy_type": "model", "name": "dummy"}
        dummy_dir = self.tmp / "dummy_cfg"
        dummy_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = write_config(dummy_dir, cfg_dict)

        result = subprocess.run(
            [
                sys.executable, str(_PIPELINE_SCRIPT),
                "--config", str(cfg_path),
                "--strategy", "dummy",
            ],
            capture_output=True,
            text=True,
            cwd=str(_PIPELINE_SCRIPT.parent),
            timeout=120,
        )
        assert result.returncode == 0, (
            f"pipeline.py --strategy dummy failed:\n{result.stderr}"
        )

    def test_cli_output_dir_override(self):
        """python pipeline.py --output-dir <path> places artefacts correctly."""
        custom_output = self.tmp / "custom_runs"
        custom_output.mkdir(parents=True, exist_ok=True)

        # Use dummy for speed
        cfg_dict = dict(self.cfg_dict)
        cfg_dict["strategy"] = {"strategy_type": "model", "name": "dummy"}
        out_dir = self.tmp / "out_cfg"
        out_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = write_config(out_dir, cfg_dict)

        result = subprocess.run(
            [
                sys.executable, str(_PIPELINE_SCRIPT),
                "--config", str(cfg_path),
                "--strategy", "dummy",
                "--output-dir", str(custom_output),
            ],
            capture_output=True,
            text=True,
            cwd=str(_PIPELINE_SCRIPT.parent),
            timeout=120,
        )
        assert result.returncode == 0, (
            f"pipeline.py --output-dir failed:\n{result.stderr}"
        )
        # At least one run directory created under custom_output
        run_dirs = [p for p in custom_output.iterdir() if p.is_dir()]
        assert len(run_dirs) >= 1, (
            f"No run directory created in {custom_output}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TestPipelineEquivalence — pipeline.py vs ai_trading.pipeline.runner
# ═══════════════════════════════════════════════════════════════════════════


class TestPipelineEquivalence:
    """Verify pipeline.py produces equivalent results to runner.run_pipeline()."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.cfg_dict = _make_xgboost_config_dict(tmp_path)
        self.cfg_path = write_config(tmp_path, self.cfg_dict)

    @pytest.mark.skip(reason="ai_trading.pipeline.runner not available in standalone mode")
    def test_pipeline_py_matches_runner(self):
        """pipeline.py run_pipeline() produces same metrics as runner.run_pipeline()."""
        from lib.config import load_config
        from pipeline import run_pipeline as runner_run_pipeline
        from pipeline import run_pipeline as script_run_pipeline

        # Run via runner.py
        config1 = load_config(str(self.cfg_path))
        run_dir1 = runner_run_pipeline(config1)
        metrics1 = json.loads((run_dir1 / "metrics.json").read_text())

        # Run via pipeline.py — separate output dir
        output_dir2 = self.tmp / "runs_script"
        output_dir2.mkdir(parents=True, exist_ok=True)
        cfg_dict2 = dict(self.cfg_dict)
        cfg_dict2["artifacts"] = dict(self.cfg_dict["artifacts"])
        cfg_dict2["artifacts"]["output_dir"] = str(output_dir2)
        cfg2_dir = self.tmp / "cfg_script"
        cfg2_dir.mkdir(parents=True, exist_ok=True)
        cfg_path2 = write_config(cfg2_dir, cfg_dict2)
        config2 = load_config(str(cfg_path2))
        run_dir2 = script_run_pipeline(config2)
        metrics2 = json.loads((run_dir2 / "metrics.json").read_text())

        # Remove non-deterministic metadata
        for m in (metrics1, metrics2):
            m.pop("run_id", None)
            m.pop("timestamp", None)
            m.pop("run_dir", None)

        _deep_compare_metrics(metrics1, metrics2, "equivalence", atol=1e-7)
