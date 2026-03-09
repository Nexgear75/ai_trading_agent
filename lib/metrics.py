"""Prediction metrics, trading metrics, aggregation, and equity stitching."""

from __future__ import annotations

import logging
import math
from collections.abc import Mapping

import numpy as np
import pandas as pd
from scipy import stats

from lib.features import VALID_OUTPUT_TYPES

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# PREDICTION METRICS
# ═══════════════════════════════════════════════════════════════════════════

def _validate_pred_vectors(
    y_true: np.ndarray, y_hat: np.ndarray, *, min_length: int = 1,
) -> None:
    if y_true.ndim != 1 or y_hat.ndim != 1:
        raise ValueError(
            f"y_true and y_hat must be 1-D, got ndim={y_true.ndim} and ndim={y_hat.ndim}."
        )
    if len(y_true) != len(y_hat):
        raise ValueError(
            f"y_true and y_hat must have same length, got {len(y_true)} and {len(y_hat)}."
        )
    if len(y_true) < min_length:
        raise ValueError(f"y_true must have at least {min_length} element(s).")
    if not np.all(np.isfinite(y_true)):
        raise ValueError("y_true contains non-finite values.")
    if not np.all(np.isfinite(y_hat)):
        raise ValueError("y_hat contains non-finite values.")


def compute_mae(y_true: np.ndarray, y_hat: np.ndarray) -> float:
    _validate_pred_vectors(y_true, y_hat)
    return float(np.mean(np.abs(y_true - y_hat)))


def compute_rmse(y_true: np.ndarray, y_hat: np.ndarray) -> float:
    _validate_pred_vectors(y_true, y_hat)
    return float(np.sqrt(np.mean((y_true - y_hat) ** 2)))


def compute_directional_accuracy(y_true: np.ndarray, y_hat: np.ndarray) -> float | None:
    _validate_pred_vectors(y_true, y_hat)
    eligible = (y_true != 0.0) & (y_hat != 0.0)
    n_eligible = int(np.sum(eligible))
    if n_eligible == 0:
        return None
    sign_match = np.sign(y_true[eligible]) == np.sign(y_hat[eligible])
    return float(np.mean(sign_match))


def compute_spearman_ic(y_true: np.ndarray, y_hat: np.ndarray) -> float:
    _validate_pred_vectors(y_true, y_hat, min_length=2)
    if np.all(y_true == y_true[0]):
        raise ValueError("y_true is constant — Spearman IC is undefined.")
    if np.all(y_hat == y_hat[0]):
        raise ValueError("y_hat is constant — Spearman IC is undefined.")
    result = stats.spearmanr(y_true, y_hat)
    ic = float(result.statistic)
    if not math.isfinite(ic):
        raise ValueError(f"Spearman IC returned non-finite value: {ic}.")
    return ic


def compute_prediction_metrics(
    y_true: np.ndarray,
    y_hat: np.ndarray,
    *,
    output_type: str,
) -> dict[str, float | None]:
    if output_type not in VALID_OUTPUT_TYPES:
        raise ValueError(
            f"output_type must be one of {sorted(VALID_OUTPUT_TYPES)}, got {output_type!r}."
        )
    if output_type == "signal":
        return {"mae": None, "rmse": None, "directional_accuracy": None, "spearman_ic": None}
    try:
        spearman_ic: float | None = compute_spearman_ic(y_true, y_hat)
    except ValueError:
        spearman_ic = None
    return {
        "mae": compute_mae(y_true, y_hat),
        "rmse": compute_rmse(y_true, y_hat),
        "directional_accuracy": compute_directional_accuracy(y_true, y_hat),
        "spearman_ic": spearman_ic,
    }


# ═══════════════════════════════════════════════════════════════════════════
# TRADING METRICS
# ═══════════════════════════════════════════════════════════════════════════

def _validate_equity_curve(ec: pd.DataFrame) -> None:
    if "equity" not in ec.columns:
        raise ValueError("equity_curve must contain an 'equity' column")
    if len(ec) == 0:
        raise ValueError("equity_curve must not be empty")


def _validate_equity_curve_with_in_trade(ec: pd.DataFrame) -> None:
    _validate_equity_curve(ec)
    if "in_trade" not in ec.columns:
        raise ValueError("equity_curve must contain an 'in_trade' column")


def _validate_trades_r_net(trades: list[dict]) -> None:
    for i, trade in enumerate(trades):
        if "r_net" not in trade:
            raise ValueError(f"trade[{i}] is missing required key 'r_net'")


def _validate_sharpe_epsilon(sharpe_epsilon: float) -> None:
    if not math.isfinite(sharpe_epsilon):
        raise ValueError(f"sharpe_epsilon must be finite and > 0, got {sharpe_epsilon}")
    if sharpe_epsilon <= 0:
        raise ValueError(f"sharpe_epsilon must be > 0, got {sharpe_epsilon}")


def _validate_timeframe_hours(timeframe_hours: float) -> None:
    if not math.isfinite(timeframe_hours) or timeframe_hours <= 0:
        raise ValueError(f"timeframe_hours must be > 0, got {timeframe_hours}")


def compute_net_pnl(equity_curve: pd.DataFrame) -> float:
    _validate_equity_curve(equity_curve)
    equity = equity_curve["equity"].to_numpy(dtype=np.float64)
    return float(equity[-1] / equity[0] - 1.0)


def compute_max_drawdown(equity_curve: pd.DataFrame) -> float:
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
        k = 365.25 * 24 / timeframe_hours
        sharpe = sharpe * np.sqrt(k)
    return float(sharpe)


def compute_profit_factor(trades: list[dict]) -> float | None:
    if len(trades) == 0:
        return None
    _validate_trades_r_net(trades)
    r_nets = np.array([t["r_net"] for t in trades], dtype=np.float64)
    gains = r_nets[r_nets > 0]
    losses = r_nets[r_nets < 0]
    if len(gains) == 0 and len(losses) == 0:
        return None
    if len(losses) == 0:
        return None
    if len(gains) == 0:
        return 0.0
    return float(np.sum(gains) / np.abs(np.sum(losses)))


def compute_hit_rate(trades: list[dict]) -> float | None:
    if len(trades) == 0:
        return None
    _validate_trades_r_net(trades)
    r_nets = np.array([t["r_net"] for t in trades], dtype=np.float64)
    n_winning = int(np.sum(r_nets > 0))
    return float(n_winning / len(trades))


def compute_avg_trade_return(trades: list[dict]) -> float | None:
    if len(trades) == 0:
        return None
    _validate_trades_r_net(trades)
    r_nets = np.array([t["r_net"] for t in trades], dtype=np.float64)
    return float(np.mean(r_nets))


def compute_median_trade_return(trades: list[dict]) -> float | None:
    if len(trades) == 0:
        return None
    _validate_trades_r_net(trades)
    r_nets = np.array([t["r_net"] for t in trades], dtype=np.float64)
    return float(np.median(r_nets))


def compute_exposure_time_frac(equity_curve: pd.DataFrame) -> float:
    _validate_equity_curve_with_in_trade(equity_curve)
    in_trade = equity_curve["in_trade"].to_numpy(dtype=bool)
    return float(np.sum(in_trade) / len(in_trade))


def compute_sharpe_per_trade(
    trades: list[dict], *, sharpe_epsilon: float,
) -> float | None:
    if len(trades) == 0:
        return None
    _validate_trades_r_net(trades)
    _validate_sharpe_epsilon(sharpe_epsilon)
    r_nets = np.array([t["r_net"] for t in trades], dtype=np.float64)
    mean_r = float(np.mean(r_nets))
    std_r = float(np.std(r_nets, ddof=0))
    return float(mean_r / (std_r + sharpe_epsilon))


def compute_trading_metrics(
    equity_curve: pd.DataFrame,
    trades: list[dict],
    *,
    sharpe_epsilon: float,
    sharpe_annualized: bool,
    timeframe_hours: float,
) -> dict[str, float | int | None]:
    _validate_equity_curve_with_in_trade(equity_curve)
    _validate_sharpe_epsilon(sharpe_epsilon)
    n_trades = len(trades)
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


# ═══════════════════════════════════════════════════════════════════════════
# AGGREGATION
# ═══════════════════════════════════════════════════════════════════════════

_TRADING_METRICS = (
    "net_pnl", "net_return", "max_drawdown", "sharpe", "profit_factor",
    "hit_rate", "n_trades", "avg_trade_return", "median_trade_return",
    "exposure_time_frac",
)

PREDICTION_METRICS = (
    "mae", "rmse", "directional_accuracy", "spearman_ic",
)

_AGGREGATED_METRICS = _TRADING_METRICS + PREDICTION_METRICS


def aggregate_fold_metrics(
    fold_metrics_list: list[dict[str, float | int | None]],
) -> dict[str, float | None]:
    if len(fold_metrics_list) == 0:
        raise ValueError("fold_metrics_list must not be empty.")
    result: dict[str, float | None] = {}
    for metric in _AGGREGATED_METRICS:
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
            if len(arr) < 2:
                result[f"{metric}_std"] = 0.0
            else:
                result[f"{metric}_std"] = float(np.std(arr, ddof=1))
    return result


def _infer_candle_interval(ec: pd.DataFrame) -> pd.Timedelta | None:
    if len(ec) < 2:
        return None
    diffs = ec["time_utc"].diff().dropna()
    median: pd.Timedelta = diffs.median()
    return median


def stitch_equity_curves(
    fold_equities: list[pd.DataFrame],
) -> pd.DataFrame:
    if len(fold_equities) == 0:
        raise ValueError("fold_equities must not be empty.")
    required_cols = {"time_utc", "equity", "in_trade"}
    for i, ec in enumerate(fold_equities):
        if len(ec) == 0:
            raise ValueError(f"fold_equities[{i}] is empty (0 rows).")
        missing = required_cols - set(ec.columns)
        if missing:
            raise ValueError(
                f"fold_equities[{i}] is missing required columns: {sorted(missing)}"
            )
    parts: list[pd.DataFrame] = []
    carry_equity: float | None = None
    for k, ec in enumerate(fold_equities):
        ec_copy = ec[["time_utc", "equity", "in_trade"]].copy()
        original_equity = ec_copy["equity"].to_numpy(dtype=np.float64)
        if carry_equity is not None:
            prev_last_time = parts[-1]["time_utc"].iloc[-1]
            curr_first_time = ec_copy["time_utc"].iloc[0]
            time_delta = curr_first_time - prev_last_time
            interval = _infer_candle_interval(parts[-1])
            if interval is None:
                interval = _infer_candle_interval(ec_copy)
            if interval is not None and time_delta > interval * 1.5:
                logger.warning(
                    "Gap detected between fold %d and fold %d.", k - 1, k,
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
            original_start = original_equity[0]
            if original_start == 0.0:
                raise ValueError(
                    f"fold_equities[{k}] has equity starting at 0.0, cannot rescale."
                )
            scale = carry_equity / original_start
            ec_copy["equity"] = original_equity * scale
        ec_copy["fold"] = k
        carry_equity = float(ec_copy["equity"].iloc[-1])
        parts.append(ec_copy)
    stitched = pd.concat(parts, ignore_index=True)
    return stitched


def check_acceptance_criteria(
    aggregate: Mapping[str, float | None],
    *,
    mdd_cap: float,
) -> list[str]:
    if not math.isfinite(mdd_cap) or mdd_cap <= 0:
        raise ValueError(f"mdd_cap must be > 0, got {mdd_cap}")
    notes: list[str] = []
    net_pnl_mean = aggregate.get("net_pnl_mean")
    if net_pnl_mean is not None and net_pnl_mean <= 0:
        msg = f"net_pnl_mean <= 0 ({net_pnl_mean:.6f})"
        logger.warning(msg)
        notes.append(msg)
    pf_mean = aggregate.get("profit_factor_mean")
    if pf_mean is not None and pf_mean <= 1.0:
        msg = f"profit_factor_mean <= 1.0 ({pf_mean:.6f})"
        logger.warning(msg)
        notes.append(msg)
    mdd_mean = aggregate.get("max_drawdown_mean")
    if mdd_mean is not None and mdd_mean >= mdd_cap:
        msg = f"max_drawdown_mean >= mdd_cap ({mdd_mean:.6f} >= {mdd_cap:.6f})"
        logger.warning(msg)
        notes.append(msg)
    return notes


def derive_comparison_type(strategy_name: str) -> str:
    if not strategy_name:
        raise ValueError("strategy_name must not be empty.")
    if strategy_name == "buy_hold":
        return "contextual"
    return "go_nogo"
