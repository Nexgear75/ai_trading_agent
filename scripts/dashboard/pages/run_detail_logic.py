"""Pure business logic for the run detail page (Page 2) — header and KPI cards.

Extracts testable logic from the Streamlit rendering code.

Ref: §6.1 en-tête du run, §6.2 métriques agrégées, §9.3 conventions.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from scripts.dashboard.utils import (
    _NULL_DISPLAY,
    format_int,
    format_mean_std,
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
