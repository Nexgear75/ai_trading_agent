"""Page 4 — Analyse par fold (Fold Analysis).

Navigation fold par fold : sélection d'un run puis d'un fold,
equity curve du fold avec marqueurs entry/exit et drawdown,
scatter plot prédictions vs réalisés avec coloration Go/No-Go.

Ref: §10.2 — pages/4_fold_analysis.py, §8.1 sélection, §8.2 equity, §8.3 scatter.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from scripts.dashboard.charts import chart_fold_equity, chart_scatter_predictions
from scripts.dashboard.data_loader import (
    load_fold_equity_curve,
    load_fold_trades,
    load_predictions,
    load_run_metrics,
)
from scripts.dashboard.pages.fold_analysis_logic import (
    add_drawdown_to_figure,
    build_fold_selector_options,
    build_prediction_metrics,
    format_theta,
    get_fold_dir,
    get_fold_threshold,
    get_output_type,
)
from scripts.dashboard.utils import format_float, format_pct

# ---------------------------------------------------------------------------
# Page rendering
# ---------------------------------------------------------------------------

st.header("Analyse par fold")

runs: list[dict] = st.session_state.get("runs", [])
runs_dir: Path | None = st.session_state.get("runs_dir")

if not runs or runs_dir is None:
    st.error("Aucun run disponible. Vérifiez le répertoire des runs.")
    st.stop()

# ---------------------------------------------------------------------------
# §8.1 — Run selector
# ---------------------------------------------------------------------------

run_labels = [f"{r['strategy']['name']} ({r['run_id']})" for r in runs]
selected_run_label = st.selectbox("Sélectionner un run", run_labels)

if selected_run_label is None:
    st.warning("Veuillez sélectionner un run.")
    st.stop()

selected_idx = run_labels.index(selected_run_label)
selected_run = runs[selected_idx]
run_dir = runs_dir / selected_run["run_id"]

# ---------------------------------------------------------------------------
# §8.1 — Fold selector (dropdown + slider)
# ---------------------------------------------------------------------------

metrics = load_run_metrics(run_dir)
fold_ids = build_fold_selector_options(metrics)

if not fold_ids:
    st.info("Aucun fold disponible pour ce run.")
    st.stop()

selected_fold = st.selectbox("Fold", fold_ids, key="fold_select")
fold_index = fold_ids.index(selected_fold)
fold_slider = st.slider(
    "Navigation fold", 0, len(fold_ids) - 1, fold_index, key="fold_slider"
)

# Sync slider with dropdown
if fold_slider != fold_index:
    selected_fold = fold_ids[fold_slider]

fold_dir = get_fold_dir(run_dir, selected_fold)

# ---------------------------------------------------------------------------
# §8.2 — Equity curve du fold
# ---------------------------------------------------------------------------

equity_df = load_fold_equity_curve(fold_dir)
trades_df = load_fold_trades(fold_dir)

if equity_df is None:
    st.info(f"Equity curve non disponible pour {selected_fold}.")
else:
    trades_for_chart = (
        trades_df
        if trades_df is not None
        else pd.DataFrame(columns=["entry_time_utc", "exit_time_utc"])
    )
    fig = chart_fold_equity(equity_df, trades_for_chart)
    fig = add_drawdown_to_figure(fig, equity_df)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# §8.3 — Scatter predictions
# ---------------------------------------------------------------------------

st.subheader("Prédictions vs Réalisés")

preds_df = load_predictions(fold_dir, "test")
if preds_df is None:
    st.info(f"Prédictions non disponibles pour {selected_fold} (preds_test.csv absent).")
else:
    threshold_info = get_fold_threshold(metrics, selected_fold)
    output_type = get_output_type(metrics)

    if output_type == "signal":
        st.info("Scatter plot non disponible pour les modèles de type signal.")
    else:
        theta = threshold_info["theta"]
        method = threshold_info["method"]
        fig_scatter = chart_scatter_predictions(
            preds_df, theta if theta is not None else 0.0, method
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

        # Metrics encart §8.3
        pred_metrics = build_prediction_metrics(preds_df)
        metric_cols = st.columns(5)
        labels = [
            ("MAE", format_float(pred_metrics["mae"], decimals=4)),
            ("RMSE", format_float(pred_metrics["rmse"], decimals=4)),
            ("DA", format_pct(pred_metrics["da"])),
            ("IC", format_float(pred_metrics["ic"], decimals=4)),
            ("θ", format_theta(theta)),
        ]
        for col, (label, value) in zip(metric_cols, labels, strict=True):
            with col:
                st.metric(label=label, value=value)
