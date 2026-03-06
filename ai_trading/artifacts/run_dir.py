"""Run directory creation — canonical arborescence per §15.1.

Creates the output directory structure for a pipeline run:

    <output_dir>/<run_id>/
    ├── config_snapshot.yaml
    ├── folds/
    │   ├── fold_00/
    │   │   └── model_artifacts/
    │   ├── fold_01/
    │   │   └── model_artifacts/
    │   └── ...

Task #044 — WS-11.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml

from ai_trading.config import PipelineConfig


def generate_run_id(strategy_name: str) -> str:
    """Generate a run identifier: ``YYYYMMDD_HHMMSS_<strategy>``.

    Parameters
    ----------
    strategy_name:
        Name of the strategy (e.g. ``"xgboost_reg"``).

    Returns
    -------
    str
        Run identifier string.

    Raises
    ------
    ValueError
        If *strategy_name* is empty.
    """
    if not strategy_name:
        raise ValueError("strategy_name must be a non-empty string")

    utc_now = datetime.now(UTC)
    timestamp = utc_now.strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{strategy_name}"


def save_config_snapshot(run_dir: Path, config: PipelineConfig) -> None:
    """Write the fully-resolved config as ``config_snapshot.yaml``.

    Parameters
    ----------
    run_dir:
        Path to the run directory (must already exist).
    config:
        Fully-resolved pipeline configuration.

    Raises
    ------
    FileNotFoundError
        If *run_dir* does not exist.
    """
    if not run_dir.is_dir():
        raise FileNotFoundError(
            f"run_dir does not exist: {run_dir}"
        )

    snapshot_path = run_dir / "config_snapshot.yaml"
    data = config.model_dump()
    snapshot_path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def create_run_dir(
    config: PipelineConfig,
    strategy_name: str,
    n_folds: int,
) -> Path:
    """Create the canonical run directory tree (§15.1).

    Parameters
    ----------
    config:
        Pipeline configuration (reads ``config.artifacts.output_dir``).
    strategy_name:
        Strategy name used in the run_id.
    n_folds:
        Number of walk-forward folds.

    Returns
    -------
    Path
        Absolute path to the created run directory.

    Raises
    ------
    FileNotFoundError
        If ``config.artifacts.output_dir`` does not exist.
    ValueError
        If *n_folds* < 1.
    """
    if n_folds < 1:
        raise ValueError(f"n_folds must be >= 1, got {n_folds}")

    output_dir = Path(config.artifacts.output_dir)
    if not output_dir.is_dir():
        raise FileNotFoundError(
            f"output_dir does not exist: {output_dir}"
        )

    run_id = generate_run_id(strategy_name)
    run_dir = output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Create fold subdirectories with model_artifacts
    folds_dir = run_dir / "folds"
    for i in range(n_folds):
        fold_dir = folds_dir / f"fold_{i:02d}" / "model_artifacts"
        fold_dir.mkdir(parents=True, exist_ok=True)

    # Write config snapshot
    save_config_snapshot(run_dir, config)

    return run_dir
