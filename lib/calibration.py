"""Threshold calibration for trading signal generation."""

from __future__ import annotations

import logging
import math

import numpy as np
import pandas as pd

from lib.backtest import apply_cost_model, build_equity_curve, execute_trades
from lib.features import VALID_OUTPUT_TYPES

logger = logging.getLogger(__name__)

_VALID_OBJECTIVES = frozenset({"max_net_pnl_with_mdd_cap"})


def compute_quantile_thresholds(
    y_hat_val: np.ndarray,
    q_grid: list[float],
) -> dict[float, float]:
    if y_hat_val.ndim != 1:
        raise ValueError(f"y_hat_val must be 1D, got shape {y_hat_val.shape}")
    if y_hat_val.size == 0:
        raise ValueError("y_hat_val must not be empty")
    if len(q_grid) == 0:
        raise ValueError("q_grid must not be empty")
    if len(q_grid) != len(set(q_grid)):
        raise ValueError("q_grid must not contain duplicates")
    for q in q_grid:
        if not math.isfinite(q):
            raise ValueError(f"q_grid values must be finite, got {q}")
        if q < 0.0 or q > 1.0:
            raise ValueError(f"q_grid values must be in [0, 1], got {q}")
    thresholds = np.quantile(y_hat_val, q_grid)
    return dict(zip(q_grid, thresholds.tolist(), strict=True))


def apply_threshold(
    y_hat: np.ndarray,
    theta: float,
) -> np.ndarray:
    if y_hat.ndim != 1:
        raise ValueError(f"y_hat must be 1D, got shape {y_hat.shape}")
    return (y_hat > theta).astype(np.int32)


def compute_max_drawdown_array(equity: np.ndarray) -> float:
    if equity.ndim != 1:
        raise ValueError(f"equity must be 1D, got shape {equity.shape}")
    if equity.size == 0:
        raise ValueError("equity must not be empty")
    running_max = np.maximum.accumulate(equity)
    drawdowns = np.where(running_max > 0, (running_max - equity) / running_max, 0.0)
    return float(np.max(drawdowns))


def calibrate_threshold(
    y_hat_val: np.ndarray,
    ohlcv_val: pd.DataFrame,
    q_grid: list[float],
    horizon: int,
    fee_rate_per_side: float,
    slippage_rate_per_side: float,
    initial_equity: float,
    position_fraction: float,
    objective: str,
    mdd_cap: float,
    min_trades: int,
    output_type: str,
) -> dict:
    if output_type not in VALID_OUTPUT_TYPES:
        raise ValueError(
            f"output_type must be one of {sorted(VALID_OUTPUT_TYPES)}, got '{output_type}'"
        )
    if output_type == "signal":
        return {
            "theta": None, "quantile": None, "method": "none",
            "net_pnl": None, "mdd": None, "n_trades": None, "details": None,
        }
    if y_hat_val.ndim != 1:
        raise ValueError(f"y_hat_val must be 1D, got shape {y_hat_val.shape}")
    if y_hat_val.size == 0:
        raise ValueError("y_hat_val must not be empty")
    if len(y_hat_val) != len(ohlcv_val):
        raise ValueError(
            f"y_hat_val length ({len(y_hat_val)}) must match ohlcv_val length ({len(ohlcv_val)})"
        )
    if len(q_grid) == 0:
        raise ValueError("q_grid must not be empty")
    if objective not in _VALID_OBJECTIVES:
        raise ValueError(f"objective must be one of {sorted(_VALID_OBJECTIVES)}, got '{objective}'")

    thresholds = compute_quantile_thresholds(y_hat_val, q_grid)
    details: list[dict] = []
    for q in q_grid:
        theta = thresholds[q]
        signals = apply_threshold(y_hat_val, theta)
        trades = execute_trades(
            signals=signals, ohlcv=ohlcv_val, horizon=horizon, execution_mode="standard",
        )
        enriched_trades = apply_cost_model(
            trades=trades,
            fee_rate_per_side=fee_rate_per_side,
            slippage_rate_per_side=slippage_rate_per_side,
        )
        if len(enriched_trades) == 0:
            net_pnl = 0.0
            mdd = 0.0
            n_trades_cal = 0
        else:
            equity_df = build_equity_curve(
                trades=enriched_trades, ohlcv=ohlcv_val,
                initial_equity=initial_equity, position_fraction=position_fraction,
            )
            equity_array = equity_df["equity"].to_numpy(dtype=np.float64)
            final_equity = float(equity_array[-1])
            net_pnl = final_equity / initial_equity - 1.0
            mdd = compute_max_drawdown_array(equity_array)
            n_trades_cal = len(enriched_trades)
        feasible = (mdd <= mdd_cap) and (n_trades_cal >= min_trades)
        details.append({
            "quantile": q, "theta": theta, "net_pnl": net_pnl,
            "mdd": mdd, "n_trades": n_trades_cal, "feasible": feasible,
        })

    feasible_candidates = [d for d in details if d["feasible"]]
    if len(feasible_candidates) > 0:
        feasible_candidates.sort(key=lambda d: (-d["net_pnl"], -d["quantile"]))
        best = feasible_candidates[0]
        return {
            "theta": best["theta"], "quantile": best["quantile"],
            "method": "quantile_grid", "net_pnl": best["net_pnl"],
            "mdd": best["mdd"], "n_trades": best["n_trades"], "details": details,
        }

    mdd_feasible = [d for d in details if d["mdd"] <= mdd_cap]
    if len(mdd_feasible) > 0:
        mdd_feasible.sort(key=lambda d: -d["quantile"])
        best = mdd_feasible[0]
        logger.warning(
            "Fallback E.2.2 step 1: relaxing min_trades. Selected θ=%.6f",
            best["theta"],
        )
        return {
            "theta": best["theta"], "quantile": best["quantile"],
            "method": "fallback_relax_min_trades", "net_pnl": best["net_pnl"],
            "mdd": best["mdd"], "n_trades": best["n_trades"], "details": details,
        }

    logger.warning("Fallback E.2.2 step 2: θ=+∞ (no-trade).")
    return {
        "theta": float("inf"), "quantile": None,
        "method": "fallback_no_trade", "net_pnl": 0.0,
        "mdd": 0.0, "n_trades": 0, "details": details,
    }
