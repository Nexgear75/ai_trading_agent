"""Page 1 — Vue d'ensemble (Overview).

Affiche la liste des runs disponibles avec métriques clés,
tableau récapitulatif et filtres par modèle/date.

Ref: §10.2 — pages/1_overview.py
"""

from __future__ import annotations

import streamlit as st

from scripts.dashboard.pages.overview_logic import (
    build_overview_dataframe,
    build_warnings_mask,
    filter_by_strategy,
    filter_by_type,
    format_overview_dataframe,
    get_unique_strategies,
)

# ---------------------------------------------------------------------------
# Page rendering
# ---------------------------------------------------------------------------

st.header("Vue d'ensemble des runs")

# Retrieve runs from session state (populated by app.py)
if "runs" not in st.session_state or st.session_state["runs"] is None:
    st.error("Aucun run chargé. Vérifiez la configuration du répertoire runs.")
    st.stop()

runs: list[dict] = st.session_state["runs"]

if not runs:
    st.info("Aucun run trouvé dans le répertoire (ou uniquement des runs dummy exclus).")
    st.stop()

# Build raw DataFrame
df_raw = build_overview_dataframe(runs)

# Warnings mask (for tooltip indicators)
warnings_mask = build_warnings_mask(runs)

# ---------------------------------------------------------------------------
# Filters (§5.3)
# ---------------------------------------------------------------------------

col_filter_type, col_filter_strat = st.columns(2)

with col_filter_type:
    type_filter = st.selectbox(
        "Filtrer par type",
        options=["Tous", "Modèles", "Baselines"],
        index=0,
    )

with col_filter_strat:
    available_strategies = get_unique_strategies(df_raw)
    strategy_filter = st.multiselect(
        "Filtrer par stratégie",
        options=available_strategies,
        default=[],
    )

# Apply filters
df_filtered = filter_by_type(df_raw, type_filter)
df_filtered = filter_by_strategy(df_filtered, strategy_filter)

if df_filtered.empty:
    st.info("Aucun run ne correspond aux filtres sélectionnés.")
    st.stop()

# ---------------------------------------------------------------------------
# Warning indicators — add ⚠️ to Run IDs with warnings
# ---------------------------------------------------------------------------

# Build a set of run_ids that have warnings
warning_run_ids = set()
for m, has_warn in zip(runs, warnings_mask, strict=True):
    if has_warn:
        warning_run_ids.add(m["run_id"])

# Create display DataFrame with warning indicators
df_display = df_filtered.copy()
df_display["Run ID"] = df_display["Run ID"].apply(
    lambda rid: f"⚠️ {rid}" if rid in warning_run_ids else rid
)

# Format for display (§9.3)
df_formatted = format_overview_dataframe(df_display)

# ---------------------------------------------------------------------------
# Table display with clickable rows (§5.2)
# ---------------------------------------------------------------------------

st.dataframe(
    df_formatted,
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------------------------------
# Row selection — click to navigate to Page 2
# ---------------------------------------------------------------------------

# Use selectbox for run selection (Streamlit dataframe click not natively supported)
run_ids = df_filtered["Run ID"].tolist()
selected_run = st.selectbox(
    "Sélectionner un run pour voir le détail",
    options=run_ids,
    index=None,
    placeholder="Cliquer pour sélectionner un run...",
)

if selected_run:
    st.session_state["selected_run_id"] = selected_run
    st.switch_page("scripts/dashboard/pages/2_run_detail.py")
