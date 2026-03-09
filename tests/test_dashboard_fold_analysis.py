"""Tests for fold analysis page logic (Page 4).

Task #085 — WS-D-5: navigation par fold et equity curve du fold.

Tests cover:
- list_fold_dirs: sorted fold directory listing
- build_fold_selector_options: fold IDs from metrics dict
- get_fold_dir: path construction
- add_drawdown_to_figure: drawdown shading on Plotly figure
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pytest

from scripts.dashboard.pages.fold_analysis_logic import (
    add_drawdown_to_figure,
    build_fold_selector_options,
    get_fold_dir,
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
