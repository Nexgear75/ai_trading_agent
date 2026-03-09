"""Page 4 — Analyse par fold (Fold Analysis).

Navigation fold par fold : sélection d'un run puis d'un fold,
equity curve du fold avec marqueurs entry/exit et drawdown,
scatter plot prédictions vs réalisés avec coloration Go/No-Go,
journal des trades du fold.

Ref: §10.2 — pages/4_fold_analysis.py, §8.1 sélection, §8.2 equity,
     §8.3 scatter, §8.4 journal des trades.
"""

from __future__ import annotations

import math
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
    build_fold_trade_journal,
    build_prediction_metrics,
    format_theta,
    get_fold_dir,
    get_fold_threshold,
    get_output_type,
    prepare_fold_trades,
)
from scripts.dashboard.pages.run_detail_logic import (
    filter_trades,
    paginate_dataframe,
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

# Clamp session state if run changed (fewer folds)
if "fold_slider" in st.session_state and st.session_state["fold_slider"] >= len(fold_ids):
    st.session_state["fold_slider"] = 0
    st.session_state["fold_select"] = fold_ids[0]


def _on_fold_select():
    """Sync slider when selectbox changes."""
    st.session_state["fold_slider"] = fold_ids.index(st.session_state["fold_select"])


def _on_fold_slider():
    """Sync selectbox when slider changes."""
    st.session_state["fold_select"] = fold_ids[st.session_state["fold_slider"]]


selected_fold = st.selectbox(
    "Fold", fold_ids, key="fold_select", on_change=_on_fold_select,
)
st.slider(
    "Navigation fold", 0, len(fold_ids) - 1, key="fold_slider",
    on_change=_on_fold_slider,
)

selected_fold = fold_ids[st.session_state.get("fold_slider", 0)]

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

        if theta is None:
            st.warning(
                "Seuil θ non disponible pour ce fold — scatter plot non affiché."
            )
        else:
            fig_scatter = chart_scatter_predictions(preds_df, theta, method)
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

st.divider()

# ---------------------------------------------------------------------------
# §8.4 — Journal des trades du fold
# ---------------------------------------------------------------------------

st.subheader("Journal des trades")

if trades_df is None or trades_df.empty:
    st.info(f"Trades non disponibles pour {selected_fold} (trades.csv absent).")
else:
    prepared_trades = prepare_fold_trades(trades_df)

    # Filters: sign + date (no fold filter — fold already selected upstream)
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        sign_options = ["Tous", "Gagnant", "Perdant"]
        selected_sign = st.radio(
            "Signe", sign_options, horizontal=True, key="fold_journal_sign",
        )
    with filter_col2:
        entry_times = pd.to_datetime(prepared_trades["entry_time_utc"])
        min_date = entry_times.min().date()
        max_date = entry_times.max().date()
        date_range = st.date_input(
            "Période",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="fold_journal_dates",
        )

    # Map sign selection to filter_trades parameter
    sign_map = {"Tous": None, "Gagnant": "winning", "Perdant": "losing"}
    sign_filter = sign_map[selected_sign]

    # Parse date range
    date_start = None
    date_end = None
    if isinstance(date_range, tuple) and len(date_range) == 2:
        date_start = pd.Timestamp(date_range[0])
        date_end = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    # Apply filters (DRY: reuse filter_trades from run_detail_logic)
    filtered = filter_trades(
        prepared_trades, sign=sign_filter, date_start=date_start, date_end=date_end,
    )

    # Build journal (DRY: fold-specific helper, no Fold column)
    journal = build_fold_trade_journal(filtered, equity_df)

    # Pagination (DRY: reuse paginate_dataframe from run_detail_logic)
    total_rows = len(journal)
    page_size = 50
    total_pages = max(1, math.ceil(total_rows / page_size))
    st.caption(f"{total_rows} trades — {total_pages} page(s)")

    if total_rows > 0:
        current_page = st.number_input(
            "Page", min_value=1, max_value=total_pages, value=1,
            key="fold_journal_page",
        )
        page_df = paginate_dataframe(journal, page=current_page, page_size=page_size)
        st.dataframe(page_df, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun trade ne correspond aux filtres sélectionnés.")
