"""Tests for sample builder (N, L, F).

Task #016 — WS-4: build sliding-window samples from features + labels.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_trading.config import WindowConfig
from tests.conftest import make_features_df, make_labels

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_window_config(seq_len: int = 4) -> WindowConfig:
    """Create a minimal WindowConfig with the given L."""
    return WindowConfig(L=seq_len, min_warmup=seq_len)


# ---------------------------------------------------------------------------
# Test: nominal shapes
# ---------------------------------------------------------------------------


class TestNominalShapes:
    """#016 — Verify output shapes in nominal scenario."""

    def test_x_seq_shape(self):
        """X_seq should be (N, L, F)."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 20, 3, 4
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        # All bars valid
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        x_seq, y_out, timestamps = build_samples(features_df, y, final_mask, config)

        # First valid sample is at t = L-1 = 3 (window [0, 1, 2, 3])
        expected_n = n_bars - seq_len + 1  # 17
        assert x_seq.shape == (expected_n, seq_len, n_features)

    def test_y_shape(self):
        """y_out should be (N,)."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 20, 3, 4
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        x_seq, y_out, timestamps = build_samples(features_df, y, final_mask, config)

        assert y_out.shape == (x_seq.shape[0],)

    def test_timestamps_length(self):
        """timestamps should have N entries matching decision timestamps."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 20, 3, 4
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        x_seq, y_out, timestamps = build_samples(features_df, y, final_mask, config)

        assert len(timestamps) == x_seq.shape[0]


# ---------------------------------------------------------------------------
# Test: dtype conventions
# ---------------------------------------------------------------------------


class TestDtypeConventions:
    """#016 — X_seq and y must be float32."""

    def test_x_seq_dtype(self):
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 20, 3, 4
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        x_seq, _, _ = build_samples(features_df, y, final_mask, config)

        assert x_seq.dtype == np.float32

    def test_y_dtype(self):
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 20, 3, 4
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        _, y_out, _ = build_samples(features_df, y, final_mask, config)

        assert y_out.dtype == np.float32


# ---------------------------------------------------------------------------
# Test: no NaN in outputs
# ---------------------------------------------------------------------------


class TestNoNaN:
    """#016 — No NaN in X_seq or y for retained samples."""

    def test_no_nan_in_x_seq(self):
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 20, 3, 4
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        x_seq, _, _ = build_samples(features_df, y, final_mask, config)

        assert not np.any(np.isnan(x_seq))

    def test_no_nan_in_y(self):
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 20, 3, 4
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        _, y_out, _ = build_samples(features_df, y, final_mask, config)

        assert not np.any(np.isnan(y_out))


# ---------------------------------------------------------------------------
# Test: window content correctness
# ---------------------------------------------------------------------------


class TestWindowContent:
    """#016 — Each window must contain the correct feature values."""

    def test_first_sample_content(self):
        """First valid sample (t=L-1) should contain features [0..L-1]."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 10, 2, 3
        features_df = make_features_df(n_bars, n_features, seed=7)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        x_seq, _, _ = build_samples(features_df, y, final_mask, config)

        # First sample window: rows [0, 1, 2]
        expected = features_df.iloc[0:seq_len].values.astype(np.float32)
        np.testing.assert_array_equal(x_seq[0], expected)

    def test_last_sample_content(self):
        """Last valid sample should contain features [n-L..n-1]."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 10, 2, 3
        features_df = make_features_df(n_bars, n_features, seed=7)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        x_seq, _, _ = build_samples(features_df, y, final_mask, config)

        # Last sample window: rows [7, 8, 9]
        expected = features_df.iloc[n_bars - seq_len : n_bars].values.astype(np.float32)
        np.testing.assert_array_equal(x_seq[-1], expected)

    def test_y_values_match_labels(self):
        """y_out[i] should correspond to y[t] for decision timestamp t."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 10, 2, 3
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars, seed=123)
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        _, y_out, _ = build_samples(features_df, y, final_mask, config)

        # With all valid, y_out[i] = y[i + L - 1] (decision at t=L-1+i)
        for i in range(len(y_out)):
            t = i + seq_len - 1
            np.testing.assert_almost_equal(
                y_out[i], np.float32(y[t]), decimal=6
            )


# ---------------------------------------------------------------------------
# Test: timestamps correctness
# ---------------------------------------------------------------------------


class TestTimestamps:
    """#016 — timestamps must correspond to decision timestamps."""

    def test_timestamps_values(self):
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 10, 2, 3
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        _, _, timestamps = build_samples(features_df, y, final_mask, config)

        # Decision timestamps start at index L-1
        expected_ts = features_df.index[seq_len - 1 :]
        pd.testing.assert_index_equal(timestamps, expected_ts)


# ---------------------------------------------------------------------------
# Test: mask filtering
# ---------------------------------------------------------------------------


class TestMaskFiltering:
    """#016 — final_mask filtering eliminates invalid samples."""

    def test_mask_reduces_n(self):
        """Masking some positions should reduce N."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 20, 3, 4
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        # Invalidate positions 5 and 10
        final_mask[5] = False
        final_mask[10] = False
        config = _make_window_config(seq_len)

        x_seq, y_out, timestamps = build_samples(features_df, y, final_mask, config)

        # N should be less than the all-valid case (17)
        all_valid_n = n_bars - seq_len + 1
        assert x_seq.shape[0] < all_valid_n

    def test_invalid_decision_excluded(self):
        """If final_mask[t] is False, sample at decision t is excluded."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 10, 2, 3
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        # Invalidate t=5 (a decision position)
        final_mask[5] = False
        config = _make_window_config(seq_len)

        _, _, timestamps = build_samples(features_df, y, final_mask, config)

        # Timestamp at index 5 should not appear in the output
        assert features_df.index[5] not in timestamps

    def test_invalid_in_window_excludes_sample(self):
        """If any bar in [t-L+1, t] has final_mask=False, sample at t is excluded."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 10, 2, 3
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        # Invalidate t=4 → samples at t=4, t=5, t=6 should be excluded
        # (windows that include position 4)
        final_mask[4] = False
        config = _make_window_config(seq_len)

        _, _, timestamps = build_samples(features_df, y, final_mask, config)

        # t=4 window [2,3,4], t=5 window [3,4,5], t=6 window [4,5,6] all excluded
        for excluded_t in [4, 5, 6]:
            assert features_df.index[excluded_t] not in timestamps

    def test_nan_in_y_excluded(self):
        """Positions where y is NaN should be excluded from samples."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 10, 2, 3
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        y[5] = np.nan  # Invalid label
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        x_seq, y_out, timestamps = build_samples(features_df, y, final_mask, config)

        # t=5 should be excluded because y[5] is NaN
        assert features_df.index[5] not in timestamps
        # No NaN in output
        assert not np.any(np.isnan(y_out))

    def test_nan_in_features_excluded(self):
        """Positions where features contain NaN in the window should be excluded."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 10, 2, 3
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        # Put NaN in features at position 3
        features_df.iloc[3, 0] = np.nan
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        x_seq, y_out, timestamps = build_samples(features_df, y, final_mask, config)

        # Windows including position 3: t=3 [1,2,3], t=4 [2,3,4], t=5 [3,4,5]
        for excluded_t in [3, 4, 5]:
            assert features_df.index[excluded_t] not in timestamps
        assert not np.any(np.isnan(x_seq))


# ---------------------------------------------------------------------------
# Test: config-driven (L from config)
# ---------------------------------------------------------------------------


class TestConfigDriven:
    """#016 — L must be read from config, not hardcoded."""

    def test_different_l_values(self):
        """Changing L in config should change output shapes."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features = 30, 2
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)

        for seq_len in [2, 5, 10]:
            config = _make_window_config(seq_len)
            x_seq, _, _ = build_samples(features_df, y, final_mask, config)
            assert x_seq.shape[1] == seq_len
            expected_n = n_bars - seq_len + 1
            assert x_seq.shape[0] == expected_n


# ---------------------------------------------------------------------------
# Test: anti-leakage
# ---------------------------------------------------------------------------


class TestAntiLeakage:
    """#016 — Each window [t-L+1, t] only contains past/present data."""

    def test_window_backward_looking(self):
        """Window for sample at t should contain exactly rows [t-L+1..t]."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 15, 2, 4
        # Use sequential values so we can verify exact content
        features_df = make_features_df(n_bars, n_features, seed=0)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        x_seq, _, timestamps = build_samples(features_df, y, final_mask, config)

        # For each sample, verify window content
        for i in range(x_seq.shape[0]):
            t = seq_len - 1 + i  # decision timestamp index
            expected_window = features_df.iloc[t - seq_len + 1 : t + 1].values
            np.testing.assert_array_almost_equal(
                x_seq[i], expected_window.astype(np.float32), decimal=6
            )


# ---------------------------------------------------------------------------
# Test: edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """#016 — Edge cases for sample builder."""

    def test_l_equals_n_bars_all_valid(self):
        """When L == n_bars, exactly 1 sample should be produced."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 5, 2, 5
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        x_seq, y_out, timestamps = build_samples(features_df, y, final_mask, config)

        assert x_seq.shape == (1, seq_len, n_features)
        assert y_out.shape == (1,)
        assert len(timestamps) == 1

    def test_l_equals_2_minimum(self):
        """L=2 (minimum valid value) should work correctly."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 5, 2, 2
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        x_seq, y_out, timestamps = build_samples(features_df, y, final_mask, config)

        expected_n = n_bars - seq_len + 1  # 4
        assert x_seq.shape == (expected_n, seq_len, n_features)

    def test_all_mask_false_produces_zero_samples(self):
        """If final_mask is all False, no samples should be produced."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 10, 2, 3
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        final_mask = np.zeros(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        x_seq, y_out, timestamps = build_samples(features_df, y, final_mask, config)

        assert x_seq.shape == (0, seq_len, n_features)
        assert y_out.shape == (0,)
        assert len(timestamps) == 0

    def test_all_y_nan_produces_zero_samples(self):
        """If all y values are NaN, no samples should be produced."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 10, 2, 3
        features_df = make_features_df(n_bars, n_features)
        y = np.full(n_bars, np.nan, dtype=np.float64)
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        x_seq, y_out, timestamps = build_samples(features_df, y, final_mask, config)

        assert x_seq.shape == (0, seq_len, n_features)
        assert y_out.shape == (0,)
        assert len(timestamps) == 0

    def test_single_feature(self):
        """F=1 should produce correct (N, L, 1) shape."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 10, 1, 3
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        x_seq, _, _ = build_samples(features_df, y, final_mask, config)

        assert x_seq.shape == (n_bars - seq_len + 1, seq_len, 1)


# ---------------------------------------------------------------------------
# Test: error cases
# ---------------------------------------------------------------------------


class TestErrorCases:
    """#016 — Input validation errors."""

    def test_y_length_mismatch(self):
        """y length must equal features_df length."""
        from ai_trading.data.dataset import build_samples

        features_df = make_features_df(10, 2)
        y = make_labels(8)  # Wrong length
        final_mask = np.ones(10, dtype=bool)
        config = _make_window_config(3)

        with pytest.raises(ValueError, match="y.*length"):
            build_samples(features_df, y, final_mask, config)

    def test_mask_length_mismatch(self):
        """final_mask length must equal features_df length."""
        from ai_trading.data.dataset import build_samples

        features_df = make_features_df(10, 2)
        y = make_labels(10)
        final_mask = np.ones(8, dtype=bool)  # Wrong length
        config = _make_window_config(3)

        with pytest.raises(ValueError, match="final_mask.*length"):
            build_samples(features_df, y, final_mask, config)

    def test_mask_wrong_dtype(self):
        """final_mask must be boolean."""
        from ai_trading.data.dataset import build_samples

        features_df = make_features_df(10, 2)
        y = make_labels(10)
        final_mask = np.ones(10, dtype=np.float64)  # Wrong dtype
        config = _make_window_config(3)

        with pytest.raises(ValueError, match="final_mask.*bool"):
            build_samples(features_df, y, final_mask, config)

    def test_y_wrong_dtype(self):
        """y must be a floating-point array."""
        from ai_trading.data.dataset import build_samples

        features_df = make_features_df(10, 2)
        y = np.ones(10, dtype=np.int32)  # Wrong dtype
        final_mask = np.ones(10, dtype=bool)
        config = _make_window_config(3)

        with pytest.raises(ValueError, match="y.*floating"):
            build_samples(features_df, y, final_mask, config)

    def test_l_greater_than_n_bars(self):
        """L > n_bars should produce 0 samples (no room for a window)."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 3, 2, 10
        features_df = make_features_df(n_bars, n_features)
        y = make_labels(n_bars)
        final_mask = np.ones(n_bars, dtype=bool)
        config = _make_window_config(seq_len)

        x_seq, y_out, timestamps = build_samples(features_df, y, final_mask, config)

        assert x_seq.shape == (0, seq_len, n_features)
        assert y_out.shape == (0,)
        assert len(timestamps) == 0

    def test_empty_features_df(self):
        """Empty features DataFrame should produce 0 samples."""
        from ai_trading.data.dataset import build_samples

        features_df = pd.DataFrame(
            columns=["feat_0", "feat_1"],
            index=pd.DatetimeIndex([], freq="1h"),
        )
        y = np.array([], dtype=np.float64)
        final_mask = np.array([], dtype=bool)
        config = _make_window_config(3)

        x_seq, y_out, timestamps = build_samples(features_df, y, final_mask, config)

        assert x_seq.shape == (0, 3, 2)
        assert y_out.shape == (0,)
        assert len(timestamps) == 0

    def test_no_features_columns(self):
        """features_df with 0 columns should raise."""
        from ai_trading.data.dataset import build_samples

        features_df = pd.DataFrame(
            index=pd.date_range("2024-01-01", periods=10, freq="1h"),
        )
        y = make_labels(10)
        final_mask = np.ones(10, dtype=bool)
        config = _make_window_config(3)

        with pytest.raises(ValueError, match="features.*column"):
            build_samples(features_df, y, final_mask, config)


# ---------------------------------------------------------------------------
# Test: complex mask scenario
# ---------------------------------------------------------------------------


class TestComplexMaskScenario:
    """#016 — Complex scenarios combining multiple mask effects."""

    def test_scattered_valid_positions(self):
        """Only positions with full valid windows should be retained."""
        from ai_trading.data.dataset import build_samples

        n_bars, n_features, seq_len = 12, 2, 3
        features_df = make_features_df(n_bars, n_features, seed=42)
        y = make_labels(n_bars, seed=42)
        # Mark only some positions as valid
        final_mask = np.array(
            [True, True, True, False, True, True, True, False, True, True, True, True],
            dtype=bool,
        )
        config = _make_window_config(seq_len)

        x_seq, y_out, timestamps = build_samples(features_df, y, final_mask, config)

        # Valid decision timestamps: t where final_mask[t]=True AND
        # full window [t-L+1..t] is all True.
        # t=0: window too short (need L=3, only index 0)
        # t=1: window too short (need L=3, only indices 0,1)
        # t=2: window [0,1,2] all True ✓
        # t=3: final_mask[3]=False ✗
        # t=4: window [2,3,4], final_mask[3]=False ✗
        # t=5: window [3,4,5], final_mask[3]=False ✗
        # t=6: window [4,5,6] all True ✓
        # t=7: final_mask[7]=False ✗
        # t=8: window [6,7,8], final_mask[7]=False ✗
        # t=9: window [7,8,9], final_mask[7]=False ✗
        # t=10: window [8,9,10] all True ✓
        # t=11: window [9,10,11] all True ✓
        expected_valid_t = [2, 6, 10, 11]
        expected_timestamps = features_df.index[expected_valid_t]

        assert len(timestamps) == len(expected_valid_t)
        pd.testing.assert_index_equal(timestamps, expected_timestamps)

        # Verify content of each retained sample
        for i, t in enumerate(expected_valid_t):
            expected_window = features_df.iloc[t - seq_len + 1 : t + 1].values
            np.testing.assert_array_almost_equal(
                x_seq[i], expected_window.astype(np.float32), decimal=6
            )
            np.testing.assert_almost_equal(
                y_out[i], np.float32(y[t]), decimal=6
            )
