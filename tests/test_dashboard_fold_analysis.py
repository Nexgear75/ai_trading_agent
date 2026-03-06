"""Tests for fold analysis page logic (Page 4).

Task #085 — WS-D-5: Page 4 — navigation fold et equity curve.
Spec refs: §8.1 navigation run/fold, §8.2 fold equity curve.

Tests cover:
- discover_folds: scanning fold directories, empty dir, no folds dir
- build_run_selector_options: label formatting from runs list
- get_run_dir: path construction
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# discover_folds
# ---------------------------------------------------------------------------


class TestDiscoverFolds:
    """§8.1 — fold discovery from run directory."""

    def test_returns_sorted_fold_names(self, tmp_path: Path) -> None:
        """discover_folds returns sorted list of fold directory names."""
        from scripts.dashboard.pages.fold_analysis_logic import discover_folds

        run_dir = tmp_path / "run_001"
        folds_dir = run_dir / "folds"
        (folds_dir / "fold_02").mkdir(parents=True)
        (folds_dir / "fold_00").mkdir()
        (folds_dir / "fold_01").mkdir()

        result = discover_folds(run_dir)
        assert result == ["fold_00", "fold_01", "fold_02"]

    def test_empty_folds_directory(self, tmp_path: Path) -> None:
        """discover_folds returns empty list when folds/ is empty."""
        from scripts.dashboard.pages.fold_analysis_logic import discover_folds

        run_dir = tmp_path / "run_001"
        (run_dir / "folds").mkdir(parents=True)

        result = discover_folds(run_dir)
        assert result == []

    def test_no_folds_directory(self, tmp_path: Path) -> None:
        """discover_folds returns empty list when folds/ does not exist."""
        from scripts.dashboard.pages.fold_analysis_logic import discover_folds

        run_dir = tmp_path / "run_001"
        run_dir.mkdir(parents=True)

        result = discover_folds(run_dir)
        assert result == []

    def test_ignores_files_in_folds_dir(self, tmp_path: Path) -> None:
        """discover_folds ignores non-directory entries in folds/."""
        from scripts.dashboard.pages.fold_analysis_logic import discover_folds

        run_dir = tmp_path / "run_001"
        folds_dir = run_dir / "folds"
        (folds_dir / "fold_00").mkdir(parents=True)
        (folds_dir / "some_file.txt").write_text("ignore me")

        result = discover_folds(run_dir)
        assert result == ["fold_00"]

    def test_single_fold(self, tmp_path: Path) -> None:
        """discover_folds works with a single fold."""
        from scripts.dashboard.pages.fold_analysis_logic import discover_folds

        run_dir = tmp_path / "run_001"
        (run_dir / "folds" / "fold_00").mkdir(parents=True)

        result = discover_folds(run_dir)
        assert result == ["fold_00"]


# ---------------------------------------------------------------------------
# build_run_selector_options
# ---------------------------------------------------------------------------


class TestBuildRunSelectorOptions:
    """§8.1 — run selector dropdown options."""

    def test_returns_label_and_run_id_tuples(self) -> None:
        """Each option is (label_with_strategy, run_id)."""
        from scripts.dashboard.pages.fold_analysis_logic import (
            build_run_selector_options,
        )

        runs = [
            {"run_id": "20260101_000000_xgb", "strategy": {"name": "xgboost_reg"}},
            {"run_id": "20260102_000000_lstm", "strategy": {"name": "lstm"}},
        ]

        result = build_run_selector_options(runs)
        assert len(result) == 2
        # Each tuple: (label, run_id)
        assert result[0][1] == "20260101_000000_xgb"
        assert result[1][1] == "20260102_000000_lstm"
        # Labels contain strategy name
        assert "xgboost_reg" in result[0][0]
        assert "lstm" in result[1][0]

    def test_empty_runs_list(self) -> None:
        """Returns empty list for no runs."""
        from scripts.dashboard.pages.fold_analysis_logic import (
            build_run_selector_options,
        )

        result = build_run_selector_options([])
        assert result == []

    def test_label_contains_run_id(self) -> None:
        """Label includes run_id for disambiguation."""
        from scripts.dashboard.pages.fold_analysis_logic import (
            build_run_selector_options,
        )

        runs = [
            {"run_id": "20260101_000000_xgb", "strategy": {"name": "xgboost_reg"}},
        ]

        result = build_run_selector_options(runs)
        assert "20260101_000000_xgb" in result[0][0]


# ---------------------------------------------------------------------------
# get_run_dir
# ---------------------------------------------------------------------------


class TestGetRunDir:
    """§8.1 — run directory path construction."""

    def test_returns_correct_path(self, tmp_path: Path) -> None:
        """get_run_dir returns runs_dir / run_id."""
        from scripts.dashboard.pages.fold_analysis_logic import get_run_dir

        result = get_run_dir(tmp_path, "20260101_000000_xgb")
        assert result == tmp_path / "20260101_000000_xgb"

    def test_return_type_is_path(self, tmp_path: Path) -> None:
        """Return type is Path."""
        from scripts.dashboard.pages.fold_analysis_logic import get_run_dir

        result = get_run_dir(tmp_path, "run_001")
        assert isinstance(result, Path)
