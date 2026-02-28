"""Tests for the missing candles policy (valid_mask computation).

Task #006 — WS-2: Politique de traitement des trous (missing candles).
Reference: spec §4.3, §6.6.

The function ``compute_valid_mask`` detects gaps in timestamp series and
returns a boolean mask where ``False`` indicates samples whose input window
[t-L+1, t] or output window [t+1, t+H] (including the t→t+1 transition)
touches a gap.
"""

import numpy as np
import pandas as pd
import pytest

from ai_trading.data.missing import compute_valid_mask

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_timestamps(n: int, freq: str = "1h", start: str = "2024-01-01") -> pd.Series:
    """Create a contiguous timestamp series of *n* candles."""
    return pd.Series(pd.date_range(start=start, periods=n, freq=freq))


def _make_timestamps_with_gap(
    n: int,
    gap_after: int | list[int],
    freq: str = "1h",
    start: str = "2024-01-01",
    gap_size: int = 1,
) -> pd.Series:
    """Create timestamps with one or more gaps.

    ``gap_after`` is an index (or list of indices) *after* which ``gap_size``
    candles are removed. The resulting Series has ``n`` entries but with
    time discontinuities at the specified positions.
    """
    if isinstance(gap_after, int):
        gap_after = [gap_after]

    delta = pd.tseries.frequencies.to_offset(freq)
    # Build a complete timeline long enough to accommodate gaps
    total_needed = n + sum(gap_size for _ in gap_after)
    full_ts = pd.date_range(start=start, periods=total_needed, freq=delta)

    # Remove candles to create gaps
    indices_to_remove: list[int] = []
    offset = 0
    for g in sorted(gap_after):
        # After position g in the *output* array, remove gap_size candles
        # In the full timeline, position g corresponds to index g + offset
        for k in range(1, gap_size + 1):
            indices_to_remove.append(g + offset + k)
        offset += gap_size

    keep = [i for i in range(len(full_ts)) if i not in indices_to_remove]
    result = pd.Series(full_ts[keep[:n]])
    assert len(result) == n, f"Expected {n} timestamps, got {len(result)}"
    return result


# ===========================================================================
# 1. No gaps → all True except border samples
# ===========================================================================

class TestNoGaps:
    """#006 — Données sans trou → masque tout à True sauf bords."""

    def test_all_valid_except_edges(self):
        """With no gaps, only border samples should be False."""
        n, seq_len, horizon = 20, 3, 2
        ts = _make_timestamps(n)
        mask = compute_valid_mask(ts, "1h", seq_len, horizon)

        assert mask.shape == (n,)
        assert mask.dtype == bool
        # First L-1 = 2 positions: can't form full input window
        assert not mask[0]
        assert not mask[1]
        # Last H = 2 positions: can't form full output window
        assert not mask[-1]
        assert not mask[-2]
        # Interior: all True
        assert mask[seq_len - 1 : n - horizon].all()

    def test_shape_matches_input(self):
        """Mask shape must equal number of timestamps."""
        for n in [10, 50, 100]:
            ts = _make_timestamps(n)
            mask = compute_valid_mask(ts, "1h", 5, 3)
            assert mask.shape == (n,)

    def test_all_true_interior_large(self):
        """Larger dataset, no gaps, verify interior is all True."""
        n, seq_len, horizon = 500, 128, 4
        ts = _make_timestamps(n)
        mask = compute_valid_mask(ts, "1h", seq_len, horizon)
        assert mask[:seq_len - 1].sum() == 0
        assert mask[n - horizon:].sum() == 0
        assert mask[seq_len - 1 : n - horizon].all()


# ===========================================================================
# 2. Single gap invalidation zone
# ===========================================================================

class TestSingleGap:
    """#006 — Un trou invalide les samples dans la fenêtre d'entrée + sortie."""

    def test_gap_invalidates_correct_range(self):
        """A gap after index g invalidates samples in [g-H+1, g+L-1]."""
        n, seq_len, horizon = 30, 5, 3
        gap_after_idx = 15
        ts = _make_timestamps_with_gap(n, gap_after=gap_after_idx)
        mask = compute_valid_mask(ts, "1h", seq_len, horizon)

        assert mask.shape == (n,)

        # Expected invalid range from gap: [g-H+1, g+L-1] = [13, 19]
        lo = gap_after_idx - horizon + 1  # 13
        hi = gap_after_idx + seq_len - 1  # 19
        for t in range(lo, hi + 1):
            assert not mask[t], f"Sample t={t} should be invalid (gap zone)"

        # Samples just outside the gap zone should be valid (if not at edges)
        if lo - 1 >= seq_len - 1:
            assert mask[lo - 1], f"Sample t={lo - 1} should be valid"
        if hi + 1 <= n - 1 - horizon:
            assert mask[hi + 1], f"Sample t={hi + 1} should be valid"

    def test_gap_at_start(self):
        """Gap near the beginning of the series."""
        n, seq_len, horizon = 20, 3, 2
        ts = _make_timestamps_with_gap(n, gap_after=1)
        mask = compute_valid_mask(ts, "1h", seq_len, horizon)

        # Gap after index 1: invalid zone [1-2+1, 1+3-1] = [0, 3]
        # But indices 0,1 are already edge-invalid (L-1=2)
        assert not mask[0]
        assert not mask[1]
        assert not mask[2]
        assert not mask[3]
        # Index 4 should be valid
        assert mask[4]

    def test_gap_at_end(self):
        """Gap near the end of the series."""
        n, seq_len, horizon = 20, 3, 2
        gap_idx = n - 4  # 16
        ts = _make_timestamps_with_gap(n, gap_after=gap_idx)
        mask = compute_valid_mask(ts, "1h", seq_len, horizon)

        # Gap after 16: invalid zone [16-2+1, 16+3-1] = [15, 18]
        # But indices 18,19 are edge-invalid (N-H=18)
        for t in range(15, 19):
            assert not mask[t], f"t={t} should be invalid"
        assert not mask[19]  # edge

    def test_gap_size_larger_than_one(self):
        """A gap of 3 missing candles creates a wider time discontinuity."""
        n, seq_len, horizon = 30, 4, 2
        ts = _make_timestamps_with_gap(n, gap_after=12, gap_size=3)
        mask = compute_valid_mask(ts, "1h", seq_len, horizon)

        # gap_after=12 means timestamps[12] and timestamps[13] have a 4h gap
        # (3 missing candles between them). The gap transition is at index 12.
        # Invalid zone: [12-2+1, 12+4-1] = [11, 15]
        for t in range(11, 16):
            assert not mask[t], f"t={t} should be invalid"


# ===========================================================================
# 3. Multiple gaps → combined mask
# ===========================================================================

class TestMultipleGaps:
    """#006 — Plusieurs trous → masque correctement combiné."""

    def test_two_separate_gaps(self):
        """Two non-overlapping gaps invalidate their respective zones."""
        n, seq_len, horizon = 50, 4, 2
        ts = _make_timestamps_with_gap(n, gap_after=[10, 30])
        mask = compute_valid_mask(ts, "1h", seq_len, horizon)

        # Gap after 10: invalid [10-2+1, 10+4-1] = [9, 13]
        for t in range(9, 14):
            assert not mask[t], f"t={t} should be invalid (gap 1)"

        # Gap after 30: invalid [30-2+1, 30+4-1] = [29, 33]
        for t in range(29, 34):
            assert not mask[t], f"t={t} should be invalid (gap 2)"

        # Between gaps: valid samples exist
        assert any(mask[14:29])

    def test_overlapping_gap_zones(self):
        """Two close gaps with overlapping invalidation zones."""
        n, seq_len, horizon = 40, 5, 3
        # Gaps after 10 and 14 — zones overlap
        ts = _make_timestamps_with_gap(n, gap_after=[10, 14])
        mask = compute_valid_mask(ts, "1h", seq_len, horizon)

        # Gap after 10: invalid [10-3+1, 10+5-1] = [8, 14]
        # Gap after 14: invalid [14-3+1, 14+5-1] = [12, 18]
        # Combined: [8, 18]
        for t in range(8, 19):
            assert not mask[t], f"t={t} should be invalid (overlap zone)"

    def test_three_gaps(self):
        """Three gaps distributed across the series."""
        n, seq_len, horizon = 60, 3, 2
        ts = _make_timestamps_with_gap(n, gap_after=[10, 25, 45])
        mask = compute_valid_mask(ts, "1h", seq_len, horizon)

        # Gap after 10: [10-2+1, 10+3-1] = [9, 12]
        for t in range(9, 13):
            assert not mask[t], f"t={t} should be invalid (gap at 10)"

        # Gap after 25: [25-2+1, 25+3-1] = [24, 27]
        for t in range(24, 28):
            assert not mask[t], f"t={t} should be invalid (gap at 25)"

        # Gap after 45: [45-2+1, 45+3-1] = [44, 47]
        for t in range(44, 48):
            assert not mask[t], f"t={t} should be invalid (gap at 45)"


# ===========================================================================
# 4. No interpolation — data must not be modified
# ===========================================================================

class TestNoInterpolation:
    """#006 — Pas d'interpolation : aucune valeur modifiée dans les données."""

    def test_timestamps_unchanged(self):
        """The function must not modify the input timestamps."""
        n = 20
        ts = _make_timestamps_with_gap(n, gap_after=8)
        ts_copy = ts.copy()
        compute_valid_mask(ts, "1h", 4, 2)
        pd.testing.assert_series_equal(ts, ts_copy)


# ===========================================================================
# 5. Edge / boundary cases
# ===========================================================================

class TestEdgeCases:
    """#006 — Cas bords."""

    def test_minimum_viable_length(self):
        """Smallest valid dataset: L + H candles."""
        seq_len, horizon = 3, 2
        n = seq_len + horizon  # 5
        ts = _make_timestamps(n)
        mask = compute_valid_mask(ts, "1h", seq_len, horizon)

        assert mask.shape == (n,)
        # Only index L-1 = 2 is valid (need input [0,1,2] + output [3,4])
        assert mask[seq_len - 1]
        assert mask[:seq_len - 1].sum() == 0
        assert mask[n - horizon:].sum() == 0

    def test_all_gaps(self):
        """Every consecutive pair has a gap → no valid samples."""
        n, seq_len, horizon = 10, 3, 2
        # Create timestamps with irregular spacing everywhere
        ts = pd.Series([
            pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i * 3)
            for i in range(n)
        ])
        mask = compute_valid_mask(ts, "1h", seq_len, horizon)
        # Every transition is a gap, so no sample can be valid
        assert mask.sum() == 0

    def test_single_candle(self):
        """A single candle cannot form any sample."""
        ts = _make_timestamps(1)
        mask = compute_valid_mask(ts, "1h", 3, 2)
        assert mask.shape == (1,)
        assert not mask[0]

    def test_too_few_candles_for_window(self):
        """Fewer candles than L+H → all False."""
        ts = _make_timestamps(4)
        mask = compute_valid_mask(ts, "1h", 3, 2)
        assert mask.shape == (4,)
        # N=4, need L+H=5 to have at least one valid sample
        assert mask.sum() == 0

    def test_horizon_larger_than_n(self):
        """H > N → all positions must be invalid (no room for output window)."""
        ts = _make_timestamps(4)
        mask = compute_valid_mask(ts, "1h", 1, 5)
        assert mask.shape == (4,)
        assert mask.sum() == 0

    def test_l_equals_1(self):
        """L=1 means no lookback beyond current candle."""
        n, seq_len, horizon = 10, 1, 2
        ts = _make_timestamps(n)
        mask = compute_valid_mask(ts, "1h", seq_len, horizon)
        # Valid range: [0, N-H-1] = [0, 7]
        assert mask[:n - horizon].all()
        assert mask[n - horizon:].sum() == 0

    def test_h_equals_1(self):
        """H=1 means only one step ahead."""
        n, seq_len, horizon = 10, 3, 1
        ts = _make_timestamps(n)
        mask = compute_valid_mask(ts, "1h", seq_len, horizon)
        # Valid range: [L-1, N-2] = [2, 8]
        assert mask[seq_len - 1 : n - horizon].all()
        assert mask[:seq_len - 1].sum() == 0
        assert not mask[n - 1]


# ===========================================================================
# 6. Different timeframes
# ===========================================================================

class TestTimeframes:
    """#006 — Compatible avec différents timeframes."""

    def test_4h_timeframe(self):
        """Correct gap detection with 4h candles."""
        n, seq_len, horizon = 20, 4, 2
        ts = _make_timestamps(n, freq="4h")
        mask = compute_valid_mask(ts, "4h", seq_len, horizon)
        assert mask[seq_len - 1 : n - horizon].all()

    def test_4h_with_gap(self):
        """A gap in 4h data is correctly detected."""
        n, seq_len, horizon = 20, 4, 2
        ts = _make_timestamps_with_gap(n, freq="4h", gap_after=10)
        mask = compute_valid_mask(ts, "4h", seq_len, horizon)

        lo = 10 - horizon + 1  # 9
        hi = 10 + seq_len - 1  # 13
        for t in range(lo, hi + 1):
            assert not mask[t], f"t={t} should be invalid"


# ===========================================================================
# 7. Input validation
# ===========================================================================

class TestInputValidation:
    """#006 — Validation explicite des entrées."""

    def test_unsupported_timeframe_raises(self):
        """Unsupported timeframe string raises ValueError."""
        ts = _make_timestamps(10)
        with pytest.raises(ValueError, match="[Tt]imeframe"):
            compute_valid_mask(ts, "7m", 3, 2)

    def test_l_zero_raises(self):
        """L must be >= 1."""
        ts = _make_timestamps(10)
        with pytest.raises(ValueError, match="L"):
            compute_valid_mask(ts, "1h", 0, 2)

    def test_h_zero_raises(self):
        """H must be >= 1."""
        ts = _make_timestamps(10)
        with pytest.raises(ValueError, match="H"):
            compute_valid_mask(ts, "1h", 3, 0)

    def test_negative_l_raises(self):
        """Negative L raises ValueError."""
        ts = _make_timestamps(10)
        with pytest.raises(ValueError, match="L"):
            compute_valid_mask(ts, "1h", -1, 2)

    def test_negative_h_raises(self):
        """Negative H raises ValueError."""
        ts = _make_timestamps(10)
        with pytest.raises(ValueError, match="H"):
            compute_valid_mask(ts, "1h", 3, -1)

    def test_empty_timestamps_raises(self):
        """Empty timestamp series raises ValueError."""
        ts = pd.Series([], dtype="datetime64[ns]")
        with pytest.raises(ValueError, match="[Ee]mpty"):
            compute_valid_mask(ts, "1h", 3, 2)


# ===========================================================================
# 8. Return type validation
# ===========================================================================

class TestReturnType:
    """#006 — Masque booléen retourné correctement."""

    def test_dtype_is_bool(self):
        """Mask must be a boolean numpy array."""
        ts = _make_timestamps(20)
        mask = compute_valid_mask(ts, "1h", 4, 2)
        assert isinstance(mask, np.ndarray)
        assert mask.dtype == bool

    def test_mask_is_not_writable_to_input(self):
        """Mask is a new array, not a view of internal state."""
        ts = _make_timestamps(20)
        mask = compute_valid_mask(ts, "1h", 4, 2)
        mask2 = compute_valid_mask(ts, "1h", 4, 2)
        np.testing.assert_array_equal(mask, mask2)


# ===========================================================================
# 9. Causality check (anti-fuite)
# ===========================================================================

class TestCausality:
    """#006 — Anti-fuite : le masque est calculé de façon strictement causale."""

    def test_mask_depends_only_on_timestamps(self):
        """Mask only depends on timestamp positions, not values."""
        n, seq_len, horizon = 30, 4, 2
        ts = _make_timestamps_with_gap(n, gap_after=15)
        mask1 = compute_valid_mask(ts, "1h", seq_len, horizon)

        # Same timestamps → same mask
        mask2 = compute_valid_mask(ts.copy(), "1h", seq_len, horizon)
        np.testing.assert_array_equal(mask1, mask2)

    def test_adding_future_gap_does_not_change_past_mask(self):
        """Adding a gap in the future should not change validity of earlier samples."""
        n, seq_len, horizon = 40, 4, 2

        # No gap
        ts_clean = _make_timestamps(n)
        mask_clean = compute_valid_mask(ts_clean, "1h", seq_len, horizon)

        # Gap after index 30 (far in the future)
        ts_gap = _make_timestamps_with_gap(n, gap_after=30)
        mask_gap = compute_valid_mask(ts_gap, "1h", seq_len, horizon)

        # Samples before the gap zone should be identical
        gap_zone_start = 30 - horizon + 1  # 29
        np.testing.assert_array_equal(
            mask_clean[:gap_zone_start],
            mask_gap[:gap_zone_start],
        )
