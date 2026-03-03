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
import math
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from ai_trading.artifacts.validation import validate_manifest, validate_metrics

PROJECT_ROOT = Path(__file__).resolve().parent.parent

FULLSCALE_CONFIG = PROJECT_ROOT / "configs" / "fullscale_btc.yaml"
PARQUET_PATH = PROJECT_ROOT / "data" / "raw" / "BTCUSDT_1h.parquet"
RUNS_DIR = PROJECT_ROOT / "runs"

MIN_PARQUET_ROWS = 70_000

# Module-level cache: set once by test_make_run_all_succeeds, read by others.
_run_dir: Path | None = None


def _load_json(path: Path) -> dict:
    """Load and return a JSON file as a dict."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise TypeError(f"Expected dict from {path}, got {type(data).__name__}")
    return data


def _get_run_dir() -> Path:
    """Return the run directory created by the current test session.

    Raises ``pytest.skip`` if ``test_make_run_all_succeeds`` has not run yet.
    """
    if _run_dir is None:
        pytest.skip("run_dir not available — test_make_run_all_succeeds must run first")
    return _run_dir


@pytest.mark.fullscale
class TestFullscaleRunAll:
    """Execute ``make run-all`` on real BTCUSDT data and validate artefacts."""

    # ------------------------------------------------------------------
    # 1. Execute make run-all
    # ------------------------------------------------------------------

    def test_make_run_all_succeeds(self):
        """AC: make run-all CONFIG=configs/fullscale_btc.yaml exits with 0."""
        global _run_dir  # noqa: PLW0603

        # Ensure runs/ directory exists (it is gitignored and absent on fresh clones).
        RUNS_DIR.mkdir(parents=True, exist_ok=True)

        # Snapshot existing run dirs before execution.
        dirs_before = set(d for d in RUNS_DIR.iterdir() if d.is_dir())

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

        # Identify the newly created run directory.
        dirs_after = set(d for d in RUNS_DIR.iterdir() if d.is_dir())
        new_dirs = dirs_after - dirs_before
        assert len(new_dirs) == 1, (
            f"Expected exactly 1 new run dir, found {len(new_dirs)}: {new_dirs}"
        )
        _run_dir = new_dirs.pop()

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
        run_dir = _get_run_dir()
        assert (run_dir / "manifest.json").is_file(), (
            f"manifest.json not found in {run_dir}"
        )

    def test_run_dir_has_metrics_json(self):
        """AC: Latest run dir contains metrics.json."""
        run_dir = _get_run_dir()
        assert (run_dir / "metrics.json").is_file(), (
            f"metrics.json not found in {run_dir}"
        )

    # ------------------------------------------------------------------
    # 5. JSON Schema validation (reuses ai_trading.artifacts.validation)
    # ------------------------------------------------------------------

    def test_manifest_json_valid_schema(self):
        """AC: manifest.json validates against manifest.schema.json."""
        run_dir = _get_run_dir()
        manifest = _load_json(run_dir / "manifest.json")
        validate_manifest(manifest)

    def test_metrics_json_valid_schema(self):
        """AC: metrics.json validates against metrics.schema.json."""
        run_dir = _get_run_dir()
        metrics = _load_json(run_dir / "metrics.json")
        validate_metrics(metrics)

    # ------------------------------------------------------------------
    # 6. At least 1 fold completed
    # ------------------------------------------------------------------

    def test_at_least_one_fold(self):
        """AC: At least 1 fold directory exists under folds/."""
        run_dir = _get_run_dir()
        folds_dir = run_dir / "folds"
        assert folds_dir.is_dir(), f"folds/ directory not found in {run_dir}"
        fold_dirs = sorted(d for d in folds_dir.iterdir() if d.is_dir())
        assert len(fold_dirs) >= 1, "No fold directories found in folds/"

    # ------------------------------------------------------------------
    # 7. Equity curve
    # ------------------------------------------------------------------

    def test_equity_curve_exists(self):
        """AC: equity_curve.csv present at run dir root."""
        run_dir = _get_run_dir()
        assert (run_dir / "equity_curve.csv").is_file(), (
            f"equity_curve.csv not found in {run_dir}"
        )

    # ------------------------------------------------------------------
    # 8. Config snapshot
    # ------------------------------------------------------------------

    def test_config_snapshot_exists(self):
        """AC: config_snapshot.yaml present in run dir."""
        run_dir = _get_run_dir()
        assert (run_dir / "config_snapshot.yaml").is_file(), (
            f"config_snapshot.yaml not found in {run_dir}"
        )

    # ------------------------------------------------------------------
    # 9. Per-fold artefacts
    # ------------------------------------------------------------------

    def test_each_fold_has_metrics(self):
        """AC: Every fold has metrics_fold.json or metrics.json."""
        run_dir = _get_run_dir()
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
        run_dir = _get_run_dir()
        folds_dir = run_dir / "folds"
        assert folds_dir.is_dir(), f"folds/ directory not found in {run_dir}"
        fold_dirs = sorted(d for d in folds_dir.iterdir() if d.is_dir())
        assert len(fold_dirs) >= 1, "No fold directories found"
        for fold_dir in fold_dirs:
            assert (fold_dir / "trades.csv").is_file(), (
                f"trades.csv not found in {fold_dir.name}"
            )

    # ------------------------------------------------------------------
    # 10. Metrics coherence — Task #057
    # ------------------------------------------------------------------

    def test_fullscale_metrics_coherence(self):
        """#057 — Validate numerical coherence of metrics from fullscale run.

        For each fold:
        - net_pnl is a finite float
        - max_drawdown ∈ [0, 1]
        - n_trades >= 0
        - sharpe is a finite float (if not null)
        - hit_rate ∈ [0, 1] if n_trades > 0 (if not null)

        Aggregate:
        - mean and std present for each trading metric
        - All mean/std values are finite floats or null
        """
        run_dir = _get_run_dir()
        metrics = _load_json(run_dir / "metrics.json")

        # --- Per-fold validation ---
        folds = metrics["folds"]
        assert len(folds) >= 1, "metrics.json must contain at least 1 fold"

        for fold in folds:
            fold_id = fold["fold_id"]
            trading = fold["trading"]

            # net_pnl: finite float
            net_pnl = trading["net_pnl"]
            assert isinstance(net_pnl, (int, float)), (
                f"fold {fold_id}: net_pnl is not numeric: {net_pnl!r}"
            )
            assert math.isfinite(net_pnl), (
                f"fold {fold_id}: net_pnl is not finite: {net_pnl}"
            )

            # max_drawdown ∈ [0, 1]
            mdd = trading["max_drawdown"]
            assert isinstance(mdd, (int, float)), (
                f"fold {fold_id}: max_drawdown is not numeric: {mdd!r}"
            )
            assert 0.0 <= mdd <= 1.0, (
                f"fold {fold_id}: max_drawdown out of [0, 1]: {mdd}"
            )

            # n_trades >= 0
            n_trades = trading["n_trades"]
            assert isinstance(n_trades, int), (
                f"fold {fold_id}: n_trades is not int: {n_trades!r}"
            )
            assert n_trades >= 0, (
                f"fold {fold_id}: n_trades negative: {n_trades}"
            )

            # sharpe: finite float if not null
            sharpe = trading["sharpe"]
            if sharpe is not None:
                assert isinstance(sharpe, (int, float)), (
                    f"fold {fold_id}: sharpe is not numeric: {sharpe!r}"
                )
                assert math.isfinite(sharpe), (
                    f"fold {fold_id}: sharpe is not finite: {sharpe}"
                )

            # hit_rate ∈ [0, 1] if n_trades > 0 and not null
            hit_rate = trading["hit_rate"]
            if hit_rate is not None and n_trades > 0:
                assert isinstance(hit_rate, (int, float)), (
                    f"fold {fold_id}: hit_rate is not numeric: {hit_rate!r}"
                )
                assert 0.0 <= hit_rate <= 1.0, (
                    f"fold {fold_id}: hit_rate out of [0, 1]: {hit_rate}"
                )

        # --- Aggregate validation ---
        aggregate = metrics["aggregate"]
        agg_trading = aggregate["trading"]

        assert "mean" in agg_trading, "aggregate.trading missing 'mean'"
        assert "std" in agg_trading, "aggregate.trading missing 'std'"

        # Every key in mean must also be in std
        mean_keys = set(agg_trading["mean"].keys())
        std_keys = set(agg_trading["std"].keys())
        assert mean_keys == std_keys, (
            f"aggregate mean/std key mismatch: mean={mean_keys}, std={std_keys}"
        )

        # All mean values: finite floats
        for key, val in agg_trading["mean"].items():
            if val is not None:
                assert isinstance(val, (int, float)), (
                    f"aggregate.trading.mean.{key} is not numeric: {val!r}"
                )
                assert math.isfinite(val), (
                    f"aggregate.trading.mean.{key} is not finite: {val}"
                )

        # All std values: finite floats
        for key, val in agg_trading["std"].items():
            if val is not None:
                assert isinstance(val, (int, float)), (
                    f"aggregate.trading.std.{key} is not numeric: {val!r}"
                )
                assert math.isfinite(val), (
                    f"aggregate.trading.std.{key} is not finite: {val}"
                )
