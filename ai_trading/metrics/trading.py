"""Trading metrics — per-fold performance evaluation.

Computes all trading metrics from the equity curve and enriched trades,
as specified in §14.2 and Annexe E.2.5.

Task #041 — WS-10.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_equity_curve(ec: pd.DataFrame) -> None:
    """Validate equity curve DataFrame structure.

    Raises
    ------
    ValueError
        If required columns are missing or the DataFrame is empty.
    """
    if "equity" not in ec.columns:
        raise ValueError("equity_curve must contain an 'equity' column")
    if len(ec) == 0:
        raise ValueError("equity_curve must not be empty")


def _validate_equity_curve_with_in_trade(ec: pd.DataFrame) -> None:
    """Validate equity curve including in_trade column."""
    _validate_equity_curve(ec)
    if "in_trade" not in ec.columns:
        raise ValueError("equity_curve must contain an 'in_trade' column")


def _validate_trades_r_net(trades: list[dict]) -> None:
    """Validate that each trade dict has an 'r_net' key.

    Raises
    ------
    ValueError
        If any trade is missing 'r_net'.
    """
    for i, trade in enumerate(trades):
        if "r_net" not in trade:
            raise ValueError(f"trade[{i}] is missing required key 'r_net'")


def _validate_sharpe_epsilon(sharpe_epsilon: float) -> None:
    """Validate sharpe_epsilon is finite and > 0.

    Raises
    ------
    ValueError
        If sharpe_epsilon is non-finite, zero, or negative.
    """
    if not math.isfinite(sharpe_epsilon):
        raise ValueError(
            f"sharpe_epsilon must be finite and > 0, got {sharpe_epsilon}"
        )
    if sharpe_epsilon <= 0:
        raise ValueError(
            f"sharpe_epsilon must be > 0, got {sharpe_epsilon}"
        )


def _validate_timeframe_hours(timeframe_hours: float) -> None:
    """Validate timeframe_hours is > 0.

    Raises
    ------
    ValueError
        If timeframe_hours is not positive.
    """
    if not math.isfinite(timeframe_hours) or timeframe_hours <= 0:
        raise ValueError(
            f"timeframe_hours must be > 0, got {timeframe_hours}"
        )


# ---------------------------------------------------------------------------
# Individual metrics
# ---------------------------------------------------------------------------


def compute_net_pnl(equity_curve: pd.DataFrame) -> float:
    """Net P&L: E_T / E_0 - 1.

    Returns
    -------
    float
        Net P&L (float64). Zero if single candle.
    """
    _validate_equity_curve(equity_curve)
    equity = equity_curve["equity"].to_numpy(dtype=np.float64)
    return float(equity[-1] / equity[0] - 1.0)


def compute_max_drawdown(equity_curve: pd.DataFrame) -> float:
    """Maximum drawdown: max_t((peak_t - E_t) / peak_t).

    Returns
    -------
    float
        MDD in [0, 1] (float64).
    """
    _validate_equity_curve(equity_curve)
    equity = equity_curve["equity"].to_numpy(dtype=np.float64)
    if len(equity) <= 1:
        return 0.0
    running_peak = np.maximum.accumulate(equity)
    drawdowns = (running_peak - equity) / running_peak
    return float(np.max(drawdowns))


def compute_sharpe(
    equity_curve: pd.DataFrame,
    *,
    sharpe_epsilon: float,
    sharpe_annualized: bool,
    timeframe_hours: float,
) -> float | None:
    """Sharpe ratio: mean(r_t) / (std(r_t) + ε).

    r_t = E_t / E_{t-1} - 1 over the full test grid.

    Parameters
    ----------
    equity_curve:
        DataFrame with 'equity' column.
    sharpe_epsilon:
        Small positive value added to std to prevent division by zero.
    sharpe_annualized:
        If True, multiply by sqrt(K) where K = 365.25 * 24 / timeframe_hours.
    timeframe_hours:
        Candle interval in hours (needed only when annualizing).

    Returns
    -------
    float | None
        Sharpe ratio (float64), or None if fewer than 2 equity points.
    """
    _validate_equity_curve(equity_curve)
    _validate_sharpe_epsilon(sharpe_epsilon)
    if sharpe_annualized:
        _validate_timeframe_hours(timeframe_hours)

    equity = equity_curve["equity"].to_numpy(dtype=np.float64)
    if len(equity) < 2:
        return None

    returns = equity[1:] / equity[:-1] - 1.0
    mean_r = float(np.mean(returns))
    std_r = float(np.std(returns, ddof=0))
    sharpe = mean_r / (std_r + sharpe_epsilon)

    if sharpe_annualized:
        # 365.25 = Julian year (implementation-defined, spec §14.2 uses 365)
        k = 365.25 * 24 / timeframe_hours
        sharpe = sharpe * np.sqrt(k)

    return float(sharpe)


def compute_profit_factor(trades: list[dict]) -> float | None:
    """Profit factor: sum(gains) / |sum(losses)|.

    Per Annexe E.2.5:
    - 0 trades → None
    - Only winners (no losses) → None
    - Only losers (no gains) → 0.0

    Returns
    -------
    float | None
        Profit factor (float64), or None per spec edge cases.
    """
    if len(trades) == 0:
        return None
    _validate_trades_r_net(trades)

    r_nets = np.array([t["r_net"] for t in trades], dtype=np.float64)
    gains = r_nets[r_nets > 0]
    losses = r_nets[r_nets < 0]

    if len(gains) == 0 and len(losses) == 0:
        # All zero-return trades
        return None
    if len(losses) == 0:
        # Only winners → null
        return None
    if len(gains) == 0:
        # Only losers → 0.0
        return 0.0

    return float(np.sum(gains) / np.abs(np.sum(losses)))


def compute_hit_rate(trades: list[dict]) -> float | None:
    """Hit rate: n_winning / n_trades.

    A winning trade has r_net > 0 (strictly).

    Returns
    -------
    float | None
        Hit rate (float64), or None if 0 trades.
    """
    if len(trades) == 0:
        return None
    _validate_trades_r_net(trades)

    r_nets = np.array([t["r_net"] for t in trades], dtype=np.float64)
    n_winning = int(np.sum(r_nets > 0))
    return float(n_winning / len(trades))


def compute_avg_trade_return(trades: list[dict]) -> float | None:
    """Average trade return: mean(r_net).

    Returns
    -------
    float | None
        Mean of r_net (float64), or None if 0 trades.
    """
    if len(trades) == 0:
        return None
    _validate_trades_r_net(trades)

    r_nets = np.array([t["r_net"] for t in trades], dtype=np.float64)
    return float(np.mean(r_nets))


def compute_median_trade_return(trades: list[dict]) -> float | None:
    """Median trade return: median(r_net).

    Returns
    -------
    float | None
        Median of r_net (float64), or None if 0 trades.
    """
    if len(trades) == 0:
        return None
    _validate_trades_r_net(trades)

    r_nets = np.array([t["r_net"] for t in trades], dtype=np.float64)
    return float(np.median(r_nets))


def compute_exposure_time_frac(equity_curve: pd.DataFrame) -> float:
    """Exposure time fraction: n_candles_in_trade / n_candles_total.

    Returns
    -------
    float
        Fraction in [0, 1] (float64).
    """
    _validate_equity_curve_with_in_trade(equity_curve)
    in_trade = equity_curve["in_trade"].to_numpy(dtype=bool)
    return float(np.sum(in_trade) / len(in_trade))


def compute_sharpe_per_trade(
    trades: list[dict],
    *,
    sharpe_epsilon: float,
) -> float | None:
    """Sharpe per trade: mean(r_net) / (std(r_net) + ε).

    Computed on the r_net of executed trades only (not the full grid).

    Returns
    -------
    float | None
        Sharpe per trade (float64), or None if 0 trades.
    """
    if len(trades) == 0:
        return None
    _validate_trades_r_net(trades)
    _validate_sharpe_epsilon(sharpe_epsilon)

    r_nets = np.array([t["r_net"] for t in trades], dtype=np.float64)
    mean_r = float(np.mean(r_nets))
    std_r = float(np.std(r_nets, ddof=0))
    return float(mean_r / (std_r + sharpe_epsilon))


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------


def compute_trading_metrics(
    equity_curve: pd.DataFrame,
    trades: list[dict],
    *,
    sharpe_epsilon: float,
    sharpe_annualized: bool,
    timeframe_hours: float,
) -> dict[str, float | int | None]:
    """Compute all trading metrics for a single fold.

    Parameters
    ----------
    equity_curve:
        DataFrame with columns 'time_utc', 'equity', 'in_trade'.
    trades:
        List of enriched trade dicts with at least 'r_net'.
    sharpe_epsilon:
        Epsilon for Sharpe denominator.
    sharpe_annualized:
        Whether to annualise the Sharpe ratio.
    timeframe_hours:
        Candle interval in hours.

    Returns
    -------
    dict
        All trading metrics as a flat dict.
    """
    _validate_equity_curve_with_in_trade(equity_curve)
    _validate_sharpe_epsilon(sharpe_epsilon)

    n_trades = len(trades)

    # Spec: n_trades == 0 → specific null values for trade-dependent metrics
    if n_trades == 0:
        return {
            "net_pnl": compute_net_pnl(equity_curve),
            "net_return": compute_net_pnl(equity_curve),
            "max_drawdown": compute_max_drawdown(equity_curve),
            "sharpe": None,
            "profit_factor": None,
            "hit_rate": None,
            "n_trades": 0,
            "avg_trade_return": None,
            "median_trade_return": None,
            "exposure_time_frac": compute_exposure_time_frac(equity_curve),
            "sharpe_per_trade": None,
        }

    return {
        "net_pnl": compute_net_pnl(equity_curve),
        "net_return": compute_net_pnl(equity_curve),
        "max_drawdown": compute_max_drawdown(equity_curve),
        "sharpe": compute_sharpe(
            equity_curve,
            sharpe_epsilon=sharpe_epsilon,
            sharpe_annualized=sharpe_annualized,
            timeframe_hours=timeframe_hours,
        ),
        "profit_factor": compute_profit_factor(trades),
        "hit_rate": compute_hit_rate(trades),
        "n_trades": n_trades,
        "avg_trade_return": compute_avg_trade_return(trades),
        "median_trade_return": compute_median_trade_return(trades),
        "exposure_time_frac": compute_exposure_time_frac(equity_curve),
        "sharpe_per_trade": compute_sharpe_per_trade(
            trades, sharpe_epsilon=sharpe_epsilon
        ),
    }
