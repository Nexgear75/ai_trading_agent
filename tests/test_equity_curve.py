"""Tests for the equity curve builder — build_equity_curve / save_equity_curve_csv.

Task #029 — WS-8: Courbe d'équité.
Spec §12.4: equity curve with per-candle resolution, no mark-to-market.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ai_trading.backtest.engine import build_equity_curve, save_equity_curve_csv

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HORIZON = 4


def _make_ohlcv(n: int, start: str = "2024-01-01") -> pd.DataFrame:
    """Synthetic OHLCV DataFrame with *n* rows."""
    idx = pd.date_range(start, periods=n, freq="1h")
    rng = np.random.default_rng(42)
    opens = 100.0 + rng.standard_normal(n).cumsum()
    closes = opens + rng.standard_normal(n) * 0.5
    return pd.DataFrame(
        {
            "open": opens,
            "close": closes,
            "high": np.maximum(opens, closes) + 0.5,
            "low": np.minimum(opens, closes) - 0.5,
            "volume": rng.uniform(100, 1000, n),
        },
        index=idx,
    )


def _make_enriched_trade(
    ohlcv: pd.DataFrame,
    signal_idx: int,
    horizon: int,
    fee: float = 0.001,
    slippage: float = 0.0003,
) -> dict:
    """Build a single enriched trade dict from ohlcv at given signal index."""
    entry_idx = signal_idx + 1
    exit_idx = signal_idx + horizon
    p_entry = float(ohlcv["open"].iloc[entry_idx])
    p_exit = float(ohlcv["close"].iloc[exit_idx])
    p_entry_eff = p_entry * (1 + slippage)
    p_exit_eff = p_exit * (1 - slippage)
    fee_factor_sq = (1 - fee) ** 2
    m_net = fee_factor_sq * (p_exit_eff / p_entry_eff)
    r_net = m_net - 1
    return {
        "signal_time": ohlcv.index[signal_idx],
        "entry_time": ohlcv.index[entry_idx],
        "exit_time": ohlcv.index[exit_idx],
        "entry_price": p_entry,
        "exit_price": p_exit,
        "entry_price_eff": p_entry_eff,
        "exit_price_eff": p_exit_eff,
        "m_net": m_net,
        "r_net": r_net,
    }


def _make_fixed_price_ohlcv(
    n: int,
    open_price: float,
    close_price: float,
) -> pd.DataFrame:
    """OHLCV where open/close are constant (for numerical verification)."""
    idx = pd.date_range("2024-01-01", periods=n, freq="1h")
    return pd.DataFrame(
        {
            "open": np.full(n, open_price),
            "close": np.full(n, close_price),
            "high": np.full(n, max(open_price, close_price) + 0.5),
            "low": np.full(n, min(open_price, close_price) - 0.5),
            "volume": np.full(n, 500.0),
        },
        index=idx,
    )


# ---------------------------------------------------------------------------
# Nominal — single trade
# ---------------------------------------------------------------------------


class TestSingleTrade:
    """One trade: equity unchanged before/during, updated at exit candle."""

    def test_equity_starts_at_initial(self) -> None:
        ohlcv = _make_ohlcv(20)
        trade = _make_enriched_trade(ohlcv, signal_idx=5, horizon=HORIZON)
        curve = build_equity_curve([trade], ohlcv, 1.0, 1.0)
        assert curve["equity"].iloc[0] == pytest.approx(1.0)

    def test_equity_constant_before_trade(self) -> None:
        ohlcv = _make_ohlcv(20)
        trade = _make_enriched_trade(ohlcv, signal_idx=5, horizon=HORIZON)
        curve = build_equity_curve([trade], ohlcv, 1.0, 1.0)
        # Before entry (indices 0..5), equity must be 1.0
        entry_idx = 6  # signal_idx + 1
        for i in range(entry_idx):
            assert curve["equity"].iloc[i] == pytest.approx(1.0), f"idx={i}"

    def test_equity_constant_during_trade(self) -> None:
        """No mark-to-market: equity stays at E_entry during the trade."""
        ohlcv = _make_ohlcv(20)
        trade = _make_enriched_trade(ohlcv, signal_idx=5, horizon=HORIZON)
        curve = build_equity_curve([trade], ohlcv, 1.0, 1.0)
        entry_idx = 6
        exit_idx = 9  # signal_idx + horizon
        # From entry to exit-1, equity remains at E_entry = 1.0
        for i in range(entry_idx, exit_idx):
            assert curve["equity"].iloc[i] == pytest.approx(1.0), f"idx={i}"

    def test_equity_updated_at_exit(self) -> None:
        ohlcv = _make_ohlcv(20)
        trade = _make_enriched_trade(ohlcv, signal_idx=5, horizon=HORIZON)
        curve = build_equity_curve([trade], ohlcv, 1.0, 1.0)
        exit_idx = 9
        expected = 1.0 * (1 + 1.0 * trade["r_net"])
        assert curve["equity"].iloc[exit_idx] == pytest.approx(expected, abs=1e-12)

    def test_equity_constant_after_trade(self) -> None:
        ohlcv = _make_ohlcv(20)
        trade = _make_enriched_trade(ohlcv, signal_idx=5, horizon=HORIZON)
        curve = build_equity_curve([trade], ohlcv, 1.0, 1.0)
        exit_idx = 9
        e_exit = curve["equity"].iloc[exit_idx]
        for i in range(exit_idx + 1, len(ohlcv)):
            assert curve["equity"].iloc[i] == pytest.approx(e_exit), f"idx={i}"


# ---------------------------------------------------------------------------
# Nominal — multi-trade cumulative
# ---------------------------------------------------------------------------


class TestMultiTrade:
    """Multiple trades: E_final = E_0 × Π(1 + w × r_net_i)."""

    def test_cumulative_equity(self) -> None:
        ohlcv = _make_ohlcv(30)
        t1 = _make_enriched_trade(ohlcv, signal_idx=2, horizon=HORIZON)
        # Second trade must start after first exits (idx 2+4=6, next signal >=7)
        t2 = _make_enriched_trade(ohlcv, signal_idx=10, horizon=HORIZON)
        trades = [t1, t2]
        curve = build_equity_curve(trades, ohlcv, 1.0, 1.0)

        e_expected = 1.0
        for t in trades:
            e_expected *= 1 + 1.0 * t["r_net"]

        assert curve["equity"].iloc[-1] == pytest.approx(e_expected, abs=1e-8)

    def test_equity_between_trades_is_constant(self) -> None:
        ohlcv = _make_ohlcv(30)
        t1 = _make_enriched_trade(ohlcv, signal_idx=2, horizon=HORIZON)
        t2 = _make_enriched_trade(ohlcv, signal_idx=10, horizon=HORIZON)
        curve = build_equity_curve([t1, t2], ohlcv, 1.0, 1.0)

        # Between exit of t1 (idx 6) and entry of t2 (idx 11), equity constant
        e_after_t1 = curve["equity"].iloc[6]
        for i in range(7, 11):
            assert curve["equity"].iloc[i] == pytest.approx(e_after_t1), f"idx={i}"


# ---------------------------------------------------------------------------
# Position fraction w < 1
# ---------------------------------------------------------------------------


class TestPositionFraction:
    """w < 1.0 reduces the impact of each trade proportionally."""

    def test_w_half_reduces_impact(self) -> None:
        ohlcv = _make_ohlcv(20)
        trade = _make_enriched_trade(ohlcv, signal_idx=5, horizon=HORIZON)
        curve_full = build_equity_curve([trade], ohlcv, 1.0, 1.0)
        curve_half = build_equity_curve([trade], ohlcv, 1.0, 0.5)

        e_full = curve_full["equity"].iloc[-1]
        e_half = curve_half["equity"].iloc[-1]

        # E_full = 1 × (1 + 1.0 × r_net)
        # E_half = 1 × (1 + 0.5 × r_net)
        r = trade["r_net"]
        assert e_full == pytest.approx(1 + r, abs=1e-12)
        assert e_half == pytest.approx(1 + 0.5 * r, abs=1e-12)

    def test_cumulative_with_w(self) -> None:
        ohlcv = _make_ohlcv(30)
        t1 = _make_enriched_trade(ohlcv, signal_idx=2, horizon=HORIZON)
        t2 = _make_enriched_trade(ohlcv, signal_idx=10, horizon=HORIZON)
        w = 0.3
        curve = build_equity_curve([t1, t2], ohlcv, 1.0, w)

        e_expected = 1.0
        for t in [t1, t2]:
            e_expected *= 1 + w * t["r_net"]

        assert curve["equity"].iloc[-1] == pytest.approx(e_expected, abs=1e-8)


# ---------------------------------------------------------------------------
# Numerical example from spec
# ---------------------------------------------------------------------------


class TestNumericalExample:
    """Spec example: f=0.001, s=0.0003, Open=100, Close=102."""

    def test_spec_numerical(self) -> None:
        """Verify the exact numerical example from the spec/task."""
        n = 10
        ohlcv = _make_fixed_price_ohlcv(n, open_price=100.0, close_price=102.0)
        # Signal at t=0, entry at t=1, exit at t=4 (horizon=4)
        f = 0.001
        s = 0.0003
        p_entry_eff = 100.0 * (1 + s)
        p_exit_eff = 102.0 * (1 - s)
        fee_factor_sq = (1 - f) ** 2
        m_net = fee_factor_sq * (p_exit_eff / p_entry_eff)
        r_net = m_net - 1

        trade = {
            "signal_time": ohlcv.index[0],
            "entry_time": ohlcv.index[1],
            "exit_time": ohlcv.index[4],
            "entry_price": 100.0,
            "exit_price": 102.0,
            "entry_price_eff": p_entry_eff,
            "exit_price_eff": p_exit_eff,
            "m_net": m_net,
            "r_net": r_net,
        }

        curve = build_equity_curve([trade], ohlcv, 1.0, 1.0)
        e_exit = curve["equity"].iloc[4]

        # Expected: E_exit ≈ 1.0174 (more precisely ~1.01738)
        assert e_exit == pytest.approx(1.0 + r_net, abs=1e-8)
        assert r_net == pytest.approx(0.0174, abs=5e-4)


# ---------------------------------------------------------------------------
# in_trade column
# ---------------------------------------------------------------------------


class TestInTradeColumn:
    """in_trade: False at signal/decision bar, True from entry to exit (inclusive)."""

    def test_in_trade_single_trade(self) -> None:
        ohlcv = _make_ohlcv(20)
        trade = _make_enriched_trade(ohlcv, signal_idx=5, horizon=HORIZON)
        curve = build_equity_curve([trade], ohlcv, 1.0, 1.0)

        signal_idx = 5
        entry_idx = 6
        exit_idx = 9

        # Before entry: all False
        for i in range(entry_idx):
            assert curve["in_trade"].iloc[i] is np.bool_(False), f"idx={i}"

        # Entry to exit inclusive: True
        for i in range(entry_idx, exit_idx + 1):
            assert curve["in_trade"].iloc[i] is np.bool_(True), f"idx={i}"

        # After exit: False
        for i in range(exit_idx + 1, len(ohlcv)):
            assert curve["in_trade"].iloc[i] is np.bool_(False), f"idx={i}"

    def test_in_trade_multi_trade(self) -> None:
        ohlcv = _make_ohlcv(30)
        t1 = _make_enriched_trade(ohlcv, signal_idx=2, horizon=HORIZON)
        t2 = _make_enriched_trade(ohlcv, signal_idx=10, horizon=HORIZON)
        curve = build_equity_curve([t1, t2], ohlcv, 1.0, 1.0)

        # Gap between trades — not in trade
        for i in range(7, 11):
            assert curve["in_trade"].iloc[i] is np.bool_(False), f"gap idx={i}"

        # t2 entry to exit
        for i in range(11, 15):
            assert curve["in_trade"].iloc[i] is np.bool_(True), f"t2 idx={i}"


# ---------------------------------------------------------------------------
# CSV roundtrip
# ---------------------------------------------------------------------------


class TestCsvRoundtrip:
    """save_equity_curve_csv writes correct CSV format."""

    def test_save_and_reload(self, tmp_path: Path) -> None:
        ohlcv = _make_ohlcv(20)
        trade = _make_enriched_trade(ohlcv, signal_idx=5, horizon=HORIZON)
        curve = build_equity_curve([trade], ohlcv, 1.0, 1.0)
        csv_path = tmp_path / "equity_curve.csv"
        save_equity_curve_csv(curve, csv_path)

        loaded = pd.read_csv(csv_path)
        assert list(loaded.columns) == ["time_utc", "equity", "in_trade"]
        assert len(loaded) == len(ohlcv)

    def test_csv_equity_values_match(self, tmp_path: Path) -> None:
        ohlcv = _make_ohlcv(20)
        trade = _make_enriched_trade(ohlcv, signal_idx=5, horizon=HORIZON)
        curve = build_equity_curve([trade], ohlcv, 1.0, 1.0)
        csv_path = tmp_path / "equity_curve.csv"
        save_equity_curve_csv(curve, csv_path)

        loaded = pd.read_csv(csv_path)
        np.testing.assert_allclose(
            loaded["equity"].values, curve["equity"].values, atol=1e-12
        )


# ---------------------------------------------------------------------------
# No-trades edge case
# ---------------------------------------------------------------------------


class TestNoTrades:
    """Empty trade list → equity constant at E_0, in_trade all False."""

    def test_no_trades_equity_constant(self) -> None:
        ohlcv = _make_ohlcv(20)
        curve = build_equity_curve([], ohlcv, 1.0, 1.0)
        np.testing.assert_allclose(curve["equity"].values, 1.0)

    def test_no_trades_in_trade_all_false(self) -> None:
        ohlcv = _make_ohlcv(20)
        curve = build_equity_curve([], ohlcv, 1.0, 1.0)
        assert not curve["in_trade"].any()


# ---------------------------------------------------------------------------
# Edge — trade at last candle
# ---------------------------------------------------------------------------


class TestTradeAtLastCandle:
    """Trade whose exit_time equals the last candle timestamp."""

    def test_exit_at_last_candle(self) -> None:
        n = 10
        ohlcv = _make_ohlcv(n)
        # signal_idx=5, horizon=4 → exit_idx=9 = last index
        trade = _make_enriched_trade(ohlcv, signal_idx=5, horizon=4)
        curve = build_equity_curve([trade], ohlcv, 1.0, 1.0)
        expected = 1.0 * (1 + trade["r_net"])
        assert curve["equity"].iloc[-1] == pytest.approx(expected, abs=1e-12)


# ---------------------------------------------------------------------------
# Intra-trade equity constant (no mark-to-market)
# ---------------------------------------------------------------------------


class TestNoMarkToMarket:
    """Even if Close fluctuates wildly during a trade, equity stays constant."""

    def test_equity_constant_intra_trade_volatile(self) -> None:
        n = 20
        idx = pd.date_range("2024-01-01", periods=n, freq="1h")
        # Prices that drop sharply mid-trade then recover
        opens = np.full(n, 100.0)
        closes = np.full(n, 102.0)
        # Simulate drawdown at bar 7,8 (during trade entry=6..exit=9)
        closes[7] = 80.0  # big drawdown
        closes[8] = 85.0  # partial recovery
        ohlcv = pd.DataFrame(
            {
                "open": opens,
                "close": closes,
                "high": np.maximum(opens, closes) + 1.0,
                "low": np.minimum(opens, closes) - 1.0,
                "volume": np.full(n, 500.0),
            },
            index=idx,
        )
        # Build trade: signal=5, entry=6, exit=9
        f, s = 0.001, 0.0003
        p_entry = float(ohlcv["open"].iloc[6])
        p_exit = float(ohlcv["close"].iloc[9])  # 102.0 — recovered
        p_entry_eff = p_entry * (1 + s)
        p_exit_eff = p_exit * (1 - s)
        m_net = (1 - f) ** 2 * (p_exit_eff / p_entry_eff)
        r_net = m_net - 1
        trade = {
            "signal_time": ohlcv.index[5],
            "entry_time": ohlcv.index[6],
            "exit_time": ohlcv.index[9],
            "entry_price": p_entry,
            "exit_price": p_exit,
            "entry_price_eff": p_entry_eff,
            "exit_price_eff": p_exit_eff,
            "m_net": m_net,
            "r_net": r_net,
        }
        curve = build_equity_curve([trade], ohlcv, 1.0, 1.0)

        # Equity at bars 6, 7, 8 must be E_0 = 1.0 (constant, no MTM)
        for i in [6, 7, 8]:
            assert curve["equity"].iloc[i] == pytest.approx(1.0), f"idx={i}"


# ---------------------------------------------------------------------------
# Single_trade mode (buy & hold)
# ---------------------------------------------------------------------------


class TestSingleTradeMode:
    """Single trade covering the full period: equity constant until last candle."""

    def test_single_trade_equity(self) -> None:
        n = 10
        ohlcv = _make_fixed_price_ohlcv(n, open_price=100.0, close_price=105.0)
        f, s = 0.001, 0.0003
        p_entry_eff = 100.0 * (1 + s)
        p_exit_eff = 105.0 * (1 - s)
        m_net = (1 - f) ** 2 * (p_exit_eff / p_entry_eff)
        r_net = m_net - 1
        trade = {
            "signal_time": ohlcv.index[0],
            "entry_time": ohlcv.index[0],
            "exit_time": ohlcv.index[-1],
            "entry_price": 100.0,
            "exit_price": 105.0,
            "entry_price_eff": p_entry_eff,
            "exit_price_eff": p_exit_eff,
            "m_net": m_net,
            "r_net": r_net,
        }
        curve = build_equity_curve([trade], ohlcv, 1.0, 1.0)

        # All candles from entry to exit-1 are in trade with constant equity
        for i in range(n - 1):
            assert curve["equity"].iloc[i] == pytest.approx(1.0), f"idx={i}"

        # Exit at last candle
        expected = 1.0 * (1 + r_net)
        assert curve["equity"].iloc[-1] == pytest.approx(expected, abs=1e-8)


# ---------------------------------------------------------------------------
# Validation / error cases
# ---------------------------------------------------------------------------


class TestValidation:
    """Input validation raises on invalid inputs."""

    def test_empty_ohlcv_raises(self) -> None:
        empty_ohlcv = pd.DataFrame(
            columns=["open", "close", "high", "low", "volume"],
            index=pd.DatetimeIndex([], name="time"),
        )
        with pytest.raises(ValueError, match="ohlcv must not be empty"):
            build_equity_curve([], empty_ohlcv, 1.0, 1.0)

    def test_invalid_initial_equity_raises(self) -> None:
        ohlcv = _make_ohlcv(10)
        with pytest.raises(ValueError, match="initial_equity must be > 0"):
            build_equity_curve([], ohlcv, 0.0, 1.0)

    def test_negative_initial_equity_raises(self) -> None:
        ohlcv = _make_ohlcv(10)
        with pytest.raises(ValueError, match="initial_equity must be > 0"):
            build_equity_curve([], ohlcv, -1.0, 1.0)

    def test_invalid_position_fraction_zero_raises(self) -> None:
        ohlcv = _make_ohlcv(10)
        with pytest.raises(ValueError, match="position_fraction must be in"):
            build_equity_curve([], ohlcv, 1.0, 0.0)

    def test_invalid_position_fraction_above_one_raises(self) -> None:
        ohlcv = _make_ohlcv(10)
        with pytest.raises(ValueError, match="position_fraction must be in"):
            build_equity_curve([], ohlcv, 1.0, 1.5)

    def test_trade_missing_r_net_raises(self) -> None:
        ohlcv = _make_ohlcv(20)
        bad_trade = {
            "signal_time": ohlcv.index[5],
            "entry_time": ohlcv.index[6],
            "exit_time": ohlcv.index[9],
        }
        with pytest.raises(ValueError, match="r_net"):
            build_equity_curve([bad_trade], ohlcv, 1.0, 1.0)

    def test_trade_missing_entry_time_raises(self) -> None:
        ohlcv = _make_ohlcv(20)
        bad_trade = {
            "signal_time": ohlcv.index[5],
            "exit_time": ohlcv.index[9],
            "r_net": 0.01,
        }
        with pytest.raises(ValueError, match="entry_time"):
            build_equity_curve([bad_trade], ohlcv, 1.0, 1.0)

    def test_trade_missing_exit_time_raises(self) -> None:
        ohlcv = _make_ohlcv(20)
        bad_trade = {
            "signal_time": ohlcv.index[5],
            "entry_time": ohlcv.index[6],
            "r_net": 0.01,
        }
        with pytest.raises(ValueError, match="exit_time"):
            build_equity_curve([bad_trade], ohlcv, 1.0, 1.0)

    def test_entry_time_not_in_ohlcv_raises(self) -> None:
        ohlcv = _make_ohlcv(20)
        bad_trade = {
            "signal_time": ohlcv.index[5],
            "entry_time": pd.Timestamp("2099-01-01"),
            "exit_time": ohlcv.index[9],
            "r_net": 0.01,
        }
        with pytest.raises(ValueError, match="entry_time .* not found in ohlcv"):
            build_equity_curve([bad_trade], ohlcv, 1.0, 1.0)

    def test_exit_time_not_in_ohlcv_raises(self) -> None:
        ohlcv = _make_ohlcv(20)
        bad_trade = {
            "signal_time": ohlcv.index[5],
            "entry_time": ohlcv.index[6],
            "exit_time": pd.Timestamp("2099-01-01"),
            "r_net": 0.01,
        }
        with pytest.raises(ValueError, match="exit_time .* not found in ohlcv"):
            build_equity_curve([bad_trade], ohlcv, 1.0, 1.0)


# ---------------------------------------------------------------------------
# Output shape and columns
# ---------------------------------------------------------------------------


class TestOutputShape:
    """Equity curve DataFrame has correct shape and columns."""

    def test_columns(self) -> None:
        ohlcv = _make_ohlcv(20)
        curve = build_equity_curve([], ohlcv, 1.0, 1.0)
        assert list(curve.columns) == ["time_utc", "equity", "in_trade"]

    def test_length_matches_ohlcv(self) -> None:
        ohlcv = _make_ohlcv(20)
        curve = build_equity_curve([], ohlcv, 1.0, 1.0)
        assert len(curve) == len(ohlcv)

    def test_time_utc_matches_ohlcv_index(self) -> None:
        ohlcv = _make_ohlcv(20)
        curve = build_equity_curve([], ohlcv, 1.0, 1.0)
        pd.testing.assert_index_equal(
            pd.DatetimeIndex(curve["time_utc"]), ohlcv.index
        )
