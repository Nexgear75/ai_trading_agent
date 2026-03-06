"""Page 3 — Comparaison de runs (Comparison).

Comparaison côte à côte de plusieurs runs : tableau comparatif de métriques
avec surbrillance meilleur/pire, critères pipeline §14.4, warnings.

Ref: §7.1 multiselect, §7.2 tableau comparatif, §10.2 — pages/3_comparison.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from scripts.dashboard.charts import chart_equity_overlay, chart_radar
from scripts.dashboard.data_loader import load_config_snapshot
from scripts.dashboard.pages.comparison_logic import (
    apply_highlight_styles,
    build_comparison_dataframe,
    build_radar_data,
    check_pipeline_criteria,
    format_run_label,
    get_aggregate_notes,
    highlight_best_worst,
    load_comparison_equity_curves,
)
from scripts.dashboard.pages.overview_logic import format_overview_dataframe

# ---------------------------------------------------------------------------
# Page rendering
# ---------------------------------------------------------------------------

st.header("Comparaison de runs")

# Retrieve runs from session state (populated by app.py)
if "runs" not in st.session_state or st.session_state["runs"] is None:
    st.error("Aucun run chargé. Vérifiez la configuration du répertoire runs.")
    st.stop()

runs: list[dict] = st.session_state["runs"]

if not runs:
    st.info("Aucun run trouvé dans le répertoire.")
    st.stop()

# ---------------------------------------------------------------------------
# §7.1 — Multiselect: 2-10 runs with strategy name
# ---------------------------------------------------------------------------

# Build label → metrics mapping (§R6: guard against duplicate keys)
label_to_metrics: dict[str, dict] = {}
for m in runs:
    label = format_run_label(m)
    if label in label_to_metrics:
        raise ValueError(f"Duplicate run label: {label}")
    label_to_metrics[label] = m

selected_labels = st.sidebar.multiselect(
    "Runs à comparer (2-10)",
    options=sorted(label_to_metrics.keys()),
    default=[],
    max_selections=10,
)

if len(selected_labels) < 2:
    st.info("Sélectionnez au moins 2 runs dans la sidebar pour lancer la comparaison.")
    st.stop()

selected_runs = [label_to_metrics[label] for label in selected_labels]

# ---------------------------------------------------------------------------
# §7.2 — Comparative table
# ---------------------------------------------------------------------------

df_raw = build_comparison_dataframe(selected_runs)
highlights = highlight_best_worst(df_raw)

# Format for display (§9.3) — reuses overview formatting (DRY)
df_formatted = format_overview_dataframe(df_raw)

# §7.2 — Apply bold green / italic red highlighting via pandas Styler
st.subheader("Tableau comparatif")
styled = df_formatted.style.apply(
    lambda frame: apply_highlight_styles(frame, highlights),
    axis=None,
)
st.dataframe(
    styled,
    use_container_width=True,
    hide_index=True,
)
st.caption(
    "Meilleure valeur par colonne en **gras vert**, "
    "pire en *italique rouge* (§7.2)."
)

# ---------------------------------------------------------------------------
# §14.4 — Pipeline criteria check (✅/❌)
# ---------------------------------------------------------------------------

st.subheader("Conformité pipeline (§14.4)")

runs_dir = st.session_state.get("runs_dir")

for m in selected_runs:
    run_id = m["run_id"]

    # Try to load config_snapshot for MDD cap
    config_snapshot: dict | None = None
    if runs_dir is not None:
        run_path = Path(runs_dir) / run_id
        try:
            config_snapshot = load_config_snapshot(run_path)
        except (FileNotFoundError, ValueError):
            config_snapshot = None

    criteria = check_pipeline_criteria(m, config_snapshot)

    # Build criteria display line
    pnl_display = "✅" if criteria["pnl_ok"] else "❌"
    pf_display = "✅" if criteria["pf_ok"] else "❌"
    if criteria["mdd_ok"] is None:
        mdd_display = "—"
    elif criteria["mdd_ok"]:
        mdd_display = "✅"
    else:
        mdd_display = "❌"

    st.markdown(
        f"**{run_id}** {criteria['icon']} — "
        f"PnL: {pnl_display} · PF: {pf_display} · MDD: {mdd_display}"
    )

    # §7.2 — Display aggregate.notes if present
    notes = get_aggregate_notes(m)
    if notes:
        st.warning(f"⚠️ {run_id}: {notes}")

# ---------------------------------------------------------------------------
# §7.3 — Equity curves overlay
# ---------------------------------------------------------------------------

st.subheader("Courbes d'équité superposées (§7.3)")

if runs_dir is not None:
    curves, missing_labels = load_comparison_equity_curves(
        selected_runs, Path(runs_dir)
    )

    if missing_labels:
        st.info(
            "Equity curves absentes pour : "
            + ", ".join(missing_labels)
        )

    if curves:
        fig_overlay = chart_equity_overlay(curves)
        st.plotly_chart(fig_overlay, use_container_width=True)
    else:
        st.info("Aucune equity curve disponible pour les runs sélectionnés.")
else:
    st.warning("Répertoire de runs non configuré.")

# ---------------------------------------------------------------------------
# §7.4 — Radar chart
# ---------------------------------------------------------------------------

st.subheader("Radar comparatif (§7.4)")

radar_data = build_radar_data(selected_runs)
fig_radar = chart_radar(radar_data)
st.plotly_chart(fig_radar, use_container_width=True)
