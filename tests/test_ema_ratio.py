"""Tests for EMA ratio feature (ema_ratio_12_26).

Task #011: Feature EMA ratio — divergence relative entre EMA rapide et lente.
Covers all acceptance criteria: registration, numerical correctness,
convergence on constant series, config-driven params, NaN positions, causality.
"""

import importlib

import numpy as np
import pandas as pd
import pytest

from ai_trading.features.registry import FEATURE_REGISTRY, BaseFeature

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ohlcv(close_values):
    """Build a minimal OHLCV DataFrame from close values.

    open/high/low are set equal to close; volume = 1.0.
    """
    n = len(close_values)
    timestamps = pd.date_range("2024-01-01", periods=n, freq="1h")
    close = np.array(close_values, dtype=np.float64)
    df = pd.DataFrame(
        {
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": np.ones(n, dtype=np.float64),
        },
        index=timestamps,
    )
    return df


def _ema_reference(close_values, span):
    """Pure-Python reference EMA with SMA initialisation.

    EMA_n(n-1) = SMA(C[0..n-1])
    EMA_n(t) = alpha * C_t + (1 - alpha) * EMA_n(t-1)  for t >= n
    NaN for t < n-1
    """
    n = len(close_values)
    alpha = 2.0 / (span + 1)
    result = [float("nan")] * n

    if n < span:
        return result

    # SMA initialisation: average of first `span` values
    sma = sum(close_values[:span]) / span
    result[span - 1] = sma

    for i in range(span, n):
        result[i] = alpha * close_values[i] + (1 - alpha) * result[i - 1]

    return result


def _ema_ratio_reference(close_values, fast=12, slow=26):
    """Compute reference ema_ratio = EMA_fast / EMA_slow - 1.

    NaN wherever EMA_slow is NaN (i.e. for t < slow - 1; first valid at t = slow - 1).
    """
    ema_fast = _ema_reference(close_values, fast)
    ema_slow = _ema_reference(close_values, slow)
    n = len(close_values)
    result = [float("nan")] * n
    for i in range(n):
        if not (np.isnan(ema_fast[i]) or np.isnan(ema_slow[i])):
            result[i] = ema_fast[i] / ema_slow[i] - 1.0
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_registry():
    """Save, clear, and restore FEATURE_REGISTRY around each test.

    Uses importlib.reload() to re-run @register_feature decorator after
    clearing, so registration tests exercise the real decorator path.
    """
    import ai_trading.features.ema as ema_module

    saved = dict(FEATURE_REGISTRY)
    FEATURE_REGISTRY.clear()
    importlib.reload(ema_module)
    yield
    FEATURE_REGISTRY.clear()
    FEATURE_REGISTRY.update(saved)


@pytest.fixture
def ema_class():
    """Return EmaRatio1226 class (already registered by _clean_registry)."""
    from ai_trading.features.ema import EmaRatio1226

    return EmaRatio1226


@pytest.fixture
def ema_instance(ema_class):
    """Return an instantiated EmaRatio1226 object."""
    return ema_class()


@pytest.fixture
def default_params():
    """Default feature params matching configs/default.yaml."""
    return {"ema_fast": 12, "ema_slow": 26}


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


class TestRegistration:
    """Test #011 — AC: class registered as 'ema_ratio_12_26' in FEATURE_REGISTRY."""

    def test_ema_ratio_in_registry(self, ema_class):
        assert "ema_ratio_12_26" in FEATURE_REGISTRY

    def test_registered_class_is_ema_ratio(self, ema_class):
        assert FEATURE_REGISTRY["ema_ratio_12_26"] is ema_class

    def test_is_base_feature_subclass(self, ema_class):
        assert issubclass(ema_class, BaseFeature)

    def test_required_params(self, ema_instance):
        assert "ema_fast" in ema_instance.required_params
        assert "ema_slow" in ema_instance.required_params


# ---------------------------------------------------------------------------
# Numerical correctness tests
# ---------------------------------------------------------------------------


class TestNumerical:
    """Test #011 — AC: numerical tests with hand-computed values."""

    def test_hand_computed_small_series(self, ema_instance, default_params):
        """Verify EMA ratio against hand-computed reference on a known series."""
        rng = np.random.default_rng(42)
        close_values = list(100.0 + np.cumsum(rng.standard_normal(40) * 0.5))
        ohlcv = _make_ohlcv(close_values)

        result = ema_instance.compute(ohlcv, default_params)
        expected = _ema_ratio_reference(close_values, fast=12, slow=26)

        for i in range(len(close_values)):
            if np.isnan(expected[i]):
                assert np.isnan(result.iloc[i]), f"Expected NaN at index {i}"
            else:
                np.testing.assert_allclose(
                    result.iloc[i], expected[i], atol=1e-12,
                    err_msg=f"Mismatch at index {i}",
                )

    def test_monotonically_increasing(self, ema_instance, default_params):
        """On a strictly increasing series, EMA_fast > EMA_slow → ratio > 0."""
        close_values = [100.0 + i * 1.0 for i in range(60)]
        ohlcv = _make_ohlcv(close_values)
        result = ema_instance.compute(ohlcv, default_params)

        # After warmup, all values should be > 0
        valid = result.iloc[25:]
        assert (valid > 0).all(), "EMA ratio should be > 0 for increasing prices"

    def test_monotonically_decreasing(self, ema_instance, default_params):
        """On a strictly decreasing series, EMA_fast < EMA_slow → ratio < 0."""
        close_values = [200.0 - i * 1.0 for i in range(60)]
        ohlcv = _make_ohlcv(close_values)
        result = ema_instance.compute(ohlcv, default_params)

        # After warmup, all values should be < 0
        valid = result.iloc[25:]
        assert (valid < 0).all(), "EMA ratio should be < 0 for decreasing prices"

    def test_specific_ema_values(self, ema_instance, default_params):
        """Verify specific EMA values at known indices.

        Uses a simple series: close = [1, 2, 3, ..., 40].
        """
        close_values = [float(i + 1) for i in range(40)]
        ohlcv = _make_ohlcv(close_values)
        result = ema_instance.compute(ohlcv, default_params)

        expected = _ema_ratio_reference(close_values, fast=12, slow=26)

        # Check the first non-NaN value (at index 25 = ema_slow - 1)
        assert not np.isnan(result.iloc[25])
        np.testing.assert_allclose(result.iloc[25], expected[25], atol=1e-12)

        # Check value at index 30
        np.testing.assert_allclose(result.iloc[30], expected[30], atol=1e-12)

        # Check last value
        np.testing.assert_allclose(result.iloc[-1], expected[-1], atol=1e-12)


# ---------------------------------------------------------------------------
# Convergence on constant series
# ---------------------------------------------------------------------------


class TestConvergence:
    """Test #011 — AC: constant series → ratio = 0 (atol=1e-10)."""

    def test_constant_series_ratio_zero(self, ema_instance, default_params):
        """On a constant series, EMA_fast = EMA_slow = constant → ratio = 0."""
        close_values = [100.0] * 60
        ohlcv = _make_ohlcv(close_values)
        result = ema_instance.compute(ohlcv, default_params)

        # All non-NaN values should be 0
        valid = result.dropna()
        np.testing.assert_allclose(valid.to_numpy(), 0.0, atol=1e-10)

    def test_constant_series_different_value(self, ema_instance, default_params):
        """Constant series at 42.5 → ratio = 0."""
        close_values = [42.5] * 50
        ohlcv = _make_ohlcv(close_values)
        result = ema_instance.compute(ohlcv, default_params)

        valid = result.dropna()
        np.testing.assert_allclose(valid.to_numpy(), 0.0, atol=1e-10)


# ---------------------------------------------------------------------------
# Config-driven
# ---------------------------------------------------------------------------


class TestConfigDriven:
    """Test #011 — AC: ema_fast and ema_slow read from params, not hardcoded."""

    def test_custom_fast_slow_periods(self, ema_instance):
        """Using non-default fast=5, slow=10 should produce different results."""
        close_values = [100.0 + i * 0.5 for i in range(30)]
        ohlcv = _make_ohlcv(close_values)

        params_custom = {"ema_fast": 5, "ema_slow": 10}
        result_custom = ema_instance.compute(ohlcv, params_custom)

        expected = _ema_ratio_reference(close_values, fast=5, slow=10)

        for i in range(len(close_values)):
            if np.isnan(expected[i]):
                assert np.isnan(result_custom.iloc[i])
            else:
                np.testing.assert_allclose(
                    result_custom.iloc[i], expected[i], atol=1e-12,
                )

    def test_nan_count_matches_slow_period(self, ema_instance):
        """NaN count should match the slow period, not hardcoded 26."""
        close_values = [100.0 + i for i in range(30)]
        ohlcv = _make_ohlcv(close_values)

        params_10 = {"ema_fast": 3, "ema_slow": 10}
        result = ema_instance.compute(ohlcv, params_10)

        # First non-NaN at index slow - 1 = 9
        assert np.isnan(result.iloc[8])
        assert not np.isnan(result.iloc[9])

    def test_missing_ema_fast_raises(self, ema_instance):
        """Missing ema_fast param should raise an error."""
        ohlcv = _make_ohlcv([100.0] * 30)
        with pytest.raises(KeyError):
            ema_instance.compute(ohlcv, {"ema_slow": 26})

    def test_missing_ema_slow_raises(self, ema_instance):
        """Missing ema_slow param should raise an error."""
        ohlcv = _make_ohlcv([100.0] * 30)
        with pytest.raises(KeyError):
            ema_instance.compute(ohlcv, {"ema_fast": 12})


# ---------------------------------------------------------------------------
# NaN positions
# ---------------------------------------------------------------------------


class TestNanPositions:
    """Test #011 — AC: NaN at positions t < ema_slow."""

    def test_nan_before_slow_period(self, ema_instance, default_params):
        """All values before index ema_slow - 1 should be NaN."""
        close_values = [100.0 + i for i in range(60)]
        ohlcv = _make_ohlcv(close_values)
        result = ema_instance.compute(ohlcv, default_params)

        # Indices 0..24 (25 values) should be NaN
        for i in range(25):
            assert np.isnan(result.iloc[i]), f"Expected NaN at index {i}"

    def test_first_non_nan_at_slow_minus_one(self, ema_instance, default_params):
        """First non-NaN value at index ema_slow - 1 = 25."""
        close_values = [100.0 + i for i in range(60)]
        ohlcv = _make_ohlcv(close_values)
        result = ema_instance.compute(ohlcv, default_params)

        assert not np.isnan(result.iloc[25])

    def test_all_non_nan_after_warmup(self, ema_instance, default_params):
        """After index ema_slow - 1, all values should be non-NaN."""
        close_values = [100.0 + i for i in range(60)]
        ohlcv = _make_ohlcv(close_values)
        result = ema_instance.compute(ohlcv, default_params)

        for i in range(25, 60):
            assert not np.isnan(result.iloc[i]), f"Unexpected NaN at index {i}"

    def test_short_series_all_nan(self, ema_instance, default_params):
        """Series shorter than ema_slow → all NaN."""
        close_values = [100.0] * 20  # < 26
        ohlcv = _make_ohlcv(close_values)
        result = ema_instance.compute(ohlcv, default_params)

        assert result.isna().all()

    def test_exact_slow_length(self, ema_instance, default_params):
        """Series of exactly ema_slow bars: only last value is non-NaN."""
        close_values = [100.0 + i for i in range(26)]
        ohlcv = _make_ohlcv(close_values)
        result = ema_instance.compute(ohlcv, default_params)

        # Only index 25 should be non-NaN
        assert result.isna().sum() == 25
        assert not np.isnan(result.iloc[25])


# ---------------------------------------------------------------------------
# Causality (anti-fuite)
# ---------------------------------------------------------------------------


class TestCausality:
    """Test #011 — AC: modifying close[t > T] doesn't change ema_ratio[t <= T]."""

    def test_future_modification_no_effect(self, ema_instance, default_params):
        """Changing close prices after T doesn't affect ema_ratio at or before T."""
        rng = np.random.default_rng(123)
        close_values = list(100.0 + np.cumsum(rng.standard_normal(60) * 0.5))
        ohlcv_original = _make_ohlcv(close_values)

        result_original = ema_instance.compute(ohlcv_original, default_params)

        # Modify close prices after index T=40
        t_split = 40
        close_modified = close_values.copy()
        for i in range(t_split + 1, len(close_modified)):
            close_modified[i] = close_modified[i] + 999.0

        ohlcv_modified = _make_ohlcv(close_modified)
        result_modified = ema_instance.compute(ohlcv_modified, default_params)

        # Values at t <= T should be identical
        for i in range(t_split + 1):
            if np.isnan(result_original.iloc[i]):
                assert np.isnan(result_modified.iloc[i])
            else:
                assert result_original.iloc[i] == result_modified.iloc[i], (
                    f"Causality violation at index {i}"
                )

    def test_causality_perturbation_at_boundary(self, ema_instance, default_params):
        """Small perturbation right after T — values at T should be unchanged."""
        close_values = [100.0 + i * 0.3 for i in range(50)]
        ohlcv_original = _make_ohlcv(close_values)
        result_original = ema_instance.compute(ohlcv_original, default_params)

        t_split = 30
        close_modified = close_values.copy()
        close_modified[t_split + 1] = close_modified[t_split + 1] + 50.0

        ohlcv_modified = _make_ohlcv(close_modified)
        result_modified = ema_instance.compute(ohlcv_modified, default_params)

        for i in range(t_split + 1):
            if np.isnan(result_original.iloc[i]):
                assert np.isnan(result_modified.iloc[i])
            else:
                assert result_original.iloc[i] == result_modified.iloc[i]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test #011 — AC: edge cases and error scenarios."""

    def test_empty_dataframe(self, ema_instance, default_params):
        """Empty DataFrame → empty Series."""
        ohlcv = _make_ohlcv([])
        result = ema_instance.compute(ohlcv, default_params)
        assert len(result) == 0

    def test_single_bar(self, ema_instance, default_params):
        """Single bar → all NaN."""
        ohlcv = _make_ohlcv([100.0])
        result = ema_instance.compute(ohlcv, default_params)
        assert len(result) == 1
        assert np.isnan(result.iloc[0])

    def test_returns_series(self, ema_instance, default_params):
        """Result should be a pd.Series."""
        ohlcv = _make_ohlcv([100.0 + i for i in range(40)])
        result = ema_instance.compute(ohlcv, default_params)
        assert isinstance(result, pd.Series)

    def test_same_length_as_input(self, ema_instance, default_params):
        """Result length should match input length."""
        n = 50
        close_values = [100.0 + i for i in range(n)]
        ohlcv = _make_ohlcv(close_values)
        result = ema_instance.compute(ohlcv, default_params)
        assert len(result) == n

    def test_same_index_as_input(self, ema_instance, default_params):
        """Result index should match input OHLCV index."""
        close_values = [100.0 + i for i in range(40)]
        ohlcv = _make_ohlcv(close_values)
        result = ema_instance.compute(ohlcv, default_params)
        pd.testing.assert_index_equal(result.index, ohlcv.index)

    def test_min_periods_returns_slow_minus_one(self, ema_instance):
        """min_periods should equal index of first non-NaN (ema_slow - 1 = 25)."""
        assert ema_instance.min_periods == 25

    def test_ema_fast_equals_slow_ratio_zero(self, ema_instance):
        """When ema_fast == ema_slow, ratio should be 0 everywhere non-NaN."""
        close_values = [100.0 + i * 0.5 for i in range(40)]
        ohlcv = _make_ohlcv(close_values)
        params = {"ema_fast": 10, "ema_slow": 10}
        result = ema_instance.compute(ohlcv, params)

        valid = result.dropna()
        np.testing.assert_allclose(valid.to_numpy(), 0.0, atol=1e-14)

    def test_min_fast_min_slow(self, ema_instance):
        """ema_fast=1, ema_slow=1: ratio=0 everywhere, 0 NaN."""
        close_values = [10.0, 20.0, 30.0, 25.0]
        ohlcv = _make_ohlcv(close_values)
        result = ema_instance.compute(ohlcv, {"ema_fast": 1, "ema_slow": 1})

        assert not result.isna().any(), "No NaN expected when fast=slow=1"
        np.testing.assert_allclose(result.to_numpy(), 0.0, atol=1e-14)

    def test_fast_greater_than_slow_raises(self, ema_instance):
        """ema_fast > ema_slow should raise ValueError."""
        ohlcv = _make_ohlcv([100.0] * 30)
        with pytest.raises(ValueError):
            ema_instance.compute(ohlcv, {"ema_fast": 30, "ema_slow": 10})

    def test_zero_fast_raises(self, ema_instance):
        """ema_fast == 0 should raise ValueError."""
        ohlcv = _make_ohlcv([100.0] * 30)
        with pytest.raises(ValueError):
            ema_instance.compute(ohlcv, {"ema_fast": 0, "ema_slow": 26})

    def test_zero_slow_raises(self, ema_instance):
        """ema_slow == 0 should raise ValueError."""
        ohlcv = _make_ohlcv([100.0] * 30)
        with pytest.raises(ValueError):
            ema_instance.compute(ohlcv, {"ema_fast": 12, "ema_slow": 0})

    def test_negative_fast_raises(self, ema_instance):
        """ema_fast < 0 should raise ValueError."""
        ohlcv = _make_ohlcv([100.0] * 30)
        with pytest.raises(ValueError):
            ema_instance.compute(ohlcv, {"ema_fast": -1, "ema_slow": 26})

    def test_negative_slow_raises(self, ema_instance):
        """ema_slow < 0 should raise ValueError."""
        ohlcv = _make_ohlcv([100.0] * 30)
        with pytest.raises(ValueError):
            ema_instance.compute(ohlcv, {"ema_fast": 12, "ema_slow": -5})
