"""Page 2 — Détail d'un run (Run Detail).

Visualisation détaillée d'un run sélectionné : equity curve,
trade journal, métriques par fold, configuration utilisée.

Ref: §10.2 — pages/2_run_detail.py, §6.1 en-tête, §6.2 KPI cards,
     §6.3 equity curve, §6.4 métriques par fold.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from scripts.dashboard.charts import chart_equity_curve, chart_pnl_bar
from scripts.dashboard.data_loader import (
    load_config_snapshot,
    load_equity_curve,
    load_run_manifest,
    load_run_metrics,
)
from scripts.dashboard.pages.run_detail_logic import (
    build_fold_metrics_table,
    build_header_info,
    build_kpi_cards,
    build_pnl_bar_data,
)

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
