"""Tests for configs/fullscale_btc.yaml — full-scale BTCUSDT configuration.

Task #055 — WS-13: Configuration full-scale BTCUSDT.

Verifies that the fullscale_btc.yaml config file:
- Is parsable by the config loader without error.
- Passes strict validation (WS-1.3 cross-field checks).
- Contains the expected overridden parameters for BTC full-scale run.
- Has all other parameters identical to default.yaml.
"""

from pathlib import Path

import pytest
import yaml

from ai_trading.config import PipelineConfig, load_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FULLSCALE_PATH = PROJECT_ROOT / "configs" / "fullscale_btc.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_raw_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Nominal: file exists and is loadable
# ---------------------------------------------------------------------------


class TestFullscaleConfigExists:
    """AC: configs/fullscale_btc.yaml exists and is versioned."""

    def test_file_exists(self):
        assert FULLSCALE_PATH.is_file(), (
            f"configs/fullscale_btc.yaml not found at {FULLSCALE_PATH}"
        )

    def test_file_is_valid_yaml(self):
        raw = _load_raw_yaml(FULLSCALE_PATH)
        assert isinstance(raw, dict)


# ---------------------------------------------------------------------------
# Nominal: config loader parses without error
# ---------------------------------------------------------------------------


class TestFullscaleConfigLoads:
    """AC: PipelineConfig.from_yaml / load_config parses without error."""

    def test_load_config_succeeds(self):
        cfg = load_config(str(FULLSCALE_PATH))
        assert isinstance(cfg, PipelineConfig)


# ---------------------------------------------------------------------------
# Nominal: strict validation (WS-1.3) passes
# ---------------------------------------------------------------------------


class TestFullscaleStrictValidation:
    """AC: Strict cross-field validation passes on fullscale_btc.yaml."""

    def test_no_validation_error(self):
        """load_config triggers all Pydantic + cross-field validators."""
        cfg = load_config(str(FULLSCALE_PATH))
        # If we reach here, all validators passed.
        assert cfg is not None

    def test_embargo_gte_horizon(self):
        cfg = load_config(str(FULLSCALE_PATH))
        assert cfg.splits.embargo_bars >= cfg.label.horizon_H_bars

    def test_warmup_gte_window_length(self):
        cfg = load_config(str(FULLSCALE_PATH))
        assert cfg.window.min_warmup >= cfg.window.L

    def test_warmup_gte_feature_min(self):
        cfg = load_config(str(FULLSCALE_PATH))
        feature_min = max(
            cfg.features.params.rsi_period,
            cfg.features.params.ema_slow,
            max(cfg.features.params.vol_windows),
        )
        assert cfg.window.min_warmup >= feature_min

    def test_step_days_gte_test_days(self):
        cfg = load_config(str(FULLSCALE_PATH))
        assert cfg.splits.step_days >= cfg.splits.test_days


# ---------------------------------------------------------------------------
# Nominal: overridden parameters match spec
# ---------------------------------------------------------------------------


class TestFullscaleOverriddenParams:
    """AC: dataset, strategy, window, splits match task spec."""

    def test_dataset_start(self):
        cfg = load_config(str(FULLSCALE_PATH))
        assert cfg.dataset.start == "2017-08-17"

    def test_dataset_end(self):
        cfg = load_config(str(FULLSCALE_PATH))
        assert cfg.dataset.end == "2026-01-01"

    def test_strategy_type(self):
        cfg = load_config(str(FULLSCALE_PATH))
        assert cfg.strategy.strategy_type == "model"

    def test_strategy_name(self):
        cfg = load_config(str(FULLSCALE_PATH))
        assert cfg.strategy.name == "dummy"

    def test_window_length(self):
        cfg = load_config(str(FULLSCALE_PATH))
        assert cfg.window.L == 128

    def test_window_min_warmup(self):
        cfg = load_config(str(FULLSCALE_PATH))
        assert cfg.window.min_warmup == 200

    def test_splits_train_days(self):
        cfg = load_config(str(FULLSCALE_PATH))
        assert cfg.splits.train_days == 180

    def test_splits_test_days(self):
        cfg = load_config(str(FULLSCALE_PATH))
        assert cfg.splits.test_days == 30

    def test_splits_step_days(self):
        cfg = load_config(str(FULLSCALE_PATH))
        assert cfg.splits.step_days == 30


# ---------------------------------------------------------------------------
# Nominal: unchanged parameters identical to default.yaml
# ---------------------------------------------------------------------------


class TestFullscaleUnchangedParams:
    """AC: features, scaling, costs, backtest, thresholding match default.yaml."""

    @pytest.fixture
    def configs(self, default_config):
        fullscale = load_config(str(FULLSCALE_PATH))
        return fullscale, default_config

    def test_features_identical(self, configs):
        fullscale, default = configs
        assert fullscale.features == default.features

    def test_scaling_identical(self, configs):
        fullscale, default = configs
        assert fullscale.scaling == default.scaling

    def test_costs_identical(self, configs):
        fullscale, default = configs
        assert fullscale.costs == default.costs

    def test_backtest_identical(self, configs):
        fullscale, default = configs
        assert fullscale.backtest == default.backtest

    def test_thresholding_identical(self, configs):
        fullscale, default = configs
        assert fullscale.thresholding == default.thresholding

    def test_label_identical(self, configs):
        fullscale, default = configs
        assert fullscale.label == default.label

    def test_qa_identical(self, configs):
        fullscale, default = configs
        assert fullscale.qa == default.qa

    def test_baselines_identical(self, configs):
        fullscale, default = configs
        assert fullscale.baselines == default.baselines

    def test_training_identical(self, configs):
        fullscale, default = configs
        assert fullscale.training == default.training

    def test_models_identical(self, configs):
        fullscale, default = configs
        assert fullscale.models == default.models

    def test_metrics_identical(self, configs):
        fullscale, default = configs
        assert fullscale.metrics == default.metrics

    def test_reproducibility_identical(self, configs):
        fullscale, default = configs
        assert fullscale.reproducibility == default.reproducibility

    def test_artifacts_identical(self, configs):
        fullscale, default = configs
        assert fullscale.artifacts == default.artifacts

    def test_logging_identical(self, configs):
        fullscale, default = configs
        assert fullscale.logging == default.logging

    def test_dataset_exchange_identical(self, configs):
        fullscale, default = configs
        assert fullscale.dataset.exchange == default.dataset.exchange

    def test_dataset_symbols_identical(self, configs):
        fullscale, default = configs
        assert fullscale.dataset.symbols == default.dataset.symbols

    def test_dataset_timeframe_identical(self, configs):
        fullscale, default = configs
        assert fullscale.dataset.timeframe == default.dataset.timeframe

    def test_dataset_ingestion_identical(self, configs):
        fullscale, default = configs
        assert fullscale.dataset.ingestion == default.dataset.ingestion


# ---------------------------------------------------------------------------
# Edge: raw YAML diff is minimal (only expected keys differ)
# ---------------------------------------------------------------------------


class TestFullscaleRawYamlDiff:
    """Verify that only the expected keys differ between raw YAMLs."""

    def test_only_expected_keys_differ(self, default_yaml_data):
        raw_default = default_yaml_data
        raw_fullscale = _load_raw_yaml(FULLSCALE_PATH)

        # dataset.start and dataset.end should differ
        assert raw_fullscale["dataset"]["start"] != raw_default["dataset"]["start"]
        assert raw_fullscale["dataset"]["start"] == "2017-08-17"

        # strategy should differ
        assert raw_fullscale["strategy"]["name"] == "dummy"

        # All top-level keys present in both
        assert set(raw_fullscale.keys()) == set(raw_default.keys())


# ---------------------------------------------------------------------------
# Error: corrupted fullscale file should fail
# ---------------------------------------------------------------------------


class TestFullscaleErrorCases:
    """Error / edge cases for config loading."""

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("configs/nonexistent_btc.yaml")

    def test_corrupted_fullscale_would_fail(self, tmp_path):
        """A fullscale config missing a required section must fail validation."""
        raw = _load_raw_yaml(FULLSCALE_PATH)
        del raw["features"]
        bad_path = tmp_path / "bad_fullscale.yaml"
        bad_path.write_text(
            yaml.dump(raw, default_flow_style=False), encoding="utf-8"
        )
        with pytest.raises((ValueError, KeyError, TypeError)):
            load_config(str(bad_path))

    def test_invalid_strategy_name_rejected(self, tmp_path):
        """Changing strategy to an invalid name must fail validation."""
        raw = _load_raw_yaml(FULLSCALE_PATH)
        raw["strategy"]["name"] = "invalid_model"
        bad_path = tmp_path / "bad_strategy.yaml"
        bad_path.write_text(
            yaml.dump(raw, default_flow_style=False), encoding="utf-8"
        )
        with pytest.raises(ValueError):
            load_config(str(bad_path))

    def test_warmup_below_window_length_rejected(self, tmp_path):
        """min_warmup < L must fail cross-field validation."""
        raw = _load_raw_yaml(FULLSCALE_PATH)
        raw["window"]["min_warmup"] = 1
        bad_path = tmp_path / "bad_warmup.yaml"
        bad_path.write_text(
            yaml.dump(raw, default_flow_style=False), encoding="utf-8"
        )
        with pytest.raises(ValueError):
            load_config(str(bad_path))
