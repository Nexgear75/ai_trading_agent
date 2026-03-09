"""Page 4 — Analyse par fold (Fold Analysis).

Navigation fold par fold : sélection d'un run puis d'un fold,
equity curve du fold avec marqueurs entry/exit et drawdown.

Ref: §10.2 — pages/4_fold_analysis.py, §8.1 sélection, §8.2 equity.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from scripts.dashboard.charts import chart_fold_equity
from scripts.dashboard.data_loader import (
    load_fold_equity_curve,
    load_fold_trades,
    load_run_metrics,
)
from scripts.dashboard.pages.fold_analysis_logic import (
    add_drawdown_to_figure,
    build_fold_selector_options,
    get_fold_dir,
)

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
