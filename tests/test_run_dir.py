"""Tests for ai_trading/artifacts/run_dir.py — run directory creation.

Task #044 — WS-11: Arborescence du run (run_dir).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import yaml

from ai_trading.config import load_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_default_config():
    """Load the default pipeline config for use in tests."""
    root = Path(__file__).resolve().parent.parent
    return load_config(str(root / "configs" / "default.yaml"))


# ---------------------------------------------------------------------------
# generate_run_id
# ---------------------------------------------------------------------------


class TestGenerateRunId:
    """Tests for generate_run_id function."""

    def test_format_matches_spec(self):
        """#044 — run_id matches YYYYMMDD_HHMMSS_<strategy> format."""
        from ai_trading.artifacts.run_dir import generate_run_id

        run_id = generate_run_id("xgboost_reg")
        pattern = r"^\d{8}_\d{6}_xgboost_reg$"
        assert re.match(pattern, run_id), f"run_id '{run_id}' does not match pattern"

    def test_uses_utc_time(self):
        """#044 — run_id is generated from UTC time, not local."""
        from ai_trading.artifacts.run_dir import generate_run_id

        fake_utc = datetime(2026, 3, 1, 14, 30, 45, tzinfo=UTC)
        with patch("ai_trading.artifacts.run_dir.datetime") as mock_dt:
            mock_dt.now.return_value = fake_utc
            mock_dt.UTC = UTC
            run_id = generate_run_id("lstm_reg")

        assert run_id == "20260301_143045_lstm_reg"
        mock_dt.now.assert_called_once_with(UTC)

    def test_different_strategy_names(self):
        """#044 — run_id contains the strategy name."""
        from ai_trading.artifacts.run_dir import generate_run_id

        run_id = generate_run_id("buy_hold")
        assert run_id.endswith("_buy_hold")

    def test_empty_strategy_raises(self):
        """#044 — empty strategy name is rejected."""
        import pytest

        from ai_trading.artifacts.run_dir import generate_run_id

        with pytest.raises(ValueError, match="strategy_name"):
            generate_run_id("")


# ---------------------------------------------------------------------------
# save_config_snapshot
# ---------------------------------------------------------------------------


class TestSaveConfigSnapshot:
    """Tests for save_config_snapshot function."""

    def test_writes_yaml_file(self, tmp_path):
        """#044 — config_snapshot.yaml is written in run_dir."""
        from ai_trading.artifacts.run_dir import save_config_snapshot

        config = _load_default_config()
        run_dir = tmp_path / "test_run"
        run_dir.mkdir()

        save_config_snapshot(run_dir, config)

        snapshot_path = run_dir / "config_snapshot.yaml"
        assert snapshot_path.exists()

    def test_content_is_valid_yaml(self, tmp_path):
        """#044 — config_snapshot.yaml contains valid, loadable YAML."""
        from ai_trading.artifacts.run_dir import save_config_snapshot

        config = _load_default_config()
        run_dir = tmp_path / "test_run"
        run_dir.mkdir()

        save_config_snapshot(run_dir, config)

        snapshot_path = run_dir / "config_snapshot.yaml"
        with open(snapshot_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert isinstance(data, dict)
        # Verify key sections are present
        assert "dataset" in data
        assert "features" in data
        assert "artifacts" in data

    def test_snapshot_preserves_config_values(self, tmp_path):
        """#044 — snapshot reflects the fully-resolved config."""
        from ai_trading.artifacts.run_dir import save_config_snapshot

        config = _load_default_config()
        run_dir = tmp_path / "test_run"
        run_dir.mkdir()

        save_config_snapshot(run_dir, config)

        snapshot_path = run_dir / "config_snapshot.yaml"
        with open(snapshot_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["artifacts"]["output_dir"] == config.artifacts.output_dir
        assert data["label"]["horizon_H_bars"] == config.label.horizon_H_bars

    def test_run_dir_not_existing_raises(self, tmp_path):
        """#044 — save_config_snapshot raises if run_dir doesn't exist."""
        import pytest

        from ai_trading.artifacts.run_dir import save_config_snapshot

        config = _load_default_config()
        missing_dir = tmp_path / "nonexistent"

        with pytest.raises(FileNotFoundError):
            save_config_snapshot(missing_dir, config)


# ---------------------------------------------------------------------------
# create_run_dir
# ---------------------------------------------------------------------------


class TestCreateRunDir:
    """Tests for create_run_dir function."""

    def test_creates_run_directory(self, tmp_path, default_yaml_data, tmp_yaml):
        """#044 — create_run_dir creates the run directory under output_dir."""
        from ai_trading.artifacts.run_dir import create_run_dir

        default_yaml_data["artifacts"]["output_dir"] = str(tmp_path / "runs")
        (tmp_path / "runs").mkdir()
        cfg_path = tmp_yaml(default_yaml_data)
        config = load_config(cfg_path)

        run_dir = create_run_dir(config, "xgboost_reg", n_folds=3)

        assert run_dir.exists()
        assert run_dir.is_dir()

    def test_run_dir_under_output_dir(self, tmp_path, default_yaml_data, tmp_yaml):
        """#044 — run_dir is a child of config.artifacts.output_dir."""
        from ai_trading.artifacts.run_dir import create_run_dir

        output = tmp_path / "my_runs"
        output.mkdir()
        default_yaml_data["artifacts"]["output_dir"] = str(output)
        cfg_path = tmp_yaml(default_yaml_data)
        config = load_config(cfg_path)

        run_dir = create_run_dir(config, "gru_reg", n_folds=2)

        assert run_dir.parent == output

    def test_folds_subdirectories_created(self, tmp_path, default_yaml_data, tmp_yaml):
        """#044 — fold_00..fold_{n-1} directories are created under folds/."""
        from ai_trading.artifacts.run_dir import create_run_dir

        output = tmp_path / "runs"
        output.mkdir()
        default_yaml_data["artifacts"]["output_dir"] = str(output)
        cfg_path = tmp_yaml(default_yaml_data)
        config = load_config(cfg_path)

        run_dir = create_run_dir(config, "cnn1d_reg", n_folds=4)

        folds_dir = run_dir / "folds"
        assert folds_dir.is_dir()
        for i in range(4):
            fold_path = folds_dir / f"fold_{i:02d}"
            assert fold_path.is_dir(), f"fold_{i:02d} not created"

    def test_model_artifacts_per_fold(self, tmp_path, default_yaml_data, tmp_yaml):
        """#044 — each fold has a model_artifacts/ subdirectory."""
        from ai_trading.artifacts.run_dir import create_run_dir

        output = tmp_path / "runs"
        output.mkdir()
        default_yaml_data["artifacts"]["output_dir"] = str(output)
        cfg_path = tmp_yaml(default_yaml_data)
        config = load_config(cfg_path)

        run_dir = create_run_dir(config, "lstm_reg", n_folds=3)

        for i in range(3):
            ma = run_dir / "folds" / f"fold_{i:02d}" / "model_artifacts"
            assert ma.is_dir(), f"model_artifacts/ missing in fold_{i:02d}"

    def test_config_snapshot_created(self, tmp_path, default_yaml_data, tmp_yaml):
        """#044 — config_snapshot.yaml is created inside run_dir."""
        from ai_trading.artifacts.run_dir import create_run_dir

        output = tmp_path / "runs"
        output.mkdir()
        default_yaml_data["artifacts"]["output_dir"] = str(output)
        cfg_path = tmp_yaml(default_yaml_data)
        config = load_config(cfg_path)

        run_dir = create_run_dir(config, "xgboost_reg", n_folds=2)

        assert (run_dir / "config_snapshot.yaml").exists()

    def test_returns_path_object(self, tmp_path, default_yaml_data, tmp_yaml):
        """#044 — create_run_dir returns a Path."""
        from ai_trading.artifacts.run_dir import create_run_dir

        output = tmp_path / "runs"
        output.mkdir()
        default_yaml_data["artifacts"]["output_dir"] = str(output)
        cfg_path = tmp_yaml(default_yaml_data)
        config = load_config(cfg_path)

        result = create_run_dir(config, "dummy", n_folds=1)

        assert isinstance(result, Path)

    def test_output_dir_not_existing_raises(self, tmp_path, default_yaml_data, tmp_yaml):
        """#044 — error if output_dir does not exist."""
        import pytest

        from ai_trading.artifacts.run_dir import create_run_dir

        default_yaml_data["artifacts"]["output_dir"] = str(tmp_path / "nonexistent")
        cfg_path = tmp_yaml(default_yaml_data)
        config = load_config(cfg_path)

        with pytest.raises(FileNotFoundError, match="output_dir"):
            create_run_dir(config, "xgboost_reg", n_folds=3)

    def test_n_folds_zero_raises(self, tmp_path, default_yaml_data, tmp_yaml):
        """#044 — n_folds=0 is rejected."""
        import pytest

        from ai_trading.artifacts.run_dir import create_run_dir

        output = tmp_path / "runs"
        output.mkdir()
        default_yaml_data["artifacts"]["output_dir"] = str(output)
        cfg_path = tmp_yaml(default_yaml_data)
        config = load_config(cfg_path)

        with pytest.raises(ValueError, match="n_folds"):
            create_run_dir(config, "xgboost_reg", n_folds=0)

    def test_n_folds_negative_raises(self, tmp_path, default_yaml_data, tmp_yaml):
        """#044 — n_folds < 0 is rejected."""
        import pytest

        from ai_trading.artifacts.run_dir import create_run_dir

        output = tmp_path / "runs"
        output.mkdir()
        default_yaml_data["artifacts"]["output_dir"] = str(output)
        cfg_path = tmp_yaml(default_yaml_data)
        config = load_config(cfg_path)

        with pytest.raises(ValueError, match="n_folds"):
            create_run_dir(config, "xgboost_reg", n_folds=-1)

    def test_single_fold(self, tmp_path, default_yaml_data, tmp_yaml):
        """#044 — n_folds=1 creates exactly one fold directory."""
        from ai_trading.artifacts.run_dir import create_run_dir

        output = tmp_path / "runs"
        output.mkdir()
        default_yaml_data["artifacts"]["output_dir"] = str(output)
        cfg_path = tmp_yaml(default_yaml_data)
        config = load_config(cfg_path)

        run_dir = create_run_dir(config, "dummy", n_folds=1)

        folds = list((run_dir / "folds").iterdir())
        assert len(folds) == 1
        assert folds[0].name == "fold_00"

    def test_run_id_in_directory_name(self, tmp_path, default_yaml_data, tmp_yaml):
        """#044 — run directory name matches run_id format."""
        from ai_trading.artifacts.run_dir import create_run_dir

        output = tmp_path / "runs"
        output.mkdir()
        default_yaml_data["artifacts"]["output_dir"] = str(output)
        cfg_path = tmp_yaml(default_yaml_data)
        config = load_config(cfg_path)

        run_dir = create_run_dir(config, "patchtst_reg", n_folds=2)

        pattern = r"^\d{8}_\d{6}_patchtst_reg$"
        assert re.match(pattern, run_dir.name), (
            f"run_dir name '{run_dir.name}' doesn't match run_id pattern"
        )
