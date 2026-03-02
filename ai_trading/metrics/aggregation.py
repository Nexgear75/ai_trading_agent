"""Inter-fold aggregation — mean/std metrics, stitched equity, warnings.

Spec §14.3 (aggregation), §14.4 (acceptance warnings), §13.4 (stitched equity).

Task #042 — WS-10.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Mapping

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Metrics to aggregate (trading + prediction).
_TRADING_METRICS = (
    "net_pnl",
    "net_return",
    "max_drawdown",
    "sharpe",
    "profit_factor",
    "hit_rate",
    "n_trades",
    "avg_trade_return",
    "median_trade_return",
    "exposure_time_frac",
)

_PREDICTION_METRICS = (
    "mae",
    "rmse",
    "directional_accuracy",
    "spearman_ic",
)

_AGGREGATED_METRICS = _TRADING_METRICS + _PREDICTION_METRICS

# Keys explicitly excluded from aggregation (I-04).
_EXCLUDED_METRICS = frozenset({
    "sharpe_per_trade",
    "n_samples_train",
    "n_samples_val",
    "n_samples_test",
})


# ---------------------------------------------------------------------------
# aggregate_fold_metrics
# ---------------------------------------------------------------------------


def aggregate_fold_metrics(
    fold_metrics_list: list[dict[str, float | int | None]],
) -> dict[str, float | None]:
    """Compute mean and std (ddof=1) for each metric across test folds.

    Parameters
    ----------
    fold_metrics_list:
        One dict per fold, as returned by ``compute_trading_metrics``
        (and optionally merged with ``compute_prediction_metrics``).

    Returns
    -------
    dict
        Keys ``<metric>_mean`` and ``<metric>_std`` for every aggregated
        metric. Values are float64, or ``None`` when all folds have ``None``
        for that metric.

    Raises
    ------
    ValueError
        If *fold_metrics_list* is empty.
    """
    if len(fold_metrics_list) == 0:
        raise ValueError("fold_metrics_list must not be empty.")

    result: dict[str, float | None] = {}

    for metric in _AGGREGATED_METRICS:
        # Collect non-None values across folds.
        values: list[float] = []
        for fold in fold_metrics_list:
            val = fold.get(metric)
            if val is not None:
                values.append(float(val))

        if len(values) == 0:
            result[f"{metric}_mean"] = None
            result[f"{metric}_std"] = None
        else:
            arr = np.array(values, dtype=np.float64)
            result[f"{metric}_mean"] = float(np.mean(arr))
            result[f"{metric}_std"] = float(np.std(arr, ddof=1))

    return result


# ---------------------------------------------------------------------------
# stitch_equity_curves
# ---------------------------------------------------------------------------


def _infer_candle_interval(ec: pd.DataFrame) -> pd.Timedelta | None:
    """Infer candle interval from ``time_utc`` column (median diff).

    Returns ``None`` when fewer than 2 rows are available.
    """
    if len(ec) < 2:
        return None
    diffs = ec["time_utc"].diff().dropna()
    median: pd.Timedelta = diffs.median()  # type: ignore[assignment]
    return median


def stitch_equity_curves(
    fold_equities: list[pd.DataFrame],
) -> pd.DataFrame:
    """Stitch per-fold equity curves with continuation.

    ``E_start[k+1] = E_end[k]``: each fold's equity is rescaled so that
    it starts where the previous fold ended.

    Parameters
    ----------
    fold_equities:
        One DataFrame per fold, each with columns ``time_utc``, ``equity``,
        ``in_trade``.

    Returns
    -------
    pd.DataFrame
        Concatenated DataFrame with columns ``time_utc``, ``equity``,
        ``in_trade``, ``fold``.

    Raises
    ------
    ValueError
        If *fold_equities* is empty or any DataFrame is missing required
        columns.
    """
    if len(fold_equities) == 0:
        raise ValueError("fold_equities must not be empty.")

    required_cols = {"time_utc", "equity", "in_trade"}
    for i, ec in enumerate(fold_equities):
        if len(ec) == 0:
            raise ValueError(f"fold_equities[{i}] is empty (0 rows).")
        missing = required_cols - set(ec.columns)
        if missing:
            raise ValueError(
                f"fold_equities[{i}] is missing required columns: "
                f"{sorted(missing)}"
            )

    parts: list[pd.DataFrame] = []
    carry_equity: float | None = None

    for k, ec in enumerate(fold_equities):
        ec_copy = ec[["time_utc", "equity", "in_trade"]].copy()
        original_equity = ec_copy["equity"].to_numpy(dtype=np.float64)

        if carry_equity is not None:
            # Detect real gap between folds using inferred candle interval.
            prev_last_time = parts[-1]["time_utc"].iloc[-1]
            curr_first_time = ec_copy["time_utc"].iloc[0]
            time_delta = curr_first_time - prev_last_time

            interval = _infer_candle_interval(parts[-1])
            if interval is None:
                interval = _infer_candle_interval(ec_copy)

            if (
                interval is not None
                and time_delta > interval * 1.5
            ):
                logger.warning(
                    "Gap detected between fold %d and fold %d "
                    "(last=%s, next=%s). Inserting constant-equity rows.",
                    k - 1, k, prev_last_time, curr_first_time,
                )
                gap_times = pd.date_range(
                    start=prev_last_time + interval,
                    end=curr_first_time,
                    freq=interval,
                    inclusive="left",
                )
                if len(gap_times) > 0:
                    gap_df = pd.DataFrame({
                        "time_utc": gap_times,
                        "equity": carry_equity,
                        "in_trade": False,
                        "fold": k - 1,
                    })
                    parts.append(gap_df)

            # Rescale: multiply by (carry / original_start).
            original_start = original_equity[0]
            if original_start == 0.0:
                raise ValueError(
                    f"fold_equities[{k}] has equity starting at 0.0, "
                    "cannot rescale."
                )
            scale = carry_equity / original_start
            ec_copy["equity"] = original_equity * scale

        ec_copy["fold"] = k
        carry_equity = float(ec_copy["equity"].iloc[-1])
        parts.append(ec_copy)

    stitched = pd.concat(parts, ignore_index=True)
    return stitched


# ---------------------------------------------------------------------------
# check_acceptance_criteria
# ---------------------------------------------------------------------------


def check_acceptance_criteria(
    aggregate: Mapping[str, float | None],
    *,
    mdd_cap: float,
) -> list[str]:
    """Check §14.4 acceptance criteria and return warning notes.

    Parameters
    ----------
    aggregate:
        Aggregated metrics dict (output of ``aggregate_fold_metrics``).
    mdd_cap:
        Maximum drawdown cap from config (``thresholding.mdd_cap``).

    Returns
    -------
    list[str]
        Warning messages. Empty list if all criteria are met.

    Raises
    ------
    ValueError
        If *mdd_cap* is not positive.
    """
    if not math.isfinite(mdd_cap) or mdd_cap <= 0:
        raise ValueError(f"mdd_cap must be > 0, got {mdd_cap}")

    notes: list[str] = []

    # §14.4 — net_pnl_mean <= 0
    net_pnl_mean = aggregate.get("net_pnl_mean")
    if net_pnl_mean is not None and net_pnl_mean <= 0:
        msg = f"net_pnl_mean <= 0 ({net_pnl_mean:.6f})"
        logger.warning(msg)
        notes.append(msg)

    # §14.4 — profit_factor_mean <= 1.0
    pf_mean = aggregate.get("profit_factor_mean")
    if pf_mean is not None and pf_mean <= 1.0:
        msg = f"profit_factor_mean <= 1.0 ({pf_mean:.6f})"
        logger.warning(msg)
        notes.append(msg)

    # §14.4 — max_drawdown_mean >= mdd_cap
    mdd_mean = aggregate.get("max_drawdown_mean")
    if mdd_mean is not None and mdd_mean >= mdd_cap:
        msg = f"max_drawdown_mean >= mdd_cap ({mdd_mean:.6f} >= {mdd_cap:.6f})"
        logger.warning(msg)
        notes.append(msg)

    return notes


# ---------------------------------------------------------------------------
# derive_comparison_type
# ---------------------------------------------------------------------------


def derive_comparison_type(strategy_name: str) -> str:
    """Derive comparison type from strategy name.

    Parameters
    ----------
    strategy_name:
        Strategy name (e.g. ``"buy_hold"``, ``"xgboost_reg"``).

    Returns
    -------
    str
        ``"contextual"`` for ``buy_hold``, ``"go_nogo"`` for everything else.

    Raises
    ------
    ValueError
        If *strategy_name* is empty.
    """
    if not strategy_name:
        raise ValueError("strategy_name must not be empty.")

    if strategy_name == "buy_hold":
        return "contextual"
    return "go_nogo"
