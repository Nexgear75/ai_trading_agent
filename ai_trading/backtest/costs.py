"""Transaction cost model — per-side multiplicative.

Applies fee and slippage costs to trades produced by :func:`execute_trades`,
following the formulas in spec §12.3.

Task #027 — WS-8.
"""

from __future__ import annotations


def apply_cost_model(
    trades: list[dict],
    fee_rate_per_side: float,
    slippage_rate_per_side: float,
) -> list[dict]:
    """Enrich trades with effective prices and net return.

    Parameters
    ----------
    trades:
        List of trade dicts (from :func:`execute_trades`), each must
        contain at least ``entry_price`` and ``exit_price``.
    fee_rate_per_side:
        Fee rate applied on each side of the trade (>= 0).
    slippage_rate_per_side:
        Slippage rate applied on each side of the trade (>= 0).

    Returns
    -------
    list[dict]
        New list of dicts: original keys + ``entry_price_eff``,
        ``exit_price_eff``, ``m_net``, ``r_net``.

    Raises
    ------
    ValueError
        If parameters are negative, required keys are missing, or
        ``entry_price <= 0``.
    """
    if fee_rate_per_side < 0:
        raise ValueError(
            f"fee_rate_per_side must be >= 0, got {fee_rate_per_side}"
        )
    if slippage_rate_per_side < 0:
        raise ValueError(
            f"slippage_rate_per_side must be >= 0, got {slippage_rate_per_side}"
        )

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
            raise ValueError(
                f"entry_price must be > 0, got {p_entry}"
            )

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
