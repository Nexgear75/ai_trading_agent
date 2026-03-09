"""Page 3 — Comparaison de runs (Comparison).

Comparaison côte à côte de plusieurs runs : tableau comparatif de métriques
avec surbrillance meilleur/pire et vérification du critère §14.4.

Ref: §10.2 — pages/3_comparison.py, §7.1 multiselect, §7.2 tableau comparatif.
"""

from __future__ import annotations

import html as html_mod
import logging
from pathlib import Path

import pandas as pd
import streamlit as st

from scripts.dashboard.charts import chart_equity_overlay, chart_radar
from scripts.dashboard.data_loader import load_config_snapshot
from scripts.dashboard.pages.comparison_logic import (
    build_comparison_dataframe,
    build_equity_overlay_curves,
    build_radar_data,
    check_criterion_14_4,
    format_comparison_dataframe,
    get_aggregate_notes,
    highlight_best_worst,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page rendering
# ---------------------------------------------------------------------------

st.header("Comparaison de runs")

# Retrieve runs and runs_dir from session state (populated by app.py)
if "runs" not in st.session_state or st.session_state["runs"] is None:
    st.error("Aucun run chargé. Vérifiez la configuration du répertoire runs.")
    st.stop()

runs: list[dict] = st.session_state["runs"]
runs_dir = st.session_state.get("runs_dir")

if not runs:
    st.info("Aucun run trouvé dans le répertoire (ou uniquement des runs dummy exclus).")
    st.stop()

# ---------------------------------------------------------------------------
# §7.1 — Multiselect in sidebar (2-10 runs)
# ---------------------------------------------------------------------------

run_labels = {
    f"{m['strategy']['name']} ({m['run_id']})": m
    for m in runs
}

selected_labels = st.sidebar.multiselect(
    "Sélectionner des runs à comparer (2-10)",
    options=sorted(run_labels.keys()),
    max_selections=10,
)

if len(selected_labels) < 2:
    st.info("Sélectionnez au moins 2 runs dans la sidebar pour lancer la comparaison.")
    st.stop()

selected_runs = [run_labels[label] for label in selected_labels]

# ---------------------------------------------------------------------------
# §7.2 — Comparison table
# ---------------------------------------------------------------------------

df_raw = build_comparison_dataframe(selected_runs)
highlights = highlight_best_worst(df_raw)
df_formatted = format_comparison_dataframe(df_raw)

# ---------------------------------------------------------------------------
# §14.4 — Criterion check (✅/❌)
# ---------------------------------------------------------------------------

criterion_results: list[str] = []
for m in selected_runs:
    run_id = m["run_id"]
    config_snapshot = None
    if runs_dir is not None:
        run_path = Path(runs_dir) / run_id
        try:
            config_snapshot = load_config_snapshot(run_path)
        except FileNotFoundError:
            logger.warning(
                "config_snapshot.yaml absent pour le run %s — "
                "impossible de vérifier le seuil MDD",
                run_id,
            )

    passed = check_criterion_14_4(m, config_snapshot)
    criterion_results.append("✅" if passed else "❌")

df_formatted.insert(0, "§14.4", criterion_results)

# ---------------------------------------------------------------------------
# Display table with highlight styling
# ---------------------------------------------------------------------------


def _style_cell(row_idx: int, col: str, value: str) -> str:
    """Return styled markdown for a cell based on highlight info."""
    col_info = highlights.get(col)
    if col_info is None:
        return value
    if col_info["best"] is None:
        return value
    if row_idx == col_info["best"] and col_info["best"] != col_info["worst"]:
        return f"**:green[{value}]**"
    if row_idx == col_info["worst"] and col_info["best"] != col_info["worst"]:
        return f"*:red[{value}]*"
    return value


# Build styled display rows
styled_rows = []
for idx in range(len(df_formatted)):
    row = {}
    for col in df_formatted.columns:
        val = html_mod.escape(str(df_formatted.iloc[idx][col]))
        if col in highlights:
            val = _style_cell(idx, col, val)
        row[col] = val
    styled_rows.append(row)

df_styled = pd.DataFrame(styled_rows)
st.markdown(df_styled.to_markdown(index=False), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# §7.2 — Notes/warnings display
# ---------------------------------------------------------------------------

for m in selected_runs:
    notes = get_aggregate_notes(m)
    if notes is not None:
        st.warning(f"⚠️ **{m['run_id']}** : {notes}")

# ---------------------------------------------------------------------------
# §7.3 — Equity overlay
# ---------------------------------------------------------------------------

st.divider()

if runs_dir is not None:
    curves, missing_runs = build_equity_overlay_curves(selected_runs, Path(runs_dir))
    if missing_runs:
        st.info(f"Equity curves absentes pour : {', '.join(missing_runs)}")
    if curves:
        fig_overlay = chart_equity_overlay(curves)
        st.plotly_chart(fig_overlay, use_container_width=True)
    else:
        st.info("Aucune equity curve disponible pour les runs sélectionnés.")
else:
    st.info("Aucune equity curve disponible pour les runs sélectionnés.")

# ---------------------------------------------------------------------------
# §7.4 — Radar chart
# ---------------------------------------------------------------------------

st.divider()

radar_data = build_radar_data(selected_runs)
if radar_data:
    fig_radar = chart_radar(radar_data)
    st.plotly_chart(fig_radar, use_container_width=True)
