"""Page 4 — Analyse par fold (Fold Analysis).

Analyse détaillée fold par fold : distribution des métriques,
stabilité inter-folds, identification des folds problématiques.

Ref: §10.2 — pages/4_fold_analysis.py, §8.1 navigation, §8.2 equity curve.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from scripts.dashboard.charts import chart_fold_equity
from scripts.dashboard.data_loader import load_fold_equity_curve, load_fold_trades
from scripts.dashboard.pages.fold_analysis_logic import (
    build_run_selector_options,
    discover_folds,
    get_run_dir,
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

runs: list[dict] = st.session_state.get("runs", [])
runs_dir: Path | None = st.session_state.get("runs_dir")

if not runs or runs_dir is None:
    st.error("Aucun run disponible. Vérifiez le répertoire des runs.")
    st.stop()

# ---------------------------------------------------------------------------
# §8.1 — Run selector
# ---------------------------------------------------------------------------

run_options = build_run_selector_options(runs)
run_labels = [label for label, _ in run_options]
run_id_map = {label: run_id for label, run_id in run_options}

selected_label = st.selectbox("Sélectionner un run", run_labels)

if selected_label is None:
    st.warning("Veuillez sélectionner un run.")
    st.stop()

selected_run_id = run_id_map[selected_label]
run_dir = get_run_dir(runs_dir, selected_run_id)

# ---------------------------------------------------------------------------
# §8.1 — Fold selector (dropdown + slider)
# ---------------------------------------------------------------------------

fold_names = discover_folds(run_dir)

if not fold_names:
    st.info("Aucun fold trouvé pour ce run.")
    st.stop()

col_dropdown, col_slider = st.columns(2)

with col_dropdown:
    selected_fold = st.selectbox("Sélectionner un fold", fold_names)

with col_slider:
    fold_index = st.slider(
        "Navigation rapide",
        min_value=0,
        max_value=len(fold_names) - 1,
        value=fold_names.index(selected_fold),
    )

# Sync: slider overrides dropdown if different
if fold_names[fold_index] != selected_fold:
    selected_fold = fold_names[fold_index]

fold_dir = run_dir / "folds" / selected_fold

# ---------------------------------------------------------------------------
# §8.2 — Fold equity curve
# ---------------------------------------------------------------------------

equity_df = load_fold_equity_curve(fold_dir)

if equity_df is None:
    st.info(f"Pas de fichier equity_curve.csv pour {selected_fold}.")
    st.stop()

trades_df = load_fold_trades(fold_dir)

if trades_df is None:
    trades_df = pd.DataFrame(columns=["entry_time_utc", "exit_time_utc"])

fig = chart_fold_equity(equity_df, trades_df)
st.plotly_chart(fig, use_container_width=True)
