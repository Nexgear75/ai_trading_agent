"""Full-scale integration test — make run-all on real BTCUSDT data.

Task #056 — WS-13: Test full-scale make run-all BTCUSDT.

This test executes the entire pipeline via ``make run-all`` with the fullscale
BTC configuration, then validates that all expected artefacts are produced.

**Policy M6**: NO data fixtures, NO mocks, NO synthetic data.  Only real paths
(``configs/fullscale_btc.yaml``, ``data/raw/``, ``runs/``) and real network
access are used.

Marked ``@pytest.mark.fullscale`` — excluded from default pytest runs.
Run explicitly with: ``pytest -m fullscale tests/test_fullscale_btc.py -v --timeout=600``
"""

import json
import subprocess
from pathlib import Path

import jsonschema
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

FULLSCALE_CONFIG = PROJECT_ROOT / "configs" / "fullscale_btc.yaml"
PARQUET_PATH = PROJECT_ROOT / "data" / "raw" / "BTCUSDT_1h.parquet"
RUNS_DIR = PROJECT_ROOT / "runs"
MANIFEST_SCHEMA_PATH = PROJECT_ROOT / "docs" / "specifications" / "manifest.schema.json"
METRICS_SCHEMA_PATH = PROJECT_ROOT / "docs" / "specifications" / "metrics.schema.json"

MIN_PARQUET_ROWS = 70_000


def _find_latest_run_dir(pattern: str = "*_dummy") -> Path:
    """Return the most recent run directory matching *pattern* in ``runs/``.

    Run directories follow the ``YYYYMMDD_HHMMSS_strategy`` naming convention,
    so lexicographic sort yields chronological order.
    """
    candidates = sorted(RUNS_DIR.glob(pattern))
    if not candidates:
        raise FileNotFoundError(
            f"No run directory matching '{pattern}' found in {RUNS_DIR}"
        )
    return candidates[-1]


def _load_json(path: Path) -> dict:
    """Load and return a JSON file as a dict."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise TypeError(f"Expected dict from {path}, got {type(data).__name__}")
    return data


@pytest.mark.fullscale
class TestFullscaleRunAll:
    """Execute ``make run-all`` on real BTCUSDT data and validate artefacts."""

    # ------------------------------------------------------------------
    # 1. Execute make run-all
    # ------------------------------------------------------------------

    def test_make_run_all_succeeds(self):
        """AC: make run-all CONFIG=configs/fullscale_btc.yaml exits with 0."""
        config_rel = FULLSCALE_CONFIG.relative_to(PROJECT_ROOT)
        result = subprocess.run(
            ["make", "run-all", f"CONFIG={config_rel}"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )
        assert result.returncode == 0, (
            f"make run-all failed (rc={result.returncode}).\n"
            f"--- stdout ---\n{result.stdout[-2000:]}\n"
            f"--- stderr ---\n{result.stderr[-2000:]}"
        )

    # ------------------------------------------------------------------
    # 2. Parquet data validation
    # ------------------------------------------------------------------

    def test_parquet_has_enough_rows(self):
        """AC: BTCUSDT_1h.parquet has >= 70 000 rows."""
        assert PARQUET_PATH.is_file(), f"Parquet file not found: {PARQUET_PATH}"
        df = pd.read_parquet(PARQUET_PATH)
        assert len(df) >= MIN_PARQUET_ROWS, (
            f"Expected >= {MIN_PARQUET_ROWS} rows, got {len(df)}"
        )

    # ------------------------------------------------------------------
    # 3-4. Run directory and required root artefacts
    # ------------------------------------------------------------------

    def test_run_dir_has_manifest_json(self):
        """AC: Latest run dir contains manifest.json."""
        run_dir = _find_latest_run_dir()
        assert (run_dir / "manifest.json").is_file(), (
            f"manifest.json not found in {run_dir}"
        )

    def test_run_dir_has_metrics_json(self):
        """AC: Latest run dir contains metrics.json."""
        run_dir = _find_latest_run_dir()
        assert (run_dir / "metrics.json").is_file(), (
            f"metrics.json not found in {run_dir}"
        )

    # ------------------------------------------------------------------
    # 5. JSON Schema validation
    # ------------------------------------------------------------------

    def test_manifest_json_valid_schema(self):
        """AC: manifest.json validates against manifest.schema.json."""
        run_dir = _find_latest_run_dir()
        manifest = _load_json(run_dir / "manifest.json")
        schema = _load_json(MANIFEST_SCHEMA_PATH)
        jsonschema.validate(instance=manifest, schema=schema)

    def test_metrics_json_valid_schema(self):
        """AC: metrics.json validates against metrics.schema.json."""
        run_dir = _find_latest_run_dir()
        metrics = _load_json(run_dir / "metrics.json")
        schema = _load_json(METRICS_SCHEMA_PATH)
        jsonschema.validate(instance=metrics, schema=schema)

    # ------------------------------------------------------------------
    # 6. At least 1 fold completed
    # ------------------------------------------------------------------

    def test_at_least_one_fold(self):
        """AC: At least 1 fold directory exists under folds/."""
        run_dir = _find_latest_run_dir()
        folds_dir = run_dir / "folds"
        assert folds_dir.is_dir(), f"folds/ directory not found in {run_dir}"
        fold_dirs = sorted(d for d in folds_dir.iterdir() if d.is_dir())
        assert len(fold_dirs) >= 1, "No fold directories found in folds/"

    # ------------------------------------------------------------------
    # 7. Equity curve
    # ------------------------------------------------------------------

    def test_equity_curve_exists(self):
        """AC: equity_curve.csv present at run dir root."""
        run_dir = _find_latest_run_dir()
        assert (run_dir / "equity_curve.csv").is_file(), (
            f"equity_curve.csv not found in {run_dir}"
        )

    # ------------------------------------------------------------------
    # 8. Config snapshot
    # ------------------------------------------------------------------

    def test_config_snapshot_exists(self):
        """AC: config_snapshot.yaml present in run dir."""
        run_dir = _find_latest_run_dir()
        assert (run_dir / "config_snapshot.yaml").is_file(), (
            f"config_snapshot.yaml not found in {run_dir}"
        )

    # ------------------------------------------------------------------
    # 9. Per-fold artefacts
    # ------------------------------------------------------------------

    def test_each_fold_has_metrics(self):
        """AC: Every fold has metrics_fold.json or metrics.json."""
        run_dir = _find_latest_run_dir()
        folds_dir = run_dir / "folds"
        assert folds_dir.is_dir(), f"folds/ directory not found in {run_dir}"
        fold_dirs = sorted(d for d in folds_dir.iterdir() if d.is_dir())
        assert len(fold_dirs) >= 1, "No fold directories found"
        for fold_dir in fold_dirs:
            has_metrics = (
                (fold_dir / "metrics_fold.json").is_file()
                or (fold_dir / "metrics.json").is_file()
            )
            assert has_metrics, (
                f"No metrics_fold.json or metrics.json in {fold_dir.name}"
            )

    def test_each_fold_has_trades_csv(self):
        """AC: Every fold has trades.csv."""
        run_dir = _find_latest_run_dir()
        folds_dir = run_dir / "folds"
        assert folds_dir.is_dir(), f"folds/ directory not found in {run_dir}"
        fold_dirs = sorted(d for d in folds_dir.iterdir() if d.is_dir())
        assert len(fold_dirs) >= 1, "No fold directories found"
        for fold_dir in fold_dirs:
            assert (fold_dir / "trades.csv").is_file(), (
                f"trades.csv not found in {fold_dir.name}"
            )
