"""Streamlit dashboard entry point.

Point d'entrée principal du dashboard AI Trading Pipeline.
Configure la page Streamlit et le routage multi-pages.

Ref: §10.2 — app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Page definitions — importable without Streamlit for testing
# ---------------------------------------------------------------------------

# Absolute path to the dashboard package directory
_DASHBOARD_DIR = Path(__file__).resolve().parent

PAGE_DEFINITIONS: list[dict[str, str]] = [
    {"path": str(_DASHBOARD_DIR / "pages" / "1_overview.py"), "title": "Overview"},
    {"path": str(_DASHBOARD_DIR / "pages" / "2_run_detail.py"), "title": "Run Detail"},
    {"path": str(_DASHBOARD_DIR / "pages" / "3_comparison.py"), "title": "Comparison"},
    {"path": str(_DASHBOARD_DIR / "pages" / "4_fold_analysis.py"), "title": "Fold Analysis"},
]


# ---------------------------------------------------------------------------
# Runs directory resolution — testable without Streamlit
# ---------------------------------------------------------------------------


def resolve_runs_dir(
    cli_args: list[str],
    env: str | None,
    default: str,
) -> Path:
    """Resolve the runs directory with strict precedence: CLI > env > default.

    Parameters
    ----------
    cli_args:
        List of CLI arguments (typically ``sys.argv[1:]``).
        Supports ``--runs-dir VALUE`` and ``--runs-dir=VALUE`` syntax.
    env:
        Value of ``AI_TRADING_RUNS_DIR`` environment variable, or ``None``.
    default:
        Default path to use if neither CLI nor env is provided.

    Returns
    -------
    Path
        Resolved, validated directory path.

    Raises
    ------
    FileNotFoundError
        If the resolved path does not exist.
    NotADirectoryError
        If the resolved path exists but is not a directory.
    """
    raw_path: str | None = None

    # 1. CLI argument (highest precedence)
    raw_path = _parse_runs_dir_from_args(cli_args)

    # 2. Environment variable
    if raw_path is None:
        raw_path = env

    # 3. Default
    if raw_path is None:
        raw_path = default

    # Resolve for security (spec §11.1 — no traversal)
    resolved = Path(raw_path).resolve()

    # Strict validation — no silent fallback
    if not resolved.exists():
        raise FileNotFoundError(
            f"Runs directory does not exist: {resolved}"
        )
    if not resolved.is_dir():
        raise NotADirectoryError(
            f"Runs path is not a directory: {resolved}"
        )

    return resolved


def _parse_runs_dir_from_args(args: list[str]) -> str | None:
    """Extract ``--runs-dir`` value from CLI arguments.

    Supports both ``--runs-dir VALUE`` and ``--runs-dir=VALUE`` syntax.
    Returns ``None`` if not found.
    """
    for i, arg in enumerate(args):
        if arg == "--runs-dir" and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("--runs-dir="):
            return arg.split("=", 1)[1]
    return None


# ---------------------------------------------------------------------------
# Streamlit entry point — only runs when executed by Streamlit
# ---------------------------------------------------------------------------


def main() -> None:
    """Configure and launch the Streamlit multi-page dashboard."""
    import streamlit as st

    from scripts.dashboard.data_loader import discover_runs

    # Page config — must be the first Streamlit command (spec §9.4)
    st.set_page_config(layout="wide", page_title="AI Trading Dashboard")

    # Resolve runs directory
    runs_dir = resolve_runs_dir(
        cli_args=sys.argv[1:],
        env=os.environ.get("AI_TRADING_RUNS_DIR"),
        default="runs/",
    )

    # Discover runs and store in session_state
    if "runs" not in st.session_state:
        st.session_state.runs = discover_runs(runs_dir)
    if "runs_dir" not in st.session_state:
        st.session_state.runs_dir = runs_dir

    # Multi-page navigation (spec §10.2)
    pages = [
        st.Page(page_def["path"], title=page_def["title"])
        for page_def in PAGE_DEFINITIONS
    ]
    nav = st.navigation(pages)
    nav.run()


if __name__ == "__main__":
    main()
