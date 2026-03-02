"""Tests for SmaRuleBaseline — Task #039 (WS-9).

Covers:
- Inheritance from BaseModel, output_type, execution_mode
- fit() is a no-op returning empty dict
- predict() computes SMA via rolling().mean() on ohlcv["close"]
- Signal logic: Go (1) when SMA_fast > SMA_slow, No-Go (0) otherwise
- First decisions: SMA_slow undefined → No-Go
- Temporal alignment via meta['decision_time']
- Config-driven: fast/slow from baselines.sma.fast / baselines.sma.slow
- Validation: fast < slow enforced with raise
- Causality: modifying future prices does not change past signals
- save()/load() roundtrip
- Registry: "sma_rule" resolves via get_model_class
- Edge cases
"""

from __future__ import annotations

import importlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ai_trading.models.base import MODEL_REGISTRY, BaseModel, get_model_class

# ---------------------------------------------------------------------------
# Registry cleanup fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_model_registry():
    """Save, clear, and restore MODEL_REGISTRY around each test."""
    saved = dict(MODEL_REGISTRY)
    MODEL_REGISTRY.clear()
    yield
    MODEL_REGISTRY.clear()
    MODEL_REGISTRY.update(saved)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RNG = np.random.default_rng(999)
_N, _L, _F = 60, 5, 3
_X = _RNG.standard_normal((_N, _L, _F)).astype(np.float32)
_Y = _RNG.standard_normal((_N,)).astype(np.float32)
_X_VAL = _RNG.standard_normal((10, _L, _F)).astype(np.float32)
_Y_VAL = _RNG.standard_normal((10,)).astype(np.float32)


def _import_sma_rule():
    """Import the sma_rule module to trigger registration."""
    import ai_trading.baselines.sma_rule as mod

    MODEL_REGISTRY.pop("sma_rule", None)
    importlib.reload(mod)
    return mod.SmaRuleBaseline


def _make_ohlcv(close_prices: np.ndarray, freq: str = "1h") -> pd.DataFrame:
    """Build an OHLCV DataFrame from close prices."""
    n = len(close_prices)
    idx = pd.date_range("2024-01-01", periods=n, freq=freq)
    return pd.DataFrame(
        {
            "open": close_prices + 0.1,
            "high": close_prices + 1.0,
            "low": close_prices - 1.0,
            "close": close_prices,
            "volume": np.full(n, 1000.0),
        },
        index=idx,
    )


def _make_meta(ohlcv: pd.DataFrame, sample_indices: np.ndarray) -> dict:
    """Build meta dict with decision_time aligned to the given sample indices."""
    return {"decision_time": ohlcv.index[sample_indices]}


def _make_config(fast: int = 20, slow: int = 50):
    """Build a minimal mock config with baselines.sma.fast/slow."""

    class SmaConf:
        def __init__(self, fast: int, slow: int):
            self.fast = fast
            self.slow = slow

    class BaselinesConf:
        def __init__(self, fast: int, slow: int):
            self.sma = SmaConf(fast, slow)

    class Config:
        def __init__(self, fast: int, slow: int):
            self.baselines = BaselinesConf(fast, slow)

    return Config(fast, slow)


# ---------------------------------------------------------------------------
# Tests — Class attributes & inheritance
# ---------------------------------------------------------------------------


class TestSmaRuleAttributes:
    """#039 — SmaRuleBaseline class attributes and inheritance."""

    def test_inherits_base_model(self):
        """SmaRuleBaseline must be a subclass of BaseModel."""
        cls = _import_sma_rule()
        assert issubclass(cls, BaseModel)

    def test_output_type_is_signal(self):
        """output_type must be 'signal'."""
        cls = _import_sma_rule()
        assert cls.output_type == "signal"

    def test_execution_mode_is_standard(self):
        """execution_mode must be 'standard'."""
        cls = _import_sma_rule()
        assert cls.execution_mode == "standard"


# ---------------------------------------------------------------------------
# Tests — Registry
# ---------------------------------------------------------------------------


class TestSmaRuleRegistry:
    """#039 — sma_rule must be resolvable via get_model_class."""

    def test_registered_in_model_registry(self):
        _import_sma_rule()
        assert "sma_rule" in MODEL_REGISTRY

    def test_get_model_class_resolves(self):
        cls = _import_sma_rule()
        assert get_model_class("sma_rule") is cls


# ---------------------------------------------------------------------------
# Tests — fit() is no-op
# ---------------------------------------------------------------------------


class TestSmaRuleFit:
    """#039 — fit() must be a no-op."""

    def test_fit_returns_empty_dict(self, tmp_path):
        cls = _import_sma_rule()
        model = cls()
        config = _make_config(fast=20, slow=50)
        result = model.fit(
            X_train=_X,
            y_train=_Y,
            X_val=_X_VAL,
            y_val=_Y_VAL,
            config=config,
            run_dir=tmp_path,
        )
        assert result == {}


# ---------------------------------------------------------------------------
# Tests — predict() signal logic
# ---------------------------------------------------------------------------


class TestSmaRulePredict:
    """#039 — predict() must compute SMA crossover signals."""

    def test_uptrend_produces_go_signals(self):
        """Steady uptrend: after warmup, SMA_fast > SMA_slow → Go (1)."""
        cls = _import_sma_rule()
        model = cls()
        config = _make_config(fast=5, slow=10)
        model.fit(
            X_train=_X[:10], y_train=_Y[:10],
            X_val=_X_VAL, y_val=_Y_VAL,
            config=config, run_dir=Path("/tmp/unused"),
        )

        # Strong uptrend: SMA_fast will be above SMA_slow after warmup
        n = 100
        close = np.linspace(100, 200, n)
        ohlcv = _make_ohlcv(close)
        # Use last 20 bars as samples (well after warmup of slow=10)
        sample_idx = np.arange(80, 100)
        x_dummy = _RNG.standard_normal((len(sample_idx), _L, _F)).astype(np.float32)
        meta = _make_meta(ohlcv, sample_idx)

        signals = model.predict(x_dummy, meta=meta, ohlcv=ohlcv)
        assert signals.dtype == np.float32
        assert signals.shape == (len(sample_idx),)
        # All should be Go (1) in strong uptrend after warmup
        np.testing.assert_array_equal(signals, np.ones(len(sample_idx), dtype=np.float32))

    def test_downtrend_produces_nogo_signals(self):
        """Steady downtrend: SMA_fast < SMA_slow → No-Go (0)."""
        cls = _import_sma_rule()
        model = cls()
        config = _make_config(fast=5, slow=10)
        model.fit(
            X_train=_X[:10], y_train=_Y[:10],
            X_val=_X_VAL, y_val=_Y_VAL,
            config=config, run_dir=Path("/tmp/unused"),
        )

        n = 100
        close = np.linspace(200, 100, n)  # downtrend
        ohlcv = _make_ohlcv(close)
        sample_idx = np.arange(80, 100)
        x_dummy = _RNG.standard_normal((len(sample_idx), _L, _F)).astype(np.float32)
        meta = _make_meta(ohlcv, sample_idx)

        signals = model.predict(x_dummy, meta=meta, ohlcv=ohlcv)
        assert signals.dtype == np.float32
        # All should be No-Go (0) in steady downtrend
        np.testing.assert_array_equal(signals, np.zeros(len(sample_idx), dtype=np.float32))

    def test_first_decisions_nogo_when_sma_slow_undefined(self):
        """Before slow window is complete, signal must be No-Go (0)."""
        cls = _import_sma_rule()
        model = cls()
        config = _make_config(fast=5, slow=10)
        model.fit(
            X_train=_X[:10], y_train=_Y[:10],
            X_val=_X_VAL, y_val=_Y_VAL,
            config=config, run_dir=Path("/tmp/unused"),
        )

        n = 100
        close = np.linspace(100, 200, n)  # uptrend
        ohlcv = _make_ohlcv(close)
        # Indices within warmup of slow (indices 0..8 → SMA_slow is NaN)
        sample_idx = np.arange(0, 9)
        x_dummy = _RNG.standard_normal((len(sample_idx), _L, _F)).astype(np.float32)
        meta = _make_meta(ohlcv, sample_idx)

        signals = model.predict(x_dummy, meta=meta, ohlcv=ohlcv)
        np.testing.assert_array_equal(signals, np.zeros(len(sample_idx), dtype=np.float32))

    def test_signal_shape_and_dtype(self):
        """Signal must be float32 of shape (N,)."""
        cls = _import_sma_rule()
        model = cls()
        config = _make_config(fast=5, slow=10)
        model.fit(
            X_train=_X[:10], y_train=_Y[:10],
            X_val=_X_VAL, y_val=_Y_VAL,
            config=config, run_dir=Path("/tmp/unused"),
        )

        n = 60
        close = np.linspace(100, 200, n)
        ohlcv = _make_ohlcv(close)
        sample_idx = np.arange(20, 60)
        x_dummy = _RNG.standard_normal((len(sample_idx), _L, _F)).astype(np.float32)
        meta = _make_meta(ohlcv, sample_idx)

        signals = model.predict(x_dummy, meta=meta, ohlcv=ohlcv)
        assert signals.dtype == np.float32
        assert signals.shape == (len(sample_idx),)

    def test_signals_are_binary(self):
        """All signals must be 0.0 or 1.0."""
        cls = _import_sma_rule()
        model = cls()
        config = _make_config(fast=5, slow=10)
        model.fit(
            X_train=_X[:10], y_train=_Y[:10],
            X_val=_X_VAL, y_val=_Y_VAL,
            config=config, run_dir=Path("/tmp/unused"),
        )

        n = 100
        rng = np.random.default_rng(42)
        close = 100 + np.cumsum(rng.standard_normal(n) * 2)
        ohlcv = _make_ohlcv(close)
        sample_idx = np.arange(10, 100)
        x_dummy = _RNG.standard_normal((len(sample_idx), _L, _F)).astype(np.float32)
        meta = _make_meta(ohlcv, sample_idx)

        signals = model.predict(x_dummy, meta=meta, ohlcv=ohlcv)
        assert set(np.unique(signals)).issubset({0.0, 1.0})

    def test_temporal_alignment_via_meta(self):
        """predict() must return signals only for timestamps in meta['decision_time']."""
        cls = _import_sma_rule()
        model = cls()
        config = _make_config(fast=5, slow=10)
        model.fit(
            X_train=_X[:10], y_train=_Y[:10],
            X_val=_X_VAL, y_val=_Y_VAL,
            config=config, run_dir=Path("/tmp/unused"),
        )

        n = 60
        close = np.linspace(100, 200, n)
        ohlcv = _make_ohlcv(close)
        # Select non-contiguous indices
        sample_idx = np.array([15, 25, 35, 45, 55])
        x_dummy = _RNG.standard_normal((len(sample_idx), _L, _F)).astype(np.float32)
        meta = _make_meta(ohlcv, sample_idx)

        signals = model.predict(x_dummy, meta=meta, ohlcv=ohlcv)
        assert signals.shape == (len(sample_idx),)

    def test_equal_sma_produces_nogo(self):
        """When SMA_fast == SMA_slow exactly, signal must be No-Go (0).

        Condition is strict: Go only when SMA_fast > SMA_slow.
        """
        cls = _import_sma_rule()
        model = cls()
        config = _make_config(fast=5, slow=10)
        model.fit(
            X_train=_X[:10], y_train=_Y[:10],
            X_val=_X_VAL, y_val=_Y_VAL,
            config=config, run_dir=Path("/tmp/unused"),
        )

        # Constant prices → SMA_fast == SMA_slow at all points after warmup
        n = 60
        close = np.full(n, 100.0)
        ohlcv = _make_ohlcv(close)
        sample_idx = np.arange(10, 60)
        x_dummy = _RNG.standard_normal((len(sample_idx), _L, _F)).astype(np.float32)
        meta = _make_meta(ohlcv, sample_idx)

        signals = model.predict(x_dummy, meta=meta, ohlcv=ohlcv)
        np.testing.assert_array_equal(signals, np.zeros(len(sample_idx), dtype=np.float32))


# ---------------------------------------------------------------------------
# Tests — Config-driven & validation
# ---------------------------------------------------------------------------


class TestSmaRuleConfig:
    """#039 — Config-driven parameters and validation."""

    def test_fast_slow_from_config(self):
        """Model must read fast/slow from config.baselines.sma."""
        cls = _import_sma_rule()
        model = cls()
        config_3_7 = _make_config(fast=3, slow=7)
        model.fit(
            X_train=_X[:10], y_train=_Y[:10],
            X_val=_X_VAL, y_val=_Y_VAL,
            config=config_3_7, run_dir=Path("/tmp/unused"),
        )

        # With fast=3, slow=7, uptrend: check that signal is Go after bar 6 (0-indexed)
        n = 30
        close = np.linspace(100, 200, n)
        ohlcv = _make_ohlcv(close)
        sample_idx = np.arange(7, 30)
        x_dummy = _RNG.standard_normal((len(sample_idx), _L, _F)).astype(np.float32)
        meta = _make_meta(ohlcv, sample_idx)

        signals = model.predict(x_dummy, meta=meta, ohlcv=ohlcv)
        # Strong uptrend → all Go after slow warmup
        np.testing.assert_array_equal(signals, np.ones(len(sample_idx), dtype=np.float32))

    def test_validation_fast_ge_slow_raises(self):
        """fast >= slow must raise ValueError."""
        cls = _import_sma_rule()
        model = cls()
        config_bad = _make_config(fast=50, slow=20)
        with pytest.raises(ValueError, match="fast.*slow"):
            model.fit(
                X_train=_X[:10], y_train=_Y[:10],
                X_val=_X_VAL, y_val=_Y_VAL,
                config=config_bad, run_dir=Path("/tmp/unused"),
            )

    def test_validation_fast_eq_slow_raises(self):
        """fast == slow must raise ValueError."""
        cls = _import_sma_rule()
        model = cls()
        config_eq = _make_config(fast=20, slow=20)
        with pytest.raises(ValueError, match="fast.*slow"):
            model.fit(
                X_train=_X[:10], y_train=_Y[:10],
                X_val=_X_VAL, y_val=_Y_VAL,
                config=config_eq, run_dir=Path("/tmp/unused"),
            )


# ---------------------------------------------------------------------------
# Tests — Causality
# ---------------------------------------------------------------------------


class TestSmaRuleCausality:
    """#039 — Causality: modifying future prices must not change past signals."""

    def test_future_modification_does_not_affect_past(self):
        """Modify prices after bar T; signals for t <= T must be identical."""
        cls = _import_sma_rule()

        n = 100
        close_original = np.linspace(100, 200, n)
        ohlcv_original = _make_ohlcv(close_original.copy())

        # Modified version: perturb prices after bar 60
        close_modified = close_original.copy()
        close_modified[61:] = 50.0  # drastic change
        ohlcv_modified = _make_ohlcv(close_modified)

        config = _make_config(fast=5, slow=10)

        # Model A on original
        model_a = cls()
        model_a.fit(
            X_train=_X[:10], y_train=_Y[:10],
            X_val=_X_VAL, y_val=_Y_VAL,
            config=config, run_dir=Path("/tmp/unused"),
        )
        sample_idx = np.arange(10, 61)  # up to and including bar 60
        x_dummy = _RNG.standard_normal((len(sample_idx), _L, _F)).astype(np.float32)
        meta_a = _make_meta(ohlcv_original, sample_idx)
        signals_a = model_a.predict(x_dummy, meta=meta_a, ohlcv=ohlcv_original)

        # Model B on modified
        model_b = cls()
        model_b.fit(
            X_train=_X[:10], y_train=_Y[:10],
            X_val=_X_VAL, y_val=_Y_VAL,
            config=config, run_dir=Path("/tmp/unused"),
        )
        meta_b = _make_meta(ohlcv_modified, sample_idx)
        signals_b = model_b.predict(x_dummy, meta=meta_b, ohlcv=ohlcv_modified)

        np.testing.assert_array_equal(signals_a, signals_b)


# ---------------------------------------------------------------------------
# Tests — save/load roundtrip
# ---------------------------------------------------------------------------


class TestSmaRulePersistence:
    """#039 — save()/load() must roundtrip (stateless baseline)."""

    def test_save_load_roundtrip_directory(self, tmp_path):
        cls = _import_sma_rule()
        model = cls()
        model.save(tmp_path)

        model2 = cls()
        model2.load(tmp_path)  # should not raise

    def test_save_load_roundtrip_file(self, tmp_path):
        cls = _import_sma_rule()
        model = cls()
        filepath = tmp_path / "sma_baseline.json"
        model.save(filepath)
        assert filepath.exists()

        model2 = cls()
        model2.load(filepath)

    def test_load_nonexistent_raises(self, tmp_path):
        cls = _import_sma_rule()
        model = cls()
        with pytest.raises(FileNotFoundError):
            model.load(tmp_path / "nonexistent.json")


# ---------------------------------------------------------------------------
# Tests — Edge cases
# ---------------------------------------------------------------------------


class TestSmaRuleEdgeCases:
    """#039 — Edge cases and boundary conditions."""

    def test_predict_requires_ohlcv(self):
        """predict() without ohlcv must raise."""
        cls = _import_sma_rule()
        model = cls()
        config = _make_config(fast=5, slow=10)
        model.fit(
            X_train=_X[:10], y_train=_Y[:10],
            X_val=_X_VAL, y_val=_Y_VAL,
            config=config, run_dir=Path("/tmp/unused"),
        )
        x_dummy = _RNG.standard_normal((5, _L, _F)).astype(np.float32)
        with pytest.raises((ValueError, TypeError)):
            model.predict(x_dummy)

    def test_predict_requires_meta(self):
        """predict() without meta must raise."""
        cls = _import_sma_rule()
        model = cls()
        config = _make_config(fast=5, slow=10)
        model.fit(
            X_train=_X[:10], y_train=_Y[:10],
            X_val=_X_VAL, y_val=_Y_VAL,
            config=config, run_dir=Path("/tmp/unused"),
        )
        n = 30
        close = np.linspace(100, 200, n)
        ohlcv = _make_ohlcv(close)
        x_dummy = _RNG.standard_normal((5, _L, _F)).astype(np.float32)
        with pytest.raises((ValueError, TypeError)):
            model.predict(x_dummy, ohlcv=ohlcv)

    def test_predict_without_fit_raises(self):
        """predict() before fit() must raise (config not set)."""
        cls = _import_sma_rule()
        model = cls()
        n = 30
        close = np.linspace(100, 200, n)
        ohlcv = _make_ohlcv(close)
        sample_idx = np.arange(10, 30)
        x_dummy = _RNG.standard_normal((len(sample_idx), _L, _F)).astype(np.float32)
        meta = _make_meta(ohlcv, sample_idx)
        with pytest.raises((ValueError, AttributeError, RuntimeError)):
            model.predict(x_dummy, meta=meta, ohlcv=ohlcv)

    def test_single_sample(self):
        """predict() with a single sample must work."""
        cls = _import_sma_rule()
        model = cls()
        config = _make_config(fast=5, slow=10)
        model.fit(
            X_train=_X[:10], y_train=_Y[:10],
            X_val=_X_VAL, y_val=_Y_VAL,
            config=config, run_dir=Path("/tmp/unused"),
        )

        n = 60
        close = np.linspace(100, 200, n)
        ohlcv = _make_ohlcv(close)
        sample_idx = np.array([50])
        x_dummy = _RNG.standard_normal((1, _L, _F)).astype(np.float32)
        meta = _make_meta(ohlcv, sample_idx)

        signals = model.predict(x_dummy, meta=meta, ohlcv=ohlcv)
        assert signals.shape == (1,)
        assert signals.dtype == np.float32


# ---------------------------------------------------------------------------
# Tests — Config in default.yaml
# ---------------------------------------------------------------------------


class TestSmaConfigInYaml:
    """#039 — baselines.sma.fast / baselines.sma.slow in default.yaml."""

    def test_config_has_baselines_sma(self, default_yaml_data):
        """default.yaml must have baselines.sma.fast and baselines.sma.slow."""
        assert "baselines" in default_yaml_data
        assert "sma" in default_yaml_data["baselines"]
        sma = default_yaml_data["baselines"]["sma"]
        assert "fast" in sma
        assert "slow" in sma
        assert sma["fast"] == 20
        assert sma["slow"] == 50
