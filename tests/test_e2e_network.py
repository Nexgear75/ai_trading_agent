"""End-to-end test: make run-all with real Binance download.

Mirrors the Makefile target `run-all` (fetch-data → qa → run) using
real network access to the Binance API. Marked with ``@pytest.mark.network``
so it is skipped by default (addopts = "-m 'not network'").

Run with:
    pytest -m network tests/test_e2e_network.py -v --timeout=600
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _build_e2e_config(tmp_path: Path) -> Path:
    """Build a minimal config for a fast real-data e2e run.

    Uses a very short date range (3 days) and the dummy model to keep
    the test fast while still exercising the full pipeline with real data.
    """
    raw_dir = tmp_path / "data" / "raw"
    output_dir = tmp_path / "runs"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = {
        "logging": {"level": "INFO", "format": "text", "file": "pipeline.log"},
        "dataset": {
            "exchange": "binance",
            "symbols": ["BTCUSDT"],
            "timeframe": "1h",
            "start": "2024-01-01",
            "end": "2024-02-01",  # 31 days = ~744 candles
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
            "train_days": 1,
            "test_days": 1,
            "step_days": 1,
            "val_frac_in_train": 0.2,
            "embargo_bars": 4,
            "min_samples_train": 1,
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
            "name": "dummy",
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
            "save_trades": True,
        },
    }

    cfg_path = tmp_path / "e2e_config.yaml"
    cfg_path.write_text(yaml.dump(cfg, default_flow_style=False), encoding="utf-8")
    return cfg_path


def _run_cli(command: str, config_path: Path, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a CLI subcommand via `python -m ai_trading <command> --config <path>`.

    Returns the CompletedProcess; callers should check returncode.
    """
    cmd = [
        sys.executable, "-m", "ai_trading",
        command,
        "--config", str(config_path),
    ]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=timeout,
    )


# ===========================================================================
# Tests — all marked @pytest.mark.network (skipped by default)
# ===========================================================================


@pytest.mark.network
class TestE2ERunAll:
    """End-to-end test mirroring `make run-all` with real Binance data."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp_path = tmp_path
        self.config_path = _build_e2e_config(tmp_path)
        self.raw_dir = tmp_path / "data" / "raw"
        self.output_dir = tmp_path / "runs"

    # -- Step 1: fetch-data ---------------------------------------------------

    def test_fetch_downloads_parquet(self):
        """fetch subcommand downloads real OHLCV data and writes a parquet file."""
        result = _run_cli("fetch", self.config_path)
        assert result.returncode == 0, (
            f"fetch failed (rc={result.returncode}):\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        # At least one parquet file created in raw_dir
        parquets = list(self.raw_dir.glob("*.parquet"))
        assert len(parquets) >= 1, f"No parquet files in {self.raw_dir}"

    # -- Step 2: qa -----------------------------------------------------------

    def test_qa_passes_on_real_data(self):
        """qa subcommand succeeds on freshly downloaded data."""
        fetch_result = _run_cli("fetch", self.config_path)
        assert fetch_result.returncode == 0, (
            f"fetch prerequisite failed:\n{fetch_result.stderr}"
        )

        qa_result = _run_cli("qa", self.config_path)
        assert qa_result.returncode == 0, (
            f"qa failed (rc={qa_result.returncode}):\n"
            f"STDOUT:\n{qa_result.stdout}\nSTDERR:\n{qa_result.stderr}"
        )

    # -- Step 3: run (full pipeline) ------------------------------------------

    def test_run_produces_artifacts(self):
        """run subcommand produces manifest.json and metrics.json."""
        # Pre-requisites: fetch + qa
        fetch_result = _run_cli("fetch", self.config_path)
        assert fetch_result.returncode == 0, (
            f"fetch prerequisite failed:\n{fetch_result.stderr}"
        )

        run_result = _run_cli("run", self.config_path)
        assert run_result.returncode == 0, (
            f"run failed (rc={run_result.returncode}):\n"
            f"STDOUT:\n{run_result.stdout}\nSTDERR:\n{run_result.stderr}"
        )

        # Find the run directory (should be exactly one)
        run_dirs = [d for d in self.output_dir.iterdir() if d.is_dir()]
        assert len(run_dirs) >= 1, f"No run directory in {self.output_dir}"

        run_dir = run_dirs[0]

        # manifest.json exists and is valid JSON
        manifest_path = run_dir / "manifest.json"
        assert manifest_path.is_file(), f"manifest.json not found in {run_dir}"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "pipeline_version" in manifest

        # metrics.json exists and is valid JSON
        metrics_path = run_dir / "metrics.json"
        assert metrics_path.is_file(), f"metrics.json not found in {run_dir}"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        assert "aggregated" in metrics

    # -- Full sequence (fetch → qa → run) in one shot -------------------------

    def test_full_sequence_fetch_qa_run(self):
        """Complete fetch → qa → run sequence succeeds end-to-end."""
        # 1. fetch
        r1 = _run_cli("fetch", self.config_path)
        assert r1.returncode == 0, f"fetch failed:\n{r1.stderr}"

        # 2. qa
        r2 = _run_cli("qa", self.config_path)
        assert r2.returncode == 0, f"qa failed:\n{r2.stderr}"

        # 3. run
        r3 = _run_cli("run", self.config_path)
        assert r3.returncode == 0, f"run failed:\n{r3.stderr}"

        # Verify run produced at least one fold directory
        run_dirs = [d for d in self.output_dir.iterdir() if d.is_dir()]
        assert len(run_dirs) >= 1
        run_dir = run_dirs[0]

        fold_dirs = sorted(run_dir.glob("fold_*"))
        assert len(fold_dirs) >= 1, f"No fold directories in {run_dir}"

        # Each fold has a metrics file
        for fold_dir in fold_dirs:
            fold_metrics = fold_dir / "metrics.json"
            assert fold_metrics.is_file(), f"Missing metrics in {fold_dir}"

        # config_snapshot.yaml is written
        snapshot = run_dir / "config_snapshot.yaml"
        assert snapshot.is_file(), f"config_snapshot.yaml not found in {run_dir}"

        # Stitched equity curve exists
        equity = run_dir / "equity_curve_stitched.csv"
        assert equity.is_file(), f"equity_curve_stitched.csv not in {run_dir}"
