"""Page 2 — Détail d'un run (Run Detail).

Visualisation détaillée d'un run sélectionné : equity curve,
trade journal, métriques par fold, configuration utilisée.

Ref: §10.2 — pages/2_run_detail.py, §6.1 en-tête, §6.2 KPI cards,
     §6.3 equity curve, §6.4 métriques par fold,
     §6.5 distribution des trades, §6.6 journal des trades.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import streamlit as st

from scripts.dashboard.charts import (
    chart_equity_curve,
    chart_pnl_bar,
    chart_returns_boxplot,
    chart_returns_histogram,
)
from scripts.dashboard.data_loader import (
    load_config_snapshot,
    load_equity_curve,
    load_run_manifest,
    load_run_metrics,
    load_trades,
)
from scripts.dashboard.pages.run_detail_logic import (
    build_fold_metrics_table,
    build_header_info,
    build_kpi_cards,
    build_pnl_bar_data,
    build_trade_journal,
    compute_trade_stats,
    filter_trades,
    paginate_dataframe,
)
from scripts.dashboard.utils import format_float, format_pct

# ---------------------------------------------------------------------------
# Page rendering
# ---------------------------------------------------------------------------

runs: list[dict] = st.session_state.get("runs", [])
runs_dir: Path | None = st.session_state.get("runs_dir")

if not runs or runs_dir is None:
    st.error("Aucun run disponible. Vérifiez le répertoire des runs.")
    st.stop()

# Run selector
run_ids = [r["run_id"] for r in runs]
selected_run_id = st.selectbox("Sélectionner un run", run_ids)

if selected_run_id is None:
    st.warning("Veuillez sélectionner un run.")
    st.stop()

run_dir = runs_dir / selected_run_id

# Load artefacts
manifest = load_run_manifest(run_dir)
metrics = load_run_metrics(run_dir)
config_snapshot = load_config_snapshot(run_dir)

# Count folds from metrics.json
n_folds = len(metrics["folds"])

# ---------------------------------------------------------------------------
# §6.1 — Header
# ---------------------------------------------------------------------------

header = build_header_info(manifest, n_folds)

st.title(f"Run: {header['run_id']}")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"**Date** : {header['date']}")
    st.markdown(f"**Stratégie** : {header['strategy']}")
    if header["framework"] is not None:
        st.markdown(f"**Framework** : {header['framework']}")
with col2:
    st.markdown(f"**Symbole** : {header['symbol']}")
    st.markdown(f"**Timeframe** : {header['timeframe']}")
    st.markdown(f"**Période** : {header['period']}")
with col3:
    st.markdown(f"**Seed** : {header['seed']}")
    st.markdown(f"**Folds** : {header['n_folds']}")

st.divider()

# ---------------------------------------------------------------------------
# §6.2 — KPI cards
# ---------------------------------------------------------------------------

cards = build_kpi_cards(metrics, config_snapshot)

kpi_cols = st.columns(len(cards))
for col, card in zip(kpi_cols, cards, strict=True):
    with col:
        color = card["color"]
        if color is not None:
            st.markdown(
                f"<h4 style='color:{color}'>{card['value']}</h4>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"<h4>{card['value']}</h4>", unsafe_allow_html=True)
        st.caption(card["label"])

st.divider()

# ---------------------------------------------------------------------------
# §6.3 — Equity curve stitchée
# ---------------------------------------------------------------------------

equity_df = load_equity_curve(run_dir)

if equity_df is None:
    st.info("Equity curve non disponible pour ce run (equity_curve.csv absent).")
else:
    first_equity = equity_df["equity"].iloc[0]
    if first_equity <= 0:
        st.error(
            f"Equity curve invalide : equity[0] = {first_equity} (≤ 0). "
            "Normalisation impossible."
        )
    else:
        fig_eq = chart_equity_curve(
            equity_df,
            fold_boundaries=True,
            drawdown=True,
            in_trade_zones=True,
        )
        st.plotly_chart(fig_eq, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# §6.4 — Métriques par fold
# ---------------------------------------------------------------------------

st.subheader("Métriques par fold")

fold_table = build_fold_metrics_table(metrics)

if not fold_table.empty:
    st.dataframe(fold_table, use_container_width=True, hide_index=True)

    pnl_bar_data = build_pnl_bar_data(metrics)
    if pnl_bar_data:
        fig_pnl = chart_pnl_bar(pnl_bar_data)
        st.plotly_chart(fig_pnl, use_container_width=True)
else:
    st.info("Aucune donnée de fold disponible.")

st.divider()

# ---------------------------------------------------------------------------
# §6.5 — Distribution des trades
# ---------------------------------------------------------------------------

st.subheader("Distribution des trades")

trades_df = load_trades(run_dir)

if trades_df is None or trades_df.empty:
    st.info("Trades non disponibles pour ce run (trades.csv absent).")
else:
    # Histogram and box plot side by side
    col_hist, col_box = st.columns(2)
    with col_hist:
        fig_hist = chart_returns_histogram(trades_df)
        st.plotly_chart(fig_hist, use_container_width=True)
    with col_box:
        fig_box = chart_returns_boxplot(trades_df)
        st.plotly_chart(fig_box, use_container_width=True)

    # Statistics
    stats = compute_trade_stats(trades_df)
    stat_cols = st.columns(6)
    stat_labels = [
        ("Mean", format_float(stats["mean"], decimals=4)),
        ("Median", format_float(stats["median"], decimals=4)),
        ("Std", format_float(stats["std"], decimals=4)),
        ("Skewness", format_float(stats["skewness"], decimals=4)),
        ("Best Trade", format_pct(stats["best_trade"], decimals=2)),
        ("Worst Trade", format_pct(stats["worst_trade"], decimals=2)),
    ]
    for col, (label, value) in zip(stat_cols, stat_labels, strict=True):
        with col:
            st.metric(label=label, value=value)

st.divider()

# ---------------------------------------------------------------------------
# §6.6 — Journal des trades
# ---------------------------------------------------------------------------

st.subheader("Journal des trades")

if trades_df is None or trades_df.empty:
    st.info("Trades non disponibles pour ce run (trades.csv absent).")
else:
    # Filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        fold_options = ["Tous"] + sorted(trades_df["fold"].unique().tolist())
        selected_fold = st.selectbox("Fold", fold_options, key="journal_fold")

    with filter_col2:
        sign_options = ["Tous", "Gagnant", "Perdant"]
        selected_sign = st.radio("Signe", sign_options, horizontal=True, key="journal_sign")

    with filter_col3:
        entry_times = pd.to_datetime(trades_df["entry_time_utc"])
        min_date = entry_times.min().date()
        max_date = entry_times.max().date()
        date_range = st.date_input(
            "Période",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="journal_dates",
        )

    # Apply filters
    fold_filter = None if selected_fold == "Tous" else selected_fold
    sign_filter = None
    if selected_sign == "Gagnant":
        sign_filter = "winning"
    elif selected_sign == "Perdant":
        sign_filter = "losing"

    date_start = None
    date_end = None
    if isinstance(date_range, tuple) and len(date_range) == 2:
        date_start = pd.Timestamp(date_range[0])
        date_end = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    filtered_trades = filter_trades(
        trades_df,
        fold=fold_filter,
        sign=sign_filter,
        date_start=date_start,
        date_end=date_end,
    )

    # Build journal
    journal = build_trade_journal(filtered_trades, equity_df)

    # Pagination
    total_rows = len(journal)
    page_size = 50
    total_pages = max(1, math.ceil(total_rows / page_size))

    st.caption(f"{total_rows} trades — {total_pages} page(s)")

    if total_rows > 0:
        current_page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1,
            key="journal_page",
        )
        page_df = paginate_dataframe(journal, page=current_page, page_size=page_size)
        st.dataframe(page_df, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun trade ne correspond aux filtres sélectionnés.")
