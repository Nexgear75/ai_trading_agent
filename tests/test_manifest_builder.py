"""Tests for manifest builder — ai_trading.artifacts.manifest.

Task #045 — WS-11.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import jsonschema
import pytest

from ai_trading.artifacts.manifest import (
    STRATEGY_FRAMEWORK_MAP,
    build_manifest,
    get_git_commit,
    write_manifest,
)

# ---------------------------------------------------------------------------
# Path to the manifest JSON schema
# ---------------------------------------------------------------------------

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "specifications"
    / "manifest.schema.json"
)


@pytest.fixture
def manifest_schema() -> dict:
    """Load the manifest JSON schema."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Helpers — minimal valid inputs
# ---------------------------------------------------------------------------


def _minimal_config_snapshot() -> dict:
    """Return a minimal config_snapshot dict."""
    return {
        "dataset": {
            "exchange": "binance",
            "symbols": ["BTCUSDT"],
            "timeframe": "1h",
            "start": "2024-01-01",
            "end": "2026-01-01",
            "timezone": "UTC",
        },
        "label": {
            "horizon_H_bars": 4,
            "target_type": "log_return_trade",
        },
        "window": {"L": 128, "min_warmup": 200},
    }


def _minimal_dataset_info() -> dict:
    """Return a minimal dataset_info dict."""
    return {
        "exchange": "binance",
        "symbols": ["BTCUSDT"],
        "timeframe": "1h",
        "start": "2024-01-01",
        "end": "2026-01-01",
        "timezone": "UTC",
        "raw_files": [
            {
                "path": "data/raw/BTCUSDT_1h.parquet",
                "sha256": "a" * 64,
                "n_rows": 17544,
            }
        ],
    }


def _minimal_splits_info() -> dict:
    """Return a minimal splits_info dict with disjoint train/val."""
    return {
        "scheme": "walk_forward_rolling",
        "train_days": 180,
        "test_days": 30,
        "step_days": 30,
        "val_frac_in_train": 0.2,
        "embargo_bars": 4,
        "folds": [
            {
                "fold_id": 0,
                "train": {
                    "start_utc": "2024-01-01T00:00:00Z",
                    "end_utc": "2024-05-23T23:00:00Z",
                },
                "val": {
                    "start_utc": "2024-05-24T00:00:00Z",
                    "end_utc": "2024-06-28T23:00:00Z",
                },
                "test": {
                    "start_utc": "2024-06-29T04:00:00Z",
                    "end_utc": "2024-07-29T03:00:00Z",
                },
            }
        ],
    }


def _minimal_strategy_info() -> dict:
    """Return a minimal strategy_info dict."""
    return {
        "strategy_type": "model",
        "name": "xgboost_reg",
        "output_type": "regression",
        "hyperparams": {"max_depth": 5, "n_estimators": 500},
        "thresholding": {
            "method": "quantile_grid",
            "q_grid": [0.5, 0.6, 0.7, 0.8, 0.9, 0.95],
            "objective": "max_net_pnl_with_mdd_cap",
            "mdd_cap": 0.25,
            "min_trades": 20,
        },
    }


def _minimal_costs_info() -> dict:
    """Return a minimal costs_info dict."""
    return {
        "cost_model": "per_side_multiplicative",
        "fee_rate_per_side": 0.0005,
        "slippage_rate_per_side": 0.00025,
    }


def _minimal_environment_info() -> dict:
    """Return a minimal environment_info dict."""
    return {
        "python_version": "3.11.0",
        "platform": "linux",
        "packages": {"numpy": "1.26.0"},
    }


def _minimal_artifacts_info() -> dict:
    """Return minimal artifacts_info dict (no pipeline_log)."""
    return {
        "run_dir": "runs/20260227_120000_xgboost_reg",
        "files": {
            "manifest_json": "manifest.json",
            "metrics_json": "metrics.json",
            "config_yaml": "config_snapshot.yaml",
        },
        "per_fold": [
            {
                "fold_id": 0,
                "files": {
                    "metrics_fold_json": "folds/fold_00/metrics_fold.json",
                },
            }
        ],
    }


def _build_minimal_manifest(**overrides) -> dict:
    """Build a manifest with minimal valid inputs, applying overrides."""
    kwargs = {
        "run_id": "20260227_120000_xgboost_reg",
        "config_snapshot": _minimal_config_snapshot(),
        "dataset_info": _minimal_dataset_info(),
        "label_info": {
            "horizon_H_bars": 4,
            "target_type": "log_return_trade",
            "definition": "log(Close[t+H]/Open[t+1])",
        },
        "window_info": {"L": 128, "min_warmup": 200},
        "features_info": {
            "feature_list": [
                "logret_1", "logret_2", "logret_4",
                "vol_24", "vol_72", "logvol", "dlogvol",
                "rsi_14", "ema_ratio_12_26",
            ],
            "feature_version": "mvp_v1",
        },
        "splits_info": _minimal_splits_info(),
        "strategy_info": _minimal_strategy_info(),
        "costs_info": _minimal_costs_info(),
        "environment_info": _minimal_environment_info(),
        "artifacts_info": _minimal_artifacts_info(),
        "git_commit": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "pipeline_version": "1.0.0",
    }
    kwargs.update(overrides)
    return build_manifest(**kwargs)


# ===================================================================
# AC-1: Module exists and is importable
# ===================================================================

class TestModuleImportable:
    """#045 — AC-1: ai_trading.artifacts.manifest is importable."""

    def test_import_build_manifest(self):
        """build_manifest is importable."""
        assert callable(build_manifest)

    def test_import_write_manifest(self):
        """write_manifest is importable."""
        assert callable(write_manifest)

    def test_import_get_git_commit(self):
        """get_git_commit is importable."""
        assert callable(get_git_commit)

    def test_import_strategy_framework_map(self):
        """STRATEGY_FRAMEWORK_MAP is importable."""
        assert isinstance(STRATEGY_FRAMEWORK_MAP, dict)


# ===================================================================
# AC-2: JSON validates against manifest.schema.json
# ===================================================================

class TestSchemaValidation:
    """#045 — AC-2: manifest validates against the JSON schema."""

    def test_manifest_validates_against_schema(self, manifest_schema):
        """Nominal manifest passes schema validation."""
        manifest = _build_minimal_manifest()
        jsonschema.validate(instance=manifest, schema=manifest_schema)

    def test_manifest_with_pipeline_log_validates(self, manifest_schema):
        """Manifest with pipeline_log field validates."""
        artifacts = _minimal_artifacts_info()
        artifacts["files"]["pipeline_log"] = "pipeline.log"
        manifest = _build_minimal_manifest(artifacts_info=artifacts)
        jsonschema.validate(instance=manifest, schema=manifest_schema)

    def test_manifest_multi_fold_validates(self, manifest_schema):
        """Manifest with multiple folds validates."""
        splits = _minimal_splits_info()
        splits["folds"].append({
            "fold_id": 1,
            "train": {
                "start_utc": "2024-02-01T00:00:00Z",
                "end_utc": "2024-06-22T23:00:00Z",
            },
            "val": {
                "start_utc": "2024-06-23T00:00:00Z",
                "end_utc": "2024-07-28T23:00:00Z",
            },
            "test": {
                "start_utc": "2024-07-29T04:00:00Z",
                "end_utc": "2024-08-28T03:00:00Z",
            },
        })
        artifacts = _minimal_artifacts_info()
        artifacts["per_fold"].append({
            "fold_id": 1,
            "files": {
                "metrics_fold_json": "folds/fold_01/metrics_fold.json",
            },
        })
        manifest = _build_minimal_manifest(
            splits_info=splits,
            artifacts_info=artifacts,
        )
        jsonschema.validate(instance=manifest, schema=manifest_schema)


# ===================================================================
# AC-3: Train period excludes val (disjoint bounds)
# ===================================================================

class TestTrainExcludesVal:
    """#045 — AC-3: train and val periods are disjoint per fold."""

    def test_train_end_before_val_start(self):
        """Train end_utc < val start_utc for each fold."""
        manifest = _build_minimal_manifest()
        for fold in manifest["splits"]["folds"]:
            train_end = fold["train"]["end_utc"]
            val_start = fold["val"]["start_utc"]
            assert train_end < val_start, (
                f"fold {fold['fold_id']}: train.end_utc={train_end} "
                f"must be < val.start_utc={val_start}"
            )


# ===================================================================
# AC-4: git_commit field — valid hex hash or "unknown"
# ===================================================================

class TestGitCommit:
    """#045 — AC-4: git_commit is a 40-char hex or 'unknown'."""

    def test_git_commit_hex_hash(self):
        """Manifest contains the provided hex git_commit."""
        commit = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
        manifest = _build_minimal_manifest(git_commit=commit)
        assert manifest["git_commit"] == commit

    def test_git_commit_unknown(self):
        """Manifest accepts 'unknown' as git_commit."""
        manifest = _build_minimal_manifest(git_commit="unknown")
        assert manifest["git_commit"] == "unknown"

    def test_get_git_commit_returns_hex_in_repo(self):
        """get_git_commit returns a 40-char hex string inside a Git repo."""
        # We're running inside the ai_trading repo, so this should work.
        result = get_git_commit()
        assert len(result) == 40
        assert all(c in "0123456789abcdef" for c in result)

    def test_get_git_commit_returns_unknown_outside_repo(self, tmp_path, caplog):
        """get_git_commit returns 'unknown' + WARNING when not in a Git repo."""
        import logging

        with caplog.at_level(logging.WARNING):
            result = get_git_commit(working_dir=tmp_path)
        assert result == "unknown"
        assert any("unknown" in rec.message.lower() or "git" in rec.message.lower()
                    for rec in caplog.records)


# ===================================================================
# AC-5: pipeline_version matches ai_trading.__version__
# ===================================================================

class TestPipelineVersion:
    """#045 — AC-5: pipeline_version in manifest."""

    def test_pipeline_version_matches(self):
        """pipeline_version matches the provided value."""
        manifest = _build_minimal_manifest(pipeline_version="1.0.0")
        assert manifest["pipeline_version"] == "1.0.0"

    def test_pipeline_version_string(self):
        """pipeline_version is a string."""
        manifest = _build_minimal_manifest()
        assert isinstance(manifest["pipeline_version"], str)


# ===================================================================
# AC-6: Conditional pipeline_log field
# ===================================================================

class TestPipelineLogConditional:
    """#045 — AC-6: pipeline_log present only if configured."""

    def test_pipeline_log_absent_when_not_in_artifacts(self):
        """pipeline_log not in files when not provided."""
        artifacts = _minimal_artifacts_info()
        assert "pipeline_log" not in artifacts["files"]
        manifest = _build_minimal_manifest(artifacts_info=artifacts)
        assert "pipeline_log" not in manifest["artifacts"]["files"]

    def test_pipeline_log_present_when_in_artifacts(self):
        """pipeline_log in files when provided."""
        artifacts = _minimal_artifacts_info()
        artifacts["files"]["pipeline_log"] = "pipeline.log"
        manifest = _build_minimal_manifest(artifacts_info=artifacts)
        assert manifest["artifacts"]["files"]["pipeline_log"] == "pipeline.log"


# ===================================================================
# AC-7: STRATEGY_FRAMEWORK_MAP derivation
# ===================================================================

class TestStrategyFrameworkMap:
    """#045 — AC-7: strategy.framework derived from name via mapping."""

    @pytest.mark.parametrize("name,expected_framework", [
        ("dummy", "internal"),
        ("no_trade", "baseline"),
        ("buy_hold", "baseline"),
        ("sma_rule", "baseline"),
        ("xgboost_reg", "xgboost"),
        ("cnn1d_reg", "pytorch"),
        ("gru_reg", "pytorch"),
        ("lstm_reg", "pytorch"),
        ("patchtst_reg", "pytorch"),
        ("rl_ppo", "pytorch"),
    ])
    def test_framework_derived_for_known_strategies(
        self, name, expected_framework
    ):
        """strategy.framework is correctly derived for each known strategy."""
        strategy = _minimal_strategy_info()
        strategy["name"] = name
        # Adjust strategy_type for baselines
        if name in ("no_trade", "buy_hold", "sma_rule"):
            strategy["strategy_type"] = "baseline"
        elif name == "dummy":
            strategy["strategy_type"] = "model"
        manifest = _build_minimal_manifest(strategy_info=strategy)
        assert manifest["strategy"]["framework"] == expected_framework

    def test_framework_map_contains_all_mvp_strategies(self):
        """STRATEGY_FRAMEWORK_MAP covers all known MVP strategies."""
        expected_names = {
            "dummy", "xgboost_reg", "cnn1d_reg", "gru_reg",
            "lstm_reg", "patchtst_reg", "rl_ppo",
            "no_trade", "buy_hold", "sma_rule",
        }
        assert set(STRATEGY_FRAMEWORK_MAP.keys()) == expected_names

    def test_unknown_strategy_raises(self):
        """Unknown strategy name raises ValueError."""
        strategy = _minimal_strategy_info()
        strategy["name"] = "unknown_model"
        with pytest.raises(ValueError, match="unknown_model"):
            _build_minimal_manifest(strategy_info=strategy)


# ===================================================================
# Nominal: build_manifest produces all required top-level keys
# ===================================================================

class TestBuildManifestStructure:
    """#045 — Nominal: manifest structure and required keys."""

    def test_all_required_top_level_keys(self):
        """Manifest contains all required top-level keys per schema."""
        manifest = _build_minimal_manifest()
        required_keys = {
            "run_id", "created_at_utc", "pipeline_version", "git_commit",
            "config_snapshot", "dataset", "label", "window", "features",
            "splits", "strategy", "costs", "environment", "artifacts",
        }
        assert required_keys <= set(manifest.keys())

    def test_run_id_passthrough(self):
        """run_id is passed through to manifest."""
        manifest = _build_minimal_manifest(run_id="my_run_123")
        assert manifest["run_id"] == "my_run_123"

    def test_created_at_utc_is_iso_format(self):
        """created_at_utc is a valid ISO 8601 datetime string."""
        manifest = _build_minimal_manifest()
        dt = datetime.fromisoformat(manifest["created_at_utc"])
        assert dt.tzinfo is not None  # Timezone-aware

    def test_config_snapshot_passthrough(self):
        """config_snapshot is passed through."""
        snapshot = _minimal_config_snapshot()
        manifest = _build_minimal_manifest(config_snapshot=snapshot)
        assert manifest["config_snapshot"] == snapshot

    def test_dataset_passthrough(self):
        """dataset section is passed through."""
        manifest = _build_minimal_manifest()
        assert manifest["dataset"]["exchange"] == "binance"
        assert manifest["dataset"]["raw_files"][0]["sha256"] == "a" * 64

    def test_splits_passthrough(self):
        """splits section is passed through with folds."""
        manifest = _build_minimal_manifest()
        assert manifest["splits"]["scheme"] == "walk_forward_rolling"
        assert len(manifest["splits"]["folds"]) == 1

    def test_costs_passthrough(self):
        """costs section is passed through."""
        manifest = _build_minimal_manifest()
        assert manifest["costs"]["cost_model"] == "per_side_multiplicative"

    def test_environment_passthrough(self):
        """environment section is passed through."""
        manifest = _build_minimal_manifest()
        assert manifest["environment"]["python_version"] == "3.11.0"


# ===================================================================
# write_manifest — file I/O
# ===================================================================

class TestWriteManifest:
    """#045 — write_manifest writes valid JSON to run_dir."""

    def test_writes_manifest_json(self, tmp_path):
        """write_manifest creates manifest.json in run_dir."""
        manifest = _build_minimal_manifest()
        write_manifest(manifest, tmp_path)
        output_path = tmp_path / "manifest.json"
        assert output_path.exists()
        loaded = json.loads(output_path.read_text(encoding="utf-8"))
        assert loaded["run_id"] == manifest["run_id"]

    def test_written_json_is_valid(self, tmp_path, manifest_schema):
        """Written manifest.json validates against schema."""
        manifest = _build_minimal_manifest()
        write_manifest(manifest, tmp_path)
        output_path = tmp_path / "manifest.json"
        loaded = json.loads(output_path.read_text(encoding="utf-8"))
        jsonschema.validate(instance=loaded, schema=manifest_schema)

    def test_write_manifest_creates_run_dir(self, tmp_path):
        """write_manifest creates run_dir if it does not exist."""
        run_dir = tmp_path / "nested" / "run_dir"
        manifest = _build_minimal_manifest()
        write_manifest(manifest, run_dir)
        assert (run_dir / "manifest.json").exists()

    def test_json_indented(self, tmp_path):
        """Written JSON is human-readable (indented)."""
        manifest = _build_minimal_manifest()
        write_manifest(manifest, tmp_path)
        text = (tmp_path / "manifest.json").read_text(encoding="utf-8")
        # Indented JSON has newlines and spaces
        assert "\n" in text
        assert "  " in text


# ===================================================================
# Error cases — missing required inputs
# ===================================================================

class TestBuildManifestErrors:
    """#045 — Error cases for build_manifest."""

    def test_missing_run_id_raises(self):
        """Calling without run_id raises TypeError."""
        with pytest.raises(TypeError):
            build_manifest(  # type: ignore[call-arg]
                config_snapshot=_minimal_config_snapshot(),
                dataset_info=_minimal_dataset_info(),
                label_info={"horizon_H_bars": 4, "target_type": "log_return_trade"},
                window_info={"L": 128, "min_warmup": 200},
                features_info={"feature_list": ["logret_1"], "feature_version": "mvp_v1"},
                splits_info=_minimal_splits_info(),
                strategy_info=_minimal_strategy_info(),
                costs_info=_minimal_costs_info(),
                environment_info=_minimal_environment_info(),
                artifacts_info=_minimal_artifacts_info(),
                git_commit="abc123",
                pipeline_version="1.0.0",
            )

    def test_empty_run_id_raises(self):
        """Empty run_id raises ValueError."""
        with pytest.raises(ValueError, match="run_id"):
            _build_minimal_manifest(run_id="")

    def test_empty_pipeline_version_raises(self):
        """Empty pipeline_version raises ValueError."""
        with pytest.raises(ValueError, match="pipeline_version"):
            _build_minimal_manifest(pipeline_version="")

    def test_empty_git_commit_raises(self):
        """Empty git_commit raises ValueError."""
        with pytest.raises(ValueError, match="git_commit"):
            _build_minimal_manifest(git_commit="")
