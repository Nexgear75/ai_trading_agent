"""Pure business logic for the fold analysis page (Page 4).

Extracts testable logic (fold discovery, run selector options)
from the Streamlit rendering code.

Ref: §8.1 navigation run/fold, §8.2 fold equity curve.
"""

from __future__ import annotations

from pathlib import Path


def discover_folds(run_dir: Path) -> list[str]:
    """Scan the ``folds/`` subdirectory and return sorted fold names.

    Parameters
    ----------
    run_dir:
        Path to the run directory (expected to contain ``folds/``).

    Returns
    -------
    list[str]
        Sorted list of fold directory names (e.g. ``["fold_00", "fold_01"]``).
        Empty list if ``folds/`` does not exist or contains no subdirectories.
    """
    folds_dir = run_dir / "folds"
    if not folds_dir.is_dir():
        return []

    return sorted(
        entry.name for entry in folds_dir.iterdir() if entry.is_dir()
    )


def build_run_selector_options(runs: list[dict]) -> list[tuple[str, str]]:
    """Build (label, run_id) tuples for the run selector dropdown.

    Parameters
    ----------
    runs:
        List of validated metrics dicts (from ``discover_runs()``).

    Returns
    -------
    list[tuple[str, str]]
        Each tuple is ``(display_label, run_id)``.
    """
    options: list[tuple[str, str]] = []
    for run in runs:
        run_id = run["run_id"]
        strategy_name = run["strategy"]["name"]
        label = f"{run_id} — {strategy_name}"
        options.append((label, run_id))
    return options


def get_run_dir(runs_dir: Path, run_id: str) -> Path:
    """Return the path to a specific run directory.

    Parameters
    ----------
    runs_dir:
        Root runs directory.
    run_id:
        Run identifier (directory name).

    Returns
    -------
    Path
        ``runs_dir / run_id``.
    """
    return runs_dir / run_id
