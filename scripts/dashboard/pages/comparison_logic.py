"""Pure business logic for the comparison page (Page 3).

Extracts testable logic (DataFrame construction, highlighting, criterion check,
radar data, notes extraction, formatting) from the Streamlit rendering code.

Ref: §7.1 multiselect, §7.2 tableau comparatif, §9.3 conventions d'affichage.
"""

from __future__ import annotations

import pandas as pd

from scripts.dashboard.pages.overview_logic import (
    build_overview_dataframe,
    format_overview_dataframe,
)

# ---------------------------------------------------------------------------
# Highlight criteria: for each column, whether higher is better
# ---------------------------------------------------------------------------

_HIGHLIGHT_COLUMNS: dict[str, bool] = {
    "Net PnL (moy)": True,    # higher = better
    "Sharpe (moy)": True,     # higher = better
    "MDD (moy)": True,        # less negative = better → higher value = better
    "Win Rate (moy)": True,   # higher = better
    "Trades (moy)": True,     # higher = better
}


# ---------------------------------------------------------------------------
# DataFrame construction (§7.2 — reusing §5.2 via overview_logic)
# ---------------------------------------------------------------------------


def build_comparison_dataframe(runs: list[dict]) -> pd.DataFrame:
    """Build comparison DataFrame for selected runs.

    Delegates to ``build_overview_dataframe`` for column construction (§5.2 DRY).

    Parameters
    ----------
    runs:
        List of validated metrics dicts (from ``discover_runs()``).

    Returns
    -------
    pd.DataFrame
        One row per run, columns per §5.2, sorted by Run ID descending.
    """
    return build_overview_dataframe(runs)


# ---------------------------------------------------------------------------
# Highlight best/worst (§7.2)
# ---------------------------------------------------------------------------


def highlight_best_worst(df: pd.DataFrame) -> dict:
    """Identify best and worst row index per numeric column.

    Parameters
    ----------
    df:
        Comparison DataFrame (numeric values, not formatted).

    Returns
    -------
    dict
        ``{column_name: {"best": idx|None, "worst": idx|None}}``.
        If all values are NaN/None for a column, both are None.
    """
    result: dict = {}
    for col, higher_is_better in _HIGHLIGHT_COLUMNS.items():
        if col not in df.columns:
            continue
        series = df[col]
        non_null = series.dropna()
        if non_null.empty:
            result[col] = {"best": None, "worst": None}
            continue
        if higher_is_better:
            best_idx = int(non_null.idxmax())
            worst_idx = int(non_null.idxmin())
        else:
            best_idx = int(non_null.idxmin())
            worst_idx = int(non_null.idxmax())
        result[col] = {"best": best_idx, "worst": worst_idx}
    return result


# ---------------------------------------------------------------------------
# §14.4 criterion check
# ---------------------------------------------------------------------------


def check_criterion_14_4(
    metrics: dict, config_snapshot: dict | None
) -> bool:
    """Check §14.4 pipeline criteria for a run.

    Criteria:
    - P&L net > 0
    - Profit factor > 1.0
    - MDD < thresholding.mdd_cap (from config_snapshot)

    Parameters
    ----------
    metrics:
        A single metrics dict.
    config_snapshot:
        Parsed config_snapshot.yaml dict, or None if file was missing.

    Returns
    -------
    bool
        True if all criteria are met, False otherwise.
    """
    if config_snapshot is None:
        return False

    trading_mean = metrics["aggregate"]["trading"]["mean"]
    net_pnl = trading_mean.get("net_pnl")
    profit_factor = trading_mean.get("profit_factor")
    max_drawdown = trading_mean.get("max_drawdown")

    if net_pnl is None or profit_factor is None or max_drawdown is None:
        return False

    mdd_cap = config_snapshot["thresholding"]["mdd_cap"]

    if net_pnl <= 0:
        return False
    if profit_factor <= 1.0:
        return False
    return not max_drawdown <= mdd_cap


# ---------------------------------------------------------------------------
# Radar data builder (§7.4)
# ---------------------------------------------------------------------------


def _none_to_zero(value: float | None) -> float:
    """Convert None to 0.0 for radar chart values."""
    if value is None:
        return 0.0
    return value


def build_radar_data(runs: list[dict]) -> list[dict]:
    """Build radar chart data from selected runs.

    Each output dict: label, net_pnl, sharpe, max_drawdown, hit_rate, profit_factor.
    None values are replaced by 0.0.

    Parameters
    ----------
    runs:
        List of validated metrics dicts.

    Returns
    -------
    list[dict]
        One dict per run with label and numeric values.
    """
    result: list[dict] = []
    for m in runs:
        trading_mean = m["aggregate"]["trading"]["mean"]
        label = f"{m['strategy']['name']} ({m['run_id']})"
        result.append({
            "label": label,
            "net_pnl": _none_to_zero(trading_mean.get("net_pnl")),
            "sharpe": _none_to_zero(trading_mean.get("sharpe")),
            "max_drawdown": _none_to_zero(trading_mean.get("max_drawdown")),
            "hit_rate": _none_to_zero(trading_mean.get("hit_rate")),
            "profit_factor": _none_to_zero(trading_mean.get("profit_factor")),
        })
    return result


# ---------------------------------------------------------------------------
# Aggregate notes (§7.2)
# ---------------------------------------------------------------------------


def get_aggregate_notes(metrics: dict) -> str | None:
    """Return aggregate.notes if present and non-empty.

    Parameters
    ----------
    metrics:
        A single metrics dict.

    Returns
    -------
    str or None
        The notes string, or None if absent/empty.
    """
    notes = metrics["aggregate"].get("notes")
    if notes is None:
        return None
    if not notes:
        return None
    return notes


# ---------------------------------------------------------------------------
# Formatting (§9.3 — delegates to overview_logic)
# ---------------------------------------------------------------------------


def format_comparison_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Format comparison DataFrame for display (§9.3).

    Delegates to ``format_overview_dataframe`` for DRY consistency.

    Parameters
    ----------
    df:
        Raw comparison DataFrame (numeric values).

    Returns
    -------
    pd.DataFrame
        Copy with string-formatted values for display.
    """
    return format_overview_dataframe(df)
