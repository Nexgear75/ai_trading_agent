"""Tests for backtest trade execution engine.

Task #026 — WS-8: Règles d'exécution des trades.
Covers: standard mode, single_trade mode, one_at_a_time overlap,
long-only, edge cases, input validation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_trading.backtest.engine import execute_trades

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

HORIZON = 4


@pytest.fixture()
def ohlcv_20() -> pd.DataFrame:
    """Synthetic OHLCV DataFrame with 20 rows and DatetimeIndex."""
    n = 20
    idx = pd.date_range("2024-01-01", periods=n, freq="1h")
    rng = np.random.default_rng(42)
    opens = 100.0 + rng.standard_normal(n).cumsum()
    closes = opens + rng.standard_normal(n) * 0.5
    highs = np.maximum(opens, closes) + rng.uniform(0, 1, n)
    lows = np.minimum(opens, closes) - rng.uniform(0, 1, n)
    volumes = rng.uniform(100, 1000, n)
    return pd.DataFrame(
        {
            "open": opens,
            "close": closes,
            "high": highs,
            "low": lows,
            "volume": volumes,
        },
        index=idx,
    )


# ---------------------------------------------------------------------------
# Nominal — standard mode
# ---------------------------------------------------------------------------


class TestStandardModeSingleSignal:
    """A single Go at t produces one trade: entry=Open[t+1], exit=Close[t+H]."""

    def test_one_go_produces_one_trade(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        t = 5
        signals[t] = 1
        trades = execute_trades(signals, ohlcv_20, HORIZON, "standard")
        assert len(trades) == 1

    def test_entry_price_is_open_t_plus_1(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        t = 5
        signals[t] = 1
        trades = execute_trades(signals, ohlcv_20, HORIZON, "standard")
        assert trades[0]["entry_price"] == float(ohlcv_20["open"].iloc[t + 1])

    def test_exit_price_is_close_t_plus_h(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        t = 5
        signals[t] = 1
        trades = execute_trades(signals, ohlcv_20, HORIZON, "standard")
        assert trades[0]["exit_price"] == float(ohlcv_20["close"].iloc[t + HORIZON])

    def test_signal_time_is_t(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        t = 5
        signals[t] = 1
        trades = execute_trades(signals, ohlcv_20, HORIZON, "standard")
        assert trades[0]["signal_time"] == ohlcv_20.index[t]

    def test_entry_time_is_t_plus_1(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        t = 5
        signals[t] = 1
        trades = execute_trades(signals, ohlcv_20, HORIZON, "standard")
        assert trades[0]["entry_time"] == ohlcv_20.index[t + 1]

    def test_exit_time_is_t_plus_h(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        t = 5
        signals[t] = 1
        trades = execute_trades(signals, ohlcv_20, HORIZON, "standard")
        assert trades[0]["exit_time"] == ohlcv_20.index[t + HORIZON]


class TestStandardModeMultipleSignals:
    """Multiple spaced Go signals produce multiple trades."""

    def test_two_spaced_signals_two_trades(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        # t=0 → trade covers bars 1..4, t=10 → trade covers bars 11..14
        signals[0] = 1
        signals[10] = 1
        trades = execute_trades(signals, ohlcv_20, HORIZON, "standard")
        assert len(trades) == 2

    def test_trades_have_correct_entry_prices(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        signals[0] = 1
        signals[10] = 1
        trades = execute_trades(signals, ohlcv_20, HORIZON, "standard")
        assert trades[0]["entry_price"] == float(ohlcv_20["open"].iloc[1])
        assert trades[1]["entry_price"] == float(ohlcv_20["open"].iloc[11])


# ---------------------------------------------------------------------------
# one_at_a_time — overlap rejection
# ---------------------------------------------------------------------------


class TestOneAtATime:
    """Go during an active trade is ignored (one_at_a_time mode)."""

    def test_consecutive_go_only_first_taken(self, ohlcv_20: pd.DataFrame) -> None:
        """Go at t=0 opens trade covering bars 1..4. Go at t=2 is during trade → ignored."""
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        signals[0] = 1
        signals[2] = 1  # during active trade (exit at bar 4)
        trades = execute_trades(signals, ohlcv_20, HORIZON, "standard")
        assert len(trades) == 1

    def test_go_at_exact_exit_bar_is_accepted(self, ohlcv_20: pd.DataFrame) -> None:
        """Go at t=H (the exit bar of first trade): position freed at t>=exit → accepted."""
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        signals[0] = 1  # trade from bar 1 to bar 4
        signals[HORIZON] = 1  # t=4 = exit bar → position freed → new trade
        trades = execute_trades(signals, ohlcv_20, HORIZON, "standard")
        assert len(trades) == 2

    def test_go_after_exit_bar_is_accepted(self, ohlcv_20: pd.DataFrame) -> None:
        """Go at t=H+1 (after trade exit) should start a new trade."""
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        signals[0] = 1  # trade from bar 1 to bar 4
        signals[HORIZON + 1] = 1  # t=5, first bar after exit
        trades = execute_trades(signals, ohlcv_20, HORIZON, "standard")
        assert len(trades) == 2


# ---------------------------------------------------------------------------
# single_trade mode
# ---------------------------------------------------------------------------


class TestSingleTradeMode:
    """single_trade mode: one trade covering entire period, signals ignored."""

    def test_one_trade_returned(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.ones(len(ohlcv_20), dtype=np.int64)
        trades = execute_trades(signals, ohlcv_20, HORIZON, "single_trade")
        assert len(trades) == 1

    def test_entry_price_is_open_first(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        trades = execute_trades(signals, ohlcv_20, HORIZON, "single_trade")
        assert trades[0]["entry_price"] == float(ohlcv_20["open"].iloc[0])

    def test_exit_price_is_close_last(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        trades = execute_trades(signals, ohlcv_20, HORIZON, "single_trade")
        assert trades[0]["exit_price"] == float(ohlcv_20["close"].iloc[-1])

    def test_entry_time_is_first_timestamp(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        trades = execute_trades(signals, ohlcv_20, HORIZON, "single_trade")
        assert trades[0]["entry_time"] == ohlcv_20.index[0]

    def test_exit_time_is_last_timestamp(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        trades = execute_trades(signals, ohlcv_20, HORIZON, "single_trade")
        assert trades[0]["exit_time"] == ohlcv_20.index[-1]

    def test_signal_time_is_first_timestamp(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        trades = execute_trades(signals, ohlcv_20, HORIZON, "single_trade")
        assert trades[0]["signal_time"] == ohlcv_20.index[0]

    def test_signals_are_ignored(self, ohlcv_20: pd.DataFrame) -> None:
        """Result should be the same regardless of signal content."""
        signals_all_zero = np.zeros(len(ohlcv_20), dtype=np.int64)
        signals_all_one = np.ones(len(ohlcv_20), dtype=np.int64)
        t0 = execute_trades(signals_all_zero, ohlcv_20, HORIZON, "single_trade")
        t1 = execute_trades(signals_all_one, ohlcv_20, HORIZON, "single_trade")
        assert t0 == t1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases: no signals, boundary signals, insufficient bars."""

    def test_no_go_signal_returns_empty(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        trades = execute_trades(signals, ohlcv_20, HORIZON, "standard")
        assert trades == []

    def test_go_on_last_bar_ignored(self, ohlcv_20: pd.DataFrame) -> None:
        """Go on last bar: t+1 is out of bounds → trade ignored."""
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        signals[-1] = 1
        trades = execute_trades(signals, ohlcv_20, HORIZON, "standard")
        assert trades == []

    def test_go_where_t_plus_h_exceeds_data(self, ohlcv_20: pd.DataFrame) -> None:
        """Go at t where t+H >= len(ohlcv) → trade ignored."""
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        # t = len-H → close_idx = len-H + H = len → out of bounds
        t = len(ohlcv_20) - HORIZON
        signals[t] = 1
        trades = execute_trades(signals, ohlcv_20, HORIZON, "standard")
        assert trades == []

    def test_go_at_second_to_last_bar_with_h1(self, ohlcv_20: pd.DataFrame) -> None:
        """With H=1, Go at t=len-2: entry_idx=len-1, close_idx=len-1 → valid."""
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        t = len(ohlcv_20) - 2
        signals[t] = 1
        trades = execute_trades(signals, ohlcv_20, horizon=1, execution_mode="standard")
        assert len(trades) == 1
        assert trades[0]["entry_price"] == float(ohlcv_20["open"].iloc[t + 1])
        assert trades[0]["exit_price"] == float(ohlcv_20["close"].iloc[t + 1])


# ---------------------------------------------------------------------------
# Input validation errors
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Invalid inputs must raise errors."""

    def test_signals_with_invalid_values_raises(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.array([0, 1, 2, 0, 1] + [0] * 15, dtype=np.int64)
        with pytest.raises(ValueError, match="0 or 1"):
            execute_trades(signals, ohlcv_20, HORIZON, "standard")

    def test_signals_with_float_invalid_values_raises(
        self, ohlcv_20: pd.DataFrame
    ) -> None:
        signals = np.array([0.0, 0.5, 1.0] + [0.0] * 17)
        with pytest.raises(ValueError, match="0 or 1"):
            execute_trades(signals, ohlcv_20, HORIZON, "standard")

    def test_signals_length_mismatch_raises(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(5, dtype=np.int64)
        with pytest.raises(ValueError, match="length"):
            execute_trades(signals, ohlcv_20, HORIZON, "standard")

    def test_ohlcv_missing_open_column_raises(self, ohlcv_20: pd.DataFrame) -> None:
        df = ohlcv_20.drop(columns=["open"])
        signals = np.zeros(len(df), dtype=np.int64)
        with pytest.raises(ValueError, match="open"):
            execute_trades(signals, df, HORIZON, "standard")

    def test_ohlcv_missing_close_column_raises(self, ohlcv_20: pd.DataFrame) -> None:
        df = ohlcv_20.drop(columns=["close"])
        signals = np.zeros(len(df), dtype=np.int64)
        with pytest.raises(ValueError, match="close"):
            execute_trades(signals, df, HORIZON, "standard")

    def test_invalid_execution_mode_raises(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        with pytest.raises(ValueError, match="execution_mode"):
            execute_trades(signals, ohlcv_20, HORIZON, "invalid_mode")

    def test_horizon_zero_raises(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        with pytest.raises(ValueError, match="horizon"):
            execute_trades(signals, ohlcv_20, 0, "standard")

    def test_horizon_negative_raises(self, ohlcv_20: pd.DataFrame) -> None:
        signals = np.zeros(len(ohlcv_20), dtype=np.int64)
        with pytest.raises(ValueError, match="horizon"):
            execute_trades(signals, ohlcv_20, -1, "standard")

    def test_empty_ohlcv_raises(self) -> None:
        ohlcv = pd.DataFrame({"open": [], "close": []}, index=pd.DatetimeIndex([]))
        signals = np.array([], dtype=np.int64)
        with pytest.raises(ValueError, match="ohlcv must not be empty"):
            execute_trades(signals, ohlcv, HORIZON, "standard")
