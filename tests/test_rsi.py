"""Tests for RSI feature with Wilder smoothing.

Task #010: Feature RSI avec lissage de Wilder (rsi_14).
Covers all acceptance criteria: registration, numerical correctness,
range [0, 100], edge cases, config-driven params, NaN positions, causality.
"""

import numpy as np
import pandas as pd
import pytest

from ai_trading.features.registry import FEATURE_REGISTRY, BaseFeature

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_registry():
    """Save, clear, and restore FEATURE_REGISTRY around each test."""
    saved = dict(FEATURE_REGISTRY)
    FEATURE_REGISTRY.clear()
    yield
    FEATURE_REGISTRY.clear()
    FEATURE_REGISTRY.update(saved)


@pytest.fixture
def rsi_class():
    """Import RSI14 and ensure it is in the registry via the decorator mechanism."""
    from ai_trading.features.rsi import RSI14

    # The module may be imported here for the first time, which fires the
    # @register_feature decorator.  On subsequent tests _clean_registry clears
    # the dict, so we re-register through the decorator (not a raw dict insert)
    # to validate the registration mechanism.
    if "rsi_14" not in FEATURE_REGISTRY:
        from ai_trading.features.registry import register_feature

        register_feature("rsi_14")(RSI14)
    return RSI14


@pytest.fixture
def rsi_instance(rsi_class):
    """Return an instantiated RSI14 object."""
    return rsi_class()


@pytest.fixture
def default_params():
    """Default feature params matching configs/default.yaml."""
    return {"rsi_period": 14, "rsi_epsilon": 1e-12}


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


def _compute_rsi_reference(close_values, n=14, epsilon=1e-12):
    """Pure-Python reference implementation of Wilder RSI.

    .. note::
        This mirrors the production algorithm to validate internal
        consistency.  Independent validation of numerical correctness
        is provided by ``TestRSINumerical.test_rsi_hand_computed_small``
        which uses hand-calculated expected values.
    """
    close = list(close_values)
    length = len(close)
    result = [float("nan")] * length

    if length < n + 1:
        return result

    # Compute deltas
    deltas = [close[i] - close[i - 1] for i in range(1, length)]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]

    # SMA initialisation over first n periods (indices 0..n-1 in gains/losses)
    ag = sum(gains[:n]) / n
    al = sum(losses[:n]) / n

    # RSI at bar n
    if ag < epsilon and al < epsilon:
        result[n] = 50.0
    else:
        rs = ag / (al + epsilon)
        result[n] = 100.0 - 100.0 / (1.0 + rs)

    # Wilder smoothing for bars n+1, n+2, ...
    for i in range(n, len(gains)):
        ag = ((n - 1) * ag + gains[i]) / n
        al = ((n - 1) * al + losses[i]) / n
        bar_idx = i + 1
        if ag < epsilon and al < epsilon:
            result[bar_idx] = 50.0
        else:
            rs = ag / (al + epsilon)
            result[bar_idx] = 100.0 - 100.0 / (1.0 + rs)

    return result


# ===========================================================================
# AC-1: Class registered as rsi_14 in FEATURE_REGISTRY
# ===========================================================================


class TestRSIRegistration:
    """#010 AC-1: rsi_14 is registered in FEATURE_REGISTRY."""

    def test_rsi_14_in_registry(self, rsi_class):
        assert "rsi_14" in FEATURE_REGISTRY

    def test_rsi_14_maps_to_rsi_class(self, rsi_class):
        assert FEATURE_REGISTRY["rsi_14"] is rsi_class

    def test_rsi_14_is_base_feature_subclass(self, rsi_class):
        assert issubclass(rsi_class, BaseFeature)

    def test_rsi_14_required_params(self, rsi_class):
        assert "rsi_period" in rsi_class.required_params
        assert "rsi_epsilon" in rsi_class.required_params


# ===========================================================================
# AC-2: Numerical tests on known series (hand-computed values)
# ===========================================================================


class TestRSINumerical:
    """#010 AC-2: Numeric correctness on known series."""

    def test_rsi_simple_alternating(self, rsi_instance, default_params):
        """Alternating up/down by 1: gains and losses are equal → RSI ≈ 50."""
        # Build a series that alternates: 100, 101, 100, 101, ...
        close = []
        for i in range(30):
            close.append(100.0 + (i % 2))
        ohlcv = _make_ohlcv(close)
        result = rsi_instance.compute(ohlcv, default_params)

        # After warmup, RSI should be close to 50
        valid = result.iloc[14:]
        assert all(np.isfinite(valid))
        # For alternating series, AG ≈ AL, so RSI oscillates around 50.
        # Due to Wilder smoothing, the oscillation amplitude is ~3.6 for n=14.
        np.testing.assert_allclose(valid.values, 50.0, atol=4.0)

    def test_rsi_matches_reference(self, rsi_instance, default_params):
        """Compare output against pure-Python Wilder reference."""
        rng = np.random.default_rng(42)
        close = 100.0 + np.cumsum(rng.standard_normal(50) * 0.5)
        ohlcv = _make_ohlcv(close)
        result = rsi_instance.compute(ohlcv, default_params)

        expected = _compute_rsi_reference(close.tolist(), n=14, epsilon=1e-12)

        for i in range(len(expected)):
            if np.isnan(expected[i]):
                assert np.isnan(result.iloc[i]), f"Expected NaN at index {i}"
            else:
                np.testing.assert_allclose(
                    result.iloc[i], expected[i], atol=1e-10,
                    err_msg=f"Mismatch at index {i}",
                )

    def test_rsi_hand_computed_small(self, rsi_instance):
        """Hand-computed RSI on a small series with period=3."""
        # Use a small period to make hand-computation tractable
        params = {"rsi_period": 3, "rsi_epsilon": 1e-12}
        # close = [10, 11, 12, 11, 13]
        # deltas: [+1, +1, -1, +2]
        # gains:  [1, 1, 0, 2]
        # losses: [0, 0, 1, 0]
        # SMA init (first 3): AG_3 = (1+1+0)/3 = 2/3, AL_3 = (0+0+1)/3 = 1/3
        # RSI_3 = 100 - 100/(1 + (2/3)/(1/3 + eps)) ≈ 100 - 100/(1 + 2) = 100 - 33.33 = 66.67
        # Wilder at bar 4: AG = (2*(2/3) + 2)/3 = (4/3 + 2)/3 = (10/3)/3 = 10/9
        #                   AL = (2*(1/3) + 0)/3 = (2/3)/3 = 2/9
        # RSI_4 = 100 - 100/(1 + (10/9)/(2/9 + eps)) ≈ 100 - 100/(1 + 5) = 100 - 16.67 = 83.33
        close = [10.0, 11.0, 12.0, 11.0, 13.0]
        ohlcv = _make_ohlcv(close)
        result = rsi_instance.compute(ohlcv, params)

        # Bar 0, 1, 2: NaN  (need period=3, so first valid at bar 3)
        assert np.isnan(result.iloc[0])
        assert np.isnan(result.iloc[1])
        assert np.isnan(result.iloc[2])

        # Bar 3: RSI = 100 - 100/(1 + 2) = 66.6667
        np.testing.assert_allclose(result.iloc[3], 100.0 - 100.0 / 3.0, atol=1e-8)

        # Bar 4: RSI = 100 - 100/(1 + 5) = 83.3333
        np.testing.assert_allclose(result.iloc[4], 100.0 - 100.0 / 6.0, atol=1e-8)


# ===========================================================================
# AC-3: Result in [0, 100] for all valid entries
# ===========================================================================


class TestRSIRange:
    """#010 AC-3: RSI values are in [0, 100]."""

    def test_random_series_bounded(self, rsi_instance, default_params):
        """Random walk series — all valid RSI values within [0, 100]."""
        rng = np.random.default_rng(123)
        close = 100.0 + np.cumsum(rng.standard_normal(200) * 2.0)
        ohlcv = _make_ohlcv(close)
        result = rsi_instance.compute(ohlcv, default_params)

        valid = result.dropna()
        assert len(valid) > 0
        assert (valid >= 0.0).all()
        assert (valid <= 100.0).all()

    def test_extreme_values_bounded(self, rsi_instance, default_params):
        """Large jumps — RSI still in [0, 100]."""
        close = [100.0] + [100.0 + i * 1000.0 for i in range(1, 20)]
        close += [close[-1] - i * 500.0 for i in range(1, 20)]
        ohlcv = _make_ohlcv(close)
        result = rsi_instance.compute(ohlcv, default_params)

        valid = result.dropna()
        assert (valid >= 0.0).all()
        assert (valid <= 100.0).all()


# ===========================================================================
# AC-4: Edge cases — monotone and constant series
# ===========================================================================


class TestRSIEdgeCases:
    """#010 AC-4: Monotone increasing → 100, decreasing → 0, constant → 50."""

    def test_monotone_increasing(self, rsi_instance, default_params):
        """Strictly increasing close → RSI converges to 100."""
        close = [100.0 + i for i in range(30)]
        ohlcv = _make_ohlcv(close)
        result = rsi_instance.compute(ohlcv, default_params)

        valid = result.dropna()
        # All gains, no losses → RSI = 100
        np.testing.assert_allclose(valid.values, 100.0, atol=1e-6)

    def test_monotone_decreasing(self, rsi_instance, default_params):
        """Strictly decreasing close → RSI converges to 0."""
        close = [200.0 - i for i in range(30)]
        ohlcv = _make_ohlcv(close)
        result = rsi_instance.compute(ohlcv, default_params)

        valid = result.dropna()
        # All losses, no gains → RSI ≈ 0
        np.testing.assert_allclose(valid.values, 0.0, atol=1e-6)

    def test_constant_series(self, rsi_instance, default_params):
        """Constant close → RSI = 50 (AG = AL = 0)."""
        close = [100.0] * 30
        ohlcv = _make_ohlcv(close)
        result = rsi_instance.compute(ohlcv, default_params)

        valid = result.dropna()
        np.testing.assert_allclose(valid.values, 50.0, atol=1e-10)


# ===========================================================================
# AC-5: Config-driven — params read from config, not hardcoded
# ===========================================================================


class TestRSIConfigDriven:
    """#010 AC-5: rsi_period and rsi_epsilon are read from params."""

    def test_different_period(self, rsi_instance):
        """Changing rsi_period changes NaN warmup positions and computed output."""
        params_7 = {"rsi_period": 7, "rsi_epsilon": 1e-12}
        rng = np.random.default_rng(99)
        close = 100.0 + np.cumsum(rng.standard_normal(30))
        ohlcv = _make_ohlcv(close)

        result = rsi_instance.compute(ohlcv, params_7)

        # With period=7, first valid at bar 7 (0-based)
        assert np.isnan(result.iloc[6])
        assert np.isfinite(result.iloc[7])

    def test_different_epsilon(self, rsi_instance):
        """Different epsilon values produce slightly different outputs on edge cases."""
        close = [100.0] * 20 + [101.0] * 10  # mostly constant then step up
        ohlcv = _make_ohlcv(close)

        params_small_eps = {"rsi_period": 14, "rsi_epsilon": 1e-20}
        params_large_eps = {"rsi_period": 14, "rsi_epsilon": 1.0}

        result_small = rsi_instance.compute(ohlcv, params_small_eps)
        result_large = rsi_instance.compute(ohlcv, params_large_eps)

        # With a big epsilon, the results should differ from small epsilon
        # The constant prefix has AG=AL=0 → RSI=50, but after the step
        # the epsilon changes the RS denominator
        valid_small = result_small.dropna()
        valid_large = result_large.dropna()

        # At least one value should differ because of the epsilon in denominator
        assert not np.allclose(valid_small.values, valid_large.values)

    def test_missing_rsi_period_raises(self, rsi_instance):
        """Missing rsi_period in params raises KeyError."""
        ohlcv = _make_ohlcv([100.0] * 20)
        with pytest.raises(KeyError, match="rsi_period"):
            rsi_instance.compute(ohlcv, {"rsi_epsilon": 1e-12})

    def test_missing_rsi_epsilon_raises(self, rsi_instance):
        """Missing rsi_epsilon in params raises KeyError."""
        ohlcv = _make_ohlcv([100.0] * 20)
        with pytest.raises(KeyError, match="rsi_epsilon"):
            rsi_instance.compute(ohlcv, {"rsi_period": 14})

    def test_invalid_rsi_period_zero_raises(self, rsi_instance):
        """rsi_period=0 raises ValueError."""
        ohlcv = _make_ohlcv([100.0] * 20)
        with pytest.raises(ValueError, match="rsi_period must be >= 1"):
            rsi_instance.compute(ohlcv, {"rsi_period": 0, "rsi_epsilon": 1e-12})

    def test_invalid_rsi_period_negative_raises(self, rsi_instance):
        """rsi_period=-1 raises ValueError."""
        ohlcv = _make_ohlcv([100.0] * 20)
        with pytest.raises(ValueError, match="rsi_period must be >= 1"):
            rsi_instance.compute(ohlcv, {"rsi_period": -1, "rsi_epsilon": 1e-12})

    def test_invalid_rsi_epsilon_zero_raises(self, rsi_instance):
        """rsi_epsilon=0 raises ValueError."""
        ohlcv = _make_ohlcv([100.0] * 20)
        with pytest.raises(ValueError, match="rsi_epsilon must be > 0"):
            rsi_instance.compute(ohlcv, {"rsi_period": 14, "rsi_epsilon": 0.0})

    def test_invalid_rsi_epsilon_negative_raises(self, rsi_instance):
        """rsi_epsilon=-1e-12 raises ValueError."""
        ohlcv = _make_ohlcv([100.0] * 20)
        with pytest.raises(ValueError, match="rsi_epsilon must be > 0"):
            rsi_instance.compute(ohlcv, {"rsi_period": 14, "rsi_epsilon": -1e-12})


# ===========================================================================
# AC-6: NaN at positions t < rsi_period
# ===========================================================================


class TestRSINaN:
    """#010 AC-6: NaN at positions t < rsi_period."""

    def test_nan_before_period_14(self, rsi_instance, default_params):
        """First 14 bars (indices 0..13) should be NaN with period=14."""
        rng = np.random.default_rng(7)
        close = 100.0 + np.cumsum(rng.standard_normal(30))
        ohlcv = _make_ohlcv(close)
        result = rsi_instance.compute(ohlcv, default_params)

        # Indices 0..13 are NaN
        for i in range(14):
            assert np.isnan(result.iloc[i]), f"Expected NaN at index {i}"

        # Index 14 is the first valid value
        assert np.isfinite(result.iloc[14])

    def test_nan_before_period_7(self, rsi_instance):
        """With period=7, first 7 bars are NaN."""
        params = {"rsi_period": 7, "rsi_epsilon": 1e-12}
        rng = np.random.default_rng(8)
        close = 100.0 + np.cumsum(rng.standard_normal(20))
        ohlcv = _make_ohlcv(close)
        result = rsi_instance.compute(ohlcv, params)

        for i in range(7):
            assert np.isnan(result.iloc[i]), f"Expected NaN at index {i}"
        assert np.isfinite(result.iloc[7])

    def test_too_short_series_all_nan(self, rsi_instance, default_params):
        """Series shorter than period+1 → all NaN."""
        close = [100.0] * 14  # Need 15 bars for period=14
        ohlcv = _make_ohlcv(close)
        result = rsi_instance.compute(ohlcv, default_params)

        assert result.isna().all()


# ===========================================================================
# AC-7: Causality — modifying future data does not affect past RSI
# ===========================================================================


class TestRSICausality:
    """#010 AC-7: Modifying close[t > T] does not change rsi_14[t <= T]."""

    def test_causality_unchanged(self, rsi_instance, default_params):
        """Perturbation of future prices must not affect past RSI values."""
        rng = np.random.default_rng(55)
        close_original = list(100.0 + np.cumsum(rng.standard_normal(40)))

        # Compute RSI on original
        ohlcv_orig = _make_ohlcv(close_original)
        result_orig = rsi_instance.compute(ohlcv_orig, default_params)

        # Perturb only close[t > T] where T = 25
        t_split = 25
        close_perturbed = close_original.copy()
        for i in range(t_split + 1, len(close_perturbed)):
            close_perturbed[i] += 1000.0  # large perturbation

        ohlcv_pert = _make_ohlcv(close_perturbed)
        result_pert = rsi_instance.compute(ohlcv_pert, default_params)

        # RSI at t <= T must be identical
        for i in range(t_split + 1):
            v_orig = result_orig.iloc[i]
            v_pert = result_pert.iloc[i]
            if np.isnan(v_orig):
                assert np.isnan(v_pert), f"Expected NaN at index {i}"
            else:
                np.testing.assert_allclose(
                    v_pert, v_orig, atol=1e-15,
                    err_msg=f"Causality violation at index {i}",
                )

        # RSI at t > T should differ (sanity check that perturbation had effect)
        changed = False
        for i in range(t_split + 1, len(close_original)):
            if (
                np.isfinite(result_orig.iloc[i])
                and np.isfinite(result_pert.iloc[i])
                and not np.isclose(result_orig.iloc[i], result_pert.iloc[i])
            ):
                changed = True
                break
        assert changed, "Perturbation had no effect — sanity check failed"


# ===========================================================================
# AC-8 + additional: Error and boundary tests
# ===========================================================================


class TestRSIErrors:
    """#010 AC-8: Error and boundary scenarios."""

    def test_min_periods_property(self, rsi_instance):
        """#023: min_periods = number of leading NaN = 14 (not rsi_period + 1)."""
        assert rsi_instance.min_periods({"rsi_period": 14, "rsi_epsilon": 1e-12}) == 14

    def test_output_is_series(self, rsi_instance, default_params):
        """compute() returns a pd.Series."""
        close = [100.0 + i for i in range(30)]
        ohlcv = _make_ohlcv(close)
        result = rsi_instance.compute(ohlcv, default_params)
        assert isinstance(result, pd.Series)

    def test_output_index_matches_input(self, rsi_instance, default_params):
        """Output Series has the same index as input OHLCV."""
        close = [100.0 + i for i in range(30)]
        ohlcv = _make_ohlcv(close)
        result = rsi_instance.compute(ohlcv, default_params)
        pd.testing.assert_index_equal(result.index, ohlcv.index)

    def test_output_length_matches_input(self, rsi_instance, default_params):
        """Output has the same length as input."""
        close = [100.0 + i for i in range(30)]
        ohlcv = _make_ohlcv(close)
        result = rsi_instance.compute(ohlcv, default_params)
        assert len(result) == len(ohlcv)

    def test_single_bar_all_nan(self, rsi_instance, default_params):
        """Single-bar OHLCV → all NaN."""
        ohlcv = _make_ohlcv([100.0])
        result = rsi_instance.compute(ohlcv, default_params)
        assert result.isna().all()

    def test_exactly_period_plus_one_bars(self, rsi_instance, default_params):
        """Exactly 15 bars (period+1) → one valid value at the end."""
        close = [100.0 + i * 0.5 for i in range(15)]
        ohlcv = _make_ohlcv(close)
        result = rsi_instance.compute(ohlcv, default_params)

        assert result.iloc[:14].isna().all()
        assert np.isfinite(result.iloc[14])

    def test_empty_dataframe(self, rsi_instance, default_params):
        """Empty OHLCV DataFrame → empty Series (no crash)."""
        ohlcv = _make_ohlcv([])
        result = rsi_instance.compute(ohlcv, default_params)
        assert len(result) == 0
        assert isinstance(result, pd.Series)

    def test_rsi_period_1(self, rsi_instance):
        """Boundary: rsi_period=1 — needs 2 bars, first valid at bar 1."""
        params = {"rsi_period": 1, "rsi_epsilon": 1e-12}
        # close = [100, 102, 101, 103]
        # deltas: [+2, -1, +2]
        # period=1 → SMA init over 1 value: AG_1 = gains[0]=2, AL_1 = losses[0]=0
        # RSI_1 = 100 - 100/(1 + 2/(0+eps)) ≈ 100
        # Wilder bar 2: AG = (0*2 + 0)/1 = 0 (wait — (n-1)*AG + gain)/n = (0*2+0)/1=0
        #   actually gains[1]=0, losses[1]=1
        #   AG = (0*2 + 0)/1 = 0, AL = (0*0 + 1)/1 = 1
        #   RSI_2 = 100 - 100/(1 + 0/(1+eps)) ≈ 0
        # Wilder bar 3: gains[2]=2, losses[2]=0
        #   AG = (0*0 + 2)/1 = 2, AL = (0*1 + 0)/1 = 0
        #   RSI_3 = 100 - 100/(1 + 2/(0+eps)) ≈ 100
        close = [100.0, 102.0, 101.0, 103.0]
        ohlcv = _make_ohlcv(close)
        result = rsi_instance.compute(ohlcv, params)

        # Bar 0: NaN
        assert np.isnan(result.iloc[0])
        # Bar 1: first valid
        assert np.isfinite(result.iloc[1])
        np.testing.assert_allclose(result.iloc[1], 100.0, atol=1e-6)
        # Bar 2: pure loss → RSI ≈ 0
        np.testing.assert_allclose(result.iloc[2], 0.0, atol=1e-6)
        # Bar 3: pure gain → RSI ≈ 100
        np.testing.assert_allclose(result.iloc[3], 100.0, atol=1e-6)
