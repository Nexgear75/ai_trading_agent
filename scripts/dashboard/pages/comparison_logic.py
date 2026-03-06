"""Pure business logic for the comparison page (Page 3).

Extracts testable logic from the Streamlit rendering code.
Reuses overview_logic's build_overview_dataframe for DRY (§5.2 columns).

Ref: §7.1 multiselect, §7.2 tableau comparatif, §14.4 critères pipeline.
"""

from __future__ import annotations

import pandas as pd

from scripts.dashboard.pages.overview_logic import build_overview_dataframe

# Numeric columns eligible for best/worst highlighting (§7.2)
_NUMERIC_COLS = [
    "Net PnL (moy)",
    "Sharpe (moy)",
    "MDD (moy)",
    "Win Rate (moy)",
    "Trades (moy)",
]

# For most columns, higher is better.
# MDD is special: best = closest to zero (lowest absolute value),
# regardless of whether values are stored as negative or positive.
_HIGHER_IS_BETTER = {
    "Net PnL (moy)": True,
    "Sharpe (moy)": True,
    "MDD (moy)": None,  # Special: lowest abs value is best
    "Win Rate (moy)": True,
    "Trades (moy)": True,
}


# ---------------------------------------------------------------------------
# DataFrame construction (§7.2) — reuses overview_logic (DRY)
# ---------------------------------------------------------------------------


def build_comparison_dataframe(runs: list[dict]) -> pd.DataFrame:
    """Build comparison DataFrame from selected runs.

    Delegates to ``overview_logic.build_overview_dataframe`` for column
    construction (DRY with §5.2).

    Parameters
    ----------
    runs:
        List of validated metrics dicts for the selected runs.

    Returns
    -------
    pd.DataFrame
        One row per selected run, same columns as §5.2.
    """
    return build_overview_dataframe(runs)


# ---------------------------------------------------------------------------
# Best / worst highlighting (§7.2)
# ---------------------------------------------------------------------------


def highlight_best_worst(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Identify best and worst row indices per numeric column.

    Parameters
    ----------
    df:
        Comparison DataFrame (numeric values, not formatted).

    Returns
    -------
    dict
        ``{col_name: {"best": idx, "worst": idx}}`` for each numeric column.
        If all values are NaN for a column, that column is omitted.
    """
    result: dict[str, dict[str, int]] = {}
    for col in _NUMERIC_COLS:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        valid = series.dropna()
        if valid.empty:
            continue

        direction = _HIGHER_IS_BETTER[col]
        if direction is None:
            # MDD: best = smallest absolute value (closest to 0)
            abs_valid = valid.abs()
            best_idx = int(abs_valid.idxmin())
            worst_idx = int(abs_valid.idxmax())
        elif direction:
            best_idx = int(valid.idxmax())
            worst_idx = int(valid.idxmin())
        else:
            best_idx = int(valid.idxmin())
            worst_idx = int(valid.idxmax())

        result[col] = {"best": best_idx, "worst": worst_idx}

    return result


# ---------------------------------------------------------------------------
# Pipeline criteria check (§14.4)
# ---------------------------------------------------------------------------


def check_pipeline_criteria(
    metrics: dict,
    config_snapshot: dict | None,
) -> dict:
    """Check §14.4 pipeline conformity criteria for a single run.

    Criteria:
    - P&L net > 0
    - Profit factor > 1.0
    - MDD < thresholding.mdd_cap (from config_snapshot)

    Parameters
    ----------
    metrics:
        Full metrics dict for the run.
    config_snapshot:
        Parsed config_snapshot.yaml dict, or None if unavailable.

    Returns
    -------
    dict
        ``{"pnl_ok": bool, "pf_ok": bool, "mdd_ok": bool|None, "icon": str}``
        ``mdd_ok`` is None when config_snapshot is absent or mdd_cap missing.
        ``icon`` is "✅" only if all three criteria are True.
    """
    trading_mean = metrics["aggregate"]["trading"]["mean"]

    # P&L net > 0
    net_pnl = trading_mean.get("net_pnl")
    pnl_ok = net_pnl is not None and net_pnl > 0

    # Profit factor > 1.0
    profit_factor = trading_mean.get("profit_factor")
    pf_ok = profit_factor is not None and profit_factor > 1.0

    # MDD < mdd_cap (config-driven)
    mdd_ok: bool | None = None
    if config_snapshot is not None:
        thresholding = config_snapshot.get("thresholding")
        if isinstance(thresholding, dict):
            mdd_cap = thresholding.get("mdd_cap")
            if mdd_cap is not None:
                max_drawdown = trading_mean.get("max_drawdown")
                mdd_ok = (
                    abs(max_drawdown) < mdd_cap
                    if max_drawdown is not None
                    else False
                )

    # Icon: ✅ only if all three are True (not None)
    all_pass = pnl_ok is True and pf_ok is True and mdd_ok is True
    icon = "✅" if all_pass else "❌"

    return {"pnl_ok": pnl_ok, "pf_ok": pf_ok, "mdd_ok": mdd_ok, "icon": icon}


# ---------------------------------------------------------------------------
# Pandas Styler for best/worst highlighting (§7.2)
# ---------------------------------------------------------------------------


def apply_highlight_styles(
    df: pd.DataFrame,
    highlights: dict[str, dict[str, int]],
) -> pd.DataFrame:
    """Build a CSS-style DataFrame for best/worst cell highlighting (§7.2).

    Returns a same-shape DataFrame of CSS strings suitable for
    ``DataFrame.style.apply(fn, axis=None)``.

    - Best value: **bold green** (``font-weight: bold; color: green``)
    - Worst value: *italic red* (``font-style: italic; color: red``)
    - When best == worst (single run / tied), no styling is applied.

    Parameters
    ----------
    df:
        The (formatted) comparison DataFrame.
    highlights:
        Output of :func:`highlight_best_worst`.

    Returns
    -------
    pd.DataFrame
        CSS strings, same shape as *df*.
    """
    styles = pd.DataFrame("", index=df.index, columns=df.columns)
    for col, indices in highlights.items():
        if col not in df.columns:
            continue
        best_idx = indices["best"]
        worst_idx = indices["worst"]
        if best_idx != worst_idx:
            col_pos = list(styles.columns).index(col)
            styles.iloc[best_idx, col_pos] = (
                "font-weight: bold; color: green"
            )
            styles.iloc[worst_idx, col_pos] = (
                "font-style: italic; color: red"
            )
    return styles


# ---------------------------------------------------------------------------
# Notes extraction (§7.2)
# ---------------------------------------------------------------------------


def get_aggregate_notes(metrics: dict) -> str | None:
    """Extract aggregate.notes from metrics if present and non-empty.

    Parameters
    ----------
    metrics:
        Full metrics dict for the run.

    Returns
    -------
    str or None
        Notes string, or None if absent/empty.
    """
    notes = metrics["aggregate"].get("notes")
    if not notes:
        return None
    return notes


# ---------------------------------------------------------------------------
# Run label for multiselect (§7.1)
# ---------------------------------------------------------------------------


def format_run_label(metrics: dict) -> str:
    """Format a run for display in the multiselect widget.

    Shows run_id alongside strategy name for quick identification (§7.1).

    Parameters
    ----------
    metrics:
        Full metrics dict for the run.

    Returns
    -------
    str
        Label like ``"20260301_120000_xgb — xgboost_reg"``.
    """
    run_id = metrics["run_id"]
    strategy_name = metrics["strategy"]["name"]
    return f"{run_id} — {strategy_name}"
