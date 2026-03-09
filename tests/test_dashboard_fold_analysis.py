"""Tests for fold analysis page logic (Page 4).

Task #085 — WS-D-5: navigation par fold et equity curve du fold.
Task #086 — WS-D-5: scatter plot prédictions vs réalisés.
Task #087 — WS-D-5: journal des trades du fold.

Tests cover:
- list_fold_dirs: sorted fold directory listing
- build_fold_selector_options: fold IDs from metrics dict
- get_fold_dir: path construction
- add_drawdown_to_figure: drawdown shading on Plotly figure
- get_fold_threshold: extract threshold from metrics (#086)
- get_output_type: detect output type from metrics (#086)
- build_prediction_metrics: compute MAE, RMSE, DA, IC (#086)
- format_theta: format θ display (#086)
- prepare_fold_trades: add costs column to fold trades (#087)
- build_fold_trade_journal: journal construction for single fold (#087)
- join_fold_equity_after: equity jointure for single fold (#087)
- DRY reuse of filter_trades and paginate_dataframe (#087)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from scripts.dashboard.pages.fold_analysis_logic import (
    add_drawdown_to_figure,
    build_fold_selector_options,
    build_fold_trade_journal,
    build_prediction_metrics,
    format_theta,
    get_fold_dir,
    get_fold_threshold,
    get_output_type,
    join_fold_equity_after,
    list_fold_dirs,
    prepare_fold_trades,
)
from scripts.dashboard.pages.run_detail_logic import (
    filter_trades,
    paginate_dataframe,
)

# ---------------------------------------------------------------------------
# list_fold_dirs
# ---------------------------------------------------------------------------


class TestListFoldDirs:
    """Tests for list_fold_dirs."""

    def test_returns_sorted_fold_dirs(self, tmp_path: Path) -> None:
        """#085 — list_fold_dirs returns sorted fold directory names."""
        run_dir = tmp_path / "run_001"
        folds_dir = run_dir / "folds"
        folds_dir.mkdir(parents=True)
        (folds_dir / "fold_02").mkdir()
        (folds_dir / "fold_00").mkdir()
        (folds_dir / "fold_01").mkdir()

        result = list_fold_dirs(run_dir)
        assert result == ["fold_00", "fold_01", "fold_02"]

    def test_empty_folds_dir(self, tmp_path: Path) -> None:
        """#085 — list_fold_dirs returns empty list when folds dir is empty."""
        run_dir = tmp_path / "run_001"
        folds_dir = run_dir / "folds"
        folds_dir.mkdir(parents=True)

        result = list_fold_dirs(run_dir)
        assert result == []

    def test_no_folds_dir(self, tmp_path: Path) -> None:
        """#085 — list_fold_dirs returns empty list when folds dir does not exist."""
        run_dir = tmp_path / "run_001"
        run_dir.mkdir(parents=True)

        result = list_fold_dirs(run_dir)
        assert result == []

    def test_ignores_files_in_folds_dir(self, tmp_path: Path) -> None:
        """#085 — list_fold_dirs ignores non-directory entries."""
        run_dir = tmp_path / "run_001"
        folds_dir = run_dir / "folds"
        folds_dir.mkdir(parents=True)
        (folds_dir / "fold_00").mkdir()
        (folds_dir / "some_file.txt").write_text("ignored")

        result = list_fold_dirs(run_dir)
        assert result == ["fold_00"]


# ---------------------------------------------------------------------------
# build_fold_selector_options
# ---------------------------------------------------------------------------


class TestBuildFoldSelectorOptions:
    """Tests for build_fold_selector_options."""

    def test_returns_fold_ids(self) -> None:
        """#085 — build_fold_selector_options returns fold IDs from metrics."""
        metrics = {
            "folds": [
                {"fold_id": 0, "trading": {}, "prediction": {}},
                {"fold_id": 1, "trading": {}, "prediction": {}},
                {"fold_id": 2, "trading": {}, "prediction": {}},
            ],
            "aggregate": {},
            "run_id": "run_001",
            "strategy": {"name": "test", "strategy_type": "model"},
        }
        result = build_fold_selector_options(metrics)
        assert result == ["fold_00", "fold_01", "fold_02"]

    def test_empty_folds(self) -> None:
        """#085 — build_fold_selector_options returns empty list with no folds."""
        metrics = {
            "folds": [],
            "aggregate": {},
            "run_id": "run_001",
            "strategy": {"name": "test", "strategy_type": "model"},
        }
        result = build_fold_selector_options(metrics)
        assert result == []

    def test_single_fold(self) -> None:
        """#085 — build_fold_selector_options handles single fold."""
        metrics = {
            "folds": [
                {"fold_id": 0, "trading": {}, "prediction": {}},
            ],
            "aggregate": {},
            "run_id": "run_001",
            "strategy": {"name": "test", "strategy_type": "model"},
        }
        result = build_fold_selector_options(metrics)
        assert result == ["fold_00"]

    def test_string_fold_ids_passthrough(self) -> None:
        """#085 — build_fold_selector_options handles string fold_ids (legacy)."""
        metrics = {
            "folds": [
                {"fold_id": "fold_00", "trading": {}, "prediction": {}},
            ],
            "aggregate": {},
            "run_id": "run_001",
            "strategy": {"name": "test", "strategy_type": "model"},
        }
        result = build_fold_selector_options(metrics)
        assert result == ["fold_00"]


# ---------------------------------------------------------------------------
# get_fold_dir
# ---------------------------------------------------------------------------


class TestGetFoldDir:
    """Tests for get_fold_dir."""

    def test_correct_path(self, tmp_path: Path) -> None:
        """#085 — get_fold_dir returns run_dir / folds / fold_id."""
        run_dir = tmp_path / "run_001"
        result = get_fold_dir(run_dir, "fold_00")
        assert result == run_dir / "folds" / "fold_00"

    def test_different_fold_ids(self, tmp_path: Path) -> None:
        """#085 — get_fold_dir works with various fold IDs."""
        run_dir = tmp_path / "my_run"
        assert get_fold_dir(run_dir, "fold_05") == run_dir / "folds" / "fold_05"
        assert get_fold_dir(run_dir, "fold_99") == run_dir / "folds" / "fold_99"

    def test_int_fold_id(self, tmp_path: Path) -> None:
        """#085 — get_fold_dir handles integer fold_id from metrics."""
        run_dir = tmp_path / "my_run"
        assert get_fold_dir(run_dir, 0) == run_dir / "folds" / "fold_00"
        assert get_fold_dir(run_dir, 5) == run_dir / "folds" / "fold_05"


# ---------------------------------------------------------------------------
# add_drawdown_to_figure
# ---------------------------------------------------------------------------


class TestAddDrawdownToFigure:
    """Tests for add_drawdown_to_figure."""

    def _make_equity_df(self) -> pd.DataFrame:
        """Create a simple equity DataFrame with a drawdown."""
        return pd.DataFrame({
            "time_utc": pd.date_range("2024-01-01", periods=5, freq="h"),
            "equity": [100.0, 110.0, 105.0, 108.0, 112.0],
        })

    def test_adds_drawdown_traces(self) -> None:
        """#085 — add_drawdown_to_figure adds drawdown shading traces."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[1, 2, 3], name="Equity"))
        equity_df = self._make_equity_df()

        result = add_drawdown_to_figure(fig, equity_df)

        # Should have added 2 traces: running_max (invisible) + fill trace
        assert len(result.data) == 3  # original + 2 drawdown traces

    def test_preserves_existing_traces(self) -> None:
        """#085 — add_drawdown_to_figure preserves existing figure traces."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2], y=[1, 2], name="Original"))
        equity_df = self._make_equity_df()

        result = add_drawdown_to_figure(fig, equity_df)

        assert result.data[0].name == "Original"

    def test_drawdown_fill_trace_name(self) -> None:
        """#085 — add_drawdown_to_figure names the fill trace 'Drawdown'."""
        fig = go.Figure()
        equity_df = self._make_equity_df()

        result = add_drawdown_to_figure(fig, equity_df)

        trace_names = [t.name for t in result.data]
        assert "Drawdown" in trace_names

    def test_flat_equity_no_drawdown_area(self) -> None:
        """#085 — add_drawdown_to_figure works with monotonically increasing equity."""
        fig = go.Figure()
        equity_df = pd.DataFrame({
            "time_utc": pd.date_range("2024-01-01", periods=4, freq="h"),
            "equity": [100.0, 101.0, 102.0, 103.0],
        })

        result = add_drawdown_to_figure(fig, equity_df)

        # Traces are added regardless (drawdown is zero but fill exists)
        assert len(result.data) == 2  # running_max + fill

    def test_returns_same_figure_object(self) -> None:
        """#085 — add_drawdown_to_figure modifies and returns the same figure."""
        fig = go.Figure()
        equity_df = self._make_equity_df()

        result = add_drawdown_to_figure(fig, equity_df)

        assert result is fig

    def test_drawdown_uses_correct_color(self) -> None:
        """#085 — add_drawdown_to_figure uses COLOR_DRAWDOWN for fill."""
        from scripts.dashboard.utils import COLOR_DRAWDOWN

        fig = go.Figure()
        equity_df = self._make_equity_df()

        result = add_drawdown_to_figure(fig, equity_df)

        # The fill trace is the last one
        fill_trace = [t for t in result.data if t.name == "Drawdown"][0]
        assert fill_trace.fillcolor == COLOR_DRAWDOWN


# ---------------------------------------------------------------------------
# get_fold_threshold (#086)
# ---------------------------------------------------------------------------


class TestGetFoldThreshold:
    """Tests for get_fold_threshold."""

    def _make_metrics(
        self,
        fold_id: int = 0,
        theta: float | None = 0.005,
        method: str = "quantile",
    ) -> dict:
        return {
            "folds": [
                {
                    "fold_id": fold_id,
                    "threshold": {"theta": theta, "method": method},
                    "trading": {},
                    "prediction": {},
                }
            ],
            "aggregate": {},
            "run_id": "run_001",
            "strategy": {"name": "test", "strategy_type": "model"},
        }

    def test_fold_found_positive_theta(self) -> None:
        """#086 — get_fold_threshold returns theta and method for a known fold."""
        metrics = self._make_metrics(theta=0.005, method="quantile")
        result = get_fold_threshold(metrics, "fold_00")
        assert result["theta"] == 0.005
        assert result["method"] == "quantile"

    def test_fold_found_negative_theta(self) -> None:
        """#086 — get_fold_threshold works with negative theta."""
        metrics = self._make_metrics(theta=-0.003, method="quantile")
        result = get_fold_threshold(metrics, "fold_00")
        assert result["theta"] == -0.003

    def test_fold_found_zero_theta(self) -> None:
        """#086 — get_fold_threshold works with theta = 0."""
        metrics = self._make_metrics(theta=0.0, method="quantile")
        result = get_fold_threshold(metrics, "fold_00")
        assert result["theta"] == 0.0

    def test_fold_found_none_theta(self) -> None:
        """#086 — get_fold_threshold works with theta = None (null in JSON)."""
        metrics = self._make_metrics(theta=None, method="none")
        result = get_fold_threshold(metrics, "fold_00")
        assert result["theta"] is None
        assert result["method"] == "none"

    def test_fold_not_found_raises(self) -> None:
        """#086 — get_fold_threshold raises ValueError when fold not found."""
        metrics = self._make_metrics(fold_id=0)
        with pytest.raises(ValueError, match="fold_99"):
            get_fold_threshold(metrics, "fold_99")

    def test_multiple_folds_selects_correct(self) -> None:
        """#086 — get_fold_threshold picks the right fold among several."""
        metrics = {
            "folds": [
                {
                    "fold_id": 0,
                    "threshold": {"theta": 0.001, "method": "quantile"},
                    "trading": {},
                    "prediction": {},
                },
                {
                    "fold_id": 1,
                    "threshold": {"theta": 0.009, "method": "quantile"},
                    "trading": {},
                    "prediction": {},
                },
            ],
            "aggregate": {},
            "run_id": "run_001",
            "strategy": {"name": "test", "strategy_type": "model"},
        }
        result = get_fold_threshold(metrics, "fold_01")
        assert result["theta"] == 0.009


# ---------------------------------------------------------------------------
# get_output_type (#086)
# ---------------------------------------------------------------------------


class TestGetOutputType:
    """Tests for get_output_type."""

    def test_output_type_present_regression(self) -> None:
        """#086 — get_output_type returns value from strategy.output_type."""
        metrics = {
            "strategy": {"output_type": "regression"},
            "folds": [
                {"fold_id": 0, "threshold": {"method": "quantile"}},
            ],
        }
        assert get_output_type(metrics) == "regression"

    def test_output_type_present_signal(self) -> None:
        """#086 — get_output_type returns 'signal' from strategy.output_type."""
        metrics = {
            "strategy": {"output_type": "signal"},
            "folds": [
                {"fold_id": 0, "threshold": {"method": "none"}},
            ],
        }
        assert get_output_type(metrics) == "signal"

    def test_fallback_method_none_is_signal(self) -> None:
        """#086 — get_output_type fallback: method 'none' → 'signal'."""
        metrics = {
            "strategy": {"name": "sma_rule"},
            "folds": [
                {"fold_id": 0, "threshold": {"method": "none"}},
                {"fold_id": 1, "threshold": {"method": "none"}},
            ],
        }
        assert get_output_type(metrics) == "signal"

    def test_fallback_method_quantile_is_regression(self) -> None:
        """#086 — get_output_type fallback: method 'quantile' → 'regression'."""
        metrics = {
            "strategy": {"name": "xgboost"},
            "folds": [
                {"fold_id": 0, "threshold": {"method": "quantile"}},
            ],
        }
        assert get_output_type(metrics) == "regression"

    def test_fallback_mixed_methods_not_all_none(self) -> None:
        """#086 — get_output_type fallback: mixed methods → 'regression'."""
        metrics = {
            "strategy": {"name": "test"},
            "folds": [
                {"fold_id": 0, "threshold": {"method": "none"}},
                {"fold_id": 1, "threshold": {"method": "quantile"}},
            ],
        }
        assert get_output_type(metrics) == "regression"


# ---------------------------------------------------------------------------
# build_prediction_metrics (#086)
# ---------------------------------------------------------------------------


class TestBuildPredictionMetrics:
    """Tests for build_prediction_metrics."""

    def test_known_values(self) -> None:
        """#086 — build_prediction_metrics computes MAE, RMSE, DA, IC correctly."""
        preds_df = pd.DataFrame({
            "y_true": [0.01, -0.02, 0.03, -0.01, 0.005],
            "y_hat": [0.008, -0.015, 0.025, -0.005, 0.003],
        })
        result = build_prediction_metrics(preds_df)

        # MAE = mean(|diff|)
        diffs = np.abs(
            np.array([0.01, -0.02, 0.03, -0.01, 0.005])
            - np.array([0.008, -0.015, 0.025, -0.005, 0.003])
        )
        expected_mae = float(np.mean(diffs))
        assert result["mae"] == pytest.approx(expected_mae, abs=1e-10)

        # RMSE = sqrt(mean(diff²))
        sq_diffs = (
            np.array([0.01, -0.02, 0.03, -0.01, 0.005])
            - np.array([0.008, -0.015, 0.025, -0.005, 0.003])
        ) ** 2
        expected_rmse = float(np.sqrt(np.mean(sq_diffs)))
        assert result["rmse"] == pytest.approx(expected_rmse, abs=1e-10)

        # DA: all same sign → DA = 1.0
        assert result["da"] == pytest.approx(1.0, abs=1e-10)

        # IC: Spearman rank correlation
        assert "ic" in result
        assert isinstance(result["ic"], float)
        # Perfect rank agreement → ic close to 1.0
        assert result["ic"] > 0.9

    def test_opposite_directions(self) -> None:
        """#086 — build_prediction_metrics DA low when directions disagree."""
        preds_df = pd.DataFrame({
            "y_true": [0.01, -0.02, 0.03, -0.01],
            "y_hat": [-0.01, 0.02, -0.03, 0.01],
        })
        result = build_prediction_metrics(preds_df)
        # All directions wrong → DA = 0.0
        assert result["da"] == pytest.approx(0.0, abs=1e-10)

    def test_zero_values_in_direction(self) -> None:
        """#086 — build_prediction_metrics handles zeros in sign comparison."""
        preds_df = pd.DataFrame({
            "y_true": [0.0, 0.01, -0.01],
            "y_hat": [0.0, 0.01, -0.01],
        })
        result = build_prediction_metrics(preds_df)
        # sign(0) == sign(0) → True
        assert result["da"] == pytest.approx(1.0, abs=1e-10)


# ---------------------------------------------------------------------------
# format_theta (#086)
# ---------------------------------------------------------------------------


class TestFormatTheta:
    """Tests for format_theta."""

    def test_none_returns_em_dash(self) -> None:
        """#086 — format_theta returns '—' for None."""
        assert format_theta(None) == "—"

    def test_positive_theta(self) -> None:
        """#086 — format_theta formats positive value to 4 decimals."""
        assert format_theta(0.005) == "0.0050"

    def test_negative_theta(self) -> None:
        """#086 — format_theta formats negative value to 4 decimals."""
        assert format_theta(-0.005) == "-0.0050"

    def test_zero_theta(self) -> None:
        """#086 — format_theta formats zero to 4 decimals."""
        assert format_theta(0.0) == "0.0000"


# ---------------------------------------------------------------------------
# prepare_fold_trades (#087)
# ---------------------------------------------------------------------------


class TestPrepareFoldTrades:
    """Tests for prepare_fold_trades."""

    def test_adds_costs_column(self) -> None:
        """#087 — prepare_fold_trades adds costs = fees_paid + slippage_paid."""
        trades_df = pd.DataFrame({
            "entry_time_utc": ["2024-01-01 00:00:00"],
            "exit_time_utc": ["2024-01-01 01:00:00"],
            "entry_price": [100.0],
            "exit_price": [101.0],
            "fees_paid": [0.10],
            "slippage_paid": [0.05],
            "gross_return": [0.01],
            "net_return": [0.0085],
        })
        result = prepare_fold_trades(trades_df)
        assert "costs" in result.columns
        assert result["costs"].iloc[0] == pytest.approx(0.15)

    def test_does_not_modify_original(self) -> None:
        """#087 — prepare_fold_trades returns a copy, not modifying original."""
        trades_df = pd.DataFrame({
            "entry_time_utc": ["2024-01-01 00:00:00"],
            "exit_time_utc": ["2024-01-01 01:00:00"],
            "entry_price": [100.0],
            "exit_price": [101.0],
            "fees_paid": [0.10],
            "slippage_paid": [0.05],
            "gross_return": [0.01],
            "net_return": [0.0085],
        })
        prepare_fold_trades(trades_df)
        assert "costs" not in trades_df.columns

    def test_multiple_trades(self) -> None:
        """#087 — prepare_fold_trades computes costs for each trade."""
        trades_df = pd.DataFrame({
            "entry_time_utc": ["2024-01-01", "2024-01-02"],
            "exit_time_utc": ["2024-01-01", "2024-01-02"],
            "entry_price": [100.0, 200.0],
            "exit_price": [101.0, 199.0],
            "fees_paid": [0.10, 0.20],
            "slippage_paid": [0.05, 0.10],
            "gross_return": [0.01, -0.005],
            "net_return": [0.0085, -0.008],
        })
        result = prepare_fold_trades(trades_df)
        assert result["costs"].iloc[0] == pytest.approx(0.15)
        assert result["costs"].iloc[1] == pytest.approx(0.30)


# ---------------------------------------------------------------------------
# join_fold_equity_after (#087)
# ---------------------------------------------------------------------------


class TestJoinFoldEquityAfter:
    """Tests for join_fold_equity_after."""

    def test_none_equity_returns_none(self) -> None:
        """#087 — join_fold_equity_after returns None when equity is None."""
        trades_df = pd.DataFrame({
            "exit_time_utc": ["2024-01-01 01:00:00"],
        })
        result = join_fold_equity_after(trades_df, None)
        assert result is None

    def test_matches_equity_by_exit_time(self) -> None:
        """#087 — join_fold_equity_after matches equity via merge_asof backward."""
        trades_df = pd.DataFrame({
            "exit_time_utc": [
                "2024-01-01 02:00:00",
                "2024-01-01 04:00:00",
            ],
        })
        equity_df = pd.DataFrame({
            "time_utc": [
                "2024-01-01 01:00:00",
                "2024-01-01 02:00:00",
                "2024-01-01 03:00:00",
                "2024-01-01 04:00:00",
            ],
            "equity": [1000.0, 1010.0, 1005.0, 1020.0],
        })
        result = join_fold_equity_after(trades_df, equity_df)
        assert result is not None
        assert len(result) == 2
        assert result.iloc[0] == pytest.approx(1010.0)
        assert result.iloc[1] == pytest.approx(1020.0)

    def test_no_backward_match_returns_nan(self) -> None:
        """#087 — join_fold_equity_after returns NaN when no backward match."""
        trades_df = pd.DataFrame({
            "exit_time_utc": ["2024-01-01 00:30:00"],
        })
        equity_df = pd.DataFrame({
            "time_utc": ["2024-01-01 01:00:00"],
            "equity": [1000.0],
        })
        result = join_fold_equity_after(trades_df, equity_df)
        assert result is not None
        assert pd.isna(result.iloc[0])

    def test_empty_equity_returns_all_nan(self) -> None:
        """#087 — join_fold_equity_after returns NaN for all when equity is empty."""
        trades_df = pd.DataFrame({
            "exit_time_utc": ["2024-01-01 02:00:00"],
        })
        equity_df = pd.DataFrame(columns=["time_utc", "equity"])
        result = join_fold_equity_after(trades_df, equity_df)
        assert result is not None
        assert pd.isna(result.iloc[0])


# ---------------------------------------------------------------------------
# build_fold_trade_journal (#087)
# ---------------------------------------------------------------------------


class TestBuildFoldTradeJournal:
    """Tests for build_fold_trade_journal."""

    def _make_trades(self) -> pd.DataFrame:
        """Helper: create a minimal trades DataFrame with costs column."""
        return pd.DataFrame({
            "entry_time_utc": ["2024-01-01 00:00:00", "2024-01-02 00:00:00"],
            "exit_time_utc": ["2024-01-01 01:00:00", "2024-01-02 01:00:00"],
            "entry_price": [100.0, 200.0],
            "exit_price": [101.0, 199.0],
            "gross_return": [0.01, -0.005],
            "costs": [0.15, 0.30],
            "net_return": [0.0085, -0.008],
        })

    def test_correct_columns_no_equity(self) -> None:
        """#087 — build_fold_trade_journal has correct columns without equity."""
        trades = self._make_trades()
        journal = build_fold_trade_journal(trades, None)
        expected_cols = [
            "Entry time", "Exit time", "Entry price", "Exit price",
            "Gross return", "Costs", "Net return",
        ]
        assert list(journal.columns) == expected_cols

    def test_no_fold_column(self) -> None:
        """#087 — build_fold_trade_journal does NOT contain Fold column."""
        trades = self._make_trades()
        journal = build_fold_trade_journal(trades, None)
        assert "Fold" not in journal.columns

    def test_correct_values(self) -> None:
        """#087 — build_fold_trade_journal maps correct values."""
        trades = self._make_trades()
        journal = build_fold_trade_journal(trades, None)
        assert journal["Entry price"].iloc[0] == 100.0
        assert journal["Exit price"].iloc[1] == 199.0
        assert journal["Costs"].iloc[0] == pytest.approx(0.15)
        assert journal["Net return"].iloc[1] == pytest.approx(-0.008)

    def test_with_equity(self) -> None:
        """#087 — build_fold_trade_journal includes Equity after with equity."""
        trades = self._make_trades()
        equity_df = pd.DataFrame({
            "time_utc": [
                "2024-01-01 01:00:00",
                "2024-01-02 01:00:00",
            ],
            "equity": [1010.0, 1005.0],
        })
        journal = build_fold_trade_journal(trades, equity_df)
        assert "Equity after" in journal.columns
        assert len(journal) == 2

    def test_empty_trades_no_equity(self) -> None:
        """#087 — build_fold_trade_journal returns empty df with correct cols."""
        empty = pd.DataFrame(columns=[
            "entry_time_utc", "exit_time_utc", "entry_price", "exit_price",
            "gross_return", "costs", "net_return",
        ])
        journal = build_fold_trade_journal(empty, None)
        assert len(journal) == 0
        expected_cols = [
            "Entry time", "Exit time", "Entry price", "Exit price",
            "Gross return", "Costs", "Net return",
        ]
        assert list(journal.columns) == expected_cols

    def test_empty_trades_with_equity(self) -> None:
        """#087 — build_fold_trade_journal empty + equity → correct cols."""
        empty = pd.DataFrame(columns=[
            "entry_time_utc", "exit_time_utc", "entry_price", "exit_price",
            "gross_return", "costs", "net_return",
        ])
        equity_df = pd.DataFrame({
            "time_utc": ["2024-01-01 01:00:00"],
            "equity": [1000.0],
        })
        journal = build_fold_trade_journal(empty, equity_df)
        assert len(journal) == 0
        assert "Equity after" in journal.columns


# ---------------------------------------------------------------------------
# DRY reuse of filter_trades and paginate_dataframe (#087)
# ---------------------------------------------------------------------------


class TestFilterTradesOnFoldData:
    """Verify filter_trades from run_detail_logic works on fold trades."""

    def _make_fold_trades(self) -> pd.DataFrame:
        """Trades without fold column (as from load_fold_trades + prepare)."""
        return pd.DataFrame({
            "entry_time_utc": [
                "2024-01-01 00:00:00",
                "2024-01-02 00:00:00",
                "2024-01-03 00:00:00",
            ],
            "exit_time_utc": [
                "2024-01-01 01:00:00",
                "2024-01-02 01:00:00",
                "2024-01-03 01:00:00",
            ],
            "entry_price": [100.0, 200.0, 150.0],
            "exit_price": [101.0, 199.0, 155.0],
            "costs": [0.15, 0.30, 0.20],
            "gross_return": [0.01, -0.005, 0.033],
            "net_return": [0.0085, -0.008, 0.031],
        })

    def test_sign_filter_winning(self) -> None:
        """#087 — filter_trades sign='winning' works without fold column."""
        trades = self._make_fold_trades()
        result = filter_trades(trades, sign="winning")
        assert len(result) == 2
        assert all(result["net_return"] > 0)

    def test_sign_filter_losing(self) -> None:
        """#087 — filter_trades sign='losing' works without fold column."""
        trades = self._make_fold_trades()
        result = filter_trades(trades, sign="losing")
        assert len(result) == 1
        assert all(result["net_return"] <= 0)

    def test_date_filter(self) -> None:
        """#087 — filter_trades date filter works without fold column."""
        trades = self._make_fold_trades()
        result = filter_trades(
            trades,
            date_start=pd.Timestamp("2024-01-02"),
            date_end=pd.Timestamp("2024-01-02 23:59:59"),
        )
        assert len(result) == 1

    def test_no_fold_param_returns_all(self) -> None:
        """#087 — filter_trades with fold=None returns all rows."""
        trades = self._make_fold_trades()
        result = filter_trades(trades, fold=None, sign=None)
        assert len(result) == 3


class TestPaginateOnFoldJournal:
    """Verify paginate_dataframe from run_detail_logic works on fold journal."""

    def test_paginate_first_page(self) -> None:
        """#087 — paginate_dataframe returns first page of fold journal."""
        journal = pd.DataFrame({
            "Entry time": [f"2024-01-{i+1:02d}" for i in range(75)],
            "Net return": [0.01 * i for i in range(75)],
        })
        page1 = paginate_dataframe(journal, page=1, page_size=50)
        assert len(page1) == 50

    def test_paginate_second_page(self) -> None:
        """#087 — paginate_dataframe returns remaining rows on page 2."""
        journal = pd.DataFrame({
            "Entry time": [f"2024-01-{i+1:02d}" for i in range(75)],
            "Net return": [0.01 * i for i in range(75)],
        })
        page2 = paginate_dataframe(journal, page=2, page_size=50)
        assert len(page2) == 25
