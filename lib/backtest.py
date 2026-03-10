"""Cost model, trade execution engine, equity curve, and trade journal."""

from __future__ import annotations

import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# COST MODEL
# ═══════════════════════════════════════════════════════════════════════════

def validate_cost_rates(
    fee_rate_per_side: float,
    slippage_rate_per_side: float,
) -> None:
    if not math.isfinite(fee_rate_per_side):
        raise ValueError(f"fee_rate_per_side must be finite, got {fee_rate_per_side}")
    if fee_rate_per_side < 0 or fee_rate_per_side >= 1:
        raise ValueError(f"fee_rate_per_side must be in [0, 1), got {fee_rate_per_side}")
    if not math.isfinite(slippage_rate_per_side):
        raise ValueError(f"slippage_rate_per_side must be finite, got {slippage_rate_per_side}")
    if slippage_rate_per_side < 0 or slippage_rate_per_side >= 1:
        raise ValueError(f"slippage_rate_per_side must be in [0, 1), got {slippage_rate_per_side}")


def apply_cost_model(
    trades: list[dict],
    fee_rate_per_side: float,
    slippage_rate_per_side: float,
) -> list[dict]:
    validate_cost_rates(fee_rate_per_side, slippage_rate_per_side)
    fee_factor_sq = (1 - fee_rate_per_side) ** 2
    result: list[dict] = []
    for trade in trades:
        if "entry_price" not in trade:
            raise ValueError("trade is missing required key 'entry_price'")
        if "exit_price" not in trade:
            raise ValueError("trade is missing required key 'exit_price'")
        p_entry = trade["entry_price"]
        p_exit = trade["exit_price"]
        if p_entry <= 0:
            raise ValueError(f"entry_price must be > 0, got {p_entry}")
        p_entry_eff = p_entry * (1 + slippage_rate_per_side)
        p_exit_eff = p_exit * (1 - slippage_rate_per_side)
        m_net = fee_factor_sq * (p_exit_eff / p_entry_eff)
        r_net = m_net - 1
        enriched = {
            **trade,
            "entry_price_eff": p_entry_eff,
            "exit_price_eff": p_exit_eff,
            "m_net": m_net,
            "r_net": r_net,
        }
        result.append(enriched)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# TRADE EXECUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════

_VALID_ENGINE_EXECUTION_MODES = frozenset({"standard", "single_trade"})
_REQUIRED_TRADE_KEYS_ENGINE = frozenset({"entry_time", "exit_time", "r_net"})


def execute_trades(
    signals: np.ndarray,
    ohlcv: pd.DataFrame,
    horizon: int,
    execution_mode: str,
) -> list[dict]:
    _validate_trade_inputs(signals, ohlcv, horizon, execution_mode)
    if execution_mode == "single_trade":
        return _execute_single_trade(ohlcv)
    return _execute_standard(signals, ohlcv, horizon)


def _validate_trade_inputs(
    signals: np.ndarray,
    ohlcv: pd.DataFrame,
    horizon: int,
    execution_mode: str,
) -> None:
    if execution_mode not in _VALID_ENGINE_EXECUTION_MODES:
        raise ValueError(
            f"execution_mode must be one of {sorted(_VALID_ENGINE_EXECUTION_MODES)}, "
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


def build_equity_curve(
    trades: list[dict],
    ohlcv: pd.DataFrame,
    initial_equity: float,
    position_fraction: float,
) -> pd.DataFrame:
    if len(ohlcv) == 0:
        raise ValueError("ohlcv must not be empty")
    if initial_equity <= 0:
        raise ValueError(f"initial_equity must be > 0, got {initial_equity}")
    if position_fraction <= 0 or position_fraction > 1:
        raise ValueError(f"position_fraction must be in (0, 1], got {position_fraction}")

    n = len(ohlcv)
    timestamps = ohlcv.index
    ts_to_idx: dict[pd.Timestamp, int] = {ts: i for i, ts in enumerate(timestamps)}

    trade_ranges: list[tuple[int, int, float]] = []
    exit_events: dict[int, float] = {}
    for i, trade in enumerate(trades):
        for key in _REQUIRED_TRADE_KEYS_ENGINE:
            if key not in trade:
                raise ValueError(f"trade[{i}] is missing required key '{key}'")
        entry_time = trade["entry_time"]
        exit_time = trade["exit_time"]
        if entry_time not in ts_to_idx:
            raise ValueError(f"entry_time {entry_time} not found in ohlcv index")
        if exit_time not in ts_to_idx:
            raise ValueError(f"exit_time {exit_time} not found in ohlcv index")
        entry_pos = ts_to_idx[entry_time]
        exit_pos = ts_to_idx[exit_time]
        if exit_pos < entry_pos:
            raise ValueError(f"trade[{i}]: exit_pos ({exit_pos}) < entry_pos ({entry_pos})")
        if exit_pos in exit_events:
            raise ValueError(
                f"trade[{i}]: duplicate exit at position {exit_pos}"
            )
        exit_events[exit_pos] = trade["r_net"]
        trade_ranges.append((entry_pos, exit_pos, trade["r_net"]))

    equity = np.full(n, np.nan, dtype=np.float64)
    in_trade = np.zeros(n, dtype=bool)
    current_equity = float(initial_equity)
    equity[0] = current_equity
    for entry_pos, exit_pos, _r_net in trade_ranges:
        in_trade[entry_pos: exit_pos + 1] = True
    for t in range(n):
        equity[t] = current_equity
        if t in exit_events:
            r_net = exit_events[t]
            current_equity = current_equity * (1 + position_fraction * r_net)
            equity[t] = current_equity
    return pd.DataFrame(
        {"time_utc": timestamps, "equity": equity, "in_trade": in_trade}
    )


# ═══════════════════════════════════════════════════════════════════════════
# TRADE JOURNAL
# ═══════════════════════════════════════════════════════════════════════════

_REQUIRED_JOURNAL_TRADE_KEYS = frozenset(
    {
        "entry_time", "exit_time", "entry_price", "exit_price",
        "entry_price_eff", "exit_price_eff", "r_net", "y_true", "y_hat",
    }
)

_COLUMN_ORDER = [
    "entry_time_utc", "exit_time_utc", "entry_price", "exit_price",
    "entry_price_eff", "exit_price_eff", "f", "s", "fees_paid",
    "slippage_paid", "y_true", "y_hat", "gross_return", "net_return",
]


def export_trade_journal(
    trades: list[dict],
    path: Path,
    fee_rate_per_side: float,
    slippage_rate_per_side: float,
) -> pd.DataFrame:
    validate_cost_rates(fee_rate_per_side, slippage_rate_per_side)
    rows: list[dict] = []
    for i, trade in enumerate(trades):
        for key in _REQUIRED_JOURNAL_TRADE_KEYS:
            if key not in trade:
                raise ValueError(f"trade[{i}] is missing required key '{key}'")
        if trade["entry_price"] <= 0:
            raise ValueError(f"trade[{i}]: entry_price must be > 0")
        entry_price = trade["entry_price"]
        exit_price = trade["exit_price"]
        gross_return = (exit_price / entry_price) - 1.0
        rows.append(
            {
                "entry_time_utc": trade["entry_time"],
                "exit_time_utc": trade["exit_time"],
                "entry_price": entry_price,
                "exit_price": exit_price,
                "entry_price_eff": trade["entry_price_eff"],
                "exit_price_eff": trade["exit_price_eff"],
                "f": fee_rate_per_side,
                "s": slippage_rate_per_side,
                "fees_paid": fee_rate_per_side * (entry_price + exit_price),
                "slippage_paid": slippage_rate_per_side * (entry_price + exit_price),
                "y_true": trade["y_true"],
                "y_hat": trade["y_hat"],
                "gross_return": gross_return,
                "net_return": trade["r_net"],
            }
        )
    df = pd.DataFrame(rows, columns=_COLUMN_ORDER)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df
