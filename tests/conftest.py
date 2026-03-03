"""Shared pytest fixtures for the AI Trading test suite."""

import importlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from ai_trading.features.registry import FEATURE_REGISTRY

# Absolute path to the project root (parent of tests/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Config fixtures (M-1: factored from test_config.py / test_config_validation.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def default_config_path():
    """Absolute path to the default YAML config."""
    return PROJECT_ROOT / "configs" / "default.yaml"


@pytest.fixture
def default_config(default_config_path):
    """Load the default pipeline config via shared fixture path."""
    from ai_trading.config import load_config

    return load_config(str(default_config_path))


@pytest.fixture
def default_yaml_data(default_config_path):
    """Load the raw dict from configs/default.yaml for reuse."""
    with open(default_config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def tmp_yaml(tmp_path):
    """Factory fixture: write a dict to a temp YAML file and return its path."""

    def _write(data: dict, name: str = "cfg.yaml") -> str:
        p = tmp_path / name
        p.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
        return str(p)

    return _write


# ---------------------------------------------------------------------------
# OHLCV builder helpers (M-8: shared across feature test files)
# ---------------------------------------------------------------------------


def make_ohlcv_from_close(close_values) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame from close values.

    open/high/low are set equal to close; volume = 1.0.
    Index is hourly DatetimeIndex starting 2024-01-01.
    """
    n = len(close_values)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="1h")
    close = np.array(close_values, dtype=np.float64)
    return pd.DataFrame(
        {
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": np.ones(n, dtype=np.float64),
        },
        index=timestamps,
    )


def make_ohlcv_random(
    n_bars: int,
    seed: int = 42,
    start: str = "2023-01-01",
    tz: str | None = None,
) -> pd.DataFrame:
    """Create a synthetic OHLCV DataFrame with *n_bars* rows and random data."""
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range(start, periods=n_bars, freq="h", tz=tz)
    close = 100.0 + np.cumsum(rng.standard_normal(n_bars) * 0.5)
    close = np.abs(close) + 1.0
    high_delta = rng.uniform(0, 1, n_bars)
    low_delta = rng.uniform(0, 1, n_bars)
    open_ = close + rng.uniform(-0.5, 0.5, n_bars)
    high = np.maximum(open_, close) + high_delta
    low = np.minimum(open_, close) - low_delta
    volume = rng.uniform(100, 10000, n_bars)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=timestamps,
    )


# ---------------------------------------------------------------------------
# Shared helpers — timestamps
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# OHLCV builder — calibration & label tests (M-3, M-4)
# ---------------------------------------------------------------------------


def make_calibration_ohlcv(
    n: int,
    seed: int = 42,
    start: str = "2024-01-01",
) -> pd.DataFrame:
    """Synthetic OHLCV with deterministic prices for calibration & label tests.

    Produces distinct open/close values with positive prices.
    Used by test_theta_optimization, test_theta_bypass, test_label_target.
    """
    idx = pd.date_range(start, periods=n, freq="1h")
    rng = np.random.default_rng(seed)
    close = 100.0 + np.cumsum(rng.standard_normal(n) * 0.5)
    close = np.abs(close) + 50.0
    opens = close + rng.standard_normal(n) * 0.1
    opens = np.abs(opens) + 50.0
    return pd.DataFrame(
        {
            "open": opens,
            "high": np.maximum(opens, close) + 0.5,
            "low": np.minimum(opens, close) - 0.5,
            "close": close,
            "volume": rng.uniform(100, 1000, n),
        },
        index=idx,
    )


def make_timestamps(
    n: int, freq: str = "1h", start: str = "2024-01-01"
) -> pd.Series:
    """Create a contiguous timestamp Series of *n* candles."""
    return pd.Series(pd.date_range(start=start, periods=n, freq=freq))


# ---------------------------------------------------------------------------
# OHLCV builder — QA tests (W-1: requires timestamp_utc column, tz-aware UTC)
# ---------------------------------------------------------------------------


def make_ohlcv_for_qa(
    n: int = 10,
    timeframe: str = "1h",
    start: str = "2024-01-01",
) -> pd.DataFrame:
    """Create a clean synthetic OHLCV DataFrame for QA tests.

    Returns a DataFrame with ``timestamp_utc`` column (tz-aware UTC),
    and columns open/high/low/close/volume with deterministic values.
    This format matches the expected input of ``run_qa_checks``.
    """
    freq_map = {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1h",
        "4h": "4h",
        "1d": "1D",
    }
    freq = freq_map[timeframe]
    timestamps = pd.date_range(start=start, periods=n, freq=freq, tz="UTC")
    return pd.DataFrame({
        "timestamp_utc": timestamps,
        "open": [100.0 + i for i in range(n)],
        "high": [105.0 + i for i in range(n)],
        "low": [95.0 + i for i in range(n)],
        "close": [102.0 + i for i in range(n)],
        "volume": [1000.0 + i * 10 for i in range(n)],
    })


# ---------------------------------------------------------------------------
# OHLCV builder — volume feature tests (W-1: custom volume, constant prices)
# ---------------------------------------------------------------------------


def make_ohlcv_with_volume(volume_values) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame with custom volume values.

    close/open/high/low are set to 100.0; volume comes from *volume_values*.
    Index is hourly DatetimeIndex starting 2024-01-01.
    """
    n = len(volume_values)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="1h")
    vol = np.array(volume_values, dtype=np.float64)
    close = np.full(n, 100.0, dtype=np.float64)
    return pd.DataFrame(
        {
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": vol,
        },
        index=timestamps,
    )


# ---------------------------------------------------------------------------
# Features/labels builders (W-2: shared across sample_builder & warmup tests)
# ---------------------------------------------------------------------------


def make_features_df(
    n_bars: int,
    n_features: int = 3,
    seed: int = 42,
    nan_prefix: int = 0,
) -> pd.DataFrame:
    """Create a synthetic features DataFrame with known values.

    Parameters
    ----------
    n_bars : int
        Number of rows.
    n_features : int
        Number of feature columns.
    seed : int
        Random seed for reproducibility.
    nan_prefix : int
        If > 0, the first *nan_prefix* rows will be NaN.
    """
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range("2024-01-01", periods=n_bars, freq="1h")
    data = rng.standard_normal((n_bars, n_features))
    if nan_prefix > 0:
        data[:nan_prefix, :] = np.nan
    columns = [f"feat_{i}" for i in range(n_features)]
    return pd.DataFrame(data, index=timestamps, columns=columns)


def make_labels(n_bars: int, seed: int = 99) -> np.ndarray:
    """Create synthetic label values (float64)."""
    rng = np.random.default_rng(seed)
    return rng.standard_normal(n_bars).astype(np.float64)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rng():
    """Seeded RNG for deterministic test data."""
    return np.random.default_rng(42)


# ---------------------------------------------------------------------------
# Feature registry fixture (M-2: standardized across feature test files)
# ---------------------------------------------------------------------------


def clean_registry_with_reload(*modules):
    """Factory: create a pytest fixture that saves, clears, reloads, and restores
    FEATURE_REGISTRY around each test.

    Parameters
    ----------
    *modules : module
        Feature modules to reload after clearing (to re-run @register_feature).

    Returns
    -------
    A pytest fixture function.
    """

    @pytest.fixture(autouse=True)
    def _fixture():
        saved = dict(FEATURE_REGISTRY)
        FEATURE_REGISTRY.clear()
        for mod in modules:
            importlib.reload(mod)
        yield
        FEATURE_REGISTRY.clear()
        FEATURE_REGISTRY.update(saved)

    return _fixture


# ---------------------------------------------------------------------------
# Synthetic OHLCV fixture — geometric Brownian motion (task #051)
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_ohlcv() -> pd.DataFrame:
    """Generate a synthetic OHLCV dataset using geometric Brownian motion.

    #051 — 500 candles, no network dependency, columns conforming to §4.1:
    open, high, low, close, volume + timestamp_utc (UTC-aware).
    """
    n = 500
    seed = 42
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")

    # Geometric Brownian motion: S(t+1) = S(t) * exp((mu - sigma^2/2)*dt + sigma*sqrt(dt)*Z)
    s0 = 100.0
    mu = 0.0001  # drift per step
    sigma = 0.01  # volatility per step
    dt = 1.0
    z = rng.standard_normal(n - 1)
    log_returns = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z
    log_prices = np.concatenate([[np.log(s0)], np.log(s0) + np.cumsum(log_returns)])
    close = np.exp(log_prices)

    # Generate open/high/low around close
    open_ = close * (1.0 + rng.uniform(-0.002, 0.002, n))
    high = np.maximum(open_, close) * (1.0 + rng.uniform(0.0005, 0.005, n))
    low = np.minimum(open_, close) * (1.0 - rng.uniform(0.0005, 0.005, n))
    volume = rng.uniform(100.0, 10000.0, n)

    return pd.DataFrame(
        {
            "timestamp_utc": timestamps,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
    )


# ---------------------------------------------------------------------------
# Integration helpers — shared config builder (tasks #051, #054)
# ---------------------------------------------------------------------------


def write_integration_parquet(
    ohlcv_df: pd.DataFrame, raw_dir: Path, symbol: str,
) -> None:
    """Write OHLCV DataFrame to parquet matching the ingestion convention."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{symbol}_1h.parquet"
    ohlcv_df.to_parquet(path, index=False)


def make_integration_config(
    tmp_path: Path,
    ohlcv_df: pd.DataFrame,
    *,
    strategy_name: str = "dummy",
    strategy_type: str = "model",
    seed: int = 42,
) -> Path:
    """Build a YAML config for integration / gate testing and return its path.

    Uses short windows and few folds to keep tests fast.
    """
    raw_dir = tmp_path / "data" / "raw"
    output_dir = tmp_path / "runs"
    output_dir.mkdir(parents=True, exist_ok=True)

    write_integration_parquet(ohlcv_df, raw_dir, "BTCUSDT")

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
        "reproducibility": {"global_seed": seed, "deterministic_torch": False},
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
