"""Pure business logic for the overview page (Page 1).

Extracts testable logic (DataFrame construction, filtering, formatting)
from the Streamlit rendering code.

Ref: §5.2 tableau, §5.3 filtrage/tri, §9.3 conventions d'affichage.
"""

from __future__ import annotations

import pandas as pd

from scripts.dashboard.utils import format_float, format_pct

# ---------------------------------------------------------------------------
# Column definitions (§5.2)
# ---------------------------------------------------------------------------

_COLUMNS = [
    "Run ID",
    "Stratégie",
    "Type",
    "Folds",
    "Net PnL (moy)",
    "Sharpe (moy)",
    "MDD (moy)",
    "Win Rate (moy)",
    "Trades (moy)",
]

# Type filter mapping (§5.3)
_TYPE_FILTER_MAP: dict[str, str | None] = {
    "Tous": None,
    "Modèles": "model",
    "Baselines": "baseline",
}


# ---------------------------------------------------------------------------
# DataFrame construction (§5.2)
# ---------------------------------------------------------------------------


def build_overview_dataframe(runs: list[dict]) -> pd.DataFrame:
    """Build the overview DataFrame from a list of metrics dicts.

    Parameters
    ----------
    runs:
        List of validated metrics dicts (from ``discover_runs()``).

    Returns
    -------
    pd.DataFrame
        One row per run, columns per §5.2, sorted by Run ID descending.
    """
    if not runs:
        return pd.DataFrame(columns=_COLUMNS)

    rows: list[dict] = []
    for m in runs:
        trading_mean = m["aggregate"]["trading"]["mean"]
        rows.append({
            "Run ID": m["run_id"],
            "Stratégie": m["strategy"]["name"],
            "Type": m["strategy"]["strategy_type"],
            "Folds": len(m["folds"]),
            "Net PnL (moy)": trading_mean.get("net_pnl"),
            "Sharpe (moy)": trading_mean.get("sharpe"),
            "MDD (moy)": trading_mean.get("max_drawdown"),
            "Win Rate (moy)": trading_mean.get("hit_rate"),
            "Trades (moy)": trading_mean.get("n_trades"),
        })

    df = pd.DataFrame(rows, columns=_COLUMNS)
    # Default sort: Run ID descending (most recent first)
    df = df.sort_values("Run ID", ascending=False).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Filtering (§5.3)
# ---------------------------------------------------------------------------


def filter_by_type(df: pd.DataFrame, type_filter: str) -> pd.DataFrame:
    """Filter DataFrame by strategy type.

    Parameters
    ----------
    df:
        Overview DataFrame.
    type_filter:
        One of 'Tous', 'Modèles', 'Baselines'.

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame.

    Raises
    ------
    ValueError
        If ``type_filter`` is not a valid option.
    """
    if type_filter not in _TYPE_FILTER_MAP:
        raise ValueError(
            f"Unknown type filter: {type_filter!r}. "
            f"Valid options: {sorted(_TYPE_FILTER_MAP.keys())}"
        )

    mapped = _TYPE_FILTER_MAP[type_filter]
    if mapped is None:
        return df
    return df[df["Type"] == mapped].reset_index(drop=True)


def filter_by_strategy(df: pd.DataFrame, strategies: list[str]) -> pd.DataFrame:
    """Filter DataFrame by selected strategy names.

    Parameters
    ----------
    df:
        Overview DataFrame.
    strategies:
        List of strategy names to keep. Empty list means no filter (all rows).

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame.
    """
    if not strategies:
        return df
    return df[df["Stratégie"].isin(strategies)].reset_index(drop=True)


def get_unique_strategies(df: pd.DataFrame) -> list[str]:
    """Return sorted unique strategy names from the DataFrame.

    Parameters
    ----------
    df:
        Overview DataFrame.

    Returns
    -------
    list[str]
        Sorted list of unique strategy names.
    """
    if df.empty:
        return []
    return sorted(df["Stratégie"].unique().tolist())


# ---------------------------------------------------------------------------
# Warnings detection (§4.3)
# ---------------------------------------------------------------------------


def has_warnings(metrics: dict) -> bool:
    """Check if a run's aggregate contains warning notes.

    Parameters
    ----------
    metrics:
        A single metrics dict.

    Returns
    -------
    bool
        True if ``aggregate.notes`` is present and non-empty.
    """
    notes = metrics["aggregate"].get("notes")
    if notes is None:
        return False
    return bool(notes)


def build_warnings_mask(runs: list[dict]) -> list[bool]:
    """Build a boolean mask of runs that have warnings.

    Parameters
    ----------
    runs:
        List of metrics dicts.

    Returns
    -------
    list[bool]
        One entry per run: True if run has warnings.
    """
    return [has_warnings(m) for m in runs]


# ---------------------------------------------------------------------------
# Formatting for display (§9.3)
# ---------------------------------------------------------------------------


def format_overview_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Format the overview DataFrame for display (§9.3).

    Applies formatting rules:
    - Net PnL, MDD: :.2%
    - Sharpe: :.2f
    - Win Rate: :.1%
    - Trades: integer (no decimals)
    - None/NaN → '—'

    Parameters
    ----------
    df:
        Raw overview DataFrame (numeric values).

    Returns
    -------
    pd.DataFrame
        Copy with string-formatted values for display.
    """
    out = df.copy()
    out["Net PnL (moy)"] = out["Net PnL (moy)"].apply(
        lambda v: format_pct(_nan_to_none(v), decimals=2)
    )
    out["Sharpe (moy)"] = out["Sharpe (moy)"].apply(
        lambda v: format_float(_nan_to_none(v), decimals=2)
    )
    out["MDD (moy)"] = out["MDD (moy)"].apply(
        lambda v: format_pct(_nan_to_none(v), decimals=2)
    )
    out["Win Rate (moy)"] = out["Win Rate (moy)"].apply(
        lambda v: format_pct(_nan_to_none(v), decimals=1)
    )
    out["Trades (moy)"] = out["Trades (moy)"].apply(_format_trades)
    return out


def _nan_to_none(value: float | None) -> float | None:
    """Convert NaN to None for compatibility with format functions."""
    if value is None or pd.isna(value):
        return None
    return value


def _format_trades(value: float | None) -> str | int:
    """Format trades count: float → int string, None → '—'."""
    if value is None or pd.isna(value):
        return "—"
    return str(int(value))
