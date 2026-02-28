"""Tests for strict configuration validation — Pydantic v2 validators.

Task #003 — WS-1: Validation stricte de la configuration.
Covers: numeric bounds (Field), cross-field validators (@model_validator),
VALID_STRATEGIES mapping, MVP rules, anti-leak (embargo >= H), and edge cases.
"""

import copy
import logging

import pytest
import yaml
from pydantic import ValidationError

from ai_trading.config import PipelineConfig, load_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def default_yaml_data(default_config_path):
    """Load the raw dict from configs/default.yaml for reuse."""
    with open(default_config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def tmp_yaml(tmp_path):
    """Factory fixture: write a dict to a temp YAML file and return its path."""

    def _write(data: dict, name: str = "cfg.yaml") -> str:
        p = tmp_path / name
        p.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
        return str(p)

    return _write


def _mutate(data: dict, dotpath: str, value):
    """Set a nested key in a deep-copied dict using dot notation and return the copy."""
    d = copy.deepcopy(data)
    parts = dotpath.split(".")
    node = d
    for part in parts[:-1]:
        node = node[part]
    node[parts[-1]] = value
    return d


# ===========================================================================
# AC-1: Default config passes validation without errors
# ===========================================================================


class TestDefaultConfigValid:
    """#003 — configs/default.yaml passes strict validation."""

    def test_default_config_loads_without_error(self, default_config_path):
        cfg = load_config(str(default_config_path))
        assert isinstance(cfg, PipelineConfig)


# ===========================================================================
# AC-2/3: MVP backtest constraints
# ===========================================================================


class TestBacktestMVP:
    """#003 — backtest.mode must be one_at_a_time, direction must be long_only."""

    def test_backtest_mode_not_one_at_a_time_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "backtest.mode", "concurrent")
        with pytest.raises(ValidationError, match="backtest.mode"):
            load_config(tmp_yaml(data))

    def test_backtest_direction_not_long_only_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "backtest.direction", "long_short")
        with pytest.raises(ValidationError, match="backtest.direction"):
            load_config(tmp_yaml(data))


# ===========================================================================
# AC-4/5: Warmup constraints
# ===========================================================================


class TestWarmupConstraints:
    """#003 — min_warmup >= max(rsi_period, ema_slow, max(vol_windows)) and >= L."""

    def test_warmup_lt_feature_max_raises(self, default_yaml_data, tmp_yaml):
        # rsi_period=14, ema_slow=26, max(vol_windows)=72 → need min_warmup >= 72
        data = _mutate(default_yaml_data, "window.min_warmup", 50)
        with pytest.raises(ValidationError, match="min_warmup"):
            load_config(tmp_yaml(data))

    def test_warmup_lt_window_length_raises(self, default_yaml_data, tmp_yaml):
        # L=128 → need min_warmup >= 128
        data = _mutate(default_yaml_data, "window.min_warmup", 100)
        # Also need it >= max(features) = 72 which 100 satisfies, but 100 < 128 = L
        with pytest.raises(ValidationError, match="min_warmup"):
            load_config(tmp_yaml(data))


# ===========================================================================
# AC-6: Anti-leak — embargo_bars >= horizon_H_bars
# ===========================================================================


class TestEmbargoHorizon:
    """#003 — embargo_bars < horizon_H_bars must raise (anti-leak)."""

    def test_embargo_lt_horizon_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "splits.embargo_bars", 2)
        data = _mutate(data, "label.horizon_H_bars", 4)
        with pytest.raises(ValidationError, match="embargo_bars"):
            load_config(tmp_yaml(data))

    def test_embargo_eq_horizon_ok(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "splits.embargo_bars", 4)
        data = _mutate(data, "label.horizon_H_bars", 4)
        cfg = load_config(tmp_yaml(data))
        assert cfg.splits.embargo_bars == 4


# ===========================================================================
# AC-7/8/9: Strategy cohérence (VALID_STRATEGIES)
# ===========================================================================


class TestStrategyCohesion:
    """#003 — strategy_type must match VALID_STRATEGIES mapping."""

    def test_baseline_type_with_model_name_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "strategy.strategy_type", "baseline")
        data = _mutate(data, "strategy.name", "xgboost_reg")
        with pytest.raises(ValidationError, match="strategy"):
            load_config(tmp_yaml(data))

    def test_model_type_with_baseline_name_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "strategy.strategy_type", "model")
        data = _mutate(data, "strategy.name", "no_trade")
        with pytest.raises(ValidationError, match="strategy"):
            load_config(tmp_yaml(data))

    def test_unknown_strategy_name_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "strategy.name", "magic_model")
        with pytest.raises(ValidationError, match="strategy"):
            load_config(tmp_yaml(data))


# ===========================================================================
# AC-10: Walk-forward step_days >= test_days
# ===========================================================================


class TestWalkForwardStep:
    """#003 — step_days < test_days must raise."""

    def test_step_days_lt_test_days_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "splits.step_days", 10)
        data = _mutate(data, "splits.test_days", 30)
        with pytest.raises(ValidationError, match="step_days"):
            load_config(tmp_yaml(data))


# ===========================================================================
# AC-11: Numeric bounds — horizon, window.L, position_fraction
# ===========================================================================


class TestNumericBoundsBasic:
    """#003 — horizon_H_bars=0, L=1, position_fraction=0 must be rejected."""

    def test_horizon_zero_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "label.horizon_H_bars", 0)
        with pytest.raises(ValidationError, match="horizon_H_bars"):
            load_config(tmp_yaml(data))

    def test_window_length_one_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "window.L", 1)
        with pytest.raises(ValidationError, match="L"):
            load_config(tmp_yaml(data))

    def test_position_fraction_zero_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "backtest.position_fraction", 0)
        with pytest.raises(ValidationError, match="position_fraction"):
            load_config(tmp_yaml(data))


# ===========================================================================
# AC-12: dropout=1.0, q_grid unsorted, mdd_cap=0
# ===========================================================================


class TestDropoutQgridMddcap:
    """#003 — dropout=1.0, unsorted q_grid, mdd_cap=0 are rejected."""

    def test_dropout_one_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "models.cnn1d.dropout", 1.0)
        with pytest.raises(ValidationError, match="dropout"):
            load_config(tmp_yaml(data))

    def test_q_grid_unsorted_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(
            default_yaml_data, "thresholding.q_grid", [0.9, 0.5, 0.7]
        )
        with pytest.raises(ValidationError, match="q_grid"):
            load_config(tmp_yaml(data))

    def test_mdd_cap_zero_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "thresholding.mdd_cap", 0)
        with pytest.raises(ValidationError, match="mdd_cap"):
            load_config(tmp_yaml(data))


# ===========================================================================
# AC-13: min_trades=-1, num_layers=0
# ===========================================================================


class TestMinTradesNumLayers:
    """#003 — min_trades=-1 and num_layers=0 are rejected."""

    def test_min_trades_negative_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "thresholding.min_trades", -1)
        with pytest.raises(ValidationError, match="min_trades"):
            load_config(tmp_yaml(data))

    def test_num_layers_zero_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "models.gru.num_layers", 0)
        with pytest.raises(ValidationError, match="num_layers"):
            load_config(tmp_yaml(data))


# ===========================================================================
# AC-14: n_heads divides d_model, stride <= patch_size
# ===========================================================================


class TestPatchTSTConstraints:
    """#003 — PatchTST: n_heads must divide d_model, stride <= patch_size."""

    def test_n_heads_not_divides_d_model_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "models.patchtst.d_model", 64)
        data = _mutate(data, "models.patchtst.n_heads", 5)
        with pytest.raises(ValidationError, match="n_heads"):
            load_config(tmp_yaml(data))

    def test_stride_gt_patch_size_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "models.patchtst.stride", 20)
        data = _mutate(data, "models.patchtst.patch_size", 16)
        with pytest.raises(ValidationError, match="stride"):
            load_config(tmp_yaml(data))


# ===========================================================================
# AC-15: sma.fast=1, batch_size=0
# ===========================================================================


class TestSmaFastBatchSize:
    """#003 — sma.fast < 2 and batch_size < 1 are rejected."""

    def test_sma_fast_one_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "baselines.sma.fast", 1)
        with pytest.raises(ValidationError, match="fast"):
            load_config(tmp_yaml(data))

    def test_batch_size_zero_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "training.batch_size", 0)
        with pytest.raises(ValidationError, match="batch_size"):
            load_config(tmp_yaml(data))


# ===========================================================================
# AC-16: global_seed=-1, sharpe_epsilon=0, output_dir=""
# ===========================================================================


class TestSeedEpsilonOutputDir:
    """#003 — global_seed=-1, sharpe_epsilon=0, output_dir='' are rejected."""

    def test_global_seed_negative_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "reproducibility.global_seed", -1)
        with pytest.raises(ValidationError, match="global_seed"):
            load_config(tmp_yaml(data))

    def test_sharpe_epsilon_zero_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "metrics.sharpe_epsilon", 0)
        with pytest.raises(ValidationError, match="sharpe_epsilon"):
            load_config(tmp_yaml(data))

    def test_output_dir_empty_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "artifacts.output_dir", "")
        with pytest.raises(ValidationError, match="output_dir"):
            load_config(tmp_yaml(data))


# ===========================================================================
# AC-17: Extra/unknown YAML key rejected
# ===========================================================================


class TestExtraFieldsForbidden:
    """#003 — Unknown YAML key raises Pydantic ValidationError."""

    def test_extra_nested_key_rejected(self, default_yaml_data, tmp_yaml):
        data = copy.deepcopy(default_yaml_data)
        data["dataset"]["foo"] = "bar"
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            load_config(tmp_yaml(data))


# ===========================================================================
# AC-18: scaling.method = rolling_zscore → error (not implemented MVP)
# ===========================================================================


class TestScalingRollingZscoreRejected:
    """#003 — rolling_zscore is not implemented in MVP."""

    def test_rolling_zscore_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "scaling.method", "rolling_zscore")
        with pytest.raises(ValidationError, match="rolling_zscore"):
            load_config(tmp_yaml(data))


# ===========================================================================
# AC-19: Multiple symbols → error (MVP mono-symbol)
# ===========================================================================


class TestMVPSingleSymbol:
    """#003 — MVP requires exactly one symbol."""

    def test_multiple_symbols_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "dataset.symbols", ["BTCUSDT", "ETHUSDT"])
        with pytest.raises(ValidationError, match="symbol"):
            load_config(tmp_yaml(data))


# ===========================================================================
# AC-20: Warning if val_days < 7
# ===========================================================================


class TestValDaysWarning:
    """#003 — Warning issued when floor(train_days * val_frac_in_train) < 7."""

    def test_small_val_days_emits_warning(self, default_yaml_data, tmp_yaml, caplog):
        # train=20 * val_frac=0.2 → 4 days < 7 → warning
        data = _mutate(default_yaml_data, "splits.train_days", 20)
        data = _mutate(data, "splits.val_frac_in_train", 0.2)
        # Fix warmup to still be valid: L=2, warmup=72 → need warmup >= max(features) = 72
        data = _mutate(data, "window.L", 2)
        data = _mutate(data, "window.min_warmup", 72)
        # Fix embargo >= H
        data = _mutate(data, "splits.embargo_bars", 4)
        with caplog.at_level(logging.WARNING, logger="ai_trading.config"):
            cfg = load_config(tmp_yaml(data))
        assert isinstance(cfg, PipelineConfig)
        val_warnings = [
            r for r in caplog.records
            if r.name == "ai_trading.config" and "val_days" in r.message
        ]
        assert len(val_warnings) == 1
        assert "val_days=4" in val_warnings[0].message


# ===========================================================================
# Additional numeric bound edge cases
# ===========================================================================


class TestAdditionalNumericBounds:
    """#003 — Additional numeric bounds from task spec."""

    def test_train_days_zero_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "splits.train_days", 0)
        with pytest.raises(ValidationError, match="train_days"):
            load_config(tmp_yaml(data))

    def test_test_days_zero_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "splits.test_days", 0)
        with pytest.raises(ValidationError, match="test_days"):
            load_config(tmp_yaml(data))

    def test_step_days_zero_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "splits.step_days", 0)
        with pytest.raises(ValidationError, match="step_days"):
            load_config(tmp_yaml(data))

    def test_val_frac_zero_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "splits.val_frac_in_train", 0.0)
        with pytest.raises(ValidationError, match="val_frac"):
            load_config(tmp_yaml(data))

    def test_val_frac_above_half_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "splits.val_frac_in_train", 0.6)
        with pytest.raises(ValidationError, match="val_frac"):
            load_config(tmp_yaml(data))

    def test_fee_rate_negative_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "costs.fee_rate_per_side", -0.001)
        with pytest.raises(ValidationError, match="fee_rate"):
            load_config(tmp_yaml(data))

    def test_slippage_negative_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "costs.slippage_rate_per_side", -0.001)
        with pytest.raises(ValidationError, match="slippage"):
            load_config(tmp_yaml(data))

    def test_initial_equity_zero_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "backtest.initial_equity", 0)
        with pytest.raises(ValidationError, match="initial_equity"):
            load_config(tmp_yaml(data))

    def test_embargo_bars_negative_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "splits.embargo_bars", -1)
        with pytest.raises(ValidationError, match="embargo_bars"):
            load_config(tmp_yaml(data))

    def test_min_warmup_zero_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "window.min_warmup", 0)
        with pytest.raises(ValidationError, match="min_warmup"):
            load_config(tmp_yaml(data))

    def test_q_grid_value_out_of_range_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "thresholding.q_grid", [0.5, 1.5])
        with pytest.raises(ValidationError, match="q_grid"):
            load_config(tmp_yaml(data))

    def test_rolling_window_lt_2_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "scaling.rolling_window", 1)
        with pytest.raises(ValidationError, match="rolling_window"):
            load_config(tmp_yaml(data))

    def test_vol_windows_empty_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "features.params.vol_windows", [])
        with pytest.raises(ValidationError, match="vol_windows"):
            load_config(tmp_yaml(data))


# ===========================================================================
# Dropout bounds for all model types with dropout
# ===========================================================================


class TestDropoutAllModels:
    """#003 — dropout must be in [0, 1) for all DL models."""

    def test_gru_dropout_one_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "models.gru.dropout", 1.0)
        with pytest.raises(ValidationError, match="dropout"):
            load_config(tmp_yaml(data))

    def test_lstm_dropout_one_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "models.lstm.dropout", 1.0)
        with pytest.raises(ValidationError, match="dropout"):
            load_config(tmp_yaml(data))

    def test_patchtst_dropout_one_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "models.patchtst.dropout", 1.0)
        with pytest.raises(ValidationError, match="dropout"):
            load_config(tmp_yaml(data))

    def test_dropout_negative_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "models.cnn1d.dropout", -0.1)
        with pytest.raises(ValidationError, match="dropout"):
            load_config(tmp_yaml(data))


# ===========================================================================
# num_layers bounds for relevant models
# ===========================================================================


class TestNumLayersBounds:
    """#003 — num_layers >= 1 for GRU, LSTM, PatchTST."""

    def test_lstm_num_layers_zero_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "models.lstm.num_layers", 0)
        with pytest.raises(ValidationError, match="num_layers"):
            load_config(tmp_yaml(data))

    def test_patchtst_n_layers_zero_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "models.patchtst.n_layers", 0)
        with pytest.raises(ValidationError, match="n_layers"):
            load_config(tmp_yaml(data))


# ===========================================================================
# SMA cross constraint (if strategy is sma_rule)
# ===========================================================================


class TestSMACrossConstraint:
    """#003 — If strategy.name == sma_rule, sma.fast < sma.slow <= min_warmup."""

    def test_sma_fast_gte_slow_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "strategy.strategy_type", "baseline")
        data = _mutate(data, "strategy.name", "sma_rule")
        data = _mutate(data, "baselines.sma.fast", 50)
        data = _mutate(data, "baselines.sma.slow", 50)
        with pytest.raises(ValidationError, match="sma"):
            load_config(tmp_yaml(data))

    def test_sma_slow_gt_warmup_raises(self, default_yaml_data, tmp_yaml):
        data = _mutate(default_yaml_data, "strategy.strategy_type", "baseline")
        data = _mutate(data, "strategy.name", "sma_rule")
        data = _mutate(data, "baselines.sma.fast", 20)
        data = _mutate(data, "baselines.sma.slow", 300)
        with pytest.raises(ValidationError, match="sma"):
            load_config(tmp_yaml(data))
