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
