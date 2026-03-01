"""Tests for volume features: logvol and dlogvol.

Task #012: Features de volume (logvol, dlogvol).
Covers all acceptance criteria: registration, numerical correctness,
NaN positions, config-driven epsilon, causality, edge cases.
"""

import math

import numpy as np
import pandas as pd
import pytest

import ai_trading.features.volume as _volume_module
from ai_trading.features.registry import FEATURE_REGISTRY, BaseFeature
from tests.conftest import clean_registry_with_reload

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ohlcv_with_volume(volume_values) -> pd.DataFrame:
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
# Registry reload fixture (isolate this module's features)
# ---------------------------------------------------------------------------

clean_feature_registry = clean_registry_with_reload(_volume_module)


# ---------------------------------------------------------------------------
# Default params
# ---------------------------------------------------------------------------

_EPSILON = 1e-8
_PARAMS = {"logvol_epsilon": _EPSILON}


# ===========================================================================
# TestRegistration
# ===========================================================================


class TestRegistration:
    """Acceptance: 2 classes enregistrées : logvol, dlogvol in FEATURE_REGISTRY."""

    def test_logvol_registered(self):
        assert "logvol" in FEATURE_REGISTRY

    def test_dlogvol_registered(self):
        assert "dlogvol" in FEATURE_REGISTRY

    def test_logvol_is_base_feature_subclass(self):
        assert issubclass(FEATURE_REGISTRY["logvol"], BaseFeature)

    def test_dlogvol_is_base_feature_subclass(self):
        assert issubclass(FEATURE_REGISTRY["dlogvol"], BaseFeature)


# ===========================================================================
# TestMinPeriods
# ===========================================================================


class TestMinPeriods:
    """logvol.min_periods=0, dlogvol.min_periods=1 (contract: leading NaN count)."""

    def test_logvol_min_periods_is_0(self):
        feature = FEATURE_REGISTRY["logvol"]()
        assert feature.min_periods(_PARAMS) == 0

    def test_dlogvol_min_periods_is_1(self):
        feature = FEATURE_REGISTRY["dlogvol"]()
        assert feature.min_periods(_PARAMS) == 1


# ===========================================================================
# TestLogVolNumerical
# ===========================================================================


class TestLogVolNumerical:
    """Acceptance: tests numériques avec valeurs calculées à la main."""

    def test_logvol_basic_values(self):
        """logvol(t) = log(V_t + epsilon) for known volumes."""
        volumes = [100.0, 200.0, 500.0, 1000.0]
        ohlcv = _make_ohlcv_with_volume(volumes)
        feature = FEATURE_REGISTRY["logvol"]()
        result = feature.compute(ohlcv, _PARAMS)

        for i, v in enumerate(volumes):
            expected = math.log(v + _EPSILON)
            assert result.iloc[i] == pytest.approx(expected, rel=1e-12)

    def test_logvol_zero_volume(self):
        """Acceptance: Volume nul -> logvol ~ log(epsilon) ~ -18.42."""
        volumes = [0.0, 100.0]
        ohlcv = _make_ohlcv_with_volume(volumes)
        feature = FEATURE_REGISTRY["logvol"]()
        result = feature.compute(ohlcv, _PARAMS)

        expected = math.log(_EPSILON)
        assert result.iloc[0] == pytest.approx(expected, rel=1e-12)
        # Verify the approximate value mentioned in acceptance criteria
        assert result.iloc[0] == pytest.approx(-18.42, abs=0.1)

    def test_logvol_all_zeros(self):
        """All zero volumes should all produce log(epsilon)."""
        volumes = [0.0, 0.0, 0.0]
        ohlcv = _make_ohlcv_with_volume(volumes)
        feature = FEATURE_REGISTRY["logvol"]()
        result = feature.compute(ohlcv, _PARAMS)

        expected = math.log(_EPSILON)
        for i in range(3):
            assert result.iloc[i] == pytest.approx(expected, rel=1e-12)

    def test_logvol_no_nan(self):
        """logvol produces no NaN (available from first bar)."""
        volumes = [1.0, 2.0, 3.0, 4.0, 5.0]
        ohlcv = _make_ohlcv_with_volume(volumes)
        feature = FEATURE_REGISTRY["logvol"]()
        result = feature.compute(ohlcv, _PARAMS)

        assert not result.isna().any()


# ===========================================================================
# TestDLogVolNumerical
# ===========================================================================


class TestDLogVolNumerical:
    """Acceptance: tests numériques avec valeurs calculées à la main."""

    def test_dlogvol_basic_values(self):
        """dlogvol(t) = logvol(t) - logvol(t-1) for t >= 1."""
        volumes = [100.0, 200.0, 500.0]
        ohlcv = _make_ohlcv_with_volume(volumes)
        feature = FEATURE_REGISTRY["dlogvol"]()
        result = feature.compute(ohlcv, _PARAMS)

        # t=0 should be NaN
        assert pd.isna(result.iloc[0])
        # t=1: log(200+eps) - log(100+eps)
        expected_1 = math.log(200.0 + _EPSILON) - math.log(100.0 + _EPSILON)
        assert result.iloc[1] == pytest.approx(expected_1, rel=1e-12)
        # t=2: log(500+eps) - log(200+eps)
        expected_2 = math.log(500.0 + _EPSILON) - math.log(200.0 + _EPSILON)
        assert result.iloc[2] == pytest.approx(expected_2, rel=1e-12)

    def test_dlogvol_nan_at_t0(self):
        """Acceptance: dlogvol NaN à t=0."""
        volumes = [50.0, 100.0, 150.0]
        ohlcv = _make_ohlcv_with_volume(volumes)
        feature = FEATURE_REGISTRY["dlogvol"]()
        result = feature.compute(ohlcv, _PARAMS)

        assert pd.isna(result.iloc[0])
        assert not pd.isna(result.iloc[1])

    def test_dlogvol_constant_volume_zero_diff(self):
        """Constant volume -> dlogvol = 0 for t >= 1."""
        volumes = [100.0, 100.0, 100.0, 100.0]
        ohlcv = _make_ohlcv_with_volume(volumes)
        feature = FEATURE_REGISTRY["dlogvol"]()
        result = feature.compute(ohlcv, _PARAMS)

        assert pd.isna(result.iloc[0])
        for i in range(1, 4):
            assert result.iloc[i] == pytest.approx(0.0, abs=1e-15)


# ===========================================================================
# TestConfigDriven
# ===========================================================================


class TestConfigDriven:
    """Acceptance: logvol_epsilon lu depuis params (pas hardcodé)."""

    def test_logvol_uses_epsilon_from_params(self):
        """Different epsilon values produce different results."""
        volumes = [0.0]
        ohlcv = _make_ohlcv_with_volume(volumes)
        feature = FEATURE_REGISTRY["logvol"]()

        result_default = feature.compute(ohlcv, {"logvol_epsilon": 1e-8})
        result_custom = feature.compute(ohlcv, {"logvol_epsilon": 1.0})

        assert result_default.iloc[0] == pytest.approx(math.log(1e-8), rel=1e-12)
        assert result_custom.iloc[0] == pytest.approx(math.log(1.0 + 0.0), rel=1e-12)
        assert result_default.iloc[0] != result_custom.iloc[0]

    def test_dlogvol_uses_epsilon_from_params(self):
        """DLogVolume also respects epsilon from params."""
        volumes = [0.0, 0.0]
        ohlcv = _make_ohlcv_with_volume(volumes)
        feature = FEATURE_REGISTRY["dlogvol"]()

        result_default = feature.compute(ohlcv, {"logvol_epsilon": 1e-8})
        result_custom = feature.compute(ohlcv, {"logvol_epsilon": 1.0})

        # With constant volume, dlogvol at t=1 should be 0 regardless of epsilon
        assert result_default.iloc[1] == pytest.approx(0.0, abs=1e-15)
        assert result_custom.iloc[1] == pytest.approx(0.0, abs=1e-15)

    def test_logvol_required_params_declared(self):
        """LogVolume declares logvol_epsilon in required_params."""
        cls = FEATURE_REGISTRY["logvol"]
        assert "logvol_epsilon" in cls.required_params

    def test_dlogvol_required_params_declared(self):
        """DLogVolume declares logvol_epsilon in required_params."""
        cls = FEATURE_REGISTRY["dlogvol"]
        assert "logvol_epsilon" in cls.required_params


# ===========================================================================
# TestCausality
# ===========================================================================


class TestCausality:
    """Acceptance: modifier volume[t > T] ne modifie pas les features [t <= T]."""

    def test_logvol_causality(self):
        """Modifying future volumes does not affect past logvol values."""
        volumes_orig = [100.0, 200.0, 300.0, 400.0, 500.0]
        ohlcv_orig = _make_ohlcv_with_volume(volumes_orig)
        feature = FEATURE_REGISTRY["logvol"]()
        result_orig = feature.compute(ohlcv_orig, _PARAMS)

        # Modify volume at t=3 and t=4 (future)
        volumes_modified = [100.0, 200.0, 300.0, 9999.0, 1.0]
        ohlcv_modified = _make_ohlcv_with_volume(volumes_modified)
        result_modified = feature.compute(ohlcv_modified, _PARAMS)

        # T=2: values at t=0,1,2 must be identical
        for t in range(3):
            assert result_orig.iloc[t] == result_modified.iloc[t]

    def test_dlogvol_causality(self):
        """Modifying future volumes does not affect past dlogvol values."""
        volumes_orig = [100.0, 200.0, 300.0, 400.0, 500.0]
        ohlcv_orig = _make_ohlcv_with_volume(volumes_orig)
        feature = FEATURE_REGISTRY["dlogvol"]()
        result_orig = feature.compute(ohlcv_orig, _PARAMS)

        # Modify volume at t=3 and t=4
        volumes_modified = [100.0, 200.0, 300.0, 9999.0, 1.0]
        ohlcv_modified = _make_ohlcv_with_volume(volumes_modified)
        result_modified = feature.compute(ohlcv_modified, _PARAMS)

        # T=2: values at t=0,1,2 must be identical
        for t in range(3):
            if pd.isna(result_orig.iloc[t]):
                assert pd.isna(result_modified.iloc[t])
            else:
                assert result_orig.iloc[t] == result_modified.iloc[t]


# ===========================================================================
# TestOutputShape
# ===========================================================================


class TestOutputShape:
    """Output is pd.Series with correct length, index, and name."""

    def test_logvol_returns_series(self):
        ohlcv = _make_ohlcv_with_volume([1.0, 2.0, 3.0])
        feature = FEATURE_REGISTRY["logvol"]()
        result = feature.compute(ohlcv, _PARAMS)
        assert isinstance(result, pd.Series)

    def test_logvol_same_length(self):
        volumes = [1.0, 2.0, 3.0, 4.0]
        ohlcv = _make_ohlcv_with_volume(volumes)
        feature = FEATURE_REGISTRY["logvol"]()
        result = feature.compute(ohlcv, _PARAMS)
        assert len(result) == len(volumes)

    def test_logvol_same_index(self):
        ohlcv = _make_ohlcv_with_volume([1.0, 2.0, 3.0])
        feature = FEATURE_REGISTRY["logvol"]()
        result = feature.compute(ohlcv, _PARAMS)
        pd.testing.assert_index_equal(result.index, ohlcv.index)

    def test_dlogvol_same_length(self):
        volumes = [1.0, 2.0, 3.0, 4.0]
        ohlcv = _make_ohlcv_with_volume(volumes)
        feature = FEATURE_REGISTRY["dlogvol"]()
        result = feature.compute(ohlcv, _PARAMS)
        assert len(result) == len(volumes)

    def test_dlogvol_same_index(self):
        ohlcv = _make_ohlcv_with_volume([1.0, 2.0, 3.0])
        feature = FEATURE_REGISTRY["dlogvol"]()
        result = feature.compute(ohlcv, _PARAMS)
        pd.testing.assert_index_equal(result.index, ohlcv.index)

    def test_logvol_series_name(self):
        ohlcv = _make_ohlcv_with_volume([1.0, 2.0])
        feature = FEATURE_REGISTRY["logvol"]()
        result = feature.compute(ohlcv, _PARAMS)
        assert result.name == "logvol"

    def test_dlogvol_series_name(self):
        ohlcv = _make_ohlcv_with_volume([1.0, 2.0])
        feature = FEATURE_REGISTRY["dlogvol"]()
        result = feature.compute(ohlcv, _PARAMS)
        assert result.name == "dlogvol"


# ===========================================================================
# TestEdgeCases
# ===========================================================================


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_single_bar_logvol(self):
        """Single bar: logvol is computable."""
        ohlcv = _make_ohlcv_with_volume([42.0])
        feature = FEATURE_REGISTRY["logvol"]()
        result = feature.compute(ohlcv, _PARAMS)
        assert len(result) == 1
        assert not pd.isna(result.iloc[0])
        assert result.iloc[0] == pytest.approx(math.log(42.0 + _EPSILON), rel=1e-12)

    def test_single_bar_dlogvol(self):
        """Single bar: dlogvol → NaN (needs 2 bars for first valid)."""
        ohlcv = _make_ohlcv_with_volume([42.0])
        feature = FEATURE_REGISTRY["dlogvol"]()
        result = feature.compute(ohlcv, _PARAMS)
        assert len(result) == 1
        assert pd.isna(result.iloc[0])

    def test_two_bars_dlogvol_first_valid(self):
        """Two bars: dlogvol has first valid value at t=1."""
        volumes = [10.0, 20.0]
        ohlcv = _make_ohlcv_with_volume(volumes)
        feature = FEATURE_REGISTRY["dlogvol"]()
        result = feature.compute(ohlcv, _PARAMS)
        assert pd.isna(result.iloc[0])
        expected = math.log(20.0 + _EPSILON) - math.log(10.0 + _EPSILON)
        assert result.iloc[1] == pytest.approx(expected, rel=1e-12)

    def test_empty_dataframe_logvol(self):
        """Empty DataFrame returns empty Series."""
        ohlcv = _make_ohlcv_with_volume([])
        feature = FEATURE_REGISTRY["logvol"]()
        result = feature.compute(ohlcv, _PARAMS)
        assert isinstance(result, pd.Series)
        assert len(result) == 0

    def test_empty_dataframe_dlogvol(self):
        """Empty DataFrame returns empty Series."""
        ohlcv = _make_ohlcv_with_volume([])
        feature = FEATURE_REGISTRY["dlogvol"]()
        result = feature.compute(ohlcv, _PARAMS)
        assert isinstance(result, pd.Series)
        assert len(result) == 0

    def test_very_large_volume(self):
        """Very large volumes do not cause overflow."""
        volumes = [1e18, 1e18]
        ohlcv = _make_ohlcv_with_volume(volumes)
        feature = FEATURE_REGISTRY["logvol"]()
        result = feature.compute(ohlcv, _PARAMS)
        assert np.isfinite(result.iloc[0])
        assert result.iloc[0] == pytest.approx(math.log(1e18 + _EPSILON), rel=1e-12)

    def test_logvol_zero_epsilon_raises(self):
        """epsilon=0 must raise ValueError."""
        ohlcv = _make_ohlcv_with_volume([100.0])
        feature = FEATURE_REGISTRY["logvol"]()
        with pytest.raises(ValueError, match="logvol_epsilon must be > 0"):
            feature.compute(ohlcv, {"logvol_epsilon": 0.0})

    def test_logvol_negative_epsilon_raises(self):
        """Negative epsilon must raise ValueError."""
        ohlcv = _make_ohlcv_with_volume([100.0])
        feature = FEATURE_REGISTRY["logvol"]()
        with pytest.raises(ValueError, match="logvol_epsilon must be > 0"):
            feature.compute(ohlcv, {"logvol_epsilon": -1e-8})

    def test_dlogvol_zero_epsilon_raises(self):
        """epsilon=0 must raise ValueError for dlogvol too."""
        ohlcv = _make_ohlcv_with_volume([100.0, 200.0])
        feature = FEATURE_REGISTRY["dlogvol"]()
        with pytest.raises(ValueError, match="logvol_epsilon must be > 0"):
            feature.compute(ohlcv, {"logvol_epsilon": 0.0})
