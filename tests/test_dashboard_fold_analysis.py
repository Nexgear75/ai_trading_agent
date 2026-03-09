"""Tests for fold analysis page logic (Page 4).

Task #085 — WS-D-5: navigation par fold et equity curve du fold.
Task #086 — WS-D-5: scatter plot prédictions vs réalisés.

Tests cover:
- list_fold_dirs: sorted fold directory listing
- build_fold_selector_options: fold IDs from metrics dict
- get_fold_dir: path construction
- add_drawdown_to_figure: drawdown shading on Plotly figure
- get_fold_threshold: extract threshold from metrics (#086)
- get_output_type: detect output type from metrics (#086)
- build_prediction_metrics: compute MAE, RMSE, DA, IC (#086)
- format_theta: format θ display (#086)
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
    build_prediction_metrics,
    format_theta,
    get_fold_dir,
    get_fold_threshold,
    get_output_type,
    list_fold_dirs,
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
                {"fold_id": "fold_00", "trading": {}, "prediction": {}},
                {"fold_id": "fold_01", "trading": {}, "prediction": {}},
                {"fold_id": "fold_02", "trading": {}, "prediction": {}},
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
        fold_id: str = "fold_00",
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
        metrics = self._make_metrics(fold_id="fold_00")
        with pytest.raises(ValueError, match="fold_99"):
            get_fold_threshold(metrics, "fold_99")

    def test_multiple_folds_selects_correct(self) -> None:
        """#086 — get_fold_threshold picks the right fold among several."""
        metrics = {
            "folds": [
                {
                    "fold_id": "fold_00",
                    "threshold": {"theta": 0.001, "method": "quantile"},
                    "trading": {},
                    "prediction": {},
                },
                {
                    "fold_id": "fold_01",
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
                {"fold_id": "fold_00", "threshold": {"method": "quantile"}},
            ],
        }
        assert get_output_type(metrics) == "regression"

    def test_output_type_present_signal(self) -> None:
        """#086 — get_output_type returns 'signal' from strategy.output_type."""
        metrics = {
            "strategy": {"output_type": "signal"},
            "folds": [
                {"fold_id": "fold_00", "threshold": {"method": "none"}},
            ],
        }
        assert get_output_type(metrics) == "signal"

    def test_fallback_method_none_is_signal(self) -> None:
        """#086 — get_output_type fallback: method 'none' → 'signal'."""
        metrics = {
            "strategy": {"name": "sma_rule"},
            "folds": [
                {"fold_id": "fold_00", "threshold": {"method": "none"}},
                {"fold_id": "fold_01", "threshold": {"method": "none"}},
            ],
        }
        assert get_output_type(metrics) == "signal"

    def test_fallback_method_quantile_is_regression(self) -> None:
        """#086 — get_output_type fallback: method 'quantile' → 'regression'."""
        metrics = {
            "strategy": {"name": "xgboost"},
            "folds": [
                {"fold_id": "fold_00", "threshold": {"method": "quantile"}},
            ],
        }
        assert get_output_type(metrics) == "regression"

    def test_fallback_mixed_methods_not_all_none(self) -> None:
        """#086 — get_output_type fallback: mixed methods → 'regression'."""
        metrics = {
            "strategy": {"name": "test"},
            "folds": [
                {"fold_id": "fold_00", "threshold": {"method": "none"}},
                {"fold_id": "fold_01", "threshold": {"method": "quantile"}},
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
