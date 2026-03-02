"""Trading metrics — unit tests.

Task #041 — WS-10.
Covers: net_pnl, net_return, max_drawdown, sharpe, profit_factor,
hit_rate, n_trades, avg_trade_return, median_trade_return,
exposure_time_frac, sharpe_per_trade, sharpe annualized,
zero-trade edge case, and the aggregate compute_trading_metrics.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_trading.metrics.trading import (
    compute_avg_trade_return,
    compute_exposure_time_frac,
    compute_hit_rate,
    compute_max_drawdown,
    compute_median_trade_return,
    compute_net_pnl,
    compute_profit_factor,
    compute_sharpe,
    compute_sharpe_per_trade,
    compute_trading_metrics,
)

# ---------------------------------------------------------------------------
# Helpers — synthetic equity curves and trades
# ---------------------------------------------------------------------------

def _make_equity_curve(
    equity_values: list[float],
    in_trade_flags: list[bool] | None = None,
) -> pd.DataFrame:
    """Build a minimal equity curve DataFrame."""
    n = len(equity_values)
    times = pd.date_range("2025-01-01", periods=n, freq="h", tz="UTC")
    if in_trade_flags is None:
        in_trade_flags = [False] * n
    return pd.DataFrame({
        "time_utc": times,
        "equity": np.array(equity_values, dtype=np.float64),
        "in_trade": in_trade_flags,
    })


def _make_trades(r_nets: list[float]) -> list[dict]:
    """Build minimal trade dicts with only r_net (sufficient for metrics)."""
    return [{"r_net": float(r)} for r in r_nets]


# ===================================================================
# net_pnl and net_return
# ===================================================================

class TestNetPnl:
    """#041 — net_pnl = E_T - 1 (with E_0 = 1.0 normalisation)."""

    def test_flat_equity(self):
        """No change => net_pnl = 0."""
        ec = _make_equity_curve([1.0, 1.0, 1.0])
        assert compute_net_pnl(ec) == pytest.approx(0.0)

    def test_gain(self):
        """E goes from 1.0 to 1.05 => net_pnl = 0.05."""
        ec = _make_equity_curve([1.0, 1.02, 1.05])
        assert compute_net_pnl(ec) == pytest.approx(0.05)

    def test_loss(self):
        """E goes from 1.0 to 0.95 => net_pnl = -0.05."""
        ec = _make_equity_curve([1.0, 0.98, 0.95])
        assert compute_net_pnl(ec) == pytest.approx(-0.05)

    def test_non_unit_initial_equity(self):
        """E_0 = 100 → normalised E_T/E_0 - 1."""
        ec = _make_equity_curve([100.0, 102.0, 110.0])
        # net_pnl = 110/100 - 1 = 0.10
        assert compute_net_pnl(ec) == pytest.approx(0.10)

    def test_single_candle(self):
        """Edge: 1 candle → net_pnl = 0."""
        ec = _make_equity_curve([1.0])
        assert compute_net_pnl(ec) == pytest.approx(0.0)


# ===================================================================
# max_drawdown
# ===================================================================

class TestMaxDrawdown:
    """#041 — max_drawdown = max_t((peak_t - E_t) / peak_t), MDD ∈ [0, 1]."""

    def test_no_drawdown(self):
        """Monotonically increasing => MDD = 0."""
        ec = _make_equity_curve([1.0, 1.1, 1.2, 1.3])
        assert compute_max_drawdown(ec) == pytest.approx(0.0)

    def test_known_drawdown(self):
        """Peak 1.2, trough 0.9 => MDD = (1.2 - 0.9) / 1.2 = 0.25."""
        ec = _make_equity_curve([1.0, 1.2, 0.9, 1.1])
        assert compute_max_drawdown(ec) == pytest.approx(0.25)

    def test_total_drawdown(self):
        """Equity drops to near zero from 1.0 => MDD ≈ 1.0."""
        ec = _make_equity_curve([1.0, 0.5, 0.001])
        mdd = compute_max_drawdown(ec)
        assert 0.0 <= mdd <= 1.0
        assert mdd == pytest.approx(0.999)

    def test_multiple_drawdowns(self):
        """Multiple dips — MDD is the largest."""
        ec = _make_equity_curve([1.0, 1.2, 1.0, 1.5, 1.2])
        # First dd: (1.2 - 1.0)/1.2 = 0.1667
        # Second dd: (1.5 - 1.2)/1.5 = 0.2
        assert compute_max_drawdown(ec) == pytest.approx(0.2)

    def test_flat_equity(self):
        """Flat equity => MDD = 0."""
        ec = _make_equity_curve([1.0, 1.0, 1.0])
        assert compute_max_drawdown(ec) == pytest.approx(0.0)

    def test_single_candle(self):
        """Single candle => MDD = 0."""
        ec = _make_equity_curve([1.0])
        assert compute_max_drawdown(ec) == pytest.approx(0.0)


# ===================================================================
# sharpe
# ===================================================================

class TestSharpe:
    """#041 — sharpe = mean(r_t) / (std(r_t) + ε).

    r_t = E_t / E_{t-1} - 1 on full test grid (including r_t=0 out of trade).
    """

    def test_flat_equity(self):
        """All returns = 0 → sharpe = 0 / (0 + ε) = 0."""
        ec = _make_equity_curve([1.0, 1.0, 1.0, 1.0])
        result = compute_sharpe(ec, sharpe_epsilon=1e-12, sharpe_annualized=False,
                                timeframe_hours=1.0)
        assert result == pytest.approx(0.0)

    def test_constant_positive_returns(self):
        """Returns all equal => std ≈ 0 → sharpe = mean / ε  (very large)."""
        # E = [1.0, 1.01, 1.0201, 1.030301]  (1% each bar)
        equity = [1.0]
        for _ in range(5):
            equity.append(equity[-1] * 1.01)
        ec = _make_equity_curve(equity)
        result = compute_sharpe(ec, sharpe_epsilon=1e-12, sharpe_annualized=False,
                                timeframe_hours=1.0)
        assert result > 0

    def test_negative_sharpe(self):
        """Declining equity => negative sharpe."""
        equity = [1.0]
        for _ in range(5):
            equity.append(equity[-1] * 0.99)
        ec = _make_equity_curve(equity)
        result = compute_sharpe(ec, sharpe_epsilon=1e-12, sharpe_annualized=False,
                                timeframe_hours=1.0)
        assert result < 0

    def test_includes_zero_returns(self):
        """Grid has bars with no change — sharpe computed over full grid."""
        # 4 bars: E = [1.0, 1.0, 1.0, 1.1]
        # returns = [0.0, 0.0, 0.1]
        ec = _make_equity_curve([1.0, 1.0, 1.0, 1.1])
        result = compute_sharpe(ec, sharpe_epsilon=1e-12, sharpe_annualized=False,
                                timeframe_hours=1.0)
        assert result > 0

    def test_annualized(self):
        """sharpe_annualized=True multiplies by sqrt(K)."""
        equity = [1.0]
        for _ in range(10):
            equity.append(equity[-1] * 1.01)
        ec = _make_equity_curve(equity)
        base = compute_sharpe(ec, sharpe_epsilon=1e-12, sharpe_annualized=False,
                              timeframe_hours=1.0)
        annualized = compute_sharpe(ec, sharpe_epsilon=1e-12, sharpe_annualized=True,
                                    timeframe_hours=1.0)
        k = 365.25 * 24 / 1.0
        assert annualized == pytest.approx(base * np.sqrt(k))

    def test_single_candle_returns_none(self):
        """Only 1 candle → 0 returns → null."""
        ec = _make_equity_curve([1.0])
        result = compute_sharpe(ec, sharpe_epsilon=1e-12, sharpe_annualized=False,
                                timeframe_hours=1.0)
        assert result is None


# ===================================================================
# profit_factor (Annexe E.2.5)
# ===================================================================

class TestProfitFactor:
    """#041 — profit_factor: sum(gains) / |sum(losses)|, per Annexe E.2.5."""

    def test_normal_case(self):
        """Mixed wins and losses."""
        trades = _make_trades([0.05, -0.02, 0.03, -0.01])
        # gains = 0.05 + 0.03 = 0.08
        # losses = -0.02 + -0.01 = -0.03
        # PF = 0.08 / 0.03 = 2.6667
        pf = compute_profit_factor(trades)
        assert pf == pytest.approx(0.08 / 0.03)

    def test_zero_trades_returns_none(self):
        """0 trades → null."""
        assert compute_profit_factor([]) is None

    def test_only_winners_returns_none(self):
        """Only winners → null (spec E.2.5)."""
        trades = _make_trades([0.05, 0.03])
        assert compute_profit_factor(trades) is None

    def test_only_losers_returns_zero(self):
        """Only losers → 0.0."""
        trades = _make_trades([-0.05, -0.03])
        pf = compute_profit_factor(trades)
        assert pf == pytest.approx(0.0)

    def test_single_winning_trade_returns_none(self):
        """Single winning trade → only winners → null."""
        assert compute_profit_factor(_make_trades([0.05])) is None

    def test_single_losing_trade_returns_zero(self):
        """Single losing trade → only losers → 0.0."""
        assert compute_profit_factor(_make_trades([-0.03])) == pytest.approx(0.0)

    def test_zero_return_trade_excluded_from_both(self):
        """A trade with r_net=0 is neither a winner nor a loser."""
        # Only a zero-return trade → no gains, no losses → null
        assert compute_profit_factor(_make_trades([0.0])) is None


# ===================================================================
# hit_rate
# ===================================================================

class TestHitRate:
    """#041 — hit_rate = n_winning / n_trades."""

    def test_all_winners(self):
        trades = _make_trades([0.05, 0.03, 0.01])
        assert compute_hit_rate(trades) == pytest.approx(1.0)

    def test_all_losers(self):
        trades = _make_trades([-0.05, -0.03])
        assert compute_hit_rate(trades) == pytest.approx(0.0)

    def test_mixed(self):
        trades = _make_trades([0.05, -0.02, 0.03, -0.01])
        # 2 winners / 4 trades = 0.5
        assert compute_hit_rate(trades) == pytest.approx(0.5)

    def test_zero_trades_returns_none(self):
        assert compute_hit_rate([]) is None

    def test_zero_return_not_a_winner(self):
        """r_net = 0 is NOT a winning trade."""
        trades = _make_trades([0.0, 0.05])
        # 1 winner / 2 trades = 0.5
        assert compute_hit_rate(trades) == pytest.approx(0.5)


# ===================================================================
# avg_trade_return and median_trade_return
# ===================================================================

class TestAvgTradeReturn:
    """#041 — avg_trade_return = mean(r_net)."""

    def test_nominal(self):
        trades = _make_trades([0.10, -0.02, 0.04])
        expected = (0.10 + -0.02 + 0.04) / 3
        assert compute_avg_trade_return(trades) == pytest.approx(expected)

    def test_zero_trades_returns_none(self):
        assert compute_avg_trade_return([]) is None


class TestMedianTradeReturn:
    """#041 — median_trade_return = median(r_net)."""

    def test_odd_count(self):
        trades = _make_trades([0.01, 0.05, 0.03])
        assert compute_median_trade_return(trades) == pytest.approx(0.03)

    def test_even_count(self):
        trades = _make_trades([0.01, 0.02, 0.06, 0.08])
        assert compute_median_trade_return(trades) == pytest.approx(0.04)

    def test_zero_trades_returns_none(self):
        assert compute_median_trade_return([]) is None


# ===================================================================
# exposure_time_frac
# ===================================================================

class TestExposureTimeFrac:
    """#041 — exposure_time_frac = n_candles_in_trade / n_candles_total."""

    def test_no_exposure(self):
        ec = _make_equity_curve([1.0, 1.0, 1.0], in_trade_flags=[False, False, False])
        assert compute_exposure_time_frac(ec) == pytest.approx(0.0)

    def test_full_exposure(self):
        ec = _make_equity_curve([1.0, 1.05, 1.1], in_trade_flags=[True, True, True])
        assert compute_exposure_time_frac(ec) == pytest.approx(1.0)

    def test_partial_exposure(self):
        ec = _make_equity_curve(
            [1.0, 1.0, 1.05, 1.1, 1.0],
            in_trade_flags=[False, True, True, True, False],
        )
        # 3 in trade / 5 total = 0.6
        assert compute_exposure_time_frac(ec) == pytest.approx(0.6)


# ===================================================================
# sharpe_per_trade
# ===================================================================

class TestSharpePerTrade:
    """#041 — sharpe_per_trade = mean(r_net) / (std(r_net) + ε)."""

    def test_nominal(self):
        trades = _make_trades([0.05, -0.02, 0.03, -0.01])
        r = np.array([0.05, -0.02, 0.03, -0.01], dtype=np.float64)
        expected = float(np.mean(r)) / (float(np.std(r, ddof=0)) + 1e-12)
        result = compute_sharpe_per_trade(trades, sharpe_epsilon=1e-12)
        assert result == pytest.approx(expected)

    def test_zero_trades_returns_none(self):
        assert compute_sharpe_per_trade([], sharpe_epsilon=1e-12) is None

    def test_single_trade(self):
        """Single trade → std = 0 → result = r_net / ε."""
        trades = _make_trades([0.05])
        result = compute_sharpe_per_trade(trades, sharpe_epsilon=1e-12)
        assert result == pytest.approx(0.05 / 1e-12)


# ===================================================================
# Zero trades — all metrics
# ===================================================================

class TestZeroTrades:
    """#041 — n_trades == 0: all metrics conform to spec."""

    def test_zero_trades_aggregate(self):
        """compute_trading_metrics with 0 trades returns spec values."""
        ec = _make_equity_curve([1.0, 1.0, 1.0, 1.0])
        result = compute_trading_metrics(
            equity_curve=ec,
            trades=[],
            sharpe_epsilon=1e-12,
            sharpe_annualized=False,
            timeframe_hours=1.0,
        )
        assert result["net_pnl"] == pytest.approx(0.0)
        assert result["net_return"] == pytest.approx(0.0)
        assert result["max_drawdown"] == pytest.approx(0.0)
        assert result["sharpe"] is None
        assert result["profit_factor"] is None
        assert result["hit_rate"] is None
        assert result["n_trades"] == 0
        assert result["avg_trade_return"] is None
        assert result["median_trade_return"] is None
        assert result["exposure_time_frac"] == pytest.approx(0.0)
        assert result["sharpe_per_trade"] is None


# ===================================================================
# Aggregate compute_trading_metrics
# ===================================================================

class TestComputeTradingMetrics:
    """#041 — aggregate function returns dict with all metrics."""

    def test_nominal_aggregate(self):
        """Standard scenario with mixed trades."""
        # Equity: starts at 1.0, rises to 1.2, dips to 1.1, rises to 1.3
        ec = _make_equity_curve(
            [1.0, 1.05, 1.2, 1.1, 1.15, 1.3],
            in_trade_flags=[False, True, True, False, True, True],
        )
        trades = _make_trades([0.05, -0.02, 0.08])
        result = compute_trading_metrics(
            equity_curve=ec,
            trades=trades,
            sharpe_epsilon=1e-12,
            sharpe_annualized=False,
            timeframe_hours=1.0,
        )
        # Verify all required keys present
        required_keys = {
            "net_pnl", "net_return", "max_drawdown", "sharpe",
            "profit_factor", "hit_rate", "n_trades",
            "avg_trade_return", "median_trade_return",
            "exposure_time_frac", "sharpe_per_trade",
        }
        assert required_keys <= set(result.keys())

        # net_pnl = E_T / E_0 - 1 = 1.3 / 1.0 - 1 = 0.3
        assert result["net_pnl"] == pytest.approx(0.3)
        assert result["net_return"] == pytest.approx(0.3)

        # n_trades = 3
        assert result["n_trades"] == 3

        # hit_rate = 2 winners / 3 = 0.6667
        assert result["hit_rate"] == pytest.approx(2 / 3)

        # avg = (0.05 + -0.02 + 0.08) / 3
        assert result["avg_trade_return"] == pytest.approx((0.05 - 0.02 + 0.08) / 3)

        # exposure: 4 candles in trade / 6 total
        assert result["exposure_time_frac"] == pytest.approx(4 / 6)

        # max_drawdown from peak 1.2 to 1.1 => (1.2-1.1)/1.2
        assert result["max_drawdown"] == pytest.approx((1.2 - 1.1) / 1.2, abs=1e-10)

    def test_annualized_sharpe_in_aggregate(self):
        """sharpe_annualized=True applies sqrt(K) factor."""
        equity = [1.0]
        for _ in range(10):
            equity.append(equity[-1] * 1.01)
        ec = _make_equity_curve(equity)
        result_base = compute_trading_metrics(
            equity_curve=ec,
            trades=_make_trades([0.05]),
            sharpe_epsilon=1e-12,
            sharpe_annualized=False,
            timeframe_hours=1.0,
        )
        result_ann = compute_trading_metrics(
            equity_curve=ec,
            trades=_make_trades([0.05]),
            sharpe_epsilon=1e-12,
            sharpe_annualized=True,
            timeframe_hours=1.0,
        )
        k = 365.25 * 24 / 1.0
        assert result_ann["sharpe"] == pytest.approx(
            result_base["sharpe"] * np.sqrt(k)
        )


# ===================================================================
# Float64 convention
# ===================================================================

class TestFloat64Convention:
    """#041 — All metrics must be float64 (or None/int for n_trades)."""

    def test_all_float64(self):
        ec = _make_equity_curve(
            [1.0, 1.05, 1.1],
            in_trade_flags=[False, True, True],
        )
        trades = _make_trades([0.05])
        result = compute_trading_metrics(
            equity_curve=ec,
            trades=trades,
            sharpe_epsilon=1e-12,
            sharpe_annualized=False,
            timeframe_hours=1.0,
        )
        for key, val in result.items():
            if key == "n_trades":
                assert isinstance(val, int), f"{key} should be int"
            elif val is not None:
                assert isinstance(val, float), f"{key} should be float, got {type(val)}"
                # Check float64 precision (not float32)
                assert np.finfo(np.float64).eps < 1e-15


# ===================================================================
# Validation — invalid inputs
# ===================================================================

class TestValidation:
    """#041 — strict validation, no fallbacks."""

    def test_empty_equity_curve_raises(self):
        ec = _make_equity_curve([])
        with pytest.raises(ValueError, match="equity_curve"):
            compute_net_pnl(ec)

    def test_missing_equity_column_raises(self):
        df = pd.DataFrame({"time_utc": [1, 2], "wrong": [1.0, 1.1]})
        with pytest.raises(ValueError, match="equity"):
            compute_net_pnl(df)

    def test_missing_in_trade_column_raises(self):
        df = pd.DataFrame({
            "time_utc": [1, 2],
            "equity": [1.0, 1.1],
        })
        with pytest.raises(ValueError, match="in_trade"):
            compute_exposure_time_frac(df)

    def test_trade_missing_r_net_raises(self):
        trades = [{"some_key": 42}]
        with pytest.raises(ValueError, match="r_net"):
            compute_hit_rate(trades)

    def test_non_finite_epsilon_raises(self):
        ec = _make_equity_curve([1.0, 1.1])
        with pytest.raises(ValueError, match="sharpe_epsilon"):
            compute_sharpe(ec, sharpe_epsilon=float("nan"),
                           sharpe_annualized=False, timeframe_hours=1.0)

    def test_zero_epsilon_raises(self):
        ec = _make_equity_curve([1.0, 1.1])
        with pytest.raises(ValueError, match="sharpe_epsilon"):
            compute_sharpe(ec, sharpe_epsilon=0.0,
                           sharpe_annualized=False, timeframe_hours=1.0)

    def test_negative_epsilon_raises(self):
        ec = _make_equity_curve([1.0, 1.1])
        with pytest.raises(ValueError, match="sharpe_epsilon"):
            compute_sharpe(ec, sharpe_epsilon=-1e-12,
                           sharpe_annualized=False, timeframe_hours=1.0)

    def test_non_positive_timeframe_hours_raises(self):
        ec = _make_equity_curve([1.0, 1.1])
        with pytest.raises(ValueError, match="timeframe_hours"):
            compute_sharpe(ec, sharpe_epsilon=1e-12,
                           sharpe_annualized=True, timeframe_hours=0.0)
