"""Chart creation module for the AI Trading dashboard.

Fonctions de création des graphiques Plotly (equity curves,
distributions, heatmaps, comparaisons inter-runs).

Ref: §10.2 — charts.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from scripts.dashboard.utils import (
    COLOR_DRAWDOWN,
    COLOR_FOLD_BORDER,
    COLOR_LOSS,
    COLOR_NEUTRAL,
    COLOR_PROFIT,
)

# ---------------------------------------------------------------------------
# §6.3 — Equity curve stitchée
# ---------------------------------------------------------------------------


def chart_equity_curve(
    df: pd.DataFrame,
    fold_boundaries: bool = True,
    drawdown: bool = True,
    in_trade_zones: bool = True,
) -> go.Figure:
    """Equity curve chart with optional fold boundaries, drawdown, and in-trade zones.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns: ``time_utc``, ``equity``, ``in_trade``, ``fold``.
    fold_boundaries : bool
        Add vertical dashed lines at fold changes.
    drawdown : bool
        Add shaded drawdown area.
    in_trade_zones : bool
        Highlight periods where ``in_trade`` is True.
    """
    fig = go.Figure()

    # Normalize equity to start at 1.0
    eq_start = df["equity"].iloc[0]
    if eq_start == 0:
        raise ValueError("equity[0] must be > 0 for normalization")
    norm_equity = df["equity"] / eq_start

    # Main equity line
    fig.add_trace(
        go.Scatter(
            x=df["time_utc"],
            y=norm_equity,
            mode="lines",
            name="Equity",
            line={"color": COLOR_NEUTRAL},
        )
    )

    # Drawdown shaded area
    if drawdown:
        running_max = norm_equity.cummax()
        dd = running_max - norm_equity
        fig.add_trace(
            go.Scatter(
                x=df["time_utc"],
                y=running_max,
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["time_utc"],
                y=norm_equity,
                mode="lines",
                fill="tonexty",
                fillcolor=COLOR_DRAWDOWN,
                line={"width": 0},
                name="Drawdown",
                hovertext=[f"DD: {d:.4f}" for d in dd],
            )
        )

    # In-trade zones
    if in_trade_zones:
        in_trade_mask = df["in_trade"].astype(bool)
        if in_trade_mask.any():
            fig.add_trace(
                go.Scatter(
                    x=df.loc[in_trade_mask, "time_utc"],
                    y=norm_equity.loc[in_trade_mask],
                    mode="markers",
                    marker={"color": COLOR_PROFIT, "size": 4, "opacity": 0.4},
                    name="In Trade",
                )
            )

    # Fold boundaries (vertical lines)
    shapes = []
    if fold_boundaries:
        fold_changes = df["fold"].diff().fillna(0) != 0
        boundary_times = df.loc[fold_changes, "time_utc"]
        for t in boundary_times:
            shapes.append(
                {
                    "type": "line",
                    "x0": t,
                    "x1": t,
                    "y0": 0,
                    "y1": 1,
                    "yref": "paper",
                    "line": {
                        "color": COLOR_FOLD_BORDER,
                        "width": 1,
                        "dash": "dot",
                    },
                }
            )

    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Time",
        yaxis_title="Normalized Equity",
        shapes=shapes,
        legend={"yanchor": "top", "y": 0.99, "xanchor": "left", "x": 0.01},
    )

    return fig


# ---------------------------------------------------------------------------
# §6.4 — PnL bar chart par fold
# ---------------------------------------------------------------------------


def chart_pnl_bar(fold_metrics: list[dict]) -> go.Figure:
    """Bar chart of Net PnL per fold.

    Parameters
    ----------
    fold_metrics : list[dict]
        Each dict must contain ``fold`` and ``net_pnl`` keys.
    """
    fig = go.Figure()

    if not fold_metrics:
        fig.update_layout(title="Net PnL per Fold")
        return fig

    folds = [str(m["fold"]) for m in fold_metrics]
    pnls = [m["net_pnl"] for m in fold_metrics]
    colors = [COLOR_PROFIT if p > 0 else COLOR_LOSS for p in pnls]

    fig.add_trace(
        go.Bar(
            x=folds,
            y=pnls,
            marker_color=colors,
            name="Net PnL",
        )
    )

    fig.update_layout(
        title="Net PnL per Fold",
        xaxis_title="Fold",
        yaxis_title="Net PnL",
    )

    return fig


# ---------------------------------------------------------------------------
# §6.5 — Histogramme des rendements
# ---------------------------------------------------------------------------


def chart_returns_histogram(trades_df: pd.DataFrame) -> go.Figure:
    """Histogram of net returns per trade.

    Parameters
    ----------
    trades_df : pd.DataFrame
        Must contain column ``net_return``.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=trades_df["net_return"],
            marker_color=COLOR_NEUTRAL,
            name="Net Return",
        )
    )

    fig.update_layout(
        title="Returns Distribution",
        xaxis_title="Net Return",
        yaxis_title="Count",
    )

    return fig


# ---------------------------------------------------------------------------
# §6.5 — Box plot rendements par fold
# ---------------------------------------------------------------------------


def chart_returns_boxplot(trades_df: pd.DataFrame) -> go.Figure:
    """Box plot of net returns grouped by fold.

    Parameters
    ----------
    trades_df : pd.DataFrame
        Must contain columns ``net_return`` and ``fold``.
    """
    fig = go.Figure()

    for fold_id in sorted(trades_df["fold"].unique()):
        fold_data = trades_df.loc[trades_df["fold"] == fold_id, "net_return"]
        fig.add_trace(
            go.Box(
                y=fold_data,
                name=f"Fold {fold_id}",
            )
        )

    fig.update_layout(
        title="Returns by Fold",
        yaxis_title="Net Return",
    )

    return fig


# ---------------------------------------------------------------------------
# §7.3 — Overlay multi-runs
# ---------------------------------------------------------------------------


def chart_equity_overlay(curves: dict[str, pd.DataFrame]) -> go.Figure:
    """Overlay equity curves from multiple runs, normalized to start at 1.0.

    Parameters
    ----------
    curves : dict[str, pd.DataFrame]
        Keys are run labels, values are DataFrames with an ``equity`` column.
    """
    fig = go.Figure()

    for label, curve_df in curves.items():
        eq = curve_df["equity"]
        eq_start = eq.iloc[0]
        if eq_start == 0:
            raise ValueError(
                f"equity[0] must be > 0 for normalization (run '{label}')"
            )
        norm_eq = eq / eq_start
        fig.add_trace(
            go.Scatter(
                y=norm_eq.values,
                mode="lines",
                name=label,
            )
        )

    fig.update_layout(
        title="Equity Overlay",
        yaxis_title="Normalized Equity",
        legend={"itemclick": "toggle", "itemdoubleclick": "toggleothers"},
    )

    return fig


# ---------------------------------------------------------------------------
# §7.4 — Radar chart
# ---------------------------------------------------------------------------

_RADAR_AXES = ["Net PnL", "Sharpe", "1−MDD", "Win Rate", "PF"]


def chart_radar(runs_data: list[dict]) -> go.Figure:
    """Radar chart with 5 axes: Net PnL, Sharpe, 1-MDD, Win Rate, PF.

    Values are min-max normalized across the supplied runs.
    ``1-MDD`` is inverted so that lower drawdown scores higher.

    Parameters
    ----------
    runs_data : list[dict]
        Each dict: ``label``, ``net_pnl``, ``sharpe``, ``max_drawdown``,
        ``hit_rate``, ``profit_factor``.
    """
    fig = go.Figure()

    # Extract raw values per axis
    raw = {
        "Net PnL": [r["net_pnl"] for r in runs_data],
        "Sharpe": [r["sharpe"] for r in runs_data],
        "1−MDD": [1.0 - r["max_drawdown"] for r in runs_data],
        "Win Rate": [r["hit_rate"] for r in runs_data],
        "PF": [r["profit_factor"] for r in runs_data],
    }

    # Min-max normalization per axis
    normalized: dict[str, list[float]] = {}
    for axis, values in raw.items():
        mn = min(values)
        mx = max(values)
        if mx - mn < 1e-12:
            # All values equal → center at 0.5
            normalized[axis] = [0.5] * len(values)
        else:
            normalized[axis] = [(v - mn) / (mx - mn) for v in values]

    # Build traces
    theta = _RADAR_AXES + [_RADAR_AXES[0]]  # close the polygon
    for i, run in enumerate(runs_data):
        r_values = [normalized[ax][i] for ax in _RADAR_AXES]
        r_values.append(r_values[0])  # close
        fig.add_trace(
            go.Scatterpolar(
                r=r_values,
                theta=theta,
                fill="toself",
                name=run["label"],
            )
        )

    fig.update_layout(
        title="Radar Comparison",
        polar={"radialaxis": {"visible": True, "range": [0, 1]}},
    )

    return fig


# ---------------------------------------------------------------------------
# §8.3 — Scatter predictions
# ---------------------------------------------------------------------------


def chart_scatter_predictions(
    preds_df: pd.DataFrame,
    theta: float,
    threshold_method: str,
) -> go.Figure:
    """Scatter plot of y_hat vs y_true with Go/No-Go coloring.

    If ``threshold_method == "none"``, returns a figure with an informative
    annotation instead of scatter data (signal-type models).

    Parameters
    ----------
    preds_df : pd.DataFrame
        Must contain columns ``y_true`` and ``y_hat``.
    theta : float
        Threshold for Go/No-Go classification.
    threshold_method : str
        Method used for threshold. ``"none"`` triggers the signal fallback.
    """
    fig = go.Figure()

    if threshold_method == "none":
        fig.update_layout(
            title="Predictions Scatter",
            annotations=[
                {
                    "text": (
                        "Scatter plot non disponible"
                        " pour les modèles de type signal"
                    ),
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                    "font": {"size": 14},
                }
            ],
        )
        return fig

    y_true = preds_df["y_true"]
    y_hat = preds_df["y_hat"]

    # Go/No-Go coloring based on theta
    go_mask = np.abs(y_hat) >= theta
    colors = [COLOR_PROFIT if g else COLOR_FOLD_BORDER for g in go_mask]

    fig.add_trace(
        go.Scatter(
            x=y_hat,
            y=y_true,
            mode="markers",
            marker={"color": colors, "size": 5},
            name="Predictions",
        )
    )

    # Diagonal perfect prediction line
    all_vals = pd.concat([y_true, y_hat])
    v_min = float(all_vals.min())
    v_max = float(all_vals.max())

    fig.update_layout(
        title="Predictions Scatter",
        xaxis_title="ŷ",
        yaxis_title="y_true",
        shapes=[
            {
                "type": "line",
                "x0": v_min,
                "y0": v_min,
                "x1": v_max,
                "y1": v_max,
                "line": {"color": COLOR_FOLD_BORDER, "dash": "dot"},
            }
        ],
    )

    return fig


# ---------------------------------------------------------------------------
# §8.2 — Fold equity with trade markers
# ---------------------------------------------------------------------------


def chart_fold_equity(
    df: pd.DataFrame,
    trades_df: pd.DataFrame,
) -> go.Figure:
    """Equity curve for a fold with entry/exit trade markers.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns ``time_utc`` and ``equity``.
    trades_df : pd.DataFrame
        Must contain ``entry_time_utc`` and ``exit_time_utc``.
    """
    fig = go.Figure()

    # Equity line
    fig.add_trace(
        go.Scatter(
            x=df["time_utc"],
            y=df["equity"],
            mode="lines",
            name="Equity",
            line={"color": COLOR_NEUTRAL},
        )
    )

    if len(trades_df) == 0:
        fig.update_layout(
            title="Fold Equity",
            xaxis_title="Time",
            yaxis_title="Equity",
        )
        return fig

    # Map timestamps to equity values for marker placement
    time_to_eq = dict(zip(df["time_utc"], df["equity"], strict=True))
    if len(time_to_eq) != len(df):
        raise ValueError("duplicate time_utc in equity DataFrame")

    # Entry markers ▲ green
    entry_times = trades_df["entry_time_utc"]
    entry_eq = [time_to_eq.get(t) for t in entry_times]
    valid_entries = [
        (t, e) for t, e in zip(entry_times, entry_eq, strict=True) if e is not None
    ]
    if valid_entries:
        e_times, e_vals = zip(*valid_entries, strict=True)
        fig.add_trace(
            go.Scatter(
                x=list(e_times),
                y=list(e_vals),
                mode="markers",
                marker={
                    "symbol": "triangle-up",
                    "size": 10,
                    "color": COLOR_PROFIT,
                },
                name="Entry",
            )
        )

    # Exit markers ▼ red
    exit_times = trades_df["exit_time_utc"]
    exit_eq = [time_to_eq.get(t) for t in exit_times]
    valid_exits = [
        (t, e) for t, e in zip(exit_times, exit_eq, strict=True) if e is not None
    ]
    if valid_exits:
        x_times, x_vals = zip(*valid_exits, strict=True)
        fig.add_trace(
            go.Scatter(
                x=list(x_times),
                y=list(x_vals),
                mode="markers",
                marker={
                    "symbol": "triangle-down",
                    "size": 10,
                    "color": COLOR_LOSS,
                },
                name="Exit",
            )
        )

    fig.update_layout(
        title="Fold Equity",
        xaxis_title="Time",
        yaxis_title="Equity",
    )

    return fig
