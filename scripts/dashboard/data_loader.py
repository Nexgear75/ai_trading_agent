"""Data loader module for the AI Trading dashboard.

Chargement et validation des artefacts produits par le pipeline
(manifest.json, metrics.json, equity curves, trade journals).

Ref: §10.2 — data_loader.py
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Required keys in metrics.json (shared with scripts/compare_runs.py — DRY)
# ---------------------------------------------------------------------------

REQUIRED_TOP_KEYS = frozenset({"run_id", "strategy", "aggregate"})
REQUIRED_STRATEGY_KEYS = frozenset({"strategy_type", "name"})


# ---------------------------------------------------------------------------
# Individual loaders
# ---------------------------------------------------------------------------


def load_run_metrics(run_dir: Path) -> dict:
    """Load and validate ``metrics.json`` from a run directory.

    Parameters
    ----------
    run_dir:
        Path to the run directory (must contain ``metrics.json``).

    Returns
    -------
    dict
        Parsed and validated metrics dict.

    Raises
    ------
    FileNotFoundError
        If ``metrics.json`` does not exist.
    ValueError
        If JSON is invalid or required keys are missing.
    """
    metrics_path = run_dir / "metrics.json"
    if not metrics_path.exists():
        raise FileNotFoundError(f"metrics.json not found in {run_dir}")

    raw = metrics_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"File {metrics_path} contains invalid JSON: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"File {metrics_path}: expected a JSON object, got {type(data).__name__}"
        )

    missing = REQUIRED_TOP_KEYS - data.keys()
    if missing:
        raise ValueError(
            f"File {metrics_path}: missing required top-level keys: {sorted(missing)}"
        )

    return data


def load_run_manifest(run_dir: Path) -> dict:
    """Load ``manifest.json`` from a run directory.

    Parameters
    ----------
    run_dir:
        Path to the run directory (must contain ``manifest.json``).

    Returns
    -------
    dict
        Parsed manifest dict.

    Raises
    ------
    FileNotFoundError
        If ``manifest.json`` does not exist.
    ValueError
        If JSON is invalid.
    """
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found in {run_dir}")

    raw = manifest_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"File {manifest_path} contains invalid JSON: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"File {manifest_path}: expected a JSON object, got {type(data).__name__}"
        )

    return data


def load_config_snapshot(run_dir: Path) -> dict:
    """Load ``config_snapshot.yaml`` from a run directory.

    Parameters
    ----------
    run_dir:
        Path to the run directory (must contain ``config_snapshot.yaml``).

    Returns
    -------
    dict
        Parsed config dict.

    Raises
    ------
    FileNotFoundError
        If ``config_snapshot.yaml`` does not exist.
    ValueError
        If YAML is invalid.
    """
    config_path = run_dir / "config_snapshot.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"config_snapshot.yaml not found in {run_dir}")

    raw = config_path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"File {config_path} contains invalid YAML: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"File {config_path}: expected a YAML mapping, got {type(data).__name__}"
        )

    return data


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_runs(runs_dir: Path) -> list[dict]:
    """Discover valid runs in the given directory.

    Scans ``runs_dir`` for subdirectories containing a valid ``metrics.json``.
    Runs with ``strategy.name == "dummy"`` are silently excluded.
    Runs with broken or missing ``metrics.json`` are logged and skipped.

    Parameters
    ----------
    runs_dir:
        Path to the root runs directory.

    Returns
    -------
    list[dict]
        List of validated metrics dicts for each valid run, sorted by run_id.
    """
    if not runs_dir.is_dir():
        return []

    results: list[dict] = []
    for entry in sorted(runs_dir.iterdir()):
        if not entry.is_dir():
            continue

        metrics_path = entry / "metrics.json"
        if not metrics_path.exists():
            logger.warning("Skipping %s: metrics.json not found", entry.name)
            continue

        try:
            data = load_run_metrics(entry)
        except (ValueError, FileNotFoundError) as exc:
            logger.warning("Skipping %s: %s", entry.name, exc)
            continue

        # Exclude dummy strategy (spec §4.3)
        strategy = data.get("strategy", {})
        if isinstance(strategy, dict) and strategy.get("name") == "dummy":
            continue

        results.append(data)

    return results
