"""Tests for ai_trading.config — Config loader (YAML → Pydantic v2).

Task #002 — WS-1: Config loader Pydantic v2.
Covers acceptance criteria: nominal load, attribute access, custom file override,
CLI dot-notation override, error paths (FileNotFoundError, extra forbid, type
validation, invalid dot path), and edge cases.
"""

import copy

import pytest
import yaml
from pydantic import ValidationError

from ai_trading.config import PipelineConfig, load_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_yaml(tmp_path):
    """Factory fixture: write a dict to a temp YAML file and return its path."""
    def _write(data: dict, name: str = "cfg.yaml") -> str:
        p = tmp_path / name
        p.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
        return str(p)
    return _write


@pytest.fixture
def default_yaml_data(default_config_path):
    """Load the raw dict from configs/default.yaml for reuse."""
    with open(default_config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ===========================================================================
# AC-1: load_config returns a valid PipelineConfig
# ===========================================================================

class TestLoadConfigNominal:
    """#002 — Nominal loading of configs/default.yaml."""

    def test_returns_pipeline_config(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert isinstance(cfg, PipelineConfig)


# ===========================================================================
# AC-2: All fields accessible by attribute
# ===========================================================================

class TestAttributeAccess:
    """#002 — All YAML fields are accessible by attribute."""

    def test_dataset_symbols(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.dataset.symbols == ["BTCUSDT"]

    def test_splits_embargo_bars(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.splits.embargo_bars == 4

    def test_features_params_rsi_period(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.features.params.rsi_period == 14

    def test_models_xgboost_max_depth(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.models.xgboost.max_depth == 5

    def test_logging_level(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.logging.level == "INFO"

    def test_label_horizon(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.label.horizon_H_bars == 4

    def test_window_length(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.window.L == 128

    def test_scaling_method(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.scaling.method == "standard"

    def test_strategy_name(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.strategy.name == "xgboost_reg"

    def test_thresholding_q_grid(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.thresholding.q_grid == [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]

    def test_costs_fee_rate(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.costs.fee_rate_per_side == 0.0005

    def test_backtest_mode(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.backtest.mode == "one_at_a_time"

    def test_baselines_sma_fast(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.baselines.sma.fast == 20

    def test_training_loss(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.training.loss == "mse"

    def test_models_rl_ppo_hidden_sizes(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.models.rl_ppo.hidden_sizes == [64, 64]

    def test_metrics_sharpe_epsilon(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.metrics.sharpe_epsilon == 1.0e-12

    def test_reproducibility_global_seed(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.reproducibility.global_seed == 42

    def test_artifacts_output_dir(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert cfg.artifacts.output_dir == "runs"


# ===========================================================================
# AC-3: Override by custom YAML file
# ===========================================================================

class TestCustomFileOverride:
    """#002 — A partial custom YAML overrides default values."""

    def test_override_single_section(self, default_config_path, tmp_yaml, default_yaml_data):
        """A custom file that changes splits.train_days overrides that value."""
        custom_data = dict(default_yaml_data)
        custom_data["splits"] = dict(default_yaml_data["splits"])
        custom_data["splits"]["train_days"] = 240
        custom_path = tmp_yaml(custom_data, "custom.yaml")
        cfg = load_config(custom_path)
        assert cfg.splits.train_days == 240

    def test_override_nested_model_param(self, default_config_path, tmp_yaml, default_yaml_data):
        """Override a deeply nested parameter (models.xgboost.max_depth)."""
        custom_data = dict(default_yaml_data)
        custom_data["models"] = dict(default_yaml_data["models"])
        custom_data["models"]["xgboost"] = dict(default_yaml_data["models"]["xgboost"])
        custom_data["models"]["xgboost"]["max_depth"] = 10
        custom_path = tmp_yaml(custom_data, "deep.yaml")
        cfg = load_config(custom_path)
        assert cfg.models.xgboost.max_depth == 10


# ===========================================================================
# AC-4: CLI dot-notation override
# ===========================================================================

class TestCliDotNotationOverride:
    """#002 — --set key.subkey=value modifies the corresponding value."""

    def test_override_int_value(self, default_config_path):
        cfg = load_config(str(default_config_path), overrides=["splits.train_days=240"])
        assert cfg.splits.train_days == 240

    def test_override_float_value(self, default_config_path):
        cfg = load_config(str(default_config_path), overrides=["costs.fee_rate_per_side=0.001"])
        assert cfg.costs.fee_rate_per_side == 0.001

    def test_override_string_value(self, default_config_path):
        cfg = load_config(str(default_config_path), overrides=["logging.level=DEBUG"])
        assert cfg.logging.level == "DEBUG"

    def test_override_bool_value(self, default_config_path):
        cfg = load_config(
            str(default_config_path),
            overrides=["reproducibility.deterministic_torch=false"],
        )
        assert cfg.reproducibility.deterministic_torch is False

    def test_override_deeply_nested(self, default_config_path):
        cfg = load_config(
            str(default_config_path),
            overrides=["models.xgboost.max_depth=8"],
        )
        assert cfg.models.xgboost.max_depth == 8

    def test_multiple_overrides(self, default_config_path):
        cfg = load_config(
            str(default_config_path),
            overrides=["splits.train_days=240", "logging.level=DEBUG"],
        )
        assert cfg.splits.train_days == 240
        assert cfg.logging.level == "DEBUG"


# ===========================================================================
# AC-5: Error if dot-notation path doesn't exist
# ===========================================================================

class TestInvalidDotNotationPath:
    """#002 — Error raised when dot-notation path is unknown."""

    def test_top_level_unknown_key(self, default_config_path):
        with pytest.raises((KeyError, ValueError)):
            load_config(str(default_config_path), overrides=["nonexistent_key=42"])

    def test_nested_unknown_key(self, default_config_path):
        with pytest.raises((KeyError, ValueError)):
            load_config(str(default_config_path), overrides=["splits.unknown_field=42"])

    def test_too_deep_path(self, default_config_path):
        with pytest.raises((KeyError, ValueError)):
            load_config(
                str(default_config_path),
                overrides=["models.xgboost.max_depth.sub=1"],
            )


# ===========================================================================
# AC-6: FileNotFoundError if YAML path doesn't exist
# ===========================================================================

class TestFileNotFound:
    """#002 — Explicit error when YAML file does not exist."""

    def test_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yaml")

    def test_missing_file_relative(self):
        with pytest.raises(FileNotFoundError):
            load_config("this_file_does_not_exist.yaml")


# ===========================================================================
# AC-7: Unknown YAML key rejected (extra="forbid")
# ===========================================================================

class TestExtraForbid:
    """#002 — Unknown keys in YAML cause a validation error."""

    def test_extra_top_level_key(self, default_yaml_data, tmp_yaml):
        data = dict(default_yaml_data)
        data["unknown_section"] = {"foo": "bar"}
        path = tmp_yaml(data, "extra_top.yaml")
        with pytest.raises(Exception, match="unknown_section|extra"):
            load_config(path)

    def test_extra_nested_key(self, default_yaml_data, tmp_yaml):
        data = dict(default_yaml_data)
        data["splits"] = dict(default_yaml_data["splits"])
        data["splits"]["bogus_field"] = 999
        path = tmp_yaml(data, "extra_nested.yaml")
        with pytest.raises(Exception, match="bogus_field|extra"):
            load_config(path)


# ===========================================================================
# AC-8: Type validation by Pydantic
# ===========================================================================

class TestTypeValidation:
    """#002 — Pydantic enforces types (no silent coercion of invalid values)."""

    def test_embargo_bars_string_rejected(self, default_yaml_data, tmp_yaml):
        data = dict(default_yaml_data)
        data["splits"] = dict(default_yaml_data["splits"])
        data["splits"]["embargo_bars"] = "not_a_number"
        path = tmp_yaml(data, "type_err.yaml")
        with pytest.raises(ValidationError):
            load_config(path)

    def test_global_seed_string_rejected(self, default_yaml_data, tmp_yaml):
        data = dict(default_yaml_data)
        data["reproducibility"] = dict(default_yaml_data["reproducibility"])
        data["reproducibility"]["global_seed"] = "abc"
        path = tmp_yaml(data, "seed_err.yaml")
        with pytest.raises(ValidationError):
            load_config(path)

    def test_symbols_not_a_list(self, default_yaml_data, tmp_yaml):
        data = dict(default_yaml_data)
        data["dataset"] = dict(default_yaml_data["dataset"])
        data["dataset"]["symbols"] = 42
        path = tmp_yaml(data, "sym_err.yaml")
        with pytest.raises(ValidationError):
            load_config(path)


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases:
    """#002 — Edge cases for config loader."""

    def test_empty_overrides_list(self, default_config_path):
        """Empty override list should produce same result as no overrides."""
        cfg_no = load_config(str(default_config_path))
        cfg_empty = load_config(str(default_config_path), overrides=[])
        assert cfg_no.splits.train_days == cfg_empty.splits.train_days

    def test_override_with_equals_in_value(self, default_config_path):
        """A value containing '=' should still parse correctly (split on first '=')."""
        cfg = load_config(str(default_config_path), overrides=["logging.file=my=log.txt"])
        assert cfg.logging.file == "my=log.txt"

    def test_all_top_level_sections_present(self, default_config_path):
        """Every expected top-level section should be present on PipelineConfig."""
        cfg = load_config(str(default_config_path))
        expected_sections = [
            "logging", "dataset", "label", "window", "features", "splits",
            "scaling", "strategy", "thresholding", "costs", "backtest",
            "baselines", "training", "models", "metrics", "reproducibility",
            "artifacts",
        ]
        for section in expected_sections:
            assert hasattr(cfg, section), f"Missing section: {section}"


# ===========================================================================
# Task #003 — Strict validation rules
# ===========================================================================


class TestStrictValidationTask003:
    """#003 — Strict config validation (bounds, cross-checks, MVP constraints)."""

    @staticmethod
    def _write_mutated(default_yaml_data, tmp_yaml, mutate, name: str = "invalid.yaml"):
        data = copy.deepcopy(default_yaml_data)
        mutate(data)
        return tmp_yaml(data, name)

    def test_backtest_mode_must_be_one_at_a_time(self, default_yaml_data, tmp_yaml):
        path = self._write_mutated(
            default_yaml_data,
            tmp_yaml,
            lambda d: d["backtest"].update({"mode": "multi_positions"}),
            "invalid_backtest_mode.yaml",
        )
        with pytest.raises(ValidationError, match="one_at_a_time"):
            load_config(path)

    def test_backtest_direction_must_be_long_only(self, default_yaml_data, tmp_yaml):
        path = self._write_mutated(
            default_yaml_data,
            tmp_yaml,
            lambda d: d["backtest"].update({"direction": "short_only"}),
            "invalid_backtest_direction.yaml",
        )
        with pytest.raises(ValidationError, match="long_only"):
            load_config(path)

    def test_min_warmup_must_cover_feature_requirements(self, default_yaml_data, tmp_yaml):
        def mutate(data):
            data["window"]["min_warmup"] = 20

        path = self._write_mutated(
            default_yaml_data,
            tmp_yaml,
            mutate,
            "invalid_warmup_feature.yaml",
        )
        with pytest.raises(ValidationError, match="min_warmup"):
            load_config(path)

    def test_min_warmup_must_be_greater_or_equal_window_length(self, default_yaml_data, tmp_yaml):
        def mutate(data):
            data["window"]["L"] = 128
            data["window"]["min_warmup"] = 127

        path = self._write_mutated(
            default_yaml_data,
            tmp_yaml,
            mutate,
            "invalid_warmup_window.yaml",
        )
        with pytest.raises(ValidationError, match=r"window\.L"):
            load_config(path)

    def test_embargo_bars_must_be_greater_or_equal_horizon(self, default_yaml_data, tmp_yaml):
        def mutate(data):
            data["label"]["horizon_H_bars"] = 4
            data["splits"]["embargo_bars"] = 2

        path = self._write_mutated(default_yaml_data, tmp_yaml, mutate, "invalid_embargo.yaml")
        with pytest.raises(ValidationError, match="embargo_bars"):
            load_config(path)

    def test_strategy_type_baseline_cannot_use_model_name(self, default_yaml_data, tmp_yaml):
        def mutate(data):
            data["strategy"]["strategy_type"] = "baseline"
            data["strategy"]["name"] = "xgboost_reg"

        path = self._write_mutated(
            default_yaml_data,
            tmp_yaml,
            mutate,
            "invalid_strategy_mismatch_1.yaml",
        )
        with pytest.raises(ValidationError, match="strategy_type"):
            load_config(path)

    def test_strategy_type_model_cannot_use_baseline_name(self, default_yaml_data, tmp_yaml):
        def mutate(data):
            data["strategy"]["strategy_type"] = "model"
            data["strategy"]["name"] = "no_trade"

        path = self._write_mutated(
            default_yaml_data,
            tmp_yaml,
            mutate,
            "invalid_strategy_mismatch_2.yaml",
        )
        with pytest.raises(ValidationError, match="strategy_type"):
            load_config(path)

    def test_unknown_strategy_name_is_rejected(self, default_yaml_data, tmp_yaml):
        path = self._write_mutated(
            default_yaml_data,
            tmp_yaml,
            lambda d: d["strategy"].update({"name": "unknown_strategy"}),
            "invalid_strategy_name.yaml",
        )
        with pytest.raises(ValidationError, match=r"strategy\.name"):
            load_config(path)

    def test_step_days_must_be_greater_or_equal_test_days(self, default_yaml_data, tmp_yaml):
        def mutate(data):
            data["splits"]["test_days"] = 30
            data["splits"]["step_days"] = 29

        path = self._write_mutated(default_yaml_data, tmp_yaml, mutate, "invalid_walk_forward.yaml")
        with pytest.raises(ValidationError, match="step_days"):
            load_config(path)

    @pytest.mark.parametrize(
        ("mutate", "match"),
        [
            (lambda d: d["label"].update({"horizon_H_bars": 0}), "horizon_H_bars"),
            (lambda d: d["window"].update({"L": 1}), r"window\.L|L"),
            (lambda d: d["backtest"].update({"position_fraction": 0.0}), "position_fraction"),
            (lambda d: d["models"]["gru"].update({"dropout": 1.0}), "dropout"),
            (lambda d: d["thresholding"].update({"q_grid": [0.8, 0.6, 0.9]}), "q_grid"),
            (lambda d: d["thresholding"].update({"mdd_cap": 0.0}), "mdd_cap"),
            (lambda d: d["thresholding"].update({"min_trades": -1}), "min_trades"),
            (lambda d: d["models"]["gru"].update({"num_layers": 0}), "num_layers"),
            (
                lambda d: d["models"]["patchtst"].update({"d_model": 64, "n_heads": 3}),
                "n_heads",
            ),
            (
                lambda d: d["models"]["patchtst"].update({"patch_size": 16, "stride": 17}),
                "stride",
            ),
            (lambda d: d["baselines"]["sma"].update({"fast": 1}), r"sma\.fast|fast"),
            (lambda d: d["training"].update({"batch_size": 0}), "batch_size"),
            (lambda d: d["reproducibility"].update({"global_seed": -1}), "global_seed"),
            (lambda d: d["metrics"].update({"sharpe_epsilon": 0.0}), "sharpe_epsilon"),
            (lambda d: d["artifacts"].update({"output_dir": ""}), "output_dir"),
        ],
    )
    def test_numeric_and_structural_constraints(self, default_yaml_data, tmp_yaml, mutate, match):
        path = self._write_mutated(default_yaml_data, tmp_yaml, mutate)
        with pytest.raises(ValidationError, match=match):
            load_config(path)

    def test_unknown_yaml_nested_key_dataset_is_rejected(self, default_yaml_data, tmp_yaml):
        def mutate(data):
            data["dataset"]["foo"] = "bar"

        path = self._write_mutated(
            default_yaml_data,
            tmp_yaml,
            mutate,
            "invalid_dataset_extra.yaml",
        )
        with pytest.raises(ValidationError, match="foo|extra"):
            load_config(path)

    def test_scaling_method_rolling_zscore_is_rejected_in_mvp(self, default_yaml_data, tmp_yaml):
        path = self._write_mutated(
            default_yaml_data,
            tmp_yaml,
            lambda d: d["scaling"].update({"method": "rolling_zscore"}),
            "invalid_scaling_method.yaml",
        )
        with pytest.raises(ValidationError, match="rolling_zscore"):
            load_config(path)

    def test_dataset_must_be_single_symbol_in_mvp(self, default_yaml_data, tmp_yaml):
        def mutate(data):
            data["dataset"]["symbols"] = ["BTCUSDT", "ETHUSDT"]

        path = self._write_mutated(default_yaml_data, tmp_yaml, mutate, "invalid_symbols_len.yaml")
        with pytest.raises(ValidationError, match="symbols"):
            load_config(path)

    def test_warning_emitted_when_val_days_below_7(self, default_yaml_data, tmp_yaml):
        def mutate(data):
            data["splits"]["train_days"] = 20
            data["splits"]["val_frac_in_train"] = 0.2

        path = self._write_mutated(default_yaml_data, tmp_yaml, mutate, "warning_val_days.yaml")
        with pytest.warns(UserWarning, match="val_days"):
            load_config(path)
