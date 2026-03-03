"""Manifest builder — construct and serialize ``manifest.json`` for a run.

Builds the run manifest from resolved config, dataset metadata, splits,
strategy info, costs, environment and artifacts.  The JSON output conforms
to ``docs/specifications/manifest.schema.json`` (Draft 2020-12).

Task #045 — WS-11.
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Strategy → framework mapping (internal, not read from YAML config)
# ---------------------------------------------------------------------------

STRATEGY_FRAMEWORK_MAP: dict[str, str] = {
    "dummy": "internal",
    "xgboost_reg": "xgboost",
    "cnn1d_reg": "pytorch",
    "gru_reg": "pytorch",
    "lstm_reg": "pytorch",
    "patchtst_reg": "pytorch",
    "rl_ppo": "pytorch",
    "no_trade": "baseline",
    "buy_hold": "baseline",
    "sma_rule": "baseline",
}


def get_git_commit(working_dir: Path | None = None) -> str:
    """Return the current Git commit hash (40-char hex).

    Parameters
    ----------
    working_dir:
        Directory in which to run ``git rev-parse HEAD``.
        If *None*, uses the current working directory.

    Returns
    -------
    str
        40-character hexadecimal commit hash, or ``"unknown"`` if Git
        is unavailable or the directory is not a Git repository.
        The ``"unknown"`` case is a **documented exception** to the
        strict-no-fallback rule and is logged at WARNING level.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=working_dir,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning(
            "Could not determine git commit hash (not a git repository "
            "or git not installed). Using 'unknown' — this is a documented "
            "exception to the strict-no-fallback rule."
        )
        return "unknown"


def build_manifest(
    *,
    run_id: str,
    config_snapshot: dict,
    dataset_info: dict,
    label_info: dict,
    window_info: dict,
    features_info: dict,
    splits_info: dict,
    strategy_info: dict,
    costs_info: dict,
    environment_info: dict,
    artifacts_info: dict,
    git_commit: str,
    pipeline_version: str,
) -> dict:
    """Build a manifest dict conforming to ``manifest.schema.json``.

    All parameters are **required** (keyword-only, no defaults).

    Parameters
    ----------
    run_id:
        Unique run identifier (e.g. ``YYYYMMDD_HHMMSS_<strategy>``).
    config_snapshot:
        Fully-resolved configuration snapshot dict.
    dataset_info:
        Dataset metadata (exchange, symbols, raw_files with SHA-256, etc.).
    label_info:
        Label configuration (horizon_H_bars, target_type, definition).
    window_info:
        Window configuration (L, min_warmup).
    features_info:
        Features metadata (feature_list, feature_version).
    splits_info:
        Splits metadata including folds with disjoint train/val/test periods.
    strategy_info:
        Strategy metadata (name, strategy_type, hyperparams, thresholding).
        ``framework`` is derived automatically from ``name``.
    costs_info:
        Cost model parameters.
    environment_info:
        Runtime environment (python_version, platform, packages).
    artifacts_info:
        Artifacts metadata (run_dir, files, per_fold).
    git_commit:
        Git commit hash (40-char hex) or ``"unknown"``.
    pipeline_version:
        Pipeline version string (e.g. ``ai_trading.__version__``).

    Returns
    -------
    dict
        Manifest dict ready for JSON serialization.

    Raises
    ------
    ValueError
        If ``run_id``, ``git_commit``, or ``pipeline_version`` is empty,
        or if ``strategy_info["name"]`` is not in ``STRATEGY_FRAMEWORK_MAP``.
    """
    if not run_id:
        raise ValueError("run_id must be a non-empty string")
    if not git_commit:
        raise ValueError("git_commit must be a non-empty string")
    if not pipeline_version:
        raise ValueError("pipeline_version must be a non-empty string")

    strategy_name = strategy_info["name"]
    if strategy_name not in STRATEGY_FRAMEWORK_MAP:
        raise ValueError(
            f"Unknown strategy name '{strategy_name}'. "
            f"Known strategies: {sorted(STRATEGY_FRAMEWORK_MAP.keys())}"
        )

    # Derive framework from mapping
    framework = STRATEGY_FRAMEWORK_MAP[strategy_name]

    # Build strategy section with derived framework
    strategy_section: dict = {
        "strategy_type": strategy_info["strategy_type"],
        "name": strategy_name,
        "framework": framework,
    }
    if "hyperparams" in strategy_info:
        strategy_section["hyperparams"] = strategy_info["hyperparams"]
    if "thresholding" in strategy_info:
        strategy_section["thresholding"] = strategy_info["thresholding"]

    created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "run_id": run_id,
        "created_at_utc": created_at,
        "pipeline_version": pipeline_version,
        "git_commit": git_commit,
        "config_snapshot": config_snapshot,
        "dataset": dataset_info,
        "label": label_info,
        "window": window_info,
        "features": features_info,
        "splits": splits_info,
        "strategy": strategy_section,
        "costs": costs_info,
        "environment": environment_info,
        "artifacts": artifacts_info,
    }


def write_manifest(manifest_data: dict, run_dir: Path) -> None:
    """Write a manifest dict as ``manifest.json`` into *run_dir*.

    Parameters
    ----------
    manifest_data:
        Manifest dict (as returned by :func:`build_manifest`).
    run_dir:
        Target directory. Created (with parents) if it does not exist.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    output_path = run_dir / "manifest.json"
    output_path.write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
