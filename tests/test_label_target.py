"""Tests for label target y_t computation.

Task #015 — WS-4: Calcul de la cible y_t (label).

Covers:
- log_return_trade: y_t = log(Close[t+H] / Open[t+1])
- log_return_close_to_close: y_t = log(Close[t+H] / Close[t])
- Sample invalidation on gaps
- Unknown target_type raises ValueError
- Config-driven (no hardcoding)
- Anti-fuite: masking future prices beyond t+H does not change y_t
"""

import numpy as np
import pytest

from ai_trading.config import LabelConfig
from ai_trading.data.labels import compute_labels
from tests.conftest import make_calibration_ohlcv

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _label_config(
    horizon: int = 4,
    target_type: str = "log_return_trade",
) -> LabelConfig:
    return LabelConfig(horizon_H_bars=horizon, target_type=target_type)


# ---------------------------------------------------------------------------
# Nominal: log_return_trade
# ---------------------------------------------------------------------------


class TestLogReturnTrade:
    """y_t = log(Close[t+H] / Open[t+1])."""

    def test_values_are_correct(self):
        """#015 — Exact numerical values for log_return_trade."""
        n = 20
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config(horizon=4, target_type="log_return_trade")
        candle_mask = np.ones(n, dtype=bool)

        y, label_mask = compute_labels(ohlcv, cfg, candle_mask)

        # Manual check for a few positions
        close = ohlcv["close"].values
        open_ = ohlcv["open"].values
        for t in range(n):
            if t + 1 < n and t + 4 < n:
                expected = np.log(close[t + 4] / open_[t + 1])
                assert label_mask[t]
                np.testing.assert_allclose(y[t], expected, rtol=1e-12)

    def test_last_h_positions_are_nan(self):
        """#015 — Positions where t+H >= N must be NaN and masked out."""
        n = 10
        h = 4
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config(horizon=h)
        candle_mask = np.ones(n, dtype=bool)

        y, label_mask = compute_labels(ohlcv, cfg, candle_mask)

        # Positions n-h..n-1 cannot compute Close[t+H] (out of bounds)
        for t in range(n - h, n):
            assert not label_mask[t]
            assert np.isnan(y[t])

        # Also t where t+1 >= n → can't get Open[t+1] for log_return_trade
        # For log_return_trade: need t+1 and t+H; last invalid is max(n-H, n-1)
        # t = n-1: t+1 = n (out), t+H = n+H-1 (out) → invalid
        assert not label_mask[n - 1]

    def test_horizon_1(self):
        """#015 — Edge case H=1: y_t = log(Close[t+1] / Open[t+1])."""
        n = 10
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config(horizon=1)
        candle_mask = np.ones(n, dtype=bool)

        y, label_mask = compute_labels(ohlcv, cfg, candle_mask)

        close = ohlcv["close"].values
        open_ = ohlcv["open"].values
        for t in range(n - 1):
            expected = np.log(close[t + 1] / open_[t + 1])
            np.testing.assert_allclose(y[t], expected, rtol=1e-12)
            assert label_mask[t]

        # Last position: t+1 = n → out of bounds
        assert not label_mask[n - 1]


# ---------------------------------------------------------------------------
# Nominal: log_return_close_to_close
# ---------------------------------------------------------------------------


class TestLogReturnCloseToClose:
    """y_t = log(Close[t+H] / Close[t])."""

    def test_values_are_correct(self):
        """#015 — Exact numerical values for log_return_close_to_close."""
        n = 20
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config(horizon=4, target_type="log_return_close_to_close")
        candle_mask = np.ones(n, dtype=bool)

        y, label_mask = compute_labels(ohlcv, cfg, candle_mask)

        close = ohlcv["close"].values
        for t in range(n - 4):
            expected = np.log(close[t + 4] / close[t])
            np.testing.assert_allclose(y[t], expected, rtol=1e-12)
            assert label_mask[t]

    def test_last_h_positions_are_nan(self):
        """#015 — Positions where t+H >= N must be NaN."""
        n = 10
        h = 4
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config(horizon=h, target_type="log_return_close_to_close")
        candle_mask = np.ones(n, dtype=bool)

        y, label_mask = compute_labels(ohlcv, cfg, candle_mask)

        for t in range(n - h, n):
            assert not label_mask[t]
            assert np.isnan(y[t])

    def test_horizon_1(self):
        """#015 — Edge case H=1 close-to-close."""
        n = 10
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config(horizon=1, target_type="log_return_close_to_close")
        candle_mask = np.ones(n, dtype=bool)

        y, label_mask = compute_labels(ohlcv, cfg, candle_mask)

        close = ohlcv["close"].values
        for t in range(n - 1):
            expected = np.log(close[t + 1] / close[t])
            np.testing.assert_allclose(y[t], expected, rtol=1e-12)
            assert label_mask[t]

        assert not label_mask[n - 1]


# ---------------------------------------------------------------------------
# Switching target_type produces different values
# ---------------------------------------------------------------------------


class TestTargetTypeSwitching:
    """#015 — Changing target_type must produce different values."""

    def test_different_values_same_data(self):
        """log_return_trade != log_return_close_to_close on same OHLCV."""
        n = 20
        ohlcv = make_calibration_ohlcv(n)
        candle_mask = np.ones(n, dtype=bool)

        cfg_trade = _label_config(target_type="log_return_trade")
        cfg_c2c = _label_config(target_type="log_return_close_to_close")

        y_trade, mask_trade = compute_labels(ohlcv, cfg_trade, candle_mask)
        y_c2c, mask_c2c = compute_labels(ohlcv, cfg_c2c, candle_mask)

        # Where both masks are valid, values should generally differ
        both_valid = mask_trade & mask_c2c
        assert both_valid.sum() > 0
        # At least some values differ (open != close in synthetic data)
        diff = np.abs(y_trade[both_valid] - y_c2c[both_valid])
        assert np.any(diff > 1e-10)


# ---------------------------------------------------------------------------
# Gap handling (missing candles / candle_mask)
# ---------------------------------------------------------------------------


class TestGapInvalidation:
    """#015 — Samples must be invalidated when gaps at t+1 or t+H."""

    def test_gap_at_t_plus_1(self):
        """#015 — Gap at t+1 invalidates label at t for log_return_trade."""
        n = 20
        h = 4
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config(horizon=h, target_type="log_return_trade")
        candle_mask = np.ones(n, dtype=bool)

        # Introduce gap at position 5 → label at t=4 needs Open[5] → invalid
        candle_mask[5] = False

        y, label_mask = compute_labels(ohlcv, cfg, candle_mask)

        assert not label_mask[4]  # needs Open[t+1=5] which is a gap
        assert np.isnan(y[4])

    def test_gap_at_t_plus_h(self):
        """#015 — Gap at t+H invalidates label at t."""
        n = 20
        h = 4
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config(horizon=h, target_type="log_return_trade")
        candle_mask = np.ones(n, dtype=bool)

        # Gap at position 10 → labels needing Close[10] are invalid → t=6
        candle_mask[10] = False

        y, label_mask = compute_labels(ohlcv, cfg, candle_mask)

        assert not label_mask[6]  # needs Close[t+H=10] which is a gap
        assert np.isnan(y[6])

    def test_gap_between_t_plus_1_and_t_plus_h(self):
        """#015 — Gap anywhere in [t+1, t+H] invalidates the label."""
        n = 20
        h = 4
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config(horizon=h, target_type="log_return_trade")
        candle_mask = np.ones(n, dtype=bool)

        # Gap at position 8 → any t where 8 is in [t+1, t+H] is invalid
        # t+1 <= 8 <= t+4 → 4 <= t <= 7
        candle_mask[8] = False

        y, label_mask = compute_labels(ohlcv, cfg, candle_mask)

        for t in range(4, 8):
            assert not label_mask[t], f"label_mask[{t}] should be False (gap at 8)"
            assert np.isnan(y[t])

    def test_gap_at_t_does_not_invalidate_trade_label(self):
        """#015 — For log_return_trade, gap at t itself doesn't invalidate y_t
        (Open[t+1] and Close[t+H] may still be valid)."""
        n = 20
        h = 4
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config(horizon=h, target_type="log_return_trade")
        candle_mask = np.ones(n, dtype=bool)

        # Gap at t=3 itself, but t+1=4..t+H=7 all valid
        candle_mask[3] = False

        y, label_mask = compute_labels(ohlcv, cfg, candle_mask)

        # t=3: candle_mask[3] is False but the *label* uses [t+1..t+H]
        # The gap at t itself should not invalidate since label only needs
        # data in range [t+1, t+H]. However, candle_mask at t means the
        # sample itself might be excluded by downstream logic.
        # compute_labels masks = label_mask (about label computability)
        # The label at t=3 IS computable (Open[4] and Close[7] exist).
        # But candle_mask[3]=False means the overall sample at t=3 is already invalid
        # so label_mask can reflect either. The task says "final_mask & label_mask"
        # which means label_mask focuses on label computability.
        # Since [t+1..t+H] = [4..7] are all valid, label IS computable.
        assert label_mask[3]

    def test_gap_at_t_invalidates_c2c_label(self):
        """#015 — For close_to_close, gap at t invalidates y_t since we need Close[t]."""
        n = 20
        h = 4
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config(horizon=h, target_type="log_return_close_to_close")
        candle_mask = np.ones(n, dtype=bool)

        candle_mask[3] = False  # Gap at t=3 → need Close[t=3] → invalid

        y, label_mask = compute_labels(ohlcv, cfg, candle_mask)

        assert not label_mask[3]
        assert np.isnan(y[3])

    def test_all_gaps_produces_all_false(self):
        """#015 — All positions gaps → all labels invalid."""
        n = 10
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config(horizon=4)
        candle_mask = np.zeros(n, dtype=bool)

        y, label_mask = compute_labels(ohlcv, cfg, candle_mask)

        assert not np.any(label_mask)
        assert np.all(np.isnan(y))


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestErrorCases:
    """#015 — Invalid inputs must raise explicitly."""

    def test_unknown_target_type_raises_valueerror(self):
        """#015 — Unknown target_type raises ValueError."""
        n = 10
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config(target_type="unknown_type")
        candle_mask = np.ones(n, dtype=bool)

        with pytest.raises(ValueError, match="target_type"):
            compute_labels(ohlcv, cfg, candle_mask)

    def test_candle_mask_wrong_shape_raises(self):
        """#015 — candle_mask with wrong shape raises ValueError."""
        n = 10
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config()
        candle_mask = np.ones(n + 5, dtype=bool)

        with pytest.raises(ValueError, match="candle_mask shape"):
            compute_labels(ohlcv, cfg, candle_mask)

    def test_candle_mask_wrong_dtype_raises(self):
        """#015 — candle_mask with non-bool dtype raises ValueError."""
        n = 10
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config()
        candle_mask = np.ones(n, dtype=np.int32)

        with pytest.raises(ValueError, match="candle_mask dtype"):
            compute_labels(ohlcv, cfg, candle_mask)


# ---------------------------------------------------------------------------
# Config-driven (not hardcoded)
# ---------------------------------------------------------------------------


class TestConfigDriven:
    """#015 — Parameters come from config, not hardcoded."""

    def test_different_horizon_gives_different_results(self):
        """#015 — Changing horizon H changes label values."""
        n = 30
        ohlcv = make_calibration_ohlcv(n)
        candle_mask = np.ones(n, dtype=bool)

        y_h2, mask_h2 = compute_labels(
            ohlcv, _label_config(horizon=2), candle_mask
        )
        y_h8, mask_h8 = compute_labels(
            ohlcv, _label_config(horizon=8), candle_mask
        )

        # Some position valid in both → values differ
        both_valid = mask_h2 & mask_h8
        assert both_valid.sum() > 0
        diff = np.abs(y_h2[both_valid] - y_h8[both_valid])
        assert np.any(diff > 1e-10)


# ---------------------------------------------------------------------------
# Anti-fuite (anti-leakage)
# ---------------------------------------------------------------------------


class TestAntiLeakage:
    """#015 — Masking future prices beyond t+H must not change y_t."""

    def test_mask_prices_after_t_plus_h_no_effect(self):
        """#015 — Perturb prices at t > t+H; y_t must remain identical."""
        n = 30
        h = 4
        t_check = 10
        ohlcv_orig = make_calibration_ohlcv(n)
        cfg = _label_config(horizon=h)
        candle_mask = np.ones(n, dtype=bool)

        y_orig, mask_orig = compute_labels(ohlcv_orig, cfg, candle_mask)

        # Perturb all prices after t+H
        ohlcv_perturbed = ohlcv_orig.copy()
        perturb_start = t_check + h + 1
        ohlcv_perturbed.iloc[perturb_start:, ohlcv_perturbed.columns.get_loc("close")] = 999.0
        ohlcv_perturbed.iloc[perturb_start:, ohlcv_perturbed.columns.get_loc("open")] = 999.0

        y_pert, mask_pert = compute_labels(ohlcv_perturbed, cfg, candle_mask)

        # y_t for all t <= t_check must be identical
        for t in range(t_check + 1):
            if mask_orig[t]:
                assert mask_pert[t]
                np.testing.assert_allclose(y_pert[t], y_orig[t], rtol=1e-14)


# ---------------------------------------------------------------------------
# Output shape and dtype
# ---------------------------------------------------------------------------


class TestOutputShape:
    """#015 — Output shapes and dtypes."""

    def test_output_shapes(self):
        """y and label_mask have shape (N,)."""
        n = 20
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config()
        candle_mask = np.ones(n, dtype=bool)

        y, label_mask = compute_labels(ohlcv, cfg, candle_mask)

        assert y.shape == (n,)
        assert label_mask.shape == (n,)

    def test_y_dtype_float64(self):
        """y array uses float64 (metric-level precision)."""
        n = 20
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config()
        candle_mask = np.ones(n, dtype=bool)

        y, _ = compute_labels(ohlcv, cfg, candle_mask)

        assert y.dtype == np.float64

    def test_label_mask_dtype_bool(self):
        """label_mask is boolean."""
        n = 20
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config()
        candle_mask = np.ones(n, dtype=bool)

        _, label_mask = compute_labels(ohlcv, cfg, candle_mask)

        assert label_mask.dtype == bool


# ---------------------------------------------------------------------------
# Edge: very small dataset
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """#015 — Boundary conditions."""

    def test_dataset_smaller_than_h_plus_1(self):
        """#015 — If N < H+1 for trade or N < H+1 for c2c, all labels invalid."""
        n = 3
        h = 4
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config(horizon=h)
        candle_mask = np.ones(n, dtype=bool)

        y, label_mask = compute_labels(ohlcv, cfg, candle_mask)

        assert not np.any(label_mask)
        assert np.all(np.isnan(y))

    def test_dataset_exactly_h_plus_2(self):
        """#015 — N = H+2: two valid labels for trade, two for close_to_close."""
        h = 4
        n = h + 2  # Need t+1 and t+H both valid for trade label; min is t=0 → t+H=H → need n>H
        ohlcv = make_calibration_ohlcv(n)
        candle_mask = np.ones(n, dtype=bool)

        # For log_return_trade: need t+1 < n AND t+H < n
        # t=0: t+1=1 (<6), t+H=4 (<6) → valid
        # t=1: t+1=2 (<6), t+H=5 (<6) → valid
        # t=2: t+1=3, t+H=6 (=n) → invalid
        cfg_trade = _label_config(horizon=h, target_type="log_return_trade")
        y_t, mask_t = compute_labels(ohlcv, cfg_trade, candle_mask)
        assert mask_t[0]
        assert mask_t[1]
        assert not mask_t[2]

        # For close_to_close: need t+H < n → t < n-h = 2
        cfg_c2c = _label_config(horizon=h, target_type="log_return_close_to_close")
        y_c, mask_c = compute_labels(ohlcv, cfg_c2c, candle_mask)
        assert mask_c[0]
        assert mask_c[1]
        assert not mask_c[2]

    def test_candle_mask_all_true(self):
        """#015 — candle_mask all True: only boundary labels are invalid."""
        n = 20
        h = 4
        ohlcv = make_calibration_ohlcv(n)
        cfg = _label_config(horizon=h)
        candle_mask = np.ones(n, dtype=bool)

        y, label_mask = compute_labels(ohlcv, cfg, candle_mask)

        # For log_return_trade: valid when t+1 < n and t+H < n
        # → t < n-h and t < n-1 → t < n-h (since h >= 1)
        # Positions 0..n-h-1 valid, n-h..n-1 invalid
        assert np.all(label_mask[:n - h])
        assert not np.any(label_mask[n - h:])
