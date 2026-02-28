"""Tests for ai_trading.features.log_returns — log-return features.

Task #008: Features log-returns (logret_1, logret_2, logret_4).

Covers:
- Registration in FEATURE_REGISTRY
- Numerical correctness on synthetic data
- NaN at positions t < k
- Causality (no look-ahead)
- Nominal, error, and edge cases
"""

import numpy as np
import pandas as pd
import pytest

from ai_trading.features.registry import FEATURE_REGISTRY, BaseFeature

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ohlcv_10bars() -> pd.DataFrame:
    """Synthetic OHLCV DataFrame with 10 bars and deterministic close prices."""
    n = 10
    close = np.array([100.0, 102.0, 101.0, 105.0, 103.0,
                       107.0, 106.0, 110.0, 108.0, 112.0])
    return pd.DataFrame({
        "open": close * 0.99,
        "high": close * 1.01,
        "low": close * 0.98,
        "close": close,
        "volume": np.ones(n) * 1000.0,
    }, index=pd.date_range("2024-01-01", periods=n, freq="h"))


@pytest.fixture
def ohlcv_minimal_1() -> pd.DataFrame:
    """Minimal OHLCV with 1 bar — edge case for logret_1."""
    close = np.array([100.0])
    return pd.DataFrame({
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": np.ones(1),
    }, index=pd.date_range("2024-01-01", periods=1, freq="h"))


@pytest.fixture
def ohlcv_minimal_2() -> pd.DataFrame:
    """Minimal OHLCV with 2 bars."""
    close = np.array([100.0, 110.0])
    return pd.DataFrame({
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": np.ones(2),
    }, index=pd.date_range("2024-01-01", periods=2, freq="h"))


# ---------------------------------------------------------------------------
# Ensure log_returns module is imported so features are registered
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _import_log_returns():
    """Import log_returns module to trigger @register_feature decorators."""
    import ai_trading.features.log_returns  # noqa: F401


# ---------------------------------------------------------------------------
# Test: Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    """Test that logret_1, logret_2, logret_4 are registered correctly."""

    @pytest.mark.parametrize("name", ["logret_1", "logret_2", "logret_4"])
    def test_feature_in_registry(self, name: str) -> None:
        """#008: Each log-return feature must be registered in FEATURE_REGISTRY."""
        assert name in FEATURE_REGISTRY

    @pytest.mark.parametrize("name", ["logret_1", "logret_2", "logret_4"])
    def test_feature_is_base_feature_subclass(self, name: str) -> None:
        """#008: Each registered class must be a BaseFeature subclass."""
        cls = FEATURE_REGISTRY[name]
        assert issubclass(cls, BaseFeature)

    @pytest.mark.parametrize("name,expected_min", [
        ("logret_1", 1),
        ("logret_2", 2),
        ("logret_4", 4),
    ])
    def test_min_periods(self, name: str, expected_min: int) -> None:
        """#008: min_periods must equal k for logret_k."""
        feature = FEATURE_REGISTRY[name]()
        assert feature.min_periods == expected_min

    @pytest.mark.parametrize("name", ["logret_1", "logret_2", "logret_4"])
    def test_required_params_empty(self, name: str) -> None:
        """#008: Log-return features have no required params."""
        cls = FEATURE_REGISTRY[name]
        assert cls.required_params == []


# ---------------------------------------------------------------------------
# Test: Numerical correctness
# ---------------------------------------------------------------------------


class TestNumericalCorrectness:
    """Verify computed values match manual calculation."""

    def test_logret_1_values(self, ohlcv_10bars: pd.DataFrame) -> None:
        """#008: logret_1 = log(close / close.shift(1))."""
        feature = FEATURE_REGISTRY["logret_1"]()
        result = feature.compute(ohlcv_10bars, {})
        close = ohlcv_10bars["close"]
        expected = np.log(close / close.shift(1))
        pd.testing.assert_series_equal(result, expected, atol=1e-12)

    def test_logret_2_values(self, ohlcv_10bars: pd.DataFrame) -> None:
        """#008: logret_2 = log(close / close.shift(2))."""
        feature = FEATURE_REGISTRY["logret_2"]()
        result = feature.compute(ohlcv_10bars, {})
        close = ohlcv_10bars["close"]
        expected = np.log(close / close.shift(2))
        pd.testing.assert_series_equal(result, expected, atol=1e-12)

    def test_logret_4_values(self, ohlcv_10bars: pd.DataFrame) -> None:
        """#008: logret_4 = log(close / close.shift(4))."""
        feature = FEATURE_REGISTRY["logret_4"]()
        result = feature.compute(ohlcv_10bars, {})
        close = ohlcv_10bars["close"]
        expected = np.log(close / close.shift(4))
        pd.testing.assert_series_equal(result, expected, atol=1e-12)

    def test_logret_1_hand_calculated(self) -> None:
        """#008: logret_1 hand-verified on 3-bar example."""
        close = np.array([100.0, 200.0, 50.0])
        ohlcv = pd.DataFrame({
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": np.ones(3),
        }, index=pd.date_range("2024-01-01", periods=3, freq="h"))

        feature = FEATURE_REGISTRY["logret_1"]()
        result = feature.compute(ohlcv, {})

        assert np.isnan(result.iloc[0])
        np.testing.assert_allclose(result.iloc[1], np.log(200.0 / 100.0), atol=1e-12)
        np.testing.assert_allclose(result.iloc[2], np.log(50.0 / 200.0), atol=1e-12)


# ---------------------------------------------------------------------------
# Test: NaN at positions t < k
# ---------------------------------------------------------------------------


class TestNaNPositions:
    """Verify NaN at positions t < k for each logret_k variant."""

    def test_logret_1_nan_at_position_0(self, ohlcv_10bars: pd.DataFrame) -> None:
        """#008: logret_1 has NaN at t=0."""
        feature = FEATURE_REGISTRY["logret_1"]()
        result = feature.compute(ohlcv_10bars, {})
        assert np.isnan(result.iloc[0])
        # t=1 onwards should NOT be NaN
        assert not np.isnan(result.iloc[1])

    def test_logret_2_nan_at_positions_0_1(self, ohlcv_10bars: pd.DataFrame) -> None:
        """#008: logret_2 has NaN at t=0 and t=1."""
        feature = FEATURE_REGISTRY["logret_2"]()
        result = feature.compute(ohlcv_10bars, {})
        assert np.isnan(result.iloc[0])
        assert np.isnan(result.iloc[1])
        # t=2 onwards should NOT be NaN
        assert not np.isnan(result.iloc[2])

    def test_logret_4_nan_at_positions_0_to_3(self, ohlcv_10bars: pd.DataFrame) -> None:
        """#008: logret_4 has NaN at t=0..3."""
        feature = FEATURE_REGISTRY["logret_4"]()
        result = feature.compute(ohlcv_10bars, {})
        for i in range(4):
            assert np.isnan(result.iloc[i]), f"Expected NaN at position {i}"
        # t=4 should NOT be NaN
        assert not np.isnan(result.iloc[4])

    def test_logret_1_all_nan_with_single_bar(
        self, ohlcv_minimal_1: pd.DataFrame
    ) -> None:
        """#008: logret_1 with 1 bar → all NaN (no prior bar to compare)."""
        feature = FEATURE_REGISTRY["logret_1"]()
        result = feature.compute(ohlcv_minimal_1, {})
        assert len(result) == 1
        assert np.isnan(result.iloc[0])

    def test_logret_2_all_nan_with_2_bars(
        self, ohlcv_minimal_2: pd.DataFrame
    ) -> None:
        """#008: logret_2 with 2 bars → all NaN (need k=2 prior bars)."""
        feature = FEATURE_REGISTRY["logret_2"]()
        result = feature.compute(ohlcv_minimal_2, {})
        assert len(result) == 2
        assert np.isnan(result.iloc[0])
        assert np.isnan(result.iloc[1])


# ---------------------------------------------------------------------------
# Test: Causality (no look-ahead)
# ---------------------------------------------------------------------------


class TestCausality:
    """Modify future close prices and verify past values unchanged."""

    @pytest.mark.parametrize("name,k", [
        ("logret_1", 1),
        ("logret_2", 2),
        ("logret_4", 4),
    ])
    def test_no_look_ahead(self, ohlcv_10bars: pd.DataFrame, name: str, k: int) -> None:
        """#008: Changing close[t > T] must not change logret_k[t <= T]."""
        feature = FEATURE_REGISTRY[name]()
        split_t = 6  # T = index 6

        # Compute with original data
        result_original = feature.compute(ohlcv_10bars, {})

        # Perturb future close prices (t > T)
        ohlcv_modified = ohlcv_10bars.copy()
        ohlcv_modified.iloc[split_t + 1:, ohlcv_modified.columns.get_loc("close")] *= 999.0

        result_modified = feature.compute(ohlcv_modified, {})

        # Values at t <= T must be identical
        original_slice = result_original.iloc[: split_t + 1]
        modified_slice = result_modified.iloc[: split_t + 1]

        pd.testing.assert_series_equal(original_slice, modified_slice, atol=1e-15)


# ---------------------------------------------------------------------------
# Test: Return type and index
# ---------------------------------------------------------------------------


class TestReturnType:
    """Verify compute returns a pd.Series with correct index."""

    @pytest.mark.parametrize("name", ["logret_1", "logret_2", "logret_4"])
    def test_returns_series(self, ohlcv_10bars: pd.DataFrame, name: str) -> None:
        """#008: compute() must return a pd.Series."""
        feature = FEATURE_REGISTRY[name]()
        result = feature.compute(ohlcv_10bars, {})
        assert isinstance(result, pd.Series)

    @pytest.mark.parametrize("name", ["logret_1", "logret_2", "logret_4"])
    def test_same_index_as_input(self, ohlcv_10bars: pd.DataFrame, name: str) -> None:
        """#008: Output index must match input OHLCV index."""
        feature = FEATURE_REGISTRY[name]()
        result = feature.compute(ohlcv_10bars, {})
        pd.testing.assert_index_equal(result.index, ohlcv_10bars.index)

    @pytest.mark.parametrize("name", ["logret_1", "logret_2", "logret_4"])
    def test_same_length_as_input(self, ohlcv_10bars: pd.DataFrame, name: str) -> None:
        """#008: Output length must match input length."""
        feature = FEATURE_REGISTRY[name]()
        result = feature.compute(ohlcv_10bars, {})
        assert len(result) == len(ohlcv_10bars)


# ---------------------------------------------------------------------------
# Test: Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and error scenarios."""

    def test_constant_close_prices(self) -> None:
        """#008: Constant close → logret_k = 0.0 for valid positions."""
        close = np.full(10, 100.0)
        ohlcv = pd.DataFrame({
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": np.ones(10),
        }, index=pd.date_range("2024-01-01", periods=10, freq="h"))

        for name, k in [("logret_1", 1), ("logret_2", 2), ("logret_4", 4)]:
            feature = FEATURE_REGISTRY[name]()
            result = feature.compute(ohlcv, {})
            valid_values = result.iloc[k:]
            np.testing.assert_allclose(valid_values.values, 0.0, atol=1e-15)

    def test_monotonic_increasing_close(self) -> None:
        """#008: Monotonically increasing close → positive logret_k."""
        close = np.array([100.0, 101.0, 102.0, 103.0, 104.0,
                          105.0, 106.0, 107.0, 108.0, 109.0])
        ohlcv = pd.DataFrame({
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": np.ones(10),
        }, index=pd.date_range("2024-01-01", periods=10, freq="h"))

        for name, k in [("logret_1", 1), ("logret_2", 2), ("logret_4", 4)]:
            feature = FEATURE_REGISTRY[name]()
            result = feature.compute(ohlcv, {})
            valid_values = result.iloc[k:]
            assert (valid_values > 0).all(), f"{name}: expected all positive"

    def test_logret_symmetry(self) -> None:
        """#008: log(a/b) = -log(b/a) — test on two-bar frame."""
        close = np.array([100.0, 200.0])
        ohlcv = pd.DataFrame({
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": np.ones(2),
        }, index=pd.date_range("2024-01-01", periods=2, freq="h"))

        feature = FEATURE_REGISTRY["logret_1"]()
        result = feature.compute(ohlcv, {})
        val = result.iloc[1]

        # Reverse
        close_rev = np.array([200.0, 100.0])
        ohlcv_rev = pd.DataFrame({
            "open": close_rev,
            "high": close_rev,
            "low": close_rev,
            "close": close_rev,
            "volume": np.ones(2),
        }, index=pd.date_range("2024-01-01", periods=2, freq="h"))

        result_rev = feature.compute(ohlcv_rev, {})
        val_rev = result_rev.iloc[1]

        np.testing.assert_allclose(val, -val_rev, atol=1e-15)

    @pytest.mark.parametrize("name", ["logret_1", "logret_2", "logret_4"])
    def test_empty_dataframe(self, name: str) -> None:
        """#008: Empty DataFrame (0 bars) → empty Series, no error."""
        ohlcv = pd.DataFrame({
            "open": pd.Series([], dtype=float),
            "high": pd.Series([], dtype=float),
            "low": pd.Series([], dtype=float),
            "close": pd.Series([], dtype=float),
            "volume": pd.Series([], dtype=float),
        }, index=pd.DatetimeIndex([]))

        feature = FEATURE_REGISTRY[name]()
        result = feature.compute(ohlcv, {})
        assert isinstance(result, pd.Series)
        assert len(result) == 0

    def test_logret_4_with_3_bars_all_nan(self) -> None:
        """#008: logret_4 with 3 bars (< k=4) → all NaN."""
        close = np.array([100.0, 110.0, 105.0])
        ohlcv = pd.DataFrame({
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": np.ones(3),
        }, index=pd.date_range("2024-01-01", periods=3, freq="h"))

        feature = FEATURE_REGISTRY["logret_4"]()
        result = feature.compute(ohlcv, {})
        assert len(result) == 3
        assert result.isna().all()

    def test_logret_4_with_exactly_4_bars_all_nan(self) -> None:
        """#008: logret_4 with exactly 4 bars → all NaN (shift(4) needs at least 5 rows for first non-NaN)."""
        close = np.array([100.0, 110.0, 105.0, 120.0])
        ohlcv = pd.DataFrame({
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": np.ones(4),
        }, index=pd.date_range("2024-01-01", periods=4, freq="h"))

        feature = FEATURE_REGISTRY["logret_4"]()
        result = feature.compute(ohlcv, {})
        assert len(result) == 4
        assert result.isna().all()

    def test_logret_4_with_5_bars_first_valid(self) -> None:
        """#008: logret_4 with 5 bars → 4 NaN + 1 valid at index 4."""
        close = np.array([100.0, 110.0, 105.0, 120.0, 130.0])
        ohlcv = pd.DataFrame({
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": np.ones(5),
        }, index=pd.date_range("2024-01-01", periods=5, freq="h"))

        feature = FEATURE_REGISTRY["logret_4"]()
        result = feature.compute(ohlcv, {})
        assert len(result) == 5
        assert result.iloc[:4].isna().all()
        # index 4: log(130/100)
        np.testing.assert_allclose(
            result.iloc[4], np.log(130.0 / 100.0), atol=1e-12
        )
