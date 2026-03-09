"""Pure business logic for the fold analysis page (Page 4).

Extracts testable logic from the Streamlit rendering code.

Ref: §8.1 sélection fold, §8.2 equity curve du fold, §8.3 scatter predictions.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import spearmanr

from scripts.dashboard.utils import COLOR_DRAWDOWN

# ---------------------------------------------------------------------------
# §8.1 — Fold listing and selection helpers
# ---------------------------------------------------------------------------


def list_fold_dirs(run_dir: Path) -> list[str]:
    """Return sorted fold directory names from run_dir/folds/.

    Parameters
    ----------
    run_dir:
        Path to the run directory.

    Returns
    -------
    list[str]
        Sorted list of fold directory names (e.g. ["fold_00", "fold_01"]).
        Empty list if folds/ does not exist or is empty.
    """
    folds_dir = run_dir / "folds"
    if not folds_dir.is_dir():
        return []
    return sorted(
        entry.name for entry in folds_dir.iterdir() if entry.is_dir()
    )


def build_fold_selector_options(metrics: dict) -> list[str]:
    """Return fold IDs from a metrics.json dict.

    Parameters
    ----------
    metrics:
        Parsed metrics dict with a ``folds`` list.

    Returns
    -------
    list[str]
        List of fold_id strings in order.
    """
    return [fold["fold_id"] for fold in metrics["folds"]]


def get_fold_dir(run_dir: Path, fold_id: str) -> Path:
    """Build the path to a specific fold directory.

    Parameters
    ----------
    run_dir:
        Path to the run directory.
    fold_id:
        Fold identifier (e.g. "fold_00").

    Returns
    -------
    Path
        ``run_dir / "folds" / fold_id``.
    """
    return run_dir / "folds" / fold_id


# ---------------------------------------------------------------------------
# §8.2 — Drawdown overlay
# ---------------------------------------------------------------------------


def add_drawdown_to_figure(
    fig: go.Figure,
    equity_df: pd.DataFrame,
) -> go.Figure:
    """Add drawdown shading to an existing Plotly figure.

    Computes the running maximum of the equity series, then adds two traces:
    an invisible running-max line and a fill-to-previous trace showing the
    drawdown area.

    Parameters
    ----------
    fig:
        Existing Plotly figure (e.g. from ``chart_fold_equity``).
    equity_df:
        DataFrame with ``time_utc`` and ``equity`` columns.

    Returns
    -------
    go.Figure
        The same figure object, with drawdown traces appended.
    """
    equity = equity_df["equity"]
    running_max = equity.cummax()

    # Invisible running-max line (upper bound for fill)
    fig.add_trace(
        go.Scatter(
            x=equity_df["time_utc"],
            y=running_max,
            mode="lines",
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Fill between running_max and equity
    dd = running_max - equity
    fig.add_trace(
        go.Scatter(
            x=equity_df["time_utc"],
            y=equity,
            mode="lines",
            fill="tonexty",
            fillcolor=COLOR_DRAWDOWN,
            line={"width": 0},
            name="Drawdown",
            hovertext=[f"DD: {d:.4f}" for d in dd],
        )
    )

    return fig


# ---------------------------------------------------------------------------
# §8.3 — Threshold & output type helpers
# ---------------------------------------------------------------------------


def get_fold_threshold(metrics: dict, fold_id: str) -> dict:
    """Extract threshold info from metrics for a given fold.

    Parameters
    ----------
    metrics:
        Parsed metrics dict with a ``folds`` list.
    fold_id:
        Fold identifier (e.g. ``"fold_00"``).

    Returns
    -------
    dict
        ``{"theta": float | None, "method": str}``.

    Raises
    ------
    ValueError
        If ``fold_id`` is not found in metrics folds.
    """
    for fold in metrics["folds"]:
        if fold["fold_id"] == fold_id:
            threshold = fold["threshold"]
            return {"theta": threshold["theta"], "method": threshold["method"]}
    raise ValueError(f"Fold {fold_id!r} not found in metrics")


def get_output_type(metrics: dict) -> str:
    """Detect the output type of the model from metrics.

    Primary: reads ``metrics["strategy"]["output_type"]``.
    Fallback (older runs): if any fold has ``threshold.method == "none"``
    for *all* folds → ``"signal"``, else ``"regression"``.

    Parameters
    ----------
    metrics:
        Parsed metrics dict.

    Returns
    -------
    str
        ``"regression"`` or ``"signal"``.
    """
    output_type = metrics.get("strategy", {}).get("output_type")
    if output_type is not None:
        return output_type

    # Fallback: infer from threshold methods
    methods = [f["threshold"]["method"] for f in metrics["folds"]]
    if all(m == "none" for m in methods):
        return "signal"
    return "regression"


# ---------------------------------------------------------------------------
# §8.3 — Prediction metrics
# ---------------------------------------------------------------------------


def build_prediction_metrics(preds_df: pd.DataFrame) -> dict:
    """Compute prediction quality metrics from y_true and y_hat.

    Parameters
    ----------
    preds_df:
        DataFrame with ``y_true`` and ``y_hat`` columns.

    Returns
    -------
    dict
        Keys: ``mae``, ``rmse``, ``da``, ``ic``.
    """
    y_true = preds_df["y_true"].to_numpy()
    y_hat = preds_df["y_hat"].to_numpy()

    diff = y_true - y_hat
    mae = float(np.mean(np.abs(diff)))
    rmse = float(np.sqrt(np.mean(diff**2)))
    da = float(np.mean(np.sign(y_true) == np.sign(y_hat)))
    ic = float(spearmanr(y_true, y_hat).statistic)

    return {"mae": mae, "rmse": rmse, "da": da, "ic": ic}


def format_theta(theta: float | None) -> str:
    """Format θ for display. None → '—' (em dash)."""
    if theta is None:
        return "—"
    return f"{theta:.4f}"
