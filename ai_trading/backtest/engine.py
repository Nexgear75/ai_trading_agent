"""Trade execution engine — signals to trades.

Transforms a vector of Go/No-Go signals into a list of trades
following the rules defined in spec §12.1, §12.5 and Annexe E.2.3.

Modes:
- ``standard``: Go at *t* → long entry at ``Open[t+1]``, exit at ``Close[t+H]``.
  ``one_at_a_time``: overlapping signals are ignored.
- ``single_trade``: one trade covering the entire period (Buy & Hold).
  Entry at ``Open[first_timestamp]`` (no shift), exit at ``Close[last_timestamp]``.

Task #026 — WS-8.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

_VALID_EXECUTION_MODES = frozenset({"standard", "single_trade"})


def execute_trades(
    signals: np.ndarray,
    ohlcv: pd.DataFrame,
    horizon: int,
    execution_mode: str,
) -> list[dict]:
    """Execute trades from a signal vector and OHLCV prices.

    Parameters
    ----------
    signals:
        1-D array of 0/1 values (length must match *ohlcv*).
    ohlcv:
        DataFrame with at least ``open`` and ``close`` columns and a
        :class:`~pandas.DatetimeIndex`.
    horizon:
        Number of bars for each trade (``label.horizon_H_bars``).
    execution_mode:
        ``"standard"`` or ``"single_trade"``.

    Returns
    -------
    list[dict]
        Each dict has keys: ``signal_time``, ``entry_time``, ``exit_time``,
        ``entry_price``, ``exit_price``.
    """
    _validate_inputs(signals, ohlcv, horizon, execution_mode)

    if execution_mode == "single_trade":
        return _execute_single_trade(ohlcv)
    return _execute_standard(signals, ohlcv, horizon)


def _validate_inputs(
    signals: np.ndarray,
    ohlcv: pd.DataFrame,
    horizon: int,
    execution_mode: str,
) -> None:
    if execution_mode not in _VALID_EXECUTION_MODES:
        raise ValueError(
            f"execution_mode must be one of {sorted(_VALID_EXECUTION_MODES)}, "
            f"got '{execution_mode}'"
        )
    if len(ohlcv) == 0:
        raise ValueError("ohlcv must not be empty")
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    for col in ("open", "close"):
        if col not in ohlcv.columns:
            raise ValueError(f"ohlcv must contain a '{col}' column")
    if len(signals) != len(ohlcv):
        raise ValueError(
            f"signals length ({len(signals)}) must match ohlcv length ({len(ohlcv)})"
        )
    unique_vals = np.unique(signals)
    if not np.all(np.isin(unique_vals, [0, 1])):
        raise ValueError(
            f"signals must contain only 0 or 1, got unique values {unique_vals.tolist()}"
        )


def _execute_single_trade(ohlcv: pd.DataFrame) -> list[dict]:
    return [
        {
            "signal_time": ohlcv.index[0],
            "entry_time": ohlcv.index[0],
            "exit_time": ohlcv.index[-1],
            "entry_price": float(ohlcv["open"].iloc[0]),
            "exit_price": float(ohlcv["close"].iloc[-1]),
        }
    ]


def _execute_standard(
    signals: np.ndarray,
    ohlcv: pd.DataFrame,
    horizon: int,
) -> list[dict]:
    n = len(signals)
    trades: list[dict] = []
    position_open = False
    exit_idx = -1

    for t in range(n):
        if position_open and t >= exit_idx:
            position_open = False

        if signals[t] == 1 and not position_open:
            entry_idx = t + 1
            close_idx = t + horizon

            if entry_idx >= n or close_idx >= n:
                continue

            trades.append(
                {
                    "signal_time": ohlcv.index[t],
                    "entry_time": ohlcv.index[entry_idx],
                    "exit_time": ohlcv.index[close_idx],
                    "entry_price": float(ohlcv["open"].iloc[entry_idx]),
                    "exit_price": float(ohlcv["close"].iloc[close_idx]),
                }
            )
            position_open = True
            exit_idx = close_idx

    return trades


# ---------------------------------------------------------------------------
# Equity curve (§12.4)
# ---------------------------------------------------------------------------

_REQUIRED_TRADE_KEYS = frozenset({"entry_time", "exit_time", "r_net"})


def build_equity_curve(
    trades: list[dict],
    ohlcv: pd.DataFrame,
    initial_equity: float,
    position_fraction: float,
) -> pd.DataFrame:
    """Build per-candle equity curve from enriched trades.

    Parameters
    ----------
    trades:
        Enriched trade dicts (from :func:`apply_cost_model`), each must
        contain ``entry_time``, ``exit_time``, and ``r_net``.
    ohlcv:
        OHLCV DataFrame with a :class:`~pandas.DatetimeIndex`.
    initial_equity:
        Starting equity value (``config.backtest.initial_equity``).
    position_fraction:
        Fraction of equity allocated per trade (``config.backtest.position_fraction``).

    Returns
    -------
    pd.DataFrame
        Columns: ``time_utc``, ``equity``, ``in_trade``.
    """
    if len(ohlcv) == 0:
        raise ValueError("ohlcv must not be empty")
    if initial_equity <= 0:
        raise ValueError(
            f"initial_equity must be > 0, got {initial_equity}"
        )
    if position_fraction <= 0 or position_fraction > 1:
        raise ValueError(
            f"position_fraction must be in (0, 1], got {position_fraction}"
        )

    n = len(ohlcv)
    timestamps = ohlcv.index
    # Build a fast lookup from timestamp → positional index
    ts_to_idx: dict[pd.Timestamp, int] = {ts: i for i, ts in enumerate(timestamps)}

    # Validate trades and resolve positional indices
    trade_ranges: list[tuple[int, int, float]] = []
    exit_events: dict[int, float] = {}
    for i, trade in enumerate(trades):
        for key in _REQUIRED_TRADE_KEYS:
            if key not in trade:
                raise ValueError(
                    f"trade[{i}] is missing required key '{key}'"
                )
        entry_time = trade["entry_time"]
        exit_time = trade["exit_time"]
        if entry_time not in ts_to_idx:
            raise ValueError(
                f"entry_time {entry_time} not found in ohlcv index"
            )
        if exit_time not in ts_to_idx:
            raise ValueError(
                f"exit_time {exit_time} not found in ohlcv index"
            )
        entry_pos = ts_to_idx[entry_time]
        exit_pos = ts_to_idx[exit_time]
        if exit_pos < entry_pos:
            raise ValueError(
                f"trade[{i}]: exit_pos ({exit_pos}) < entry_pos ({entry_pos})"
            )
        if exit_pos in exit_events:
            raise ValueError(
                f"trade[{i}]: duplicate exit at position {exit_pos} "
                f"(overlapping trades are not allowed)"
            )
        exit_events[exit_pos] = trade["r_net"]
        trade_ranges.append((entry_pos, exit_pos, trade["r_net"]))

    # Build equity and in_trade arrays
    equity = np.full(n, np.nan, dtype=np.float64)
    in_trade = np.zeros(n, dtype=bool)

    current_equity = float(initial_equity)
    equity[0] = current_equity

    # Mark in_trade ranges (vectorized slice assignment)
    for entry_pos, exit_pos, _r_net in trade_ranges:
        in_trade[entry_pos : exit_pos + 1] = True

    # Walk forward candle by candle
    for t in range(n):
        equity[t] = current_equity
        if t in exit_events:
            r_net = exit_events[t]
            current_equity = current_equity * (1 + position_fraction * r_net)
            equity[t] = current_equity

    return pd.DataFrame(
        {
            "time_utc": timestamps,
            "equity": equity,
            "in_trade": in_trade,
        }
    )


def save_equity_curve_csv(equity_curve: pd.DataFrame, path: Path) -> None:
    """Save equity curve DataFrame to CSV.

    Parameters
    ----------
    equity_curve:
        DataFrame with columns ``time_utc``, ``equity``, ``in_trade``.
    path:
        Destination file path.
    """
    equity_curve.to_csv(path, index=False)
