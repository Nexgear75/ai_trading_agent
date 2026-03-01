"""Tests for warmup validation — apply_warmup function.

Task #014 — WS-3: Warmup et validation de causalité.

Tests cover:
- Warmup mask: first min_warmup rows always False in final mask.
- AND combination of warmup mask and valid_mask (gap mask).
- ValueError when NaN found in valid zone (post-warmup).
- min_warmup passed by caller (config-driven: caller reads config.window.min_warmup).
- min_warmup < max(min_periods) → ValueError.
- Nominal: 500 bars, min_warmup=200, no gaps → 300 valid samples.
- NaN injected post-warmup → error raised.
- Combination with gaps in data → correct mask.
- Edge cases and boundary conditions.
"""

import numpy as np
import pandas as pd
import pytest

from ai_trading.features.warmup import apply_warmup

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeFeature:
    """Minimal fake feature with a configurable min_periods."""

    def __init__(self, mp: int):
        self._mp = mp

    def min_periods(self, params: dict) -> int:
        return self._mp


def _make_features_df(n: int, n_features: int = 3, nan_prefix: int = 0) -> pd.DataFrame:
    """Build a features DataFrame with n rows and optional leading NaNs."""
    rng = np.random.default_rng(42)
    data = rng.standard_normal((n, n_features))
    if nan_prefix > 0:
        data[:nan_prefix, :] = np.nan
    idx = pd.date_range("2024-01-01", periods=n, freq="1h")
    cols = [f"feat_{i}" for i in range(n_features)]
    return pd.DataFrame(data, index=idx, columns=cols)


# ---------------------------------------------------------------------------
# Nominal cases
# ---------------------------------------------------------------------------


class TestNominal:
    """Nominal apply_warmup scenarios."""

    def test_warmup_200_bars_500_no_gaps(self):
        """#014 AC: min_warmup=200, 500 bars no gaps → 300 valid samples."""
        n = 500
        min_warmup = 200
        features_df = _make_features_df(n, nan_prefix=100)
        valid_mask = np.ones(n, dtype=bool)
        instances = [_FakeFeature(100)]

        final_mask = apply_warmup(features_df, valid_mask, min_warmup, instances, {})

        assert final_mask.dtype == bool
        assert final_mask.shape == (n,)
        assert final_mask.sum() == 300

    def test_first_min_warmup_rows_always_false(self):
        """#014 AC: The first min_warmup rows are always False."""
        n = 100
        min_warmup = 30
        features_df = _make_features_df(n, nan_prefix=10)
        valid_mask = np.ones(n, dtype=bool)
        instances = [_FakeFeature(10)]

        final_mask = apply_warmup(features_df, valid_mask, min_warmup, instances, {})

        assert not np.any(final_mask[:min_warmup])
        assert np.all(final_mask[min_warmup:])

    def test_final_mask_is_and_combination(self):
        """#014 AC: final_mask = warmup_mask AND valid_mask."""
        n = 100
        min_warmup = 20
        features_df = _make_features_df(n, nan_prefix=10)
        valid_mask = np.ones(n, dtype=bool)
        # Invalidate some rows in valid_mask beyond warmup
        valid_mask[50] = False
        valid_mask[70] = False
        instances = [_FakeFeature(10)]

        final_mask = apply_warmup(features_df, valid_mask, min_warmup, instances, {})

        # Warmup zone: all False
        assert not np.any(final_mask[:min_warmup])
        # Post-warmup: respects valid_mask
        assert not final_mask[50]
        assert not final_mask[70]
        # Other post-warmup rows: True
        expected_true = set(range(min_warmup, n)) - {50, 70}
        for i in expected_true:
            assert final_mask[i], f"Expected True at index {i}"


class TestCombinationWithGaps:
    """#014 AC: Combination with gaps in data → correct mask."""

    def test_gap_in_valid_mask_combined(self):
        """Gaps in valid_mask are combined with warmup."""
        n = 200
        min_warmup = 50
        features_df = _make_features_df(n, nan_prefix=30)
        # Simulate a gap invalidating rows 80-90
        valid_mask = np.ones(n, dtype=bool)
        valid_mask[80:91] = False
        instances = [_FakeFeature(30)]

        final_mask = apply_warmup(features_df, valid_mask, min_warmup, instances, {})

        # Warmup zone: all False
        assert not np.any(final_mask[:min_warmup])
        # Gap zone: all False
        assert not np.any(final_mask[80:91])
        # Valid zone outside warmup and gap: True
        assert np.all(final_mask[min_warmup:80])
        assert np.all(final_mask[91:])

    def test_all_invalid_in_valid_mask(self):
        """If valid_mask is all False, final mask is all False."""
        n = 100
        min_warmup = 20
        features_df = _make_features_df(n, nan_prefix=10)
        valid_mask = np.zeros(n, dtype=bool)
        instances = [_FakeFeature(10)]

        final_mask = apply_warmup(features_df, valid_mask, min_warmup, instances, {})

        assert not np.any(final_mask)


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestErrors:
    """Error handling in apply_warmup."""

    def test_nan_in_valid_zone_raises(self):
        """#014 AC: NaN injected post-warmup → ValueError."""
        n = 100
        min_warmup = 20
        features_df = _make_features_df(n, nan_prefix=10)
        # Inject NaN in the valid zone (post-warmup)
        features_df.iloc[50, 0] = np.nan
        valid_mask = np.ones(n, dtype=bool)
        instances = [_FakeFeature(10)]

        with pytest.raises(ValueError, match="NaN"):
            apply_warmup(features_df, valid_mask, min_warmup, instances, {})

    def test_nan_in_multiple_columns_raises(self):
        """NaN in any column of valid zone → ValueError."""
        n = 100
        min_warmup = 20
        features_df = _make_features_df(n, nan_prefix=10)
        # NaN in second column only
        features_df.iloc[60, 1] = np.nan
        valid_mask = np.ones(n, dtype=bool)
        instances = [_FakeFeature(10)]

        with pytest.raises(ValueError, match="NaN"):
            apply_warmup(features_df, valid_mask, min_warmup, instances, {})

    def test_min_warmup_less_than_max_min_periods_raises(self):
        """#014 AC: min_warmup < max(min_periods) → ValueError."""
        n = 100
        min_warmup = 10
        features_df = _make_features_df(n, nan_prefix=20)
        valid_mask = np.ones(n, dtype=bool)
        # max(min_periods) = 20 > min_warmup = 10
        instances = [_FakeFeature(5), _FakeFeature(20)]

        with pytest.raises(ValueError, match="min_warmup"):
            apply_warmup(features_df, valid_mask, min_warmup, instances, {})

    def test_nan_in_warmup_zone_is_ok(self):
        """NaN in warmup zone (masked out) should NOT raise."""
        n = 100
        min_warmup = 30
        features_df = _make_features_df(n, nan_prefix=25)
        valid_mask = np.ones(n, dtype=bool)
        instances = [_FakeFeature(25)]

        # Should not raise — NaNs are all in the warmup zone
        final_mask = apply_warmup(features_df, valid_mask, min_warmup, instances, {})
        assert final_mask.sum() == n - min_warmup

    def test_nan_in_gap_zone_is_ok(self):
        """NaN in a gap-masked zone should NOT raise."""
        n = 100
        min_warmup = 20
        features_df = _make_features_df(n, nan_prefix=10)
        # Mark row 50 as invalid in valid_mask (simulating gap)
        valid_mask = np.ones(n, dtype=bool)
        valid_mask[50] = False
        # Inject NaN at row 50 (masked out by valid_mask)
        features_df.iloc[50, 0] = np.nan
        instances = [_FakeFeature(10)]

        # Should not raise — NaN is in a masked-out row
        final_mask = apply_warmup(features_df, valid_mask, min_warmup, instances, {})
        assert not final_mask[50]

    def test_missing_params_key_raises_valueerror(self):
        """Feature needing params key but params={} → ValueError (not KeyError)."""
        n = 100
        min_warmup = 20
        features_df = _make_features_df(n, nan_prefix=10)
        valid_mask = np.ones(n, dtype=bool)

        class _ParamFeature:
            def min_periods(self, params: dict) -> int:
                return params["rsi_period"]

        instances = [_ParamFeature()]

        with pytest.raises(ValueError, match="params is missing a key"):
            apply_warmup(features_df, valid_mask, min_warmup, instances, {})


# ---------------------------------------------------------------------------
# Edge / boundary cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge and boundary conditions."""

    def test_min_warmup_equals_max_min_periods(self):
        """min_warmup == max(min_periods) is valid (no error)."""
        n = 100
        min_warmup = 20
        features_df = _make_features_df(n, nan_prefix=20)
        valid_mask = np.ones(n, dtype=bool)
        instances = [_FakeFeature(20), _FakeFeature(10)]

        final_mask = apply_warmup(features_df, valid_mask, min_warmup, instances, {})
        assert final_mask.sum() == n - min_warmup

    def test_min_warmup_equals_n(self):
        """min_warmup == n → all rows masked out (0 valid)."""
        n = 50
        min_warmup = 50
        features_df = _make_features_df(n, nan_prefix=10)
        valid_mask = np.ones(n, dtype=bool)
        instances = [_FakeFeature(10)]

        final_mask = apply_warmup(features_df, valid_mask, min_warmup, instances, {})
        assert final_mask.sum() == 0

    def test_min_warmup_greater_than_n(self):
        """min_warmup > n → all rows masked out (0 valid)."""
        n = 30
        min_warmup = 100
        features_df = _make_features_df(n, nan_prefix=10)
        valid_mask = np.ones(n, dtype=bool)
        instances = [_FakeFeature(10)]

        final_mask = apply_warmup(features_df, valid_mask, min_warmup, instances, {})
        assert final_mask.sum() == 0

    def test_single_feature_instance(self):
        """Works with a single feature instance."""
        n = 50
        min_warmup = 10
        features_df = _make_features_df(n, n_features=1, nan_prefix=5)
        valid_mask = np.ones(n, dtype=bool)
        instances = [_FakeFeature(5)]

        final_mask = apply_warmup(features_df, valid_mask, min_warmup, instances, {})
        assert final_mask.sum() == n - min_warmup

    def test_empty_feature_instances_raises(self):
        """Empty feature_instances list → ValueError (max of empty)."""
        n = 50
        min_warmup = 10
        features_df = _make_features_df(n)
        valid_mask = np.ones(n, dtype=bool)

        with pytest.raises(ValueError, match="feature_instances"):
            apply_warmup(features_df, valid_mask, min_warmup, [], {})

    def test_return_type_is_ndarray(self):
        """Return value is a numpy bool array."""
        n = 50
        min_warmup = 10
        features_df = _make_features_df(n, nan_prefix=5)
        valid_mask = np.ones(n, dtype=bool)
        instances = [_FakeFeature(5)]

        final_mask = apply_warmup(features_df, valid_mask, min_warmup, instances, {})
        assert isinstance(final_mask, np.ndarray)
        assert final_mask.dtype == bool

    def test_valid_mask_length_mismatch_raises(self):
        """valid_mask length != features_df length → ValueError."""
        n = 50
        min_warmup = 10
        features_df = _make_features_df(n, nan_prefix=5)
        valid_mask = np.ones(n + 5, dtype=bool)
        instances = [_FakeFeature(5)]

        with pytest.raises(ValueError, match="length"):
            apply_warmup(features_df, valid_mask, min_warmup, instances, {})

    def test_multiple_features_max_min_periods_used(self):
        """With multiple features, the max(min_periods) is the constraint."""
        n = 100
        min_warmup = 30
        features_df = _make_features_df(n, nan_prefix=25)
        valid_mask = np.ones(n, dtype=bool)
        # min_periods: 5, 25, 15 → max = 25 <= 30 → OK
        instances = [_FakeFeature(5), _FakeFeature(25), _FakeFeature(15)]

        final_mask = apply_warmup(features_df, valid_mask, min_warmup, instances, {})
        assert final_mask.sum() == n - min_warmup

    def test_min_warmup_one_less_than_max_min_periods_raises(self):
        """min_warmup = max(min_periods) - 1 → ValueError (off-by-one check)."""
        n = 100
        min_warmup = 19
        features_df = _make_features_df(n, nan_prefix=20)
        valid_mask = np.ones(n, dtype=bool)
        instances = [_FakeFeature(20)]

        with pytest.raises(ValueError, match="min_warmup"):
            apply_warmup(features_df, valid_mask, min_warmup, instances, {})
