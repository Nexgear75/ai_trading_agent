"""Data loader module for the AI Trading dashboard.

Chargement et validation des artefacts produits par le pipeline
(manifest.json, metrics.json, equity curves, trade journals).

Ref: §10.2 — data_loader.py
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
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

    if not isinstance(data["strategy"], dict):
        raise ValueError(
            f"File {metrics_path}: 'strategy' must be a JSON object, "
            f"got {type(data['strategy']).__name__}"
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
        strategy = data["strategy"]
        if strategy.get("name") == "dummy":
            continue

        results.append(data)

    results.sort(key=lambda d: d["run_id"])
    return results


# ---------------------------------------------------------------------------
# Required columns for CSV files
# ---------------------------------------------------------------------------

_EQUITY_CURVE_COLS = frozenset({"time_utc", "equity", "in_trade", "fold"})
_FOLD_EQUITY_CURVE_COLS = frozenset({"time_utc", "equity", "in_trade"})
_TRADES_COLS = frozenset({
    "entry_time_utc",
    "exit_time_utc",
    "entry_price",
    "exit_price",
    "entry_price_eff",
    "exit_price_eff",
    "f",
    "s",
    "fees_paid",
    "slippage_paid",
    "y_true",
    "y_hat",
    "gross_return",
    "net_return",
})
_PREDICTIONS_COLS = frozenset({"timestamp", "y_true", "y_hat"})


def _validate_columns(
    df: pd.DataFrame, required: frozenset[str], filepath: Path
) -> None:
    """Raise ``ValueError`` if *df* is missing any of *required* columns."""
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"File {filepath}: missing required columns: {sorted(missing)}"
        )


# ---------------------------------------------------------------------------
# CSV loaders
# ---------------------------------------------------------------------------


def load_equity_curve(run_dir: Path) -> pd.DataFrame | None:
    """Load the stitched ``equity_curve.csv`` from a run directory.

    Returns ``None`` if the file does not exist.
    Raises ``ValueError`` if the file exists but required columns are missing.
    """
    csv_path = run_dir / "equity_curve.csv"
    if not csv_path.exists():
        return None

    df = pd.read_csv(csv_path)
    _validate_columns(df, _EQUITY_CURVE_COLS, csv_path)
    return df


def load_fold_equity_curve(fold_dir: Path) -> pd.DataFrame | None:
    """Load ``equity_curve.csv`` from a single fold directory.

    Returns ``None`` if the file does not exist.
    Raises ``ValueError`` if the file exists but required columns are missing.
    """
    csv_path = fold_dir / "equity_curve.csv"
    if not csv_path.exists():
        return None

    df = pd.read_csv(csv_path)
    _validate_columns(df, _FOLD_EQUITY_CURVE_COLS, csv_path)
    return df


def load_trades(run_dir: Path) -> pd.DataFrame | None:
    """Concatenate ``trades.csv`` from all folds under *run_dir*.

    Adds a ``fold`` column derived from the fold directory name (e.g. ``fold_00``)
    and a computed ``costs`` column (``fees_paid + slippage_paid``).

    Returns ``None`` if no ``trades.csv`` files are found.
    Raises ``ValueError`` if a file exists but required columns are missing.
    """
    folds_dir = run_dir / "folds"
    if not folds_dir.is_dir():
        return None

    frames: list[pd.DataFrame] = []
    for fold_dir in sorted(folds_dir.iterdir()):
        if not fold_dir.is_dir():
            continue
        trades_path = fold_dir / "trades.csv"
        if not trades_path.exists():
            continue
        df = pd.read_csv(trades_path)
        _validate_columns(df, _TRADES_COLS, trades_path)
        df["fold"] = fold_dir.name
        frames.append(df)

    if not frames:
        return None

    result = pd.concat(frames, ignore_index=True)
    result["costs"] = result["fees_paid"] + result["slippage_paid"]
    return result


def load_fold_trades(fold_dir: Path) -> pd.DataFrame | None:
    """Load ``trades.csv`` from a single fold directory.

    Returns ``None`` if the file does not exist.
    Raises ``ValueError`` if the file exists but required columns are missing.
    """
    trades_path = fold_dir / "trades.csv"
    if not trades_path.exists():
        return None

    df = pd.read_csv(trades_path)
    _validate_columns(df, _TRADES_COLS, trades_path)
    return df


def load_predictions(fold_dir: Path, split: str) -> pd.DataFrame | None:
    """Load ``preds_val.csv`` or ``preds_test.csv`` from a fold directory.

    Parameters
    ----------
    fold_dir:
        Path to the fold directory.
    split:
        ``"val"`` or ``"test"``.

    Returns ``None`` if the file does not exist.
    Raises ``ValueError`` if the file exists but required columns are missing.
    """
    csv_path = fold_dir / f"preds_{split}.csv"
    if not csv_path.exists():
        return None

    df = pd.read_csv(csv_path)
    _validate_columns(df, _PREDICTIONS_COLS, csv_path)
    return df


def load_fold_metrics(fold_dir: Path) -> dict | None:
    """Load ``metrics_fold.json`` from a fold directory.

    Returns ``None`` if the file does not exist.
    Raises ``ValueError`` if the JSON is invalid or not a dict.
    """
    json_path = fold_dir / "metrics_fold.json"
    if not json_path.exists():
        return None

    raw = json_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"File {json_path} contains invalid JSON: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"File {json_path}: expected a JSON object, got {type(data).__name__}"
        )

    return data
