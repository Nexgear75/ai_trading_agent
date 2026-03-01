"""Tests for execution metadata (meta).

Task #018 — WS-4: build execution metadata for each valid sample.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_trading.config import LabelConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ohlcv(n_bars: int, seed: int = 42) -> pd.DataFrame:
    """Create synthetic OHLCV with distinct open/close for verification."""
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range("2024-01-01", periods=n_bars, freq="1h", tz="UTC")
    close = 100.0 + np.cumsum(rng.standard_normal(n_bars) * 0.5)
    close = np.abs(close) + 1.0
    open_ = close + rng.uniform(-0.5, 0.5, n_bars)
    high = np.maximum(open_, close) + rng.uniform(0, 1, n_bars)
    low = np.minimum(open_, close) - rng.uniform(0, 1, n_bars)
    volume = rng.uniform(100, 10000, n_bars)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=timestamps,
    )


def _make_label_config(
    h: int = 4, target_type: str = "log_return_trade"
) -> LabelConfig:
    return LabelConfig(horizon_H_bars=h, target_type=target_type)


# ---------------------------------------------------------------------------
# Test: nominal shape and columns
# ---------------------------------------------------------------------------


class TestNominalShapeAndColumns:
    """#018 — meta DataFrame has expected shape and columns."""

    def test_meta_shape(self):
        from ai_trading.data.dataset import build_meta

        n_bars = 20
        h = 4
        ohlcv = _make_ohlcv(n_bars)
        timestamps = pd.DatetimeIndex(ohlcv.index[5 : n_bars - h])
        config = _make_label_config(h=h)

        meta = build_meta(ohlcv, timestamps, config)

        assert meta.shape[0] == len(timestamps)
        assert meta.shape[1] >= 5

    def test_meta_columns(self):
        from ai_trading.data.dataset import build_meta

        n_bars = 20
        h = 4
        ohlcv = _make_ohlcv(n_bars)
        timestamps = pd.DatetimeIndex(ohlcv.index[5 : n_bars - h])
        config = _make_label_config(h=h)

        meta = build_meta(ohlcv, timestamps, config)

        expected_cols = {
            "decision_time",
            "entry_time",
            "exit_time",
            "entry_price",
            "exit_price",
        }
        assert expected_cols.issubset(set(meta.columns))


# ---------------------------------------------------------------------------
# Test: correct prices
# ---------------------------------------------------------------------------


class TestCorrectPrices:
    """#018 — entry_price = Open[t+1], exit_price = Close[t+H]."""

    def test_entry_price_is_open_t_plus_1(self):
        from ai_trading.data.dataset import build_meta

        n_bars = 20
        h = 4
        ohlcv = _make_ohlcv(n_bars)
        timestamps = pd.DatetimeIndex([ohlcv.index[10]])
        config = _make_label_config(h=h)

        meta = build_meta(ohlcv, timestamps, config)

        expected_entry_price = ohlcv["open"].iloc[11]
        assert meta["entry_price"].iloc[0] == expected_entry_price

    def test_exit_price_is_close_t_plus_h(self):
        from ai_trading.data.dataset import build_meta

        n_bars = 20
        h = 4
        ohlcv = _make_ohlcv(n_bars)
        timestamps = pd.DatetimeIndex([ohlcv.index[10]])
        config = _make_label_config(h=h)

        meta = build_meta(ohlcv, timestamps, config)

        expected_exit_price = ohlcv["close"].iloc[14]  # 10 + 4
        assert meta["exit_price"].iloc[0] == expected_exit_price

    def test_prices_with_multiple_samples(self):
        from ai_trading.data.dataset import build_meta

        n_bars = 30
        h = 3
        ohlcv = _make_ohlcv(n_bars)
        decision_indices = [5, 10, 15, 20]
        timestamps = pd.DatetimeIndex([ohlcv.index[i] for i in decision_indices])
        config = _make_label_config(h=h)

        meta = build_meta(ohlcv, timestamps, config)

        for row_idx, t_idx in enumerate(decision_indices):
            assert meta["entry_price"].iloc[row_idx] == ohlcv["open"].iloc[t_idx + 1]
            assert meta["exit_price"].iloc[row_idx] == ohlcv["close"].iloc[t_idx + h]


# ---------------------------------------------------------------------------
# Test: correct timestamps
# ---------------------------------------------------------------------------


class TestCorrectTimestamps:
    """#018 — decision_time, entry_time, exit_time are correct."""

    def test_decision_time_is_close_time_of_t(self):
        from ai_trading.data.dataset import build_meta

        n_bars = 20
        h = 4
        ohlcv = _make_ohlcv(n_bars)
        timestamps = pd.DatetimeIndex([ohlcv.index[10]])
        config = _make_label_config(h=h)
        interval = ohlcv.index[1] - ohlcv.index[0]  # 1h

        meta = build_meta(ohlcv, timestamps, config)

        # decision_time = close_time(t) = open_time(t) + interval
        expected = ohlcv.index[10] + interval
        assert meta["decision_time"].iloc[0] == expected

    def test_entry_time_is_open_time_of_t_plus_1(self):
        from ai_trading.data.dataset import build_meta

        n_bars = 20
        h = 4
        ohlcv = _make_ohlcv(n_bars)
        timestamps = pd.DatetimeIndex([ohlcv.index[10]])
        config = _make_label_config(h=h)

        meta = build_meta(ohlcv, timestamps, config)

        expected = ohlcv.index[11]  # open_time(t+1)
        assert meta["entry_time"].iloc[0] == expected

    def test_exit_time_is_close_time_of_t_plus_h(self):
        from ai_trading.data.dataset import build_meta

        n_bars = 20
        h = 4
        ohlcv = _make_ohlcv(n_bars)
        timestamps = pd.DatetimeIndex([ohlcv.index[10]])
        config = _make_label_config(h=h)
        interval = ohlcv.index[1] - ohlcv.index[0]

        meta = build_meta(ohlcv, timestamps, config)

        # exit_time = close_time(t+H) = open_time(t+H) + interval
        expected = ohlcv.index[14] + interval
        assert meta["exit_time"].iloc[0] == expected

    def test_timestamps_are_utc(self):
        from ai_trading.data.dataset import build_meta

        n_bars = 20
        h = 4
        ohlcv = _make_ohlcv(n_bars)
        timestamps = pd.DatetimeIndex(ohlcv.index[5 : n_bars - h])
        config = _make_label_config(h=h)

        meta = build_meta(ohlcv, timestamps, config)

        for col in ["decision_time", "entry_time", "exit_time"]:
            dt_index = pd.DatetimeIndex(meta[col])
            assert dt_index.tz is not None, f"{col} should be tz-aware"
            assert str(dt_index.tz) == "UTC", f"{col} tz should be UTC"

    def test_timestamps_with_multiple_samples(self):
        from ai_trading.data.dataset import build_meta

        n_bars = 30
        h = 3
        ohlcv = _make_ohlcv(n_bars)
        decision_indices = [5, 10, 15]
        timestamps = pd.DatetimeIndex([ohlcv.index[i] for i in decision_indices])
        config = _make_label_config(h=h)
        interval = ohlcv.index[1] - ohlcv.index[0]

        meta = build_meta(ohlcv, timestamps, config)

        for row_idx, t_idx in enumerate(decision_indices):
            assert meta["decision_time"].iloc[row_idx] == ohlcv.index[t_idx] + interval
            assert meta["entry_time"].iloc[row_idx] == ohlcv.index[t_idx + 1]
            assert (
                meta["exit_time"].iloc[row_idx] == ohlcv.index[t_idx + h] + interval
            )


# ---------------------------------------------------------------------------
# Test: coherence with labels
# ---------------------------------------------------------------------------


class TestCoherenceLogReturnTrade:
    """#018 — y_t ≈ log(exit_price / entry_price) for log_return_trade."""

    def test_coherence(self):
        from ai_trading.data.dataset import build_meta
        from ai_trading.data.labels import compute_labels

        n_bars = 30
        h = 4
        ohlcv = _make_ohlcv(n_bars)
        candle_mask = np.ones(n_bars, dtype=bool)
        config = _make_label_config(h=h, target_type="log_return_trade")

        y, label_mask = compute_labels(ohlcv, config, candle_mask)

        valid_indices = np.where(label_mask)[0]
        timestamps = pd.DatetimeIndex(ohlcv.index[valid_indices])

        meta = build_meta(ohlcv, timestamps, config)

        # y_t ≈ log(exit_price / entry_price)
        for i, t_idx in enumerate(valid_indices):
            expected = np.log(
                meta["exit_price"].iloc[i] / meta["entry_price"].iloc[i]
            )
            np.testing.assert_allclose(y[t_idx], expected, atol=1e-10)


class TestCoherenceLogReturnCloseToClose:
    """#018 — y_t ≈ log(Close[t+H] / Close[t]) for close-to-close."""

    def test_coherence(self):
        from ai_trading.data.dataset import build_meta
        from ai_trading.data.labels import compute_labels

        n_bars = 30
        h = 4
        ohlcv = _make_ohlcv(n_bars)
        candle_mask = np.ones(n_bars, dtype=bool)
        config = _make_label_config(h=h, target_type="log_return_close_to_close")

        y, label_mask = compute_labels(ohlcv, config, candle_mask)

        valid_indices = np.where(label_mask)[0]
        timestamps = pd.DatetimeIndex(ohlcv.index[valid_indices])

        meta = build_meta(ohlcv, timestamps, config)

        # y_t ≈ log(Close[t+H] / Close[t])
        # exit_price = Close[t+H], Close[t] = ohlcv.close.iloc[t_idx]
        for _i, t_idx in enumerate(valid_indices):
            close_t_h = ohlcv["close"].iloc[t_idx + h]
            assert meta["exit_price"].iloc[_i] == close_t_h
            expected = np.log(
                ohlcv["close"].iloc[t_idx + h] / ohlcv["close"].iloc[t_idx]
            )
            np.testing.assert_allclose(y[t_idx], expected, atol=1e-10)


# ---------------------------------------------------------------------------
# Test: horizon from config (not hardcoded)
# ---------------------------------------------------------------------------


class TestHorizonFromConfig:
    """#018 — horizon_H_bars read from config, not hardcoded."""

    def test_different_horizons_produce_different_exit_prices(self):
        from ai_trading.data.dataset import build_meta

        n_bars = 30
        ohlcv = _make_ohlcv(n_bars)
        timestamps = pd.DatetimeIndex([ohlcv.index[5]])

        meta_h2 = build_meta(ohlcv, timestamps, _make_label_config(h=2))
        meta_h6 = build_meta(ohlcv, timestamps, _make_label_config(h=6))

        # Different H -> different exit prices (Close[t+H])
        assert meta_h2["exit_price"].iloc[0] == ohlcv["close"].iloc[7]
        assert meta_h6["exit_price"].iloc[0] == ohlcv["close"].iloc[11]

    def test_different_horizons_produce_different_exit_times(self):
        from ai_trading.data.dataset import build_meta

        n_bars = 30
        ohlcv = _make_ohlcv(n_bars)
        timestamps = pd.DatetimeIndex([ohlcv.index[5]])

        meta_h2 = build_meta(ohlcv, timestamps, _make_label_config(h=2))
        meta_h6 = build_meta(ohlcv, timestamps, _make_label_config(h=6))

        assert meta_h2["exit_time"].iloc[0] != meta_h6["exit_time"].iloc[0]


# ---------------------------------------------------------------------------
# Test: edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """#018 — Edge cases for build_meta."""

    def test_empty_timestamps(self):
        from ai_trading.data.dataset import build_meta

        ohlcv = _make_ohlcv(20)
        timestamps = pd.DatetimeIndex([], tz="UTC")
        config = _make_label_config(h=4)

        meta = build_meta(ohlcv, timestamps, config)

        assert meta.shape[0] == 0
        expected_cols = {
            "decision_time",
            "entry_time",
            "exit_time",
            "entry_price",
            "exit_price",
        }
        assert expected_cols.issubset(set(meta.columns))

    def test_single_sample(self):
        from ai_trading.data.dataset import build_meta

        ohlcv = _make_ohlcv(20)
        timestamps = pd.DatetimeIndex([ohlcv.index[5]])
        config = _make_label_config(h=4)

        meta = build_meta(ohlcv, timestamps, config)

        assert meta.shape[0] == 1
        assert meta["entry_price"].iloc[0] == ohlcv["open"].iloc[6]
        assert meta["exit_price"].iloc[0] == ohlcv["close"].iloc[9]

    def test_h_equals_1(self):
        """Minimum horizon: exit_price = Close[t+1], entry = Open[t+1]."""
        from ai_trading.data.dataset import build_meta

        ohlcv = _make_ohlcv(20)
        timestamps = pd.DatetimeIndex([ohlcv.index[5]])
        config = _make_label_config(h=1)

        meta = build_meta(ohlcv, timestamps, config)

        assert meta["entry_price"].iloc[0] == ohlcv["open"].iloc[6]
        assert meta["exit_price"].iloc[0] == ohlcv["close"].iloc[6]  # t+1

    def test_decision_at_boundary(self):
        """Decision at the last valid position (t+H == last bar)."""
        from ai_trading.data.dataset import build_meta

        n_bars = 20
        h = 4
        ohlcv = _make_ohlcv(n_bars)
        # Last valid position: t = n_bars - h - 1 = 15
        last_valid = n_bars - h - 1
        timestamps = pd.DatetimeIndex([ohlcv.index[last_valid]])
        config = _make_label_config(h=h)

        meta = build_meta(ohlcv, timestamps, config)

        assert meta.shape[0] == 1
        assert meta["exit_price"].iloc[0] == ohlcv["close"].iloc[last_valid + h]

    def test_timestamp_not_in_ohlcv_raises(self):
        """Timestamp not found in ohlcv should raise ValueError."""
        from ai_trading.data.dataset import build_meta

        ohlcv = _make_ohlcv(20)
        bad_ts = pd.DatetimeIndex([pd.Timestamp("2099-01-01", tz="UTC")])
        config = _make_label_config(h=4)

        with pytest.raises(ValueError, match="not found in ohlcv"):
            build_meta(ohlcv, bad_ts, config)

    def test_insufficient_future_bars_raises(self):
        """t+H beyond ohlcv should raise ValueError."""
        from ai_trading.data.dataset import build_meta

        ohlcv = _make_ohlcv(10)
        # Decision at last bar => t+H is out of bounds
        timestamps = pd.DatetimeIndex([ohlcv.index[-1]])
        config = _make_label_config(h=4)

        with pytest.raises(ValueError, match="beyond ohlcv"):
            build_meta(ohlcv, timestamps, config)

    def test_ohlcv_needs_at_least_2_bars_for_interval(self):
        """Cannot infer candle interval from a single-bar OHLCV."""
        from ai_trading.data.dataset import build_meta

        ohlcv = _make_ohlcv(1)
        timestamps = pd.DatetimeIndex([ohlcv.index[0]])
        config = _make_label_config(h=1)

        with pytest.raises(ValueError):
            build_meta(ohlcv, timestamps, config)
