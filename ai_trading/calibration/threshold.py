"""Quantile-grid threshold calibration (§11.2, §11.3)."""

from __future__ import annotations

import logging
import math

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from ai_trading.backtest.costs import apply_cost_model
from ai_trading.backtest.engine import build_equity_curve, execute_trades
from ai_trading.models.base import VALID_OUTPUT_TYPES

logger = logging.getLogger(__name__)


def compute_quantile_thresholds(
    y_hat_val: NDArray[np.floating],
    q_grid: list[float],
) -> dict[float, float]:
    """Compute threshold θ(q) = quantile_q(y_hat_val) for each q in q_grid.

    Parameters
    ----------
    y_hat_val : 1D array of validation predictions.
    q_grid : list of quantile levels, each in [0, 1].

    Returns
    -------
    dict mapping each q to its computed threshold θ(q) as a Python float.

    Raises
    ------
    ValueError
        If y_hat_val is not 1D, is empty, q_grid is empty, or q values
        are outside [0, 1].
    """
    if y_hat_val.ndim != 1:
        raise ValueError(
            f"y_hat_val must be 1D, got shape {y_hat_val.shape}"
        )
    if y_hat_val.size == 0:
        raise ValueError("y_hat_val must not be empty")
    if len(q_grid) == 0:
        raise ValueError("q_grid must not be empty")
    if len(q_grid) != len(set(q_grid)):
        raise ValueError("q_grid must not contain duplicates")
    for q in q_grid:
        if not math.isfinite(q):
            raise ValueError(
                f"q_grid values must be finite, got {q}"
            )
        if q < 0.0 or q > 1.0:
            raise ValueError(
                f"q_grid values must be in [0, 1], got {q}"
            )

    thresholds = np.quantile(y_hat_val, q_grid)
    return dict(zip(q_grid, thresholds.tolist(), strict=True))


def apply_threshold(
    y_hat: NDArray[np.floating],
    theta: float,
) -> NDArray[np.signedinteger]:
    """Generate binary Go/No-Go signals: 1 if y_hat[t] > theta, else 0.

    Parameters
    ----------
    y_hat : 1D array of predictions.
    theta : threshold value.

    Returns
    -------
    1D int32 array of same shape as y_hat.

    Raises
    ------
    ValueError
        If y_hat is not 1D.
    """
    if y_hat.ndim != 1:
        raise ValueError(
            f"y_hat must be 1D, got shape {y_hat.shape}"
        )
    return (y_hat > theta).astype(np.int32)


_VALID_OBJECTIVES = frozenset({"max_net_pnl_with_mdd_cap"})


def compute_max_drawdown(equity: NDArray[np.floating]) -> float:
    """Compute maximum drawdown from an equity curve array.

    MDD = max_t( (peak_t - E_t) / peak_t )  (spec §14.2 glossary).

    Parameters
    ----------
    equity : 1D array of equity values.

    Returns
    -------
    float
        Max drawdown in [0, 1]. 0 means no drawdown.

    Raises
    ------
    ValueError
        If equity is not 1D or is empty.
    """
    if equity.ndim != 1:
        raise ValueError(
            f"equity must be 1D, got shape {equity.shape}"
        )
    if equity.size == 0:
        raise ValueError("equity must not be empty")

    running_max = np.maximum.accumulate(equity)
    drawdowns = np.where(
        running_max > 0,
        (running_max - equity) / running_max,
        0.0,
    )
    return float(np.max(drawdowns))



def calibrate_threshold(
    y_hat_val: NDArray[np.floating],
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
    """Calibrate threshold θ on validation data (§11.3).

    For each quantile in q_grid, compute θ, generate signals, run backtest,
    compute metrics, filter by constraints, and select the θ that maximizes
    net P&L. Tiebreaker: prefer highest quantile (most conservative).

    When ``output_type="signal"``, the model already produces binary Go/No-Go
    signals — calibration is bypassed entirely (§11.4, §11.5).

    Parameters
    ----------
    y_hat_val : 1D validation predictions.
    ohlcv_val : Validation OHLCV DataFrame with DatetimeIndex.
    q_grid : Quantile levels for threshold candidates.
    horizon : Trade horizon in bars (label.horizon_H_bars).
    fee_rate_per_side : Per-side fee rate.
    slippage_rate_per_side : Per-side slippage rate.
    initial_equity : Starting equity (backtest.initial_equity).
    position_fraction : Fraction per trade (backtest.position_fraction).
    objective : Optimization objective name.
    mdd_cap : Maximum allowed drawdown.
    min_trades : Minimum number of trades required.
    output_type : Model output type — ``"regression"`` runs full
        calibration, ``"signal"`` bypasses calibration entirely.

    Returns
    -------
    dict with keys: theta, quantile, method, net_pnl, mdd, n_trades, details.
        For ``output_type="signal"``: method="none", theta=None, quantile=None,
        details=None.
    """
    # --- Validate output_type ---
    if output_type not in VALID_OUTPUT_TYPES:
        raise ValueError(
            f"output_type must be one of {sorted(VALID_OUTPUT_TYPES)}, "
            f"got '{output_type}'"
        )

    # --- Bypass for signal models (§11.4, §11.5) ---
    if output_type == "signal":
        return {
            "theta": None,
            "quantile": None,
            "method": "none",
            "net_pnl": None,
            "mdd": None,
            "n_trades": None,
            "details": None,
        }

    # --- Input validation ---
    if y_hat_val.ndim != 1:
        raise ValueError(
            f"y_hat_val must be 1D, got shape {y_hat_val.shape}"
        )
    if y_hat_val.size == 0:
        raise ValueError("y_hat_val must not be empty")
    if len(y_hat_val) != len(ohlcv_val):
        raise ValueError(
            f"y_hat_val length ({len(y_hat_val)}) must match "
            f"ohlcv_val length ({len(ohlcv_val)})"
        )
    if len(q_grid) == 0:
        raise ValueError("q_grid must not be empty")
    if objective not in _VALID_OBJECTIVES:
        raise ValueError(
            f"objective must be one of {sorted(_VALID_OBJECTIVES)}, "
            f"got '{objective}'"
        )

    # --- Compute θ candidates from quantile grid ---
    thresholds = compute_quantile_thresholds(y_hat_val, q_grid)

    # --- Evaluate each candidate ---
    details: list[dict] = []

    for q in q_grid:
        theta = thresholds[q]
        signals = apply_threshold(y_hat_val, theta)

        # Execute trades on validation
        trades = execute_trades(
            signals=signals,
            ohlcv=ohlcv_val,
            horizon=horizon,
            execution_mode="standard",
        )

        # Apply cost model
        enriched_trades = apply_cost_model(
            trades=trades,
            fee_rate_per_side=fee_rate_per_side,
            slippage_rate_per_side=slippage_rate_per_side,
        )

        # Build equity curve (reset to initial_equity for each candidate)
        if len(enriched_trades) == 0:
            # No trades: equity stays flat
            net_pnl = 0.0
            mdd = 0.0
            n_trades = 0
        else:
            equity_df = build_equity_curve(
                trades=enriched_trades,
                ohlcv=ohlcv_val,
                initial_equity=initial_equity,
                position_fraction=position_fraction,
            )
            equity_array = equity_df["equity"].to_numpy(dtype=np.float64)
            final_equity = float(equity_array[-1])
            net_pnl = final_equity - initial_equity
            mdd = compute_max_drawdown(equity_array)
            n_trades = len(enriched_trades)

        feasible = (mdd <= mdd_cap) and (n_trades >= min_trades)

        details.append({
            "quantile": q,
            "theta": theta,
            "net_pnl": net_pnl,
            "mdd": mdd,
            "n_trades": n_trades,
            "feasible": feasible,
        })

    # --- Select best feasible θ ---
    feasible_candidates = [d for d in details if d["feasible"]]

    if len(feasible_candidates) > 0:
        # Normal path: select best P&L, tiebreaker = highest quantile
        feasible_candidates.sort(key=lambda d: (-d["net_pnl"], -d["quantile"]))
        best = feasible_candidates[0]
        return {
            "theta": best["theta"],
            "quantile": best["quantile"],
            "method": "quantile_grid",
            "net_pnl": best["net_pnl"],
            "mdd": best["mdd"],
            "n_trades": best["n_trades"],
            "details": details,
        }

    # --- Fallback E.2.2 step 1: relax min_trades to 0 ---
    mdd_feasible = [d for d in details if d["mdd"] <= mdd_cap]

    if len(mdd_feasible) > 0:
        # Pick highest quantile (most conservative) among mdd-feasible
        mdd_feasible.sort(key=lambda d: -d["quantile"])
        best = mdd_feasible[0]
        logger.warning(
            "Fallback E.2.2 step 1: no θ satisfies both mdd_cap=%.4f and "
            "min_trades=%d. Relaxing min_trades to 0. Selected θ=%.6f "
            "(quantile=%.2f, mdd=%.4f, n_trades=%d).",
            mdd_cap,
            min_trades,
            best["theta"],
            best["quantile"],
            best["mdd"],
            best["n_trades"],
        )
        return {
            "theta": best["theta"],
            "quantile": best["quantile"],
            "method": "fallback_relax_min_trades",
            "net_pnl": best["net_pnl"],
            "mdd": best["mdd"],
            "n_trades": best["n_trades"],
            "details": details,
        }

    # --- Fallback E.2.2 step 2: θ = +∞ (no-trade) ---
    logger.warning(
        "Fallback E.2.2 step 2: no θ satisfies mdd_cap=%.4f. "
        "Setting θ=+∞ (no-trade for this fold).",
        mdd_cap,
    )
    return {
        "theta": float("inf"),
        "quantile": None,
        "method": "fallback_no_trade",
        "net_pnl": 0.0,
        "mdd": 0.0,
        "n_trades": 0,
        "details": details,
    }
