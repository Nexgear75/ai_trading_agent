"""Tests for the Streamlit dashboard entry point — app.py.

Task #078 — WS-D-2: Point d'entrée Streamlit et navigation multi-pages.

Tests cover:
- runs_dir resolution logic (CLI > env var > default)
- Path validation (error on non-existent directory)
- Path security (resolve for traversal prevention)
- Page definitions for multi-page navigation
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# resolve_runs_dir tests
# ---------------------------------------------------------------------------


class TestResolveRunsDir:
    """Test runs_dir resolution with precedence: CLI > env var > default."""

    def test_default_when_no_cli_no_env(self, tmp_path: Path) -> None:
        """Default 'runs/' is returned when no CLI arg and no env var."""
        from scripts.dashboard.app import resolve_runs_dir

        runs = tmp_path / "runs"
        runs.mkdir()

        result = resolve_runs_dir(cli_args=[], env=None, default=str(runs))
        assert result == runs.resolve()

    def test_cli_arg_takes_precedence_over_env(self, tmp_path: Path) -> None:
        """CLI --runs-dir overrides env var."""
        from scripts.dashboard.app import resolve_runs_dir

        cli_dir = tmp_path / "cli_runs"
        cli_dir.mkdir()
        env_dir = tmp_path / "env_runs"
        env_dir.mkdir()

        result = resolve_runs_dir(
            cli_args=["--runs-dir", str(cli_dir)],
            env=str(env_dir),
            default="runs/",
        )
        assert result == cli_dir.resolve()

    def test_env_var_takes_precedence_over_default(self, tmp_path: Path) -> None:
        """Env var AI_TRADING_RUNS_DIR overrides default."""
        from scripts.dashboard.app import resolve_runs_dir

        env_dir = tmp_path / "env_runs"
        env_dir.mkdir()

        result = resolve_runs_dir(
            cli_args=[],
            env=str(env_dir),
            default="runs/",
        )
        assert result == env_dir.resolve()

    def test_cli_arg_with_equals_syntax(self, tmp_path: Path) -> None:
        """CLI --runs-dir=/path syntax is supported."""
        from scripts.dashboard.app import resolve_runs_dir

        cli_dir = tmp_path / "cli_runs"
        cli_dir.mkdir()

        result = resolve_runs_dir(
            cli_args=["--runs-dir=" + str(cli_dir)],
            env=None,
            default="runs/",
        )
        assert result == cli_dir.resolve()

    def test_error_if_directory_does_not_exist(self, tmp_path: Path) -> None:
        """Raise FileNotFoundError if the resolved directory does not exist."""
        from scripts.dashboard.app import resolve_runs_dir

        nonexistent = tmp_path / "nonexistent_runs"

        with pytest.raises(FileNotFoundError, match="does not exist"):
            resolve_runs_dir(
                cli_args=["--runs-dir", str(nonexistent)],
                env=None,
                default="runs/",
            )

    def test_error_if_path_is_file_not_directory(self, tmp_path: Path) -> None:
        """Raise NotADirectoryError if the resolved path is a file."""
        from scripts.dashboard.app import resolve_runs_dir

        a_file = tmp_path / "not_a_dir"
        a_file.write_text("data")

        with pytest.raises(NotADirectoryError, match="not a directory"):
            resolve_runs_dir(
                cli_args=["--runs-dir", str(a_file)],
                env=None,
                default="runs/",
            )

    def test_path_is_resolved_for_security(self, tmp_path: Path) -> None:
        """Path is resolved (no symlink/traversal ambiguity)."""
        from scripts.dashboard.app import resolve_runs_dir

        real_dir = tmp_path / "real_runs"
        real_dir.mkdir()
        # Use parent traversal: real_runs/../real_runs
        traversal = str(real_dir / ".." / "real_runs")

        result = resolve_runs_dir(
            cli_args=["--runs-dir", traversal],
            env=None,
            default="runs/",
        )
        assert result == real_dir.resolve()
        assert ".." not in str(result)

    def test_env_var_nonexistent_directory_errors(self, tmp_path: Path) -> None:
        """Error raised when env var points to non-existent directory."""
        from scripts.dashboard.app import resolve_runs_dir

        with pytest.raises(FileNotFoundError, match="does not exist"):
            resolve_runs_dir(
                cli_args=[],
                env=str(tmp_path / "nonexistent"),
                default="runs/",
            )

    def test_default_nonexistent_directory_errors(self, tmp_path: Path) -> None:
        """Error raised when default points to non-existent directory."""
        from scripts.dashboard.app import resolve_runs_dir

        with pytest.raises(FileNotFoundError, match="does not exist"):
            resolve_runs_dir(
                cli_args=[],
                env=None,
                default=str(tmp_path / "nonexistent"),
            )

    def test_cli_unknown_args_ignored(self, tmp_path: Path) -> None:
        """Unknown CLI args are ignored; only --runs-dir is parsed."""
        from scripts.dashboard.app import resolve_runs_dir

        runs = tmp_path / "runs"
        runs.mkdir()

        result = resolve_runs_dir(
            cli_args=["--other-flag", "value", "--runs-dir", str(runs)],
            env=None,
            default="runs/",
        )
        assert result == runs.resolve()

    def test_returns_path_object(self, tmp_path: Path) -> None:
        """Return type is pathlib.Path."""
        from scripts.dashboard.app import resolve_runs_dir

        runs = tmp_path / "runs"
        runs.mkdir()

        result = resolve_runs_dir(cli_args=[], env=None, default=str(runs))
        assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# Page definitions tests
# ---------------------------------------------------------------------------


class TestPageDefinitions:
    """Test that page definitions are correctly defined."""

    def test_page_definitions_exist(self) -> None:
        """PAGE_DEFINITIONS is available and contains 4 pages."""
        from scripts.dashboard.app import PAGE_DEFINITIONS

        assert isinstance(PAGE_DEFINITIONS, list)
        assert len(PAGE_DEFINITIONS) == 4

    def test_page_definitions_order(self) -> None:
        """Pages are in correct order: overview, run_detail, comparison, fold_analysis."""
        from scripts.dashboard.app import PAGE_DEFINITIONS

        titles = [p["title"] for p in PAGE_DEFINITIONS]
        assert titles == ["Overview", "Run Detail", "Comparison", "Fold Analysis"]

    def test_page_definitions_have_required_keys(self) -> None:
        """Each page definition has 'path' and 'title' keys."""
        from scripts.dashboard.app import PAGE_DEFINITIONS

        for page_def in PAGE_DEFINITIONS:
            assert "path" in page_def, f"Missing 'path' in {page_def}"
            assert "title" in page_def, f"Missing 'title' in {page_def}"

    def test_page_files_exist(self) -> None:
        """All referenced page files exist on disk."""
        from scripts.dashboard.app import PAGE_DEFINITIONS

        for page_def in PAGE_DEFINITIONS:
            page_path = Path(page_def["path"])
            assert page_path.exists(), f"Page file does not exist: {page_path}"
