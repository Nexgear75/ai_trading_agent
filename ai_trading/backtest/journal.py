"""Trade journal CSV export — §12.6.

Builds a DataFrame with the normative columns from enriched trade dicts
(output of :func:`~ai_trading.backtest.costs.apply_cost_model`) and
writes it to CSV.

Task #035 — WS-8.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

_REQUIRED_TRADE_KEYS = frozenset(
    {
        "entry_time",
        "exit_time",
        "entry_price",
        "exit_price",
        "entry_price_eff",
        "exit_price_eff",
        "r_net",
        "y_true",
        "y_hat",
    }
)

_COLUMN_ORDER = [
    "entry_time_utc",
    "exit_time_utc",
    "entry_price",
    "exit_price",
    "entry_price_eff",
    "exit_price_eff",
    "f",
    "s",
    "fees_paid",
    "slippage_paid",
    "y_true",
    "y_hat",
    "gross_return",
    "net_return",
]


def export_trade_journal(
    trades: list[dict],
    path: Path,
    fee_rate_per_side: float,
    slippage_rate_per_side: float,
) -> pd.DataFrame:
    """Build the trade journal DataFrame and write it to CSV.

    Parameters
    ----------
    trades:
        Enriched trade dicts (from :func:`apply_cost_model`), each must
        contain the keys listed in ``_REQUIRED_TRADE_KEYS`` plus ``y_true``
        and ``y_hat`` set by the caller.
    path:
        Destination CSV file path.
    fee_rate_per_side:
        Fee rate per side ``f`` (from ``costs.fee_rate_per_side``).
    slippage_rate_per_side:
        Slippage rate per side ``s`` (from ``costs.slippage_rate_per_side``).

    Returns
    -------
    pd.DataFrame
        Journal with columns in the order specified by §12.6.
    """
    _validate_rates(fee_rate_per_side, slippage_rate_per_side)

    rows: list[dict] = []
    for i, trade in enumerate(trades):
        _validate_trade(trade, i)

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
    df.to_csv(path, index=False)
    return df


def _validate_rates(
    fee_rate_per_side: float,
    slippage_rate_per_side: float,
) -> None:
    if not math.isfinite(fee_rate_per_side):
        raise ValueError(
            f"fee_rate_per_side must be finite, got {fee_rate_per_side}"
        )
    if fee_rate_per_side < 0 or fee_rate_per_side >= 1:
        raise ValueError(
            f"fee_rate_per_side must be in [0, 1), got {fee_rate_per_side}"
        )
    if not math.isfinite(slippage_rate_per_side):
        raise ValueError(
            f"slippage_rate_per_side must be finite, got {slippage_rate_per_side}"
        )
    if slippage_rate_per_side < 0 or slippage_rate_per_side >= 1:
        raise ValueError(
            f"slippage_rate_per_side must be in [0, 1), got {slippage_rate_per_side}"
        )


def _validate_trade(trade: dict, index: int) -> None:
    for key in _REQUIRED_TRADE_KEYS:
        if key not in trade:
            raise ValueError(
                f"trade[{index}] is missing required key '{key}'"
            )
    if trade["entry_price"] <= 0:
        raise ValueError(
            f"trade[{index}]: entry_price must be > 0, got {trade['entry_price']}"
        )
