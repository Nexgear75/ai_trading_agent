"""Tests for scripts/dashboard/pages/1_overview.py — overview table and filters.

Task #079 — WS-D-2: Page 1 — tableau récapitulatif et filtres.
Spec refs: §5.2 tableau, §5.3 filtrage/tri, §9.3 conventions d'affichage.

Tests cover:
- build_overview_dataframe: construction from metrics dicts
- filter_by_type: dropdown Tous / Modèles / Baselines
- filter_by_strategy: multiselect filtering
- has_warnings: aggregate.notes detection
- default sort order (Run ID descending)
- formatting conventions
- empty / edge cases
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


# ---------------------------------------------------------------------------
# §5.2 — build_overview_dataframe : column construction
# ---------------------------------------------------------------------------


class TestBuildOverviewDataframe:
    """#079 — Build overview DataFrame from metrics dicts (§5.2)."""

    def test_single_run_columns(self) -> None:
        """#079 — DataFrame has all expected columns from §5.2."""
        from scripts.dashboard.pages.overview_logic import build_overview_dataframe

        runs = [_make_metrics()]
        df = build_overview_dataframe(runs)
        expected_cols = {
            "Run ID",
            "Stratégie",
            "Type",
            "Folds",
            "Net PnL moy",
            "Sharpe moy",
            "MDD moy",
            "Win Rate moy",
            "Trades moy",
        }
        assert set(df.columns) == expected_cols

    def test_single_run_values(self) -> None:
        """#079 — Values are correctly extracted from a single run."""
        from scripts.dashboard.pages.overview_logic import build_overview_dataframe

        runs = [
            _make_metrics(
                run_id="run_001",
                strategy_name="xgboost_reg",
                strategy_type="model",
                n_folds=5,
                net_pnl=0.0345,
                sharpe=1.23,
                max_drawdown=-0.05,
                hit_rate=0.552,
                n_trades=42.0,
            )
        ]
        df = build_overview_dataframe(runs)
        assert len(df) == 1
        row = df.iloc[0]
        assert row["Run ID"] == "run_001"
        assert row["Stratégie"] == "xgboost_reg"
        assert row["Type"] == "model"
        assert row["Folds"] == 5
        assert row["Net PnL moy"] == pytest.approx(0.0345)
        assert row["Sharpe moy"] == pytest.approx(1.23)
        assert row["MDD moy"] == pytest.approx(-0.05)
        assert row["Win Rate moy"] == pytest.approx(0.552)
        assert row["Trades moy"] == pytest.approx(42.0)

    def test_multiple_runs(self) -> None:
        """#079 — Multiple runs produce multiple rows."""
        from scripts.dashboard.pages.overview_logic import build_overview_dataframe

        runs = [
            _make_metrics(run_id="run_001", strategy_name="xgboost_reg"),
            _make_metrics(run_id="run_002", strategy_name="sma_rule", strategy_type="baseline"),
            _make_metrics(run_id="run_003", strategy_name="buy_hold", strategy_type="baseline"),
        ]
        df = build_overview_dataframe(runs)
        assert len(df) == 3

    def test_none_metric_values_preserved(self) -> None:
        """#079 — None values in metrics are preserved as NaN in DataFrame."""
        from scripts.dashboard.pages.overview_logic import build_overview_dataframe

        runs = [_make_metrics(net_pnl=None, sharpe=None, hit_rate=None)]
        df = build_overview_dataframe(runs)
        assert pd.isna(df.iloc[0]["Net PnL moy"])
        assert pd.isna(df.iloc[0]["Sharpe moy"])
        assert pd.isna(df.iloc[0]["Win Rate moy"])

    def test_zero_folds(self) -> None:
        """#079 — A run with 0 folds shows Folds=0."""
        from scripts.dashboard.pages.overview_logic import build_overview_dataframe

        runs = [_make_metrics(n_folds=0)]
        df = build_overview_dataframe(runs)
        assert df.iloc[0]["Folds"] == 0

    def test_empty_runs_list(self) -> None:
        """#079 — Empty list produces empty DataFrame with correct columns."""
        from scripts.dashboard.pages.overview_logic import build_overview_dataframe

        df = build_overview_dataframe([])
        assert len(df) == 0
        expected_cols = {
            "Run ID",
            "Stratégie",
            "Type",
            "Folds",
            "Net PnL moy",
            "Sharpe moy",
            "MDD moy",
            "Win Rate moy",
            "Trades moy",
        }
        assert set(df.columns) == expected_cols


# ---------------------------------------------------------------------------
# §5.2 — Default sort: Run ID descending
# ---------------------------------------------------------------------------


class TestDefaultSort:
    """#079 — Default sort order is Run ID descending (most recent first)."""

    def test_sorted_descending_by_run_id(self) -> None:
        """#079 — Runs are sorted by Run ID descending."""
        from scripts.dashboard.pages.overview_logic import build_overview_dataframe

        runs = [
            _make_metrics(run_id="20260101_000000_a"),
            _make_metrics(run_id="20260303_000000_c"),
            _make_metrics(run_id="20260202_000000_b"),
        ]
        df = build_overview_dataframe(runs)
        run_ids = df["Run ID"].tolist()
        assert run_ids == [
            "20260303_000000_c",
            "20260202_000000_b",
            "20260101_000000_a",
        ]


# ---------------------------------------------------------------------------
# §5.3 — filter_by_type
# ---------------------------------------------------------------------------


class TestFilterByType:
    """#079 — Filter by type: Tous / Modèles / Baselines (§5.3)."""

    @pytest.fixture
    def mixed_df(self) -> pd.DataFrame:
        from scripts.dashboard.pages.overview_logic import build_overview_dataframe

        runs = [
            _make_metrics(run_id="r1", strategy_name="xgboost", strategy_type="model"),
            _make_metrics(run_id="r2", strategy_name="sma_rule", strategy_type="baseline"),
            _make_metrics(run_id="r3", strategy_name="lstm", strategy_type="model"),
        ]
        return build_overview_dataframe(runs)

    def test_filter_tous(self, mixed_df: pd.DataFrame) -> None:
        """#079 — 'Tous' returns all rows."""
        from scripts.dashboard.pages.overview_logic import filter_by_type

        result = filter_by_type(mixed_df, "Tous")
        assert len(result) == 3

    def test_filter_modeles(self, mixed_df: pd.DataFrame) -> None:
        """#079 — 'Modèles' returns only model rows."""
        from scripts.dashboard.pages.overview_logic import filter_by_type

        result = filter_by_type(mixed_df, "Modèles")
        assert len(result) == 2
        assert set(result["Type"]) == {"model"}

    def test_filter_baselines(self, mixed_df: pd.DataFrame) -> None:
        """#079 — 'Baselines' returns only baseline rows."""
        from scripts.dashboard.pages.overview_logic import filter_by_type

        result = filter_by_type(mixed_df, "Baselines")
        assert len(result) == 1
        assert set(result["Type"]) == {"baseline"}

    def test_filter_invalid_type_raises(self, mixed_df: pd.DataFrame) -> None:
        """#079 — Invalid type filter raises ValueError."""
        from scripts.dashboard.pages.overview_logic import filter_by_type

        with pytest.raises(ValueError, match="Unknown type filter"):
            filter_by_type(mixed_df, "Unknown")

    def test_filter_modeles_when_none_exist(self) -> None:
        """#079 — Filtering for 'Modèles' when only baselines returns empty."""
        from scripts.dashboard.pages.overview_logic import (
            build_overview_dataframe,
            filter_by_type,
        )

        runs = [_make_metrics(strategy_type="baseline")]
        df = build_overview_dataframe(runs)
        result = filter_by_type(df, "Modèles")
        assert len(result) == 0


# ---------------------------------------------------------------------------
# §5.3 — filter_by_strategy
# ---------------------------------------------------------------------------


class TestFilterByStrategy:
    """#079 — Filter by strategy: multiselect (§5.3)."""

    @pytest.fixture
    def multi_strat_df(self) -> pd.DataFrame:
        from scripts.dashboard.pages.overview_logic import build_overview_dataframe

        runs = [
            _make_metrics(run_id="r1", strategy_name="xgboost_reg"),
            _make_metrics(run_id="r2", strategy_name="sma_rule"),
            _make_metrics(run_id="r3", strategy_name="xgboost_reg"),
            _make_metrics(run_id="r4", strategy_name="buy_hold"),
        ]
        return build_overview_dataframe(runs)

    def test_filter_single_strategy(self, multi_strat_df: pd.DataFrame) -> None:
        """#079 — Filtering by a single strategy returns matching rows."""
        from scripts.dashboard.pages.overview_logic import filter_by_strategy

        result = filter_by_strategy(multi_strat_df, ["xgboost_reg"])
        assert len(result) == 2
        assert set(result["Stratégie"]) == {"xgboost_reg"}

    def test_filter_multiple_strategies(self, multi_strat_df: pd.DataFrame) -> None:
        """#079 — Filtering by multiple strategies returns union."""
        from scripts.dashboard.pages.overview_logic import filter_by_strategy

        result = filter_by_strategy(multi_strat_df, ["xgboost_reg", "buy_hold"])
        assert len(result) == 3

    def test_filter_empty_selection_returns_all(self, multi_strat_df: pd.DataFrame) -> None:
        """#079 — Empty selection (no filter) returns all rows."""
        from scripts.dashboard.pages.overview_logic import filter_by_strategy

        result = filter_by_strategy(multi_strat_df, [])
        assert len(result) == 4

    def test_filter_nonexistent_strategy(self, multi_strat_df: pd.DataFrame) -> None:
        """#079 — Filtering by a strategy not present returns empty."""
        from scripts.dashboard.pages.overview_logic import filter_by_strategy

        result = filter_by_strategy(multi_strat_df, ["nonexistent"])
        assert len(result) == 0


# ---------------------------------------------------------------------------
# §5.3 — get_unique_strategies
# ---------------------------------------------------------------------------


class TestGetUniqueStrategies:
    """#079 — Extract unique strategy names for multiselect."""

    def test_unique_strategies(self) -> None:
        """#079 — Returns sorted unique strategy names."""
        from scripts.dashboard.pages.overview_logic import (
            build_overview_dataframe,
            get_unique_strategies,
        )

        runs = [
            _make_metrics(run_id="r1", strategy_name="xgboost_reg"),
            _make_metrics(run_id="r2", strategy_name="sma_rule"),
            _make_metrics(run_id="r3", strategy_name="xgboost_reg"),
        ]
        df = build_overview_dataframe(runs)
        result = get_unique_strategies(df)
        assert result == ["sma_rule", "xgboost_reg"]

    def test_unique_strategies_empty(self) -> None:
        """#079 — Empty DataFrame returns empty list."""
        from scripts.dashboard.pages.overview_logic import (
            build_overview_dataframe,
            get_unique_strategies,
        )

        df = build_overview_dataframe([])
        result = get_unique_strategies(df)
        assert result == []


# ---------------------------------------------------------------------------
# §4.3 / §5.2 — has_warnings (aggregate.notes)
# ---------------------------------------------------------------------------


class TestHasWarnings:
    """#079 — Detect warnings in aggregate.notes."""

    def test_no_notes_key(self) -> None:
        """#079 — Metrics without 'notes' → no warning."""
        from scripts.dashboard.pages.overview_logic import has_warnings

        metrics = _make_metrics(notes=None)
        assert has_warnings(metrics) is False

    def test_empty_notes(self) -> None:
        """#079 — Empty notes string → no warning."""
        from scripts.dashboard.pages.overview_logic import has_warnings

        metrics = _make_metrics(notes="")
        assert has_warnings(metrics) is False

    def test_notes_with_content(self) -> None:
        """#079 — Non-empty notes → has warning."""
        from scripts.dashboard.pages.overview_logic import has_warnings

        metrics = _make_metrics(notes="MDD exceeds cap")
        assert has_warnings(metrics) is True


# ---------------------------------------------------------------------------
# §9.3 — format_overview_dataframe
# ---------------------------------------------------------------------------


class TestFormatOverviewDataframe:
    """#079 — Formatting conventions for display (§9.3)."""

    def test_net_pnl_formatted_as_pct(self) -> None:
        """#079 — Net PnL formatted as :.2% ."""
        from scripts.dashboard.pages.overview_logic import (
            build_overview_dataframe,
            format_overview_dataframe,
        )

        runs = [_make_metrics(net_pnl=0.0345)]
        df = build_overview_dataframe(runs)
        formatted = format_overview_dataframe(df)
        assert formatted.iloc[0]["Net PnL moy"] == "3.45%"

    def test_sharpe_formatted_as_float(self) -> None:
        """#079 — Sharpe formatted as :.2f ."""
        from scripts.dashboard.pages.overview_logic import (
            build_overview_dataframe,
            format_overview_dataframe,
        )

        runs = [_make_metrics(sharpe=1.234)]
        df = build_overview_dataframe(runs)
        formatted = format_overview_dataframe(df)
        assert formatted.iloc[0]["Sharpe moy"] == "1.23"

    def test_mdd_formatted_as_pct(self) -> None:
        """#079 — MDD formatted as :.2% ."""
        from scripts.dashboard.pages.overview_logic import (
            build_overview_dataframe,
            format_overview_dataframe,
        )

        runs = [_make_metrics(max_drawdown=-0.05)]
        df = build_overview_dataframe(runs)
        formatted = format_overview_dataframe(df)
        assert formatted.iloc[0]["MDD moy"] == "-5.00%"

    def test_win_rate_formatted_as_pct_1_decimal(self) -> None:
        """#079 — Win Rate formatted as :.1% (§9.3 special for hit_rate)."""
        from scripts.dashboard.pages.overview_logic import (
            build_overview_dataframe,
            format_overview_dataframe,
        )

        runs = [_make_metrics(hit_rate=0.552)]
        df = build_overview_dataframe(runs)
        formatted = format_overview_dataframe(df)
        assert formatted.iloc[0]["Win Rate moy"] == "55.2%"

    def test_trades_formatted_as_int(self) -> None:
        """#079 — Trades formatted as integer."""
        from scripts.dashboard.pages.overview_logic import (
            build_overview_dataframe,
            format_overview_dataframe,
        )

        runs = [_make_metrics(n_trades=42.0)]
        df = build_overview_dataframe(runs)
        formatted = format_overview_dataframe(df)
        assert formatted.iloc[0]["Trades moy"] == "42"

    def test_folds_unchanged(self) -> None:
        """#079 — Folds stays as integer (no special formatting)."""
        from scripts.dashboard.pages.overview_logic import (
            build_overview_dataframe,
            format_overview_dataframe,
        )

        runs = [_make_metrics(n_folds=5)]
        df = build_overview_dataframe(runs)
        formatted = format_overview_dataframe(df)
        assert formatted.iloc[0]["Folds"] == 5

    def test_none_values_formatted_as_dash(self) -> None:
        """#079 — None/NaN values displayed as '—' (em dash)."""
        from scripts.dashboard.pages.overview_logic import (
            build_overview_dataframe,
            format_overview_dataframe,
        )

        runs = [_make_metrics(net_pnl=None, sharpe=None, hit_rate=None)]
        df = build_overview_dataframe(runs)
        formatted = format_overview_dataframe(df)
        assert formatted.iloc[0]["Net PnL moy"] == "—"
        assert formatted.iloc[0]["Sharpe moy"] == "—"
        assert formatted.iloc[0]["Win Rate moy"] == "—"


# ---------------------------------------------------------------------------
# §5.2 — build_warnings_mask
# ---------------------------------------------------------------------------


class TestBuildWarningsMask:
    """#079 — Build a boolean mask of runs with warnings."""

    def test_no_warnings(self) -> None:
        """#079 — All runs without notes → all False."""
        from scripts.dashboard.pages.overview_logic import build_warnings_mask

        runs = [
            _make_metrics(run_id="r1"),
            _make_metrics(run_id="r2"),
        ]
        mask = build_warnings_mask(runs)
        assert mask == [False, False]

    def test_some_warnings(self) -> None:
        """#079 — Mixed runs: warnings detected correctly."""
        from scripts.dashboard.pages.overview_logic import build_warnings_mask

        runs = [
            _make_metrics(run_id="r1", notes="MDD exceeded"),
            _make_metrics(run_id="r2"),
            _make_metrics(run_id="r3", notes="Low PnL"),
        ]
        mask = build_warnings_mask(runs)
        assert mask == [True, False, True]

    def test_empty_runs(self) -> None:
        """#079 — Empty list → empty mask."""
        from scripts.dashboard.pages.overview_logic import build_warnings_mask

        assert build_warnings_mask([]) == []


# ---------------------------------------------------------------------------
# §5.2 — Run ID column for navigation
# ---------------------------------------------------------------------------


class TestGetRunIdFromRow:
    """#079 — Extract run_id from DataFrame row index for navigation."""

    def test_extract_run_id(self) -> None:
        """#079 — run_id column is available for session_state storage."""
        from scripts.dashboard.pages.overview_logic import build_overview_dataframe

        runs = [_make_metrics(run_id="20260303_112351_xgboost")]
        df = build_overview_dataframe(runs)
        assert df.iloc[0]["Run ID"] == "20260303_112351_xgboost"
