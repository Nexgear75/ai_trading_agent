"""Tests for scripts/dashboard/data_loader.py — run discovery and validation.

Task #074 — WS-D-1: Data loader discovery and validation of runs.

Verifies:
- discover_runs() discovers valid runs, excludes dummy, handles empty/broken
- load_run_metrics() validates required keys, raises on missing
- load_run_manifest() loads manifest.json
- load_config_snapshot() loads config_snapshot.yaml
- DRY with scripts/compare_runs.py (shared validation logic)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Helpers — synthetic run directory builders
# ---------------------------------------------------------------------------


def _make_metrics_dict(
    *,
    run_id: str = "run_001",
    strategy_name: str = "xgboost_reg",
    strategy_type: str = "model",
) -> dict:
    """Build a minimal valid metrics.json dict."""
    return {
        "run_id": run_id,
        "strategy": {
            "strategy_type": strategy_type,
            "name": strategy_name,
        },
        "aggregate": {
            "trading": {
                "mean": {
                    "net_pnl": 100.0,
                    "max_drawdown": -0.05,
                    "sharpe": 1.2,
                    "profit_factor": 1.5,
                    "n_trades": 10,
                    "net_return": 0.05,
                },
                "std": {
                    "net_pnl": 10.0,
                    "max_drawdown": 0.02,
                    "sharpe": 0.3,
                    "profit_factor": 0.2,
                    "n_trades": 2,
                    "net_return": 0.01,
                },
            },
            "prediction": {
                "mean": {"mae": 0.01, "rmse": 0.02, "directional_accuracy": 0.55},
                "std": {"mae": 0.001, "rmse": 0.002, "directional_accuracy": 0.03},
            },
        },
        "folds": [],
    }


def _write_run(
    runs_dir: Path,
    run_id: str,
    *,
    strategy_name: str = "xgboost_reg",
    strategy_type: str = "model",
    include_manifest: bool = True,
    include_config: bool = True,
) -> Path:
    """Create a synthetic run directory with metrics.json (and optionally others)."""
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    metrics = _make_metrics_dict(
        run_id=run_id,
        strategy_name=strategy_name,
        strategy_type=strategy_type,
    )
    (run_dir / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")

    if include_manifest:
        manifest = {"run_id": run_id, "status": "completed"}
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

    if include_config:
        config = {"strategy": {"name": strategy_name}}
        (run_dir / "config_snapshot.yaml").write_text(
            yaml.dump(config), encoding="utf-8"
        )

    return run_dir


# ---------------------------------------------------------------------------
# §1 — discover_runs
# ---------------------------------------------------------------------------


class TestDiscoverRuns:
    """Tests for discover_runs()."""

    def test_valid_run_discovered(self, tmp_path: Path) -> None:
        """#074 — A valid run with metrics.json is discovered."""
        from scripts.dashboard.data_loader import discover_runs

        _write_run(tmp_path, "run_001")
        result = discover_runs(tmp_path)
        assert len(result) == 1
        assert result[0]["run_id"] == "run_001"

    def test_multiple_valid_runs(self, tmp_path: Path) -> None:
        """#074 — Multiple valid runs are all discovered."""
        from scripts.dashboard.data_loader import discover_runs

        _write_run(tmp_path, "run_001")
        _write_run(tmp_path, "run_002", strategy_name="sma_rule", strategy_type="baseline")
        result = discover_runs(tmp_path)
        assert len(result) == 2
        run_ids = {r["run_id"] for r in result}
        assert run_ids == {"run_001", "run_002"}

    def test_dummy_run_excluded(self, tmp_path: Path) -> None:
        """#074 — A run with strategy.name == 'dummy' is excluded."""
        from scripts.dashboard.data_loader import discover_runs

        _write_run(tmp_path, "run_valid")
        _write_run(tmp_path, "run_dummy", strategy_name="dummy", strategy_type="model")
        result = discover_runs(tmp_path)
        assert len(result) == 1
        assert result[0]["run_id"] == "run_valid"

    def test_empty_directory(self, tmp_path: Path) -> None:
        """#074 — Empty runs directory returns empty list."""
        from scripts.dashboard.data_loader import discover_runs

        result = discover_runs(tmp_path)
        assert result == []

    def test_missing_metrics_json_excluded(self, tmp_path: Path) -> None:
        """#074 — A run directory without metrics.json is excluded."""
        from scripts.dashboard.data_loader import discover_runs

        (tmp_path / "run_no_metrics").mkdir()
        _write_run(tmp_path, "run_valid")
        result = discover_runs(tmp_path)
        assert len(result) == 1
        assert result[0]["run_id"] == "run_valid"

    def test_broken_json_excluded_and_logged(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """#074 — Broken JSON in metrics.json is logged but doesn't crash."""
        from scripts.dashboard.data_loader import discover_runs

        # Create a run with broken JSON
        broken_dir = tmp_path / "run_broken"
        broken_dir.mkdir()
        (broken_dir / "metrics.json").write_text("{invalid json", encoding="utf-8")

        # Create a valid run
        _write_run(tmp_path, "run_valid")

        with caplog.at_level(logging.WARNING):
            result = discover_runs(tmp_path)

        assert len(result) == 1
        assert result[0]["run_id"] == "run_valid"
        # Check that warning was logged for the broken run
        assert any("run_broken" in msg for msg in caplog.messages)

    def test_missing_required_keys_excluded_and_logged(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """#074 — metrics.json missing required keys is excluded and logged."""
        from scripts.dashboard.data_loader import discover_runs

        # Create a run with incomplete metrics
        incomplete_dir = tmp_path / "run_incomplete"
        incomplete_dir.mkdir()
        incomplete_metrics = {"run_id": "run_incomplete"}  # missing strategy, aggregate
        (incomplete_dir / "metrics.json").write_text(
            json.dumps(incomplete_metrics), encoding="utf-8"
        )

        _write_run(tmp_path, "run_valid")

        with caplog.at_level(logging.WARNING):
            result = discover_runs(tmp_path)

        assert len(result) == 1
        assert result[0]["run_id"] == "run_valid"
        assert any("run_incomplete" in msg for msg in caplog.messages)

    def test_non_directory_entries_ignored(self, tmp_path: Path) -> None:
        """#074 — Regular files at root of runs_dir are ignored."""
        from scripts.dashboard.data_loader import discover_runs

        # Create a file (not a directory) in runs_dir
        (tmp_path / "some_file.txt").write_text("not a run", encoding="utf-8")
        _write_run(tmp_path, "run_valid")
        result = discover_runs(tmp_path)
        assert len(result) == 1

    def test_non_dict_strategy_excluded_and_logged(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """#074 — Run with non-dict strategy is excluded and logged."""
        from scripts.dashboard.data_loader import discover_runs

        bad_dir = tmp_path / "run_bad_strategy"
        bad_dir.mkdir()
        bad_metrics = {"run_id": "run_bad_strategy", "strategy": "xgboost", "aggregate": {}}
        (bad_dir / "metrics.json").write_text(json.dumps(bad_metrics), encoding="utf-8")

        _write_run(tmp_path, "run_valid")

        with caplog.at_level(logging.WARNING):
            result = discover_runs(tmp_path)

        assert len(result) == 1
        assert result[0]["run_id"] == "run_valid"
        assert any("run_bad_strategy" in msg for msg in caplog.messages)


# ---------------------------------------------------------------------------
# §2 — load_run_metrics
# ---------------------------------------------------------------------------


class TestLoadRunMetrics:
    """Tests for load_run_metrics()."""

    def test_valid_metrics(self, tmp_path: Path) -> None:
        """#074 — Valid metrics.json is loaded and returned."""
        from scripts.dashboard.data_loader import load_run_metrics

        run_dir = _write_run(tmp_path, "run_001")
        result = load_run_metrics(run_dir)
        assert result["run_id"] == "run_001"
        assert "strategy" in result
        assert "aggregate" in result

    def test_missing_run_id_raises(self, tmp_path: Path) -> None:
        """#074 — Missing 'run_id' key raises ValueError."""
        from scripts.dashboard.data_loader import load_run_metrics

        run_dir = tmp_path / "run_bad"
        run_dir.mkdir()
        bad_metrics = {"strategy": {"name": "x", "strategy_type": "model"}, "aggregate": {}}
        (run_dir / "metrics.json").write_text(
            json.dumps(bad_metrics), encoding="utf-8"
        )
        with pytest.raises(ValueError, match="run_id"):
            load_run_metrics(run_dir)

    def test_missing_strategy_raises(self, tmp_path: Path) -> None:
        """#074 — Missing 'strategy' key raises ValueError."""
        from scripts.dashboard.data_loader import load_run_metrics

        run_dir = tmp_path / "run_bad"
        run_dir.mkdir()
        bad_metrics = {"run_id": "x", "aggregate": {}}
        (run_dir / "metrics.json").write_text(
            json.dumps(bad_metrics), encoding="utf-8"
        )
        with pytest.raises(ValueError, match="strategy"):
            load_run_metrics(run_dir)

    def test_missing_aggregate_raises(self, tmp_path: Path) -> None:
        """#074 — Missing 'aggregate' key raises ValueError."""
        from scripts.dashboard.data_loader import load_run_metrics

        run_dir = tmp_path / "run_bad"
        run_dir.mkdir()
        bad_metrics = {"run_id": "x", "strategy": {"name": "x", "strategy_type": "model"}}
        (run_dir / "metrics.json").write_text(
            json.dumps(bad_metrics), encoding="utf-8"
        )
        with pytest.raises(ValueError, match="aggregate"):
            load_run_metrics(run_dir)

    def test_broken_json_raises(self, tmp_path: Path) -> None:
        """#074 — Broken JSON in metrics.json raises ValueError."""
        from scripts.dashboard.data_loader import load_run_metrics

        run_dir = tmp_path / "run_bad"
        run_dir.mkdir()
        (run_dir / "metrics.json").write_text("not json{", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid JSON"):
            load_run_metrics(run_dir)

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        """#074 — Missing metrics.json raises FileNotFoundError."""
        from scripts.dashboard.data_loader import load_run_metrics

        run_dir = tmp_path / "run_empty"
        run_dir.mkdir()
        with pytest.raises(FileNotFoundError):
            load_run_metrics(run_dir)

    def test_non_dict_json_raises(self, tmp_path: Path) -> None:
        """#074 — metrics.json containing a list raises ValueError."""
        from scripts.dashboard.data_loader import load_run_metrics

        run_dir = tmp_path / "run_bad"
        run_dir.mkdir()
        (run_dir / "metrics.json").write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(ValueError, match="JSON object"):
            load_run_metrics(run_dir)

    def test_strategy_not_dict_raises(self, tmp_path: Path) -> None:
        """#074 — strategy value that is not a dict raises ValueError."""
        from scripts.dashboard.data_loader import load_run_metrics

        run_dir = tmp_path / "run_bad"
        run_dir.mkdir()
        bad_metrics = {"run_id": "x", "strategy": "xgboost", "aggregate": {}}
        (run_dir / "metrics.json").write_text(
            json.dumps(bad_metrics), encoding="utf-8"
        )
        with pytest.raises(ValueError, match="'strategy' must be a JSON object"):
            load_run_metrics(run_dir)


# ---------------------------------------------------------------------------
# §3 — load_run_manifest
# ---------------------------------------------------------------------------


class TestLoadRunManifest:
    """Tests for load_run_manifest()."""

    def test_valid_manifest(self, tmp_path: Path) -> None:
        """#074 — Valid manifest.json is loaded and returned."""
        from scripts.dashboard.data_loader import load_run_manifest

        run_dir = _write_run(tmp_path, "run_001")
        result = load_run_manifest(run_dir)
        assert result["run_id"] == "run_001"
        assert result["status"] == "completed"

    def test_missing_manifest_raises(self, tmp_path: Path) -> None:
        """#074 — Missing manifest.json raises FileNotFoundError."""
        from scripts.dashboard.data_loader import load_run_manifest

        run_dir = tmp_path / "run_no_manifest"
        run_dir.mkdir()
        with pytest.raises(FileNotFoundError):
            load_run_manifest(run_dir)

    def test_broken_manifest_raises(self, tmp_path: Path) -> None:
        """#074 — Broken JSON in manifest.json raises ValueError."""
        from scripts.dashboard.data_loader import load_run_manifest

        run_dir = tmp_path / "run_bad"
        run_dir.mkdir()
        (run_dir / "manifest.json").write_text("{broken", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid JSON"):
            load_run_manifest(run_dir)


# ---------------------------------------------------------------------------
# §4 — load_config_snapshot
# ---------------------------------------------------------------------------


class TestLoadConfigSnapshot:
    """Tests for load_config_snapshot()."""

    def test_valid_config(self, tmp_path: Path) -> None:
        """#074 — Valid config_snapshot.yaml is loaded and returned."""
        from scripts.dashboard.data_loader import load_config_snapshot

        run_dir = _write_run(tmp_path, "run_001")
        result = load_config_snapshot(run_dir)
        assert result["strategy"]["name"] == "xgboost_reg"

    def test_missing_config_raises(self, tmp_path: Path) -> None:
        """#074 — Missing config_snapshot.yaml raises FileNotFoundError."""
        from scripts.dashboard.data_loader import load_config_snapshot

        run_dir = tmp_path / "run_no_config"
        run_dir.mkdir()
        with pytest.raises(FileNotFoundError):
            load_config_snapshot(run_dir)

    def test_broken_yaml_raises(self, tmp_path: Path) -> None:
        """#074 — Broken YAML raises ValueError."""
        from scripts.dashboard.data_loader import load_config_snapshot

        run_dir = tmp_path / "run_bad"
        run_dir.mkdir()
        (run_dir / "config_snapshot.yaml").write_text(
            ":\n  :\n    - broken: [", encoding="utf-8"
        )
        with pytest.raises(ValueError, match="invalid YAML"):
            load_config_snapshot(run_dir)


# ---------------------------------------------------------------------------
# §5 — DRY: compare_runs.py uses shared validation
# ---------------------------------------------------------------------------


class TestDRYWithCompareRuns:
    """Verify that compare_runs.py imports validation logic from data_loader."""

    def test_compare_runs_imports_from_data_loader(self) -> None:
        """#074 — compare_runs.py must import validation constants from data_loader."""
        import ast
        from pathlib import Path

        compare_runs_path = (
            Path(__file__).resolve().parent.parent / "scripts" / "compare_runs.py"
        )
        source = compare_runs_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Check that compare_runs.py imports from scripts.dashboard.data_loader
        imports_from_data_loader = False
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and "data_loader" in node.module
            ):
                imports_from_data_loader = True
                break
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "data_loader" in alias.name:
                        imports_from_data_loader = True
                        break

        assert imports_from_data_loader, (
            "compare_runs.py must import from data_loader for DRY compliance"
        )

    def test_no_duplicate_required_keys_constant(self) -> None:
        """#074 — REQUIRED_TOP_KEYS must not be re-assigned in compare_runs.py."""
        import ast
        from pathlib import Path

        compare_runs_path = (
            Path(__file__).resolve().parent.parent / "scripts" / "compare_runs.py"
        )
        source = compare_runs_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Verify REQUIRED_TOP_KEYS is not re-assigned in compare_runs.py
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "REQUIRED_TOP_KEYS":
                        pytest.fail(
                            "REQUIRED_TOP_KEYS redefined in compare_runs.py — "
                            "should be imported from data_loader"
                        )
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "REQUIRED_STRATEGY_KEYS":
                        pytest.fail(
                            "REQUIRED_STRATEGY_KEYS redefined in compare_runs.py — "
                            "should be imported from data_loader"
                        )
