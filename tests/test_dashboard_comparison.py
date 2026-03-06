"""Tests for scripts/dashboard/pages/comparison_logic.py — comparison table.

Task #083 — WS-D-4: Page 3 — sélection runs et tableau comparatif.
Spec refs: §7.1 multiselect, §7.2 tableau comparatif, §14.4 critères pipeline.

Tests cover:
- build_comparison_dataframe: construction from multiple runs
- highlight_best_worst: detection of best/worst per column
- check_pipeline_criteria: ✅/❌ with all pass, some fail, config absent
- get_aggregate_notes: extraction of notes from metrics
- format_run_label: strategy name alongside run ID
- edge cases: empty, single run, None values
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Helpers — synthetic metrics dicts
# ---------------------------------------------------------------------------


def _make_metrics(
    *,
    run_id: str = "20260301_120000_xgboost",
    strategy_name: str = "xgboost_reg",
    strategy_type: str = "model",
    n_folds: int = 3,
    net_pnl: float | None = 0.0345,
    sharpe: float | None = 1.23,
    max_drawdown: float | None = -0.05,
    hit_rate: float | None = 0.552,
    n_trades: float | None = 42.0,
    profit_factor: float | None = 1.5,
    notes: str | None = None,
) -> dict:
    """Build a minimal valid metrics dict matching discover_runs() output."""
    trading_mean: dict = {
        "net_pnl": net_pnl,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "hit_rate": hit_rate,
        "n_trades": n_trades,
        "profit_factor": profit_factor,
    }

    agg: dict = {
        "trading": {
            "mean": trading_mean,
        },
    }
    if notes is not None:
        agg["notes"] = notes

    folds = [{"fold_id": f"fold_{i:02d}"} for i in range(n_folds)]

    return {
        "run_id": run_id,
        "strategy": {
            "name": strategy_name,
            "strategy_type": strategy_type,
        },
        "aggregate": agg,
        "folds": folds,
    }


# ---------------------------------------------------------------------------
# §7.2 — build_comparison_dataframe
# ---------------------------------------------------------------------------


class TestBuildComparisonDataframe:
    """#083 — Build comparison DataFrame from selected run metrics (§7.2)."""

    def test_two_runs_columns(self) -> None:
        """#083 — DataFrame has all §5.2 columns."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
        )

        runs = [
            _make_metrics(run_id="run_001", strategy_name="xgboost_reg"),
            _make_metrics(run_id="run_002", strategy_name="sma_rule"),
        ]
        df = build_comparison_dataframe(runs)
        expected_cols = {
            "Run ID",
            "Stratégie",
            "Type",
            "Folds",
            "Net PnL (moy)",
            "Sharpe (moy)",
            "MDD (moy)",
            "Win Rate (moy)",
            "Trades (moy)",
        }
        assert set(df.columns) == expected_cols

    def test_two_runs_row_count(self) -> None:
        """#083 — Two runs produce two rows."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
        )

        runs = [
            _make_metrics(run_id="run_001"),
            _make_metrics(run_id="run_002"),
        ]
        df = build_comparison_dataframe(runs)
        assert len(df) == 2

    def test_values_extracted_correctly(self) -> None:
        """#083 — Metric values are correctly extracted."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
        )

        runs = [
            _make_metrics(
                run_id="run_001",
                strategy_name="xgboost_reg",
                net_pnl=0.05,
                sharpe=1.5,
                max_drawdown=-0.03,
            ),
        ]
        df = build_comparison_dataframe(runs)
        row = df.iloc[0]
        assert row["Run ID"] == "run_001"
        assert row["Stratégie"] == "xgboost_reg"
        assert row["Net PnL (moy)"] == pytest.approx(0.05)
        assert row["Sharpe (moy)"] == pytest.approx(1.5)
        assert row["MDD (moy)"] == pytest.approx(-0.03)

    def test_empty_runs_list(self) -> None:
        """#083 — Empty list produces empty DataFrame with correct columns."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
        )

        df = build_comparison_dataframe([])
        assert len(df) == 0
        assert "Run ID" in df.columns


# ---------------------------------------------------------------------------
# §7.2 — highlight_best_worst
# ---------------------------------------------------------------------------

# Numeric columns where highlighting applies
_HIGHLIGHT_COLS = [
    "Net PnL (moy)",
    "Sharpe (moy)",
    "MDD (moy)",
    "Win Rate (moy)",
    "Trades (moy)",
]


class TestHighlightBestWorst:
    """#083 — Detect best (green) and worst (red) per column (§7.2)."""

    def test_basic_best_worst(self) -> None:
        """#083 — Identifies best and worst indices in numeric columns."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
            highlight_best_worst,
        )

        # Note: build_comparison_dataframe sorts by Run ID descending.
        # run_B > run_A alphabetically → idx 0=run_B, idx 1=run_A.
        runs = [
            _make_metrics(
                run_id="run_A",
                net_pnl=0.10,
                sharpe=2.0,
                max_drawdown=-0.02,
                hit_rate=0.6,
                n_trades=50.0,
            ),
            _make_metrics(
                run_id="run_B",
                net_pnl=0.02,
                sharpe=0.5,
                max_drawdown=-0.10,
                hit_rate=0.4,
                n_trades=20.0,
            ),
        ]
        df = build_comparison_dataframe(runs)
        result = highlight_best_worst(df)

        # After sort descending: idx 0=run_B, idx 1=run_A
        # Net PnL: higher is better → best=run_A(idx 1), worst=run_B(idx 0)
        assert result["Net PnL (moy)"]["best"] == 1
        assert result["Net PnL (moy)"]["worst"] == 0

        # Sharpe: higher is better
        assert result["Sharpe (moy)"]["best"] == 1
        assert result["Sharpe (moy)"]["worst"] == 0

        # MDD: lower abs value is better.
        # run_A: -0.02, run_B: -0.10. Lower value = worse (more drawdown).
        # idx 1=run_A(-0.02) is best (less drawdown), idx 0=run_B(-0.10) worst.
        assert result["MDD (moy)"]["best"] == 1
        assert result["MDD (moy)"]["worst"] == 0

        # Win Rate: higher is better
        assert result["Win Rate (moy)"]["best"] == 1
        assert result["Win Rate (moy)"]["worst"] == 0

        # Trades: higher is better
        assert result["Trades (moy)"]["best"] == 1
        assert result["Trades (moy)"]["worst"] == 0

    def test_three_runs_best_worst(self) -> None:
        """#083 — With 3 runs, best/worst correctly identified."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
            highlight_best_worst,
        )

        # Sorted descending: r3(idx 0), r2(idx 1), r1(idx 2)
        runs = [
            _make_metrics(run_id="r1", net_pnl=0.05),
            _make_metrics(run_id="r2", net_pnl=0.10),
            _make_metrics(run_id="r3", net_pnl=-0.02),
        ]
        df = build_comparison_dataframe(runs)
        result = highlight_best_worst(df)

        # net_pnl: best=r2(0.10) at idx 1, worst=r3(-0.02) at idx 0
        assert result["Net PnL (moy)"]["best"] == 1  # r2
        assert result["Net PnL (moy)"]["worst"] == 0  # r3

    def test_only_numeric_columns_in_result(self) -> None:
        """#083 — Result only contains numeric columns, not Run ID/Stratégie/Type."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
            highlight_best_worst,
        )

        runs = [
            _make_metrics(run_id="r1"),
            _make_metrics(run_id="r2"),
        ]
        df = build_comparison_dataframe(runs)
        result = highlight_best_worst(df)

        assert "Run ID" not in result
        assert "Stratégie" not in result
        assert "Type" not in result
        for col in _HIGHLIGHT_COLS:
            assert col in result

    def test_nan_values_excluded(self) -> None:
        """#083 — NaN values do not cause errors in best/worst detection."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
            highlight_best_worst,
        )

        # Sorted descending: r2(idx 0), r1(idx 1)
        runs = [
            _make_metrics(run_id="r1", net_pnl=0.05),
            _make_metrics(run_id="r2", net_pnl=None),
        ]
        df = build_comparison_dataframe(runs)
        result = highlight_best_worst(df)

        # Only one valid value (r1 at idx 1) → best and worst are both idx 1
        assert result["Net PnL (moy)"]["best"] == 1
        assert result["Net PnL (moy)"]["worst"] == 1

    def test_single_run_best_equals_worst(self) -> None:
        """#083 — With a single run, best == worst for all columns."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
            highlight_best_worst,
        )

        runs = [_make_metrics(run_id="r1")]
        df = build_comparison_dataframe(runs)
        result = highlight_best_worst(df)

        for col in _HIGHLIGHT_COLS:
            assert result[col]["best"] == result[col]["worst"]


# ---------------------------------------------------------------------------
# §14.4 — check_pipeline_criteria
# ---------------------------------------------------------------------------


class TestCheckPipelineCriteria:
    """#083 — Pipeline conformity check ✅/❌ per run (§14.4)."""

    def test_all_criteria_pass(self) -> None:
        """#083 — All criteria pass → ✅."""
        from scripts.dashboard.pages.comparison_logic import (
            check_pipeline_criteria,
        )

        metrics = _make_metrics(
            net_pnl=0.05,
            profit_factor=1.5,
            max_drawdown=-0.03,
        )
        config_snapshot = {"thresholding": {"mdd_cap": 0.10}}

        result = check_pipeline_criteria(metrics, config_snapshot)
        assert result["pnl_ok"] is True
        assert result["pf_ok"] is True
        assert result["mdd_ok"] is True
        assert result["icon"] == "✅"

    def test_negative_pnl_fails(self) -> None:
        """#083 — Negative PnL → ❌."""
        from scripts.dashboard.pages.comparison_logic import (
            check_pipeline_criteria,
        )

        metrics = _make_metrics(
            net_pnl=-0.02,
            profit_factor=1.5,
            max_drawdown=-0.03,
        )
        config_snapshot = {"thresholding": {"mdd_cap": 0.10}}

        result = check_pipeline_criteria(metrics, config_snapshot)
        assert result["pnl_ok"] is False
        assert result["icon"] == "❌"

    def test_profit_factor_below_one_fails(self) -> None:
        """#083 — Profit factor < 1.0 → ❌."""
        from scripts.dashboard.pages.comparison_logic import (
            check_pipeline_criteria,
        )

        metrics = _make_metrics(
            net_pnl=0.05,
            profit_factor=0.8,
            max_drawdown=-0.03,
        )
        config_snapshot = {"thresholding": {"mdd_cap": 0.10}}

        result = check_pipeline_criteria(metrics, config_snapshot)
        assert result["pf_ok"] is False
        assert result["icon"] == "❌"

    def test_mdd_exceeds_cap_fails(self) -> None:
        """#083 — MDD exceeds cap → ❌."""
        from scripts.dashboard.pages.comparison_logic import (
            check_pipeline_criteria,
        )

        # max_drawdown is stored as a positive magnitude (0.079 = 7.9%)
        # mdd_cap is 0.05 = 5%
        # abs(max_drawdown) >= mdd_cap → fail
        metrics = _make_metrics(
            net_pnl=0.05,
            profit_factor=1.5,
            max_drawdown=0.08,
        )
        config_snapshot = {"thresholding": {"mdd_cap": 0.05}}

        result = check_pipeline_criteria(metrics, config_snapshot)
        assert result["mdd_ok"] is False
        assert result["icon"] == "❌"

    def test_config_snapshot_absent(self) -> None:
        """#083 — No config_snapshot → MDD criterion is None (shown as '—')."""
        from scripts.dashboard.pages.comparison_logic import (
            check_pipeline_criteria,
        )

        metrics = _make_metrics(
            net_pnl=0.05,
            profit_factor=1.5,
            max_drawdown=-0.03,
        )

        result = check_pipeline_criteria(metrics, None)
        assert result["pnl_ok"] is True
        assert result["pf_ok"] is True
        assert result["mdd_ok"] is None
        assert result["icon"] == "❌"  # Cannot confirm all criteria

    def test_config_snapshot_missing_mdd_cap(self) -> None:
        """#083 — config_snapshot without thresholding.mdd_cap → MDD None."""
        from scripts.dashboard.pages.comparison_logic import (
            check_pipeline_criteria,
        )

        metrics = _make_metrics(
            net_pnl=0.05,
            profit_factor=1.5,
            max_drawdown=-0.03,
        )
        config_snapshot: dict = {"thresholding": {}}

        result = check_pipeline_criteria(metrics, config_snapshot)
        assert result["mdd_ok"] is None

    def test_pnl_exactly_zero_fails(self) -> None:
        """#083 — PnL exactly 0 fails (criterion is >0, not >=0)."""
        from scripts.dashboard.pages.comparison_logic import (
            check_pipeline_criteria,
        )

        metrics = _make_metrics(net_pnl=0.0, profit_factor=1.5, max_drawdown=-0.01)
        config_snapshot = {"thresholding": {"mdd_cap": 0.10}}

        result = check_pipeline_criteria(metrics, config_snapshot)
        assert result["pnl_ok"] is False

    def test_profit_factor_exactly_one_fails(self) -> None:
        """#083 — Profit factor exactly 1.0 fails (criterion is >1.0)."""
        from scripts.dashboard.pages.comparison_logic import (
            check_pipeline_criteria,
        )

        metrics = _make_metrics(net_pnl=0.05, profit_factor=1.0, max_drawdown=-0.01)
        config_snapshot = {"thresholding": {"mdd_cap": 0.10}}

        result = check_pipeline_criteria(metrics, config_snapshot)
        assert result["pf_ok"] is False

    def test_none_net_pnl_fails(self) -> None:
        """#083 — None net_pnl → pnl_ok is False."""
        from scripts.dashboard.pages.comparison_logic import (
            check_pipeline_criteria,
        )

        metrics = _make_metrics(net_pnl=None, profit_factor=1.5, max_drawdown=-0.01)
        config_snapshot = {"thresholding": {"mdd_cap": 0.10}}

        result = check_pipeline_criteria(metrics, config_snapshot)
        assert result["pnl_ok"] is False

    def test_none_profit_factor_fails(self) -> None:
        """#083 — None profit_factor → pf_ok is False."""
        from scripts.dashboard.pages.comparison_logic import (
            check_pipeline_criteria,
        )

        metrics = _make_metrics(net_pnl=0.05, profit_factor=None, max_drawdown=-0.01)
        config_snapshot = {"thresholding": {"mdd_cap": 0.10}}

        result = check_pipeline_criteria(metrics, config_snapshot)
        assert result["pf_ok"] is False


# ---------------------------------------------------------------------------
# §7.2 — get_aggregate_notes
# ---------------------------------------------------------------------------


class TestGetAggregateNotes:
    """#083 — Extract aggregate.notes from metrics (§7.2)."""

    def test_notes_present(self) -> None:
        """#083 — Returns notes string when present."""
        from scripts.dashboard.pages.comparison_logic import get_aggregate_notes

        metrics = _make_metrics(notes="MDD exceeds cap")
        assert get_aggregate_notes(metrics) == "MDD exceeds cap"

    def test_notes_absent(self) -> None:
        """#083 — Returns None when notes key absent."""
        from scripts.dashboard.pages.comparison_logic import get_aggregate_notes

        metrics = _make_metrics(notes=None)
        assert get_aggregate_notes(metrics) is None

    def test_notes_empty_string(self) -> None:
        """#083 — Returns None when notes is empty string."""
        from scripts.dashboard.pages.comparison_logic import get_aggregate_notes

        metrics = _make_metrics(notes="")
        assert get_aggregate_notes(metrics) is None


# ---------------------------------------------------------------------------
# §7.1 — format_run_label
# ---------------------------------------------------------------------------


class TestFormatRunLabel:
    """#083 — Run label = run_id + strategy name for multiselect (§7.1)."""

    def test_label_format(self) -> None:
        """#083 — Label shows run_id and strategy name."""
        from scripts.dashboard.pages.comparison_logic import format_run_label

        metrics = _make_metrics(
            run_id="20260301_120000_xgb",
            strategy_name="xgboost_reg",
        )
        label = format_run_label(metrics)
        assert "20260301_120000_xgb" in label
        assert "xgboost_reg" in label
