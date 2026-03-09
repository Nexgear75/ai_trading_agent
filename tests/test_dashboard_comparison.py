"""Tests for scripts/dashboard/pages/comparison_logic.py — comparison table logic.

Task #083 — WS-D-4: Page 3 — sélection des runs et tableau comparatif.
Spec refs: §7.1 multiselect, §7.2 tableau comparatif, §9.3 conventions d'affichage.

Tests cover:
- build_comparison_dataframe: 0 runs, 1 run, 3 runs, None values
- highlight_best_worst: numeric columns, ties, single run, all None
- check_criterion_14_4: all pass, pnl fails, pf fails, mdd fails, missing mdd_cap, None metrics
- build_radar_data: normal, None values, single run
- get_aggregate_notes: present, absent, empty
- format_comparison_dataframe: formatting correctness
"""

from __future__ import annotations

import pandas as pd
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
    profit_factor: float | None = 1.8,
    notes: str | None = None,
) -> dict:
    """Build a minimal valid metrics dict matching discover_runs() output."""
    agg: dict = {
        "trading": {
            "mean": {
                "net_pnl": net_pnl,
                "sharpe": sharpe,
                "max_drawdown": max_drawdown,
                "hit_rate": hit_rate,
                "n_trades": n_trades,
                "profit_factor": profit_factor,
            },
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


def _make_config_snapshot(*, mdd_cap: float = -0.10) -> dict:
    """Build a minimal config_snapshot dict."""
    return {"thresholding": {"mdd_cap": mdd_cap}}


# ===========================================================================
# §7.2 — build_comparison_dataframe
# ===========================================================================


class TestBuildComparisonDataframe:
    """#083 — Build comparison DataFrame from selected runs (§7.2)."""

    def test_empty_runs(self) -> None:
        """#083 — Empty list returns empty DataFrame with correct columns."""
        from scripts.dashboard.pages.comparison_logic import build_comparison_dataframe

        df = build_comparison_dataframe([])
        assert df.empty
        assert "Run ID" in df.columns
        assert "Net PnL (moy)" in df.columns

    def test_single_run(self) -> None:
        """#083 — Single run produces one-row DataFrame."""
        from scripts.dashboard.pages.comparison_logic import build_comparison_dataframe

        runs = [_make_metrics(run_id="run_A", net_pnl=0.05)]
        df = build_comparison_dataframe(runs)
        assert len(df) == 1
        assert df.iloc[0]["Run ID"] == "run_A"
        assert df.iloc[0]["Net PnL (moy)"] == pytest.approx(0.05)

    def test_three_runs(self) -> None:
        """#083 — Three runs produce three rows with correct values."""
        from scripts.dashboard.pages.comparison_logic import build_comparison_dataframe

        runs = [
            _make_metrics(run_id="run_A", strategy_name="strat_a"),
            _make_metrics(run_id="run_B", strategy_name="strat_b"),
            _make_metrics(run_id="run_C", strategy_name="strat_c"),
        ]
        df = build_comparison_dataframe(runs)
        assert len(df) == 3
        assert set(df["Stratégie"]) == {"strat_a", "strat_b", "strat_c"}

    def test_none_values(self) -> None:
        """#083 — None metric values are preserved in the DataFrame."""
        from scripts.dashboard.pages.comparison_logic import build_comparison_dataframe

        runs = [_make_metrics(net_pnl=None, sharpe=None)]
        df = build_comparison_dataframe(runs)

        assert pd.isna(df.iloc[0]["Net PnL (moy)"])
        assert pd.isna(df.iloc[0]["Sharpe (moy)"])

    def test_columns_match_overview(self) -> None:
        """#083 — Comparison DF has same columns as overview DF (§5.2)."""
        from scripts.dashboard.pages.comparison_logic import build_comparison_dataframe
        from scripts.dashboard.pages.overview_logic import build_overview_dataframe

        runs = [_make_metrics()]
        df_comp = build_comparison_dataframe(runs)
        df_over = build_overview_dataframe(runs)
        assert list(df_comp.columns) == list(df_over.columns)


# ===========================================================================
# §7.2 — highlight_best_worst
# ===========================================================================


class TestHighlightBestWorst:
    """#083 — Highlight best/worst per numeric column (§7.2)."""

    def test_basic_highlight(self) -> None:
        """#083 — Best and worst indices identified for numeric columns."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
            highlight_best_worst,
        )

        # build_overview_dataframe sorts by Run ID descending → C(0), B(1), A(2)
        runs = [
            _make_metrics(run_id="A", net_pnl=0.10, sharpe=2.0, max_drawdown=-0.02),
            _make_metrics(run_id="B", net_pnl=0.05, sharpe=1.0, max_drawdown=-0.08),
            _make_metrics(run_id="C", net_pnl=-0.01, sharpe=0.5, max_drawdown=-0.15),
        ]
        df = build_comparison_dataframe(runs)
        result = highlight_best_worst(df)

        # After descending sort: idx0=C, idx1=B, idx2=A
        # Net PnL: higher is better → best=A(idx 2), worst=C(idx 0)
        assert result["Net PnL (moy)"]["best"] == 2
        assert result["Net PnL (moy)"]["worst"] == 0

        # Sharpe: higher is better → best=A(idx 2), worst=C(idx 0)
        assert result["Sharpe (moy)"]["best"] == 2
        assert result["Sharpe (moy)"]["worst"] == 0

        # MDD: higher value = better (closer to 0)
        # A=-0.02(idx2), B=-0.08(idx1), C=-0.15(idx0) → best=idx2, worst=idx0
        assert result["MDD (moy)"]["best"] == 2
        assert result["MDD (moy)"]["worst"] == 0

    def test_ties(self) -> None:
        """#083 — Ties return first occurrence index."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
            highlight_best_worst,
        )

        runs = [
            _make_metrics(run_id="A", net_pnl=0.10),
            _make_metrics(run_id="B", net_pnl=0.10),
        ]
        df = build_comparison_dataframe(runs)
        result = highlight_best_worst(df)
        # Both are equal; first index (0) for best, also 0 for worst
        assert result["Net PnL (moy)"]["best"] == 0
        assert result["Net PnL (moy)"]["worst"] == 0

    def test_single_run(self) -> None:
        """#083 — Single run: best == worst for all columns."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
            highlight_best_worst,
        )

        runs = [_make_metrics(run_id="solo")]
        df = build_comparison_dataframe(runs)
        result = highlight_best_worst(df)
        for col_info in result.values():
            assert col_info["best"] == col_info["worst"]

    def test_all_none(self) -> None:
        """#083 — All None values: best and worst are None."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
            highlight_best_worst,
        )

        runs = [
            _make_metrics(run_id="A", net_pnl=None, sharpe=None,
                          max_drawdown=None, hit_rate=None, n_trades=None),
            _make_metrics(run_id="B", net_pnl=None, sharpe=None,
                          max_drawdown=None, hit_rate=None, n_trades=None),
        ]
        df = build_comparison_dataframe(runs)
        result = highlight_best_worst(df)
        assert result["Net PnL (moy)"]["best"] is None
        assert result["Net PnL (moy)"]["worst"] is None


# ===========================================================================
# §7.2 — check_criterion_14_4
# ===========================================================================


class TestCheckCriterion144:
    """#083 — §14.4 criterion verification (P&L > 0, PF > 1.0, MDD < cap)."""

    def test_all_pass(self) -> None:
        """#083 — All criteria met → True."""
        from scripts.dashboard.pages.comparison_logic import check_criterion_14_4

        metrics = _make_metrics(net_pnl=0.05, profit_factor=1.5, max_drawdown=-0.03)
        config = _make_config_snapshot(mdd_cap=-0.10)
        assert check_criterion_14_4(metrics, config) is True

    def test_pnl_fails(self) -> None:
        """#083 — P&L net <= 0 → False."""
        from scripts.dashboard.pages.comparison_logic import check_criterion_14_4

        metrics = _make_metrics(net_pnl=-0.01, profit_factor=1.5, max_drawdown=-0.03)
        config = _make_config_snapshot(mdd_cap=-0.10)
        assert check_criterion_14_4(metrics, config) is False

    def test_pnl_zero_fails(self) -> None:
        """#083 — P&L net == 0 → False (strictly > 0 required)."""
        from scripts.dashboard.pages.comparison_logic import check_criterion_14_4

        metrics = _make_metrics(net_pnl=0.0, profit_factor=1.5, max_drawdown=-0.03)
        config = _make_config_snapshot(mdd_cap=-0.10)
        assert check_criterion_14_4(metrics, config) is False

    def test_profit_factor_fails(self) -> None:
        """#083 — profit_factor <= 1.0 → False."""
        from scripts.dashboard.pages.comparison_logic import check_criterion_14_4

        metrics = _make_metrics(net_pnl=0.05, profit_factor=0.9, max_drawdown=-0.03)
        config = _make_config_snapshot(mdd_cap=-0.10)
        assert check_criterion_14_4(metrics, config) is False

    def test_profit_factor_exactly_one_fails(self) -> None:
        """#083 — profit_factor == 1.0 → False (strictly > 1.0)."""
        from scripts.dashboard.pages.comparison_logic import check_criterion_14_4

        metrics = _make_metrics(net_pnl=0.05, profit_factor=1.0, max_drawdown=-0.03)
        config = _make_config_snapshot(mdd_cap=-0.10)
        assert check_criterion_14_4(metrics, config) is False

    def test_mdd_fails(self) -> None:
        """#083 — MDD exceeds cap → False."""
        from scripts.dashboard.pages.comparison_logic import check_criterion_14_4

        # max_drawdown=-0.15 is worse than mdd_cap=-0.10
        metrics = _make_metrics(net_pnl=0.05, profit_factor=1.5, max_drawdown=-0.15)
        config = _make_config_snapshot(mdd_cap=-0.10)
        assert check_criterion_14_4(metrics, config) is False

    def test_mdd_equal_to_cap_fails(self) -> None:
        """#083 — MDD exactly at cap → False (strictly < required)."""
        from scripts.dashboard.pages.comparison_logic import check_criterion_14_4

        metrics = _make_metrics(net_pnl=0.05, profit_factor=1.5, max_drawdown=-0.10)
        config = _make_config_snapshot(mdd_cap=-0.10)
        assert check_criterion_14_4(metrics, config) is False

    def test_missing_config_snapshot_returns_false(self) -> None:
        """#083 — config_snapshot is None (file missing) → False."""
        from scripts.dashboard.pages.comparison_logic import check_criterion_14_4

        metrics = _make_metrics(net_pnl=0.05, profit_factor=1.5, max_drawdown=-0.03)
        assert check_criterion_14_4(metrics, None) is False

    def test_none_pnl_returns_false(self) -> None:
        """#083 — net_pnl is None → False."""
        from scripts.dashboard.pages.comparison_logic import check_criterion_14_4

        metrics = _make_metrics(net_pnl=None, profit_factor=1.5, max_drawdown=-0.03)
        config = _make_config_snapshot(mdd_cap=-0.10)
        assert check_criterion_14_4(metrics, config) is False

    def test_none_profit_factor_returns_false(self) -> None:
        """#083 — profit_factor is None → False."""
        from scripts.dashboard.pages.comparison_logic import check_criterion_14_4

        metrics = _make_metrics(net_pnl=0.05, profit_factor=None, max_drawdown=-0.03)
        config = _make_config_snapshot(mdd_cap=-0.10)
        assert check_criterion_14_4(metrics, config) is False

    def test_none_max_drawdown_returns_false(self) -> None:
        """#083 — max_drawdown is None → False."""
        from scripts.dashboard.pages.comparison_logic import check_criterion_14_4

        metrics = _make_metrics(net_pnl=0.05, profit_factor=1.5, max_drawdown=None)
        config = _make_config_snapshot(mdd_cap=-0.10)
        assert check_criterion_14_4(metrics, config) is False


# ===========================================================================
# §7.4 — build_radar_data
# ===========================================================================


class TestBuildRadarData:
    """#083 — Build radar data for chart_radar (§7.4)."""

    def test_normal(self) -> None:
        """#083 — Normal case: radar data extracted from metrics."""
        from scripts.dashboard.pages.comparison_logic import build_radar_data

        runs = [
            _make_metrics(
                run_id="A", strategy_name="strat_a",
                net_pnl=0.05, sharpe=1.5, max_drawdown=-0.03,
                hit_rate=0.55, profit_factor=1.8,
            ),
        ]
        result = build_radar_data(runs)
        assert len(result) == 1
        assert result[0]["label"] == "strat_a (A)"
        assert result[0]["net_pnl"] == pytest.approx(0.05)
        assert result[0]["sharpe"] == pytest.approx(1.5)
        assert result[0]["max_drawdown"] == pytest.approx(-0.03)
        assert result[0]["hit_rate"] == pytest.approx(0.55)
        assert result[0]["profit_factor"] == pytest.approx(1.8)

    def test_none_values_replaced_by_zero(self) -> None:
        """#083 — None metric values are replaced by 0.0 in radar data."""
        from scripts.dashboard.pages.comparison_logic import build_radar_data

        runs = [
            _make_metrics(
                run_id="A", strategy_name="s",
                net_pnl=None, sharpe=None, max_drawdown=None,
                hit_rate=None, profit_factor=None,
            ),
        ]
        result = build_radar_data(runs)
        assert result[0]["net_pnl"] == 0.0
        assert result[0]["sharpe"] == 0.0
        assert result[0]["max_drawdown"] == 0.0
        assert result[0]["hit_rate"] == 0.0
        assert result[0]["profit_factor"] == 0.0

    def test_multiple_runs(self) -> None:
        """#083 — Multiple runs produce multiple radar dicts."""
        from scripts.dashboard.pages.comparison_logic import build_radar_data

        runs = [
            _make_metrics(run_id="A", strategy_name="s1"),
            _make_metrics(run_id="B", strategy_name="s2"),
        ]
        result = build_radar_data(runs)
        assert len(result) == 2
        assert result[0]["label"] == "s1 (A)"
        assert result[1]["label"] == "s2 (B)"


# ===========================================================================
# §7.2 — get_aggregate_notes
# ===========================================================================


class TestGetAggregateNotes:
    """#083 — Extract aggregate.notes from metrics (§7.2)."""

    def test_notes_present(self) -> None:
        """#083 — Notes present → returned as string."""
        from scripts.dashboard.pages.comparison_logic import get_aggregate_notes

        metrics = _make_metrics(notes="MDD exceeded cap on 3 folds")
        assert get_aggregate_notes(metrics) == "MDD exceeded cap on 3 folds"

    def test_notes_absent(self) -> None:
        """#083 — No notes key → None."""
        from scripts.dashboard.pages.comparison_logic import get_aggregate_notes

        metrics = _make_metrics()  # no notes
        assert get_aggregate_notes(metrics) is None

    def test_notes_empty_string(self) -> None:
        """#083 — Empty string notes → None (treated as absent)."""
        from scripts.dashboard.pages.comparison_logic import get_aggregate_notes

        metrics = _make_metrics(notes="")
        assert get_aggregate_notes(metrics) is None


# ===========================================================================
# §9.3 — format_comparison_dataframe
# ===========================================================================


class TestFormatComparisonDataframe:
    """#083 — Format comparison DataFrame for display (§9.3)."""

    def test_pnl_formatted_as_pct(self) -> None:
        """#083 — Net PnL formatted as percentage."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
            format_comparison_dataframe,
        )

        runs = [_make_metrics(net_pnl=0.0345)]
        df = build_comparison_dataframe(runs)
        formatted = format_comparison_dataframe(df)
        assert formatted.iloc[0]["Net PnL (moy)"] == "3.45%"

    def test_sharpe_formatted_as_float(self) -> None:
        """#083 — Sharpe formatted as float with 2 decimals."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
            format_comparison_dataframe,
        )

        runs = [_make_metrics(sharpe=1.234)]
        df = build_comparison_dataframe(runs)
        formatted = format_comparison_dataframe(df)
        assert formatted.iloc[0]["Sharpe (moy)"] == "1.23"

    def test_mdd_formatted_as_pct(self) -> None:
        """#083 — MDD formatted as percentage."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
            format_comparison_dataframe,
        )

        runs = [_make_metrics(max_drawdown=-0.05)]
        df = build_comparison_dataframe(runs)
        formatted = format_comparison_dataframe(df)
        assert formatted.iloc[0]["MDD (moy)"] == "-5.00%"

    def test_win_rate_formatted_as_pct_1_decimal(self) -> None:
        """#083 — Win Rate formatted as percentage with 1 decimal."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
            format_comparison_dataframe,
        )

        runs = [_make_metrics(hit_rate=0.552)]
        df = build_comparison_dataframe(runs)
        formatted = format_comparison_dataframe(df)
        assert formatted.iloc[0]["Win Rate (moy)"] == "55.2%"

    def test_trades_formatted_as_int(self) -> None:
        """#083 — Trades formatted as integer."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
            format_comparison_dataframe,
        )

        runs = [_make_metrics(n_trades=42.0)]
        df = build_comparison_dataframe(runs)
        formatted = format_comparison_dataframe(df)
        assert formatted.iloc[0]["Trades (moy)"] == "42"

    def test_none_displayed_as_dash(self) -> None:
        """#083 — None values displayed as em-dash '—'."""
        from scripts.dashboard.pages.comparison_logic import (
            build_comparison_dataframe,
            format_comparison_dataframe,
        )

        runs = [_make_metrics(net_pnl=None, sharpe=None)]
        df = build_comparison_dataframe(runs)
        formatted = format_comparison_dataframe(df)
        assert formatted.iloc[0]["Net PnL (moy)"] == "—"
        assert formatted.iloc[0]["Sharpe (moy)"] == "—"
