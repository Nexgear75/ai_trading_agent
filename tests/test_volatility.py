"""Tests for ai_trading.features.volatility — rolling volatility features.

Task #009: Features de volatilité rolling (vol_24, vol_72).
"""

import numpy as np
import pandas as pd
import pytest

import ai_trading.features.volatility as _vol_module
from ai_trading.features.registry import FEATURE_REGISTRY, BaseFeature
from tests.conftest import clean_registry_with_reload
from tests.conftest import make_ohlcv_random as _make_ohlcv

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_params() -> dict:
    """Default volatility params (only volatility_ddof is required by these features)."""
    return {
        "volatility_ddof": 0,
    }


def _import_volatility():
    """Import the volatility module to trigger registration."""
    import ai_trading.features.volatility  # noqa: F401


_clean_registry = clean_registry_with_reload(_vol_module)


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------

class TestVolatilityRegistration:
    """Verify vol_24 and vol_72 are registered in FEATURE_REGISTRY."""

    def test_vol_24_registered(self):
        """#009 vol_24 must be registered after module import."""
        _import_volatility()
        assert "vol_24" in FEATURE_REGISTRY

    def test_vol_72_registered(self):
        """#009 vol_72 must be registered after module import."""
        _import_volatility()
        assert "vol_72" in FEATURE_REGISTRY

    def test_vol_24_is_base_feature_subclass(self):
        """#009 vol_24 class must be a BaseFeature subclass."""
        _import_volatility()
        cls = FEATURE_REGISTRY["vol_24"]
        assert issubclass(cls, BaseFeature)

    def test_vol_72_is_base_feature_subclass(self):
        """#009 vol_72 class must be a BaseFeature subclass."""
        _import_volatility()
        cls = FEATURE_REGISTRY["vol_72"]
        assert issubclass(cls, BaseFeature)


# ---------------------------------------------------------------------------
# min_periods tests
# ---------------------------------------------------------------------------

class TestMinPeriods:
    """Verify min_periods matches the window size."""

    def test_vol_24_min_periods(self):
        """#009 vol_24.min_periods == 24."""
        _import_volatility()
        instance = FEATURE_REGISTRY["vol_24"]()
        assert instance.min_periods({}) == 24

    def test_vol_72_min_periods(self):
        """#009 vol_72.min_periods == 72."""
        _import_volatility()
        instance = FEATURE_REGISTRY["vol_72"]()
        assert instance.min_periods({}) == 72


# ---------------------------------------------------------------------------
# required_params tests
# ---------------------------------------------------------------------------

class TestRequiredParams:
    """Verify required_params includes volatility_ddof and does not require vol_windows."""

    def test_vol_24_required_params(self):
        """#009 vol_24 must require volatility_ddof."""
        _import_volatility()
        cls = FEATURE_REGISTRY["vol_24"]
        assert "volatility_ddof" in cls.required_params
        assert "vol_windows" not in cls.required_params

    def test_vol_72_required_params(self):
        """#009 vol_72 must require volatility_ddof."""
        _import_volatility()
        cls = FEATURE_REGISTRY["vol_72"]
        assert "volatility_ddof" in cls.required_params
        assert "vol_windows" not in cls.required_params


# ---------------------------------------------------------------------------
# Numerical correctness tests
# ---------------------------------------------------------------------------

class TestNumericalCorrectness:
    """Verify compute() produces values identical to manual np.std(ddof=0)."""

    def test_vol_24_numerical_match(self):
        """#009 vol_24 must match np.std(logret, ddof=0) over 24-bar window."""
        _import_volatility()
        ohlcv = _make_ohlcv(100)
        params = _default_params()
        instance = FEATURE_REGISTRY["vol_24"]()
        result = instance.compute(ohlcv, params)

        close = np.asarray(ohlcv["close"].values)
        logreturns = np.log(close[1:] / close[:-1])

        # pandas logret[t] = log(close[t]/close[t-1]) = logreturns[t-1]
        # rolling(24) at index t uses logret[t-23..t] → logreturns[t-24..t-1]
        t = 30
        window = logreturns[t - 24: t]  # 24 logreturns ending at logret[t]
        expected = np.std(window, ddof=0)
        # result index is aligned with ohlcv; logret at t=0 is NaN, vol at t maps to
        # the rolling std ending at bar t
        np.testing.assert_allclose(result.iloc[t], expected, rtol=1e-10)

    def test_vol_72_numerical_match(self):
        """#009 vol_72 must match np.std(logret, ddof=0) over 72-bar window."""
        _import_volatility()
        ohlcv = _make_ohlcv(200)
        params = _default_params()
        instance = FEATURE_REGISTRY["vol_72"]()
        result = instance.compute(ohlcv, params)

        close = np.asarray(ohlcv["close"].values)
        logreturns = np.log(close[1:] / close[:-1])

        # pandas logret[t] = logreturns[t-1]; rolling(72) at t uses logreturns[t-72..t-1]
        t = 80
        window = logreturns[t - 72: t]
        expected = np.std(window, ddof=0)
        np.testing.assert_allclose(result.iloc[t], expected, rtol=1e-10)

    def test_vol_24_multiple_positions(self):
        """#009 vol_24 correctness at several positions."""
        _import_volatility()
        ohlcv = _make_ohlcv(100)
        params = _default_params()
        instance = FEATURE_REGISTRY["vol_24"]()
        result = instance.compute(ohlcv, params)

        close = np.asarray(ohlcv["close"].values)
        logreturns = np.log(close[1:] / close[:-1])

        for t in [24, 40, 60, 99]:
            window = logreturns[t - 24: t]
            expected = np.std(window, ddof=0)
            np.testing.assert_allclose(
                result.iloc[t], expected, rtol=1e-10,
                err_msg=f"Mismatch at t={t}",
            )


# ---------------------------------------------------------------------------
# ddof configuration tests
# ---------------------------------------------------------------------------

class TestDdofConfig:
    """Verify ddof is read from config, not hardcoded."""

    def test_ddof_1_gives_different_result(self):
        """#009 Using ddof=1 must yield different values from ddof=0."""
        _import_volatility()
        ohlcv = _make_ohlcv(100)
        params_0 = {"volatility_ddof": 0}
        params_1 = {"volatility_ddof": 1}

        instance = FEATURE_REGISTRY["vol_24"]()
        result_0 = instance.compute(ohlcv, params_0)
        result_1 = instance.compute(ohlcv, params_1)

        # They must differ at non-NaN positions
        valid = ~result_0.isna() & ~result_1.isna()
        assert valid.sum() > 0
        assert not np.allclose(
            np.asarray(result_0[valid].values),
            np.asarray(result_1[valid].values),
        ), "ddof=0 and ddof=1 should produce different values"

    def test_ddof_1_numerical_match(self):
        """#009 ddof=1 must match np.std(logret, ddof=1) on the window."""
        _import_volatility()
        ohlcv = _make_ohlcv(100)
        params = {"volatility_ddof": 1}
        instance = FEATURE_REGISTRY["vol_24"]()
        result = instance.compute(ohlcv, params)

        close = np.asarray(ohlcv["close"].values)
        logreturns = np.log(close[1:] / close[:-1])

        t = 30
        window = logreturns[t - 24: t]
        expected = np.std(window, ddof=1)
        np.testing.assert_allclose(result.iloc[t], expected, rtol=1e-10)


# ---------------------------------------------------------------------------
# NaN tests (incomplete window)
# ---------------------------------------------------------------------------

class TestNaN:
    """Verify NaN at positions where the window is incomplete."""

    def test_vol_24_nan_before_window(self):
        """#009 vol_24 must be NaN for t < 24."""
        _import_volatility()
        ohlcv = _make_ohlcv(100)
        params = _default_params()
        instance = FEATURE_REGISTRY["vol_24"]()
        result = instance.compute(ohlcv, params)

        # Positions 0..23 must be NaN (24 positions: index 0 has no logret,
        # and positions 1..23 have fewer than 24 logreturns)
        for i in range(24):
            assert np.isnan(result.iloc[i]), f"Expected NaN at position {i}"

    def test_vol_24_first_valid_at_24(self):
        """#009 vol_24 first non-NaN value at position 24."""
        _import_volatility()
        ohlcv = _make_ohlcv(100)
        params = _default_params()
        instance = FEATURE_REGISTRY["vol_24"]()
        result = instance.compute(ohlcv, params)

        assert not np.isnan(result.iloc[24]), "Position 24 should be valid"

    def test_vol_72_nan_before_window(self):
        """#009 vol_72 must be NaN for t < 72."""
        _import_volatility()
        ohlcv = _make_ohlcv(200)
        params = _default_params()
        instance = FEATURE_REGISTRY["vol_72"]()
        result = instance.compute(ohlcv, params)

        for i in range(72):
            assert np.isnan(result.iloc[i]), f"Expected NaN at position {i}"

    def test_vol_72_first_valid_at_72(self):
        """#009 vol_72 first non-NaN value at position 72."""
        _import_volatility()
        ohlcv = _make_ohlcv(200)
        params = _default_params()
        instance = FEATURE_REGISTRY["vol_72"]()
        result = instance.compute(ohlcv, params)

        assert not np.isnan(result.iloc[72]), "Position 72 should be valid"


# ---------------------------------------------------------------------------
# Causality (anti-fuite) tests
# ---------------------------------------------------------------------------

class TestCausality:
    """Verify strictly causal: modifying future data does not change past."""

    def test_vol_24_causality(self):
        """#009 Modifying close[t > T] must not change vol_24[t <= T]."""
        _import_volatility()
        params = _default_params()
        ohlcv_orig = _make_ohlcv(100)
        instance = FEATURE_REGISTRY["vol_24"]()

        result_orig = instance.compute(ohlcv_orig, params)

        # Modify future prices (t > 60)
        ohlcv_mod = ohlcv_orig.copy()
        close_col = list(ohlcv_mod.columns).index("close")
        ohlcv_mod.iloc[61:, close_col] *= 999.0

        result_mod = instance.compute(ohlcv_mod, params)

        # Values at t <= 60 must be identical
        pd.testing.assert_series_equal(
            result_orig.iloc[:61],
            result_mod.iloc[:61],
        )

    def test_vol_72_causality(self):
        """#009 Modifying close[t > T] must not change vol_72[t <= T]."""
        _import_volatility()
        params = _default_params()
        ohlcv_orig = _make_ohlcv(200)
        instance = FEATURE_REGISTRY["vol_72"]()

        result_orig = instance.compute(ohlcv_orig, params)

        ohlcv_mod = ohlcv_orig.copy()
        close_col = list(ohlcv_mod.columns).index("close")
        ohlcv_mod.iloc[120:, close_col] *= 999.0

        result_mod = instance.compute(ohlcv_mod, params)

        pd.testing.assert_series_equal(
            result_orig.iloc[:120],
            result_mod.iloc[:120],
        )


# ---------------------------------------------------------------------------
# Output shape / type tests
# ---------------------------------------------------------------------------

class TestOutputShape:
    """Verify output is a pd.Series with correct length and index."""

    def test_vol_24_returns_series(self):
        """#009 vol_24.compute() must return a pd.Series."""
        _import_volatility()
        ohlcv = _make_ohlcv(100)
        params = _default_params()
        instance = FEATURE_REGISTRY["vol_24"]()
        result = instance.compute(ohlcv, params)
        assert isinstance(result, pd.Series)

    def test_vol_24_same_length_as_input(self):
        """#009 vol_24 output length == ohlcv length."""
        _import_volatility()
        ohlcv = _make_ohlcv(100)
        params = _default_params()
        instance = FEATURE_REGISTRY["vol_24"]()
        result = instance.compute(ohlcv, params)
        assert len(result) == len(ohlcv)

    def test_vol_24_same_index_as_input(self):
        """#009 vol_24 output index matches ohlcv index."""
        _import_volatility()
        ohlcv = _make_ohlcv(100)
        params = _default_params()
        instance = FEATURE_REGISTRY["vol_24"]()
        result = instance.compute(ohlcv, params)
        pd.testing.assert_index_equal(result.index, ohlcv.index)

    def test_vol_72_same_length_as_input(self):
        """#009 vol_72 output length == ohlcv length."""
        _import_volatility()
        ohlcv = _make_ohlcv(200)
        params = _default_params()
        instance = FEATURE_REGISTRY["vol_72"]()
        result = instance.compute(ohlcv, params)
        assert len(result) == len(ohlcv)


# ---------------------------------------------------------------------------
# Edge cases / error handling
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases and error handling."""

    def test_exact_window_size_input_vol_24(self):
        """#009 With exactly 25 bars, vol_24 has 1 valid value at last pos."""
        _import_volatility()
        ohlcv = _make_ohlcv(25)
        params = _default_params()
        instance = FEATURE_REGISTRY["vol_24"]()
        result = instance.compute(ohlcv, params)

        # Positions 0..23: NaN, position 24: valid
        assert np.isnan(result.iloc[23])
        assert not np.isnan(result.iloc[24])

    def test_fewer_bars_than_window_all_nan(self):
        """#009 With fewer bars than window, all values must be NaN."""
        _import_volatility()
        ohlcv = _make_ohlcv(10)
        params = _default_params()
        instance = FEATURE_REGISTRY["vol_24"]()
        result = instance.compute(ohlcv, params)
        assert result.isna().all()

    def test_constant_prices_zero_volatility(self):
        """#009 Constant close prices → volatility == 0 (std of zeros)."""
        _import_volatility()
        n = 50
        timestamps = pd.date_range("2023-01-01", periods=n, freq="h")
        ohlcv = pd.DataFrame(
            {
                "open": 100.0,
                "high": 100.0,
                "low": 100.0,
                "close": 100.0,
                "volume": 1000.0,
            },
            index=timestamps,
        )
        params = _default_params()
        instance = FEATURE_REGISTRY["vol_24"]()
        result = instance.compute(ohlcv, params)

        # After warmup, volatility should be 0.0
        valid_values = result.dropna()
        assert len(valid_values) > 0
        np.testing.assert_allclose(np.asarray(valid_values.values), 0.0, atol=1e-15)

    def test_missing_param_raises(self):
        """#009 Missing required param must raise an error."""
        _import_volatility()
        ohlcv = _make_ohlcv(100)
        instance = FEATURE_REGISTRY["vol_24"]()
        with pytest.raises((KeyError, ValueError)):
            instance.compute(ohlcv, {})

    def test_vol_windows_from_config(self):
        """#009 vol_24 window is fixed at 24 per spec §6.5, regardless of vol_windows.

        Passing a custom vol_windows=[10, 50] must NOT change the actual rolling
        window; vol_24 always uses a 24-bar window to stay consistent with
        ``min_periods`` and the feature name contract.
        """
        _import_volatility()
        ohlcv = _make_ohlcv(100)
        params = {"vol_windows": [10, 50], "volatility_ddof": 0}
        instance = FEATURE_REGISTRY["vol_24"]()
        result = instance.compute(ohlcv, params)

        # Window is fixed at 24; positions 0..23 must be NaN, position 24 valid.
        assert np.isnan(result.iloc[10])
        assert np.isnan(result.iloc[23])
        assert not np.isnan(result.iloc[24])

    def test_vol_72_window_fixed_regardless_of_vol_windows(self):
        """#009 vol_72 window is fixed at 72 per spec §6.5, regardless of vol_windows.

        Passing a custom vol_windows=[10, 50] must NOT change the actual rolling
        window; vol_72 always uses a 72-bar window to stay consistent with
        ``min_periods`` and the feature name contract.
        """
        _import_volatility()
        ohlcv = _make_ohlcv(200)
        params = {"vol_windows": [10, 50], "volatility_ddof": 0}
        instance = FEATURE_REGISTRY["vol_72"]()
        result = instance.compute(ohlcv, params)

        # Window is fixed at 72; positions 0..71 must be NaN, position 72 valid.
        assert np.isnan(result.iloc[50])
        assert np.isnan(result.iloc[71])
        assert not np.isnan(result.iloc[72])

    def test_empty_dataframe_returns_empty_series(self):
        """#009 Empty OHLCV → empty Series (no crash)."""
        _import_volatility()
        timestamps = pd.DatetimeIndex([], dtype="datetime64[ns]", freq="h")
        ohlcv = pd.DataFrame(
            {"open": [], "high": [], "low": [], "close": [], "volume": []},
            index=timestamps,
        )
        params = _default_params()
        for name in ("vol_24", "vol_72"):
            instance = FEATURE_REGISTRY[name]()
            result = instance.compute(ohlcv, params)
            assert isinstance(result, pd.Series)
            assert len(result) == 0

    def test_single_bar_all_nan(self):
        """#009 With only 1 bar, all values must be NaN."""
        _import_volatility()
        ohlcv = _make_ohlcv(1)
        params = _default_params()
        for name in ("vol_24", "vol_72"):
            instance = FEATURE_REGISTRY[name]()
            result = instance.compute(ohlcv, params)
            assert len(result) == 1
            assert result.isna().all()

    def test_exact_window_bars_all_nan_vol_24(self):
        """#009 With exactly 24 bars, vol_24 must be all NaN.

        24 bars produce only 23 log-returns, which is less than the
        required window of 24.
        """
        _import_volatility()
        ohlcv = _make_ohlcv(24)
        params = _default_params()
        instance = FEATURE_REGISTRY["vol_24"]()
        result = instance.compute(ohlcv, params)
        assert result.isna().all(), (
            "24 bars yield 23 logreturns < window 24 → all NaN expected"
        )
