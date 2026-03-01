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


def make_timestamps(
    n: int, freq: str = "1h", start: str = "2024-01-01"
) -> pd.Series:
    """Create a contiguous timestamp Series of *n* candles."""
    return pd.Series(pd.date_range(start=start, periods=n, freq=freq))


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
