"""Pure business logic for the run detail page (Page 2).

Extracts testable logic from the Streamlit rendering code.

Ref: §6.1 en-tête du run, §6.2 métriques agrégées,
     §6.3 equity curve, §6.4 métriques par fold, §9.3 conventions,
     §6.5 distribution des trades, §6.6 journal des trades.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.stats import skew

from scripts.dashboard.utils import (
    _NULL_DISPLAY,
    format_float,
    format_int,
    format_mean_std,
    format_pct,
    format_sharpe_per_trade,
    hit_rate_color,
    mdd_color,
    pnl_color,
    profit_factor_color,
    sharpe_color,
)

# ---------------------------------------------------------------------------
# §6.1 — Header info
# ---------------------------------------------------------------------------


def build_header_info(manifest: dict, n_folds: int) -> dict:
    """Build header information dict from manifest (§6.1).

    Parameters
    ----------
    manifest:
        Parsed ``manifest.json`` dict.
    n_folds:
        Number of folds (counted externally from fold directories or metrics).

    Returns
    -------
    dict
        Keys: run_id, date, strategy, framework, symbol, timeframe,
        period, seed, n_folds.
    """
    # Parse created_at_utc → formatted date
    raw_date = manifest["created_at_utc"]
    dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
    date_str = dt.strftime("%Y-%m-%d %H:%M") + " UTC"

    # Strategy info
    strategy_block = manifest["strategy"]
    strategy_name = strategy_block["name"]
    framework = strategy_block.get("framework")

    # Dataset info from top-level manifest (§6.1)
    dataset = manifest["dataset"]
    symbols = dataset["symbols"]
    symbol_str = ", ".join(symbols)
    timeframe = dataset["timeframe"]
    start = dataset["start"]
    end = dataset["end"]
    period = f"{start} — {end} (excl.)"

    # Seed from config_snapshot
    seed = manifest["config_snapshot"]["reproducibility"]["global_seed"]

    return {
        "run_id": manifest["run_id"],
        "date": date_str,
        "strategy": strategy_name,
        "framework": framework,
        "symbol": symbol_str,
        "timeframe": timeframe,
        "period": period,
        "seed": seed,
        "n_folds": n_folds,
    }


# ---------------------------------------------------------------------------
# §6.2 — KPI cards helpers
# ---------------------------------------------------------------------------


def count_non_null_folds(folds: list[dict], metric_key: str) -> int:
    """Count folds with a non-null value for a specific trading metric.

    Parameters
    ----------
    folds:
        List of fold dicts from ``metrics.json``.
    metric_key:
        Key within ``fold["trading"]`` to check.

    Returns
    -------
    int
        Number of folds where the metric is not None.
    """
    count = 0
    for fold in folds:
        trading = fold.get("trading")
        if trading is None:
            continue
        if trading.get(metric_key) is not None:
            count += 1
    return count


def build_kpi_cards(metrics: dict, config_snapshot: dict) -> list[dict]:
    """Build the 6 KPI card data dicts from metrics and config (§6.2).

    Parameters
    ----------
    metrics:
        Parsed ``metrics.json`` dict (with ``folds`` and ``aggregate``).
    config_snapshot:
        Parsed ``config_snapshot.yaml`` dict.

    Returns
    -------
    list[dict]
        List of 6 dicts with keys: label, value, color.
    """
    folds = metrics["folds"]
    n_total = len(folds)
    agg = metrics["aggregate"]["trading"]
    mean = agg["mean"]
    std = agg["std"]

    # Sharpe label conditional (§6.2)
    sharpe_annualized = config_snapshot["metrics"]["sharpe_annualized"]
    sharpe_label = (
        "Sharpe Ratio (annualisé)" if sharpe_annualized else "Sharpe Ratio"
    )

    # Build each card
    cards: list[dict] = []

    # 1. Net PnL — pct format, 2 decimals
    _add_card(
        cards,
        label="Net PnL",
        mean_val=mean.get("net_pnl"),
        std_val=std.get("net_pnl"),
        fmt_type="pct",
        color_fn=pnl_color,
        folds=folds,
        metric_key="net_pnl",
        n_total=n_total,
    )

    # 2. Sharpe Ratio — float format, 2 decimals
    _add_card(
        cards,
        label=sharpe_label,
        mean_val=mean.get("sharpe"),
        std_val=std.get("sharpe"),
        fmt_type="float",
        color_fn=sharpe_color,
        folds=folds,
        metric_key="sharpe",
        n_total=n_total,
    )

    # 3. Max Drawdown — pct format, 2 decimals
    _add_card(
        cards,
        label="Max Drawdown",
        mean_val=mean.get("max_drawdown"),
        std_val=std.get("max_drawdown"),
        fmt_type="pct",
        color_fn=mdd_color,
        folds=folds,
        metric_key="max_drawdown",
        n_total=n_total,
    )

    # 4. Hit Rate — pct format, 1 decimal
    _add_card(
        cards,
        label="Hit Rate",
        mean_val=mean.get("hit_rate"),
        std_val=std.get("hit_rate"),
        fmt_type="pct",
        color_fn=hit_rate_color,
        folds=folds,
        metric_key="hit_rate",
        n_total=n_total,
        decimals=1,
    )

    # 5. Profit Factor — float format, 2 decimals
    _add_card(
        cards,
        label="Profit Factor",
        mean_val=mean.get("profit_factor"),
        std_val=std.get("profit_factor"),
        fmt_type="float",
        color_fn=profit_factor_color,
        folds=folds,
        metric_key="profit_factor",
        n_total=n_total,
    )

    # 6. Nombre de trades — integer format
    n_trades_mean = mean.get("n_trades")
    if n_trades_mean is not None:
        trades_value = format_int(int(round(n_trades_mean)))
    else:
        trades_value = _NULL_DISPLAY
    cards.append({
        "label": "Nombre de trades",
        "value": trades_value,
        "color": None,
    })

    return cards


def _add_card(
    cards: list[dict],
    *,
    label: str,
    mean_val: float | None,
    std_val: float | None,
    fmt_type: str,
    color_fn: Callable[[float | None], str],
    folds: list[dict],
    metric_key: str,
    n_total: int,
    decimals: int = 2,
) -> None:
    """Add a formatted KPI card dict to *cards*."""
    n_contributing = count_non_null_folds(folds, metric_key)

    if mean_val is not None and std_val is None:
        raise ValueError(
            f"Metric '{metric_key}': mean is not None but std is None. "
            "Aggregate data is inconsistent."
        )

    value = format_mean_std(
        mean=mean_val,
        std=std_val if std_val is not None else 0.0,
        fmt_type=fmt_type,
        n_contributing=n_contributing,
        n_total=n_total,
        decimals=decimals,
    )

    cards.append({
        "label": label,
        "value": value,
        "color": color_fn(mean_val),
    })


# ---------------------------------------------------------------------------
# §6.4 — Fold metrics table
# ---------------------------------------------------------------------------


def _fmt_theta(threshold: dict) -> str:
    """Format θ value, returning '—' for method='none' or null theta."""
    method = threshold.get("method")
    theta = threshold.get("theta")
    if method == "none" or theta is None:
        return _NULL_DISPLAY
    return format_float(theta, decimals=4)


def _fmt_quantile(threshold: dict) -> str:
    """Format selected_quantile, returning '—' for null."""
    q = threshold.get("selected_quantile")
    if q is None:
        return _NULL_DISPLAY
    return format_float(q, decimals=2)


def build_fold_metrics_table(metrics: dict) -> pd.DataFrame:
    """Build a formatted fold metrics DataFrame (§6.4).

    Parameters
    ----------
    metrics:
        Parsed ``metrics.json`` dict with ``folds`` list.

    Returns
    -------
    pd.DataFrame
        One row per fold, columns per §6.4 spec.
    """
    columns = [
        "Fold", "θ", "Method", "Quantile",
        "Net PnL", "Sharpe", "MDD", "Win Rate",
        "N Trades", "MAE", "RMSE", "DA", "IC", "Sharpe/Trade",
    ]

    folds = metrics["folds"]
    if not folds:
        return pd.DataFrame(columns=columns)

    rows: list[dict] = []
    for fold in folds:
        threshold = fold["threshold"]
        trading = fold["trading"]
        prediction = fold["prediction"]

        n_trades = trading.get("n_trades")
        sharpe_pt = trading.get("sharpe_per_trade")

        row = {
            "Fold": fold["fold_id"],
            "θ": _fmt_theta(threshold),
            "Method": threshold["method"],
            "Quantile": _fmt_quantile(threshold),
            "Net PnL": format_pct(trading.get("net_pnl")),
            "Sharpe": format_float(trading.get("sharpe")),
            "MDD": format_pct(trading.get("max_drawdown")),
            "Win Rate": format_pct(trading.get("hit_rate")),
            "N Trades": (
                str(n_trades) if n_trades is not None else _NULL_DISPLAY
            ),
            "MAE": format_float(prediction.get("mae"), decimals=4),
            "RMSE": format_float(prediction.get("rmse"), decimals=4),
            "DA": format_pct(prediction.get("directional_accuracy")),
            "IC": format_float(prediction.get("spearman_ic"), decimals=4),
            "Sharpe/Trade": format_sharpe_per_trade(
                sharpe_pt, n_trades if n_trades is not None else 0,
            ),
        }
        rows.append(row)

    return pd.DataFrame(rows, columns=columns)


def build_pnl_bar_data(metrics: dict) -> list[dict]:
    """Extract fold/net_pnl pairs for the PnL bar chart (§6.4).

    Parameters
    ----------
    metrics:
        Parsed ``metrics.json`` dict.

    Returns
    -------
    list[dict]
        Each dict has ``fold`` (int) and ``net_pnl`` (float) keys.
    """
    result: list[dict] = []
    for fold in metrics["folds"]:
        trading = fold["trading"]
        pnl = trading.get("net_pnl")
        result.append({
            "fold": fold["fold_id"],
            "net_pnl": pnl if pnl is not None else 0.0,
        })
    return result


# ---------------------------------------------------------------------------
# §6.5 — Trade distribution statistics
# ---------------------------------------------------------------------------


def compute_trade_stats(trades_df: pd.DataFrame) -> dict:
    """Compute trade distribution statistics (§6.5).

    Parameters
    ----------
    trades_df:
        Trades DataFrame with ``net_return`` column.

    Returns
    -------
    dict
        Keys: mean, median, std, skewness, best_trade, worst_trade.

    Raises
    ------
    ValueError
        If trades_df is empty.
    """
    if trades_df.empty:
        raise ValueError("trades_df is empty: cannot compute trade stats")

    net = trades_df["net_return"]
    return {
        "mean": float(net.mean()),
        "median": float(net.median()),
        "std": float(net.std()),
        "skewness": float(skew(net.values, bias=False)),
        "best_trade": float(net.max()),
        "worst_trade": float(net.min()),
    }


# ---------------------------------------------------------------------------
# §6.6 — Equity after jointure
# ---------------------------------------------------------------------------

_FOLD_NUM_RE = re.compile(r"fold_(\d+)")


def _fold_str_to_int(fold_str: str) -> int:
    """Convert fold string like 'fold_00' to integer 0."""
    m = _FOLD_NUM_RE.search(fold_str)
    if m is None:
        raise ValueError(f"Cannot parse fold number from '{fold_str}'")
    return int(m.group(1))


def join_equity_after(
    trades_df: pd.DataFrame,
    equity_df: pd.DataFrame | None,
) -> pd.Series | None:
    """Join equity values to trades via merge_asof per fold (§6.6).

    Parameters
    ----------
    trades_df:
        Trades DataFrame with ``exit_time_utc`` and ``fold`` columns.
    equity_df:
        Stitched equity curve with ``time_utc``, ``equity``, ``fold`` columns.
        If None, returns None.

    Returns
    -------
    pd.Series or None
        Series of equity values aligned with trades_df.
        NaN where no backward match is found.
    """
    if equity_df is None:
        return None

    # Parse timestamps
    trades_time = pd.to_datetime(trades_df["exit_time_utc"])
    equity_time = pd.to_datetime(equity_df["time_utc"])

    # Build a working copy for the merge
    trades_work = pd.DataFrame({
        "exit_ts": trades_time,
        "fold_int": trades_df["fold"].map(_fold_str_to_int),
        "_orig_idx": range(len(trades_df)),
    })
    equity_work = pd.DataFrame({
        "exit_ts": equity_time,
        "fold_int": equity_df["fold"].astype(int),
        "equity": equity_df["equity"].values,
    }).sort_values("exit_ts")

    # Merge asof per fold
    result = np.full(len(trades_df), np.nan, dtype=np.float64)

    for fold_val in trades_work["fold_int"].unique():
        t_mask = trades_work["fold_int"] == fold_val
        e_mask = equity_work["fold_int"] == fold_val

        t_sub = trades_work.loc[t_mask].sort_values("exit_ts")
        e_sub = equity_work.loc[e_mask].sort_values("exit_ts")

        if e_sub.empty:
            continue

        merged = pd.merge_asof(
            t_sub[["exit_ts", "_orig_idx"]],
            e_sub[["exit_ts", "equity"]],
            on="exit_ts",
            direction="backward",
        )

        valid = merged.dropna(subset=["equity"])
        if not valid.empty:
            idxs = valid["_orig_idx"].astype(int).values
            result[idxs] = valid["equity"].values

    return pd.Series(result, index=trades_df.index)


# ---------------------------------------------------------------------------
# §6.6 — Trade journal construction
# ---------------------------------------------------------------------------


def build_trade_journal(
    trades_df: pd.DataFrame,
    equity_df: pd.DataFrame | None,
) -> pd.DataFrame:
    """Build the formatted trade journal DataFrame (§6.6).

    Parameters
    ----------
    trades_df:
        Trades DataFrame from ``load_trades()``.
    equity_df:
        Stitched equity curve from ``load_equity_curve()``, or None.

    Returns
    -------
    pd.DataFrame
        Journal with columns per §6.6 spec.
    """
    if trades_df.empty:
        cols = [
            "Fold", "Entry time", "Exit time", "Entry price", "Exit price",
            "Gross return", "Costs", "Net return",
        ]
        if equity_df is not None:
            cols.append("Equity after")
        return pd.DataFrame(columns=cols)

    journal = pd.DataFrame({
        "Fold": trades_df["fold"].values,
        "Entry time": trades_df["entry_time_utc"].values,
        "Exit time": trades_df["exit_time_utc"].values,
        "Entry price": trades_df["entry_price"].values,
        "Exit price": trades_df["exit_price"].values,
        "Gross return": trades_df["gross_return"].values,
        "Costs": trades_df["costs"].values,
        "Net return": trades_df["net_return"].values,
    })

    # Add Equity after column only if equity data is available
    equity_after = join_equity_after(trades_df, equity_df)
    if equity_after is not None:
        journal["Equity after"] = equity_after.apply(
            lambda v: _NULL_DISPLAY if pd.isna(v) else v
        )

    return journal


# ---------------------------------------------------------------------------
# §11.2 — Pagination
# ---------------------------------------------------------------------------


def paginate_dataframe(
    df: pd.DataFrame,
    page: int,
    page_size: int = 50,
) -> pd.DataFrame:
    """Return a page slice of the DataFrame (§11.2).

    Parameters
    ----------
    df:
        Input DataFrame.
    page:
        1-based page number.
    page_size:
        Rows per page (default 50 per §11.2).

    Returns
    -------
    pd.DataFrame
        Slice for the requested page.

    Raises
    ------
    ValueError
        If page < 1.
    """
    if page < 1:
        raise ValueError(f"page must be >= 1, got {page}")
    if page_size < 1:
        raise ValueError(f"page_size must be >= 1, got {page_size}")

    start = (page - 1) * page_size
    end = start + page_size
    return df.iloc[start:end]


# ---------------------------------------------------------------------------
# §6.6 — Trade filters
# ---------------------------------------------------------------------------


def filter_trades(
    trades_df: pd.DataFrame,
    *,
    fold: str | None = None,
    sign: str | None = None,
    date_start: pd.Timestamp | None = None,
    date_end: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Filter trades DataFrame by fold, sign, and date range (§6.6).

    Parameters
    ----------
    trades_df:
        Trades DataFrame with ``fold``, ``net_return``, ``entry_time_utc``.
    fold:
        Fold name to filter on (e.g. 'fold_00'). None = all folds.
    sign:
        'winning' (net_return > 0) or 'losing' (net_return <= 0). None = all.
    date_start, date_end:
        Date range filter on entry_time_utc. None = no filter.

    Returns
    -------
    pd.DataFrame
        Filtered trades.
    """
    if sign is not None and sign not in ("winning", "losing"):
        raise ValueError(
            f"sign must be 'winning', 'losing', or None, got {sign!r}"
        )

    mask = pd.Series(True, index=trades_df.index)

    if fold is not None:
        mask = mask & (trades_df["fold"] == fold)

    if sign == "winning":
        mask = mask & (trades_df["net_return"] > 0)
    elif sign == "losing":
        mask = mask & (trades_df["net_return"] <= 0)

    if date_start is not None or date_end is not None:
        entry_times = pd.to_datetime(trades_df["entry_time_utc"])
        if date_start is not None:
            mask = mask & (entry_times >= date_start)
        if date_end is not None:
            mask = mask & (entry_times <= date_end)

    return trades_df.loc[mask]
