"""Config loader — YAML → Pydantic v2 model.

Provides :func:`load_config` to load a YAML configuration file into a
fully-typed :class:`PipelineConfig` Pydantic model, with optional CLI
dot-notation overrides.  All sub-models use ``extra="forbid"`` to reject
unknown keys.

Task #002 — WS-1.
Task #003 — WS-1: Strict validation (bounds, cross-field, MVP rules).
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Strict base — every sub-model inherits extra="forbid"
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

VALID_STRATEGIES: dict[str, str] = {
    "xgboost_reg": "model",
    "cnn1d_reg": "model",
    "gru_reg": "model",
    "lstm_reg": "model",
    "patchtst_reg": "model",
    "rl_ppo": "model",
    "no_trade": "baseline",
    "buy_hold": "baseline",
    "sma_rule": "baseline",
}


class _StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Sub-models (one per YAML section)
# ---------------------------------------------------------------------------


class LoggingConfig(_StrictBase):
    level: str
    format: str
    file: str | None


class DatasetConfig(_StrictBase):
    exchange: str
    symbols: list[str]
    timeframe: str
    start: str
    end: str
    timezone: str
    raw_dir: str


class LabelConfig(_StrictBase):
    horizon_H_bars: int = Field(ge=1)  # noqa: N815
    target_type: str


class WindowConfig(_StrictBase):
    L: int = Field(ge=2)  # noqa: N815
    min_warmup: int = Field(ge=1)


class FeaturesParamsConfig(_StrictBase):
    rsi_period: int
    rsi_epsilon: float
    ema_fast: int
    ema_slow: int
    vol_windows: list[int] = Field(min_length=1)
    logvol_epsilon: float
    volatility_ddof: int


class FeaturesConfig(_StrictBase):
    feature_version: str
    feature_list: list[str]
    params: FeaturesParamsConfig


class SplitsConfig(_StrictBase):
    scheme: str
    train_days: int = Field(ge=1)
    test_days: int = Field(ge=1)
    step_days: int = Field(ge=1)
    val_frac_in_train: float = Field(gt=0, le=0.5)
    embargo_bars: int = Field(ge=0)
    min_samples_train: int = Field(ge=1)
    min_samples_test: int = Field(ge=1)


class ScalingConfig(_StrictBase):
    method: str
    epsilon: float
    robust_quantile_low: float
    robust_quantile_high: float
    rolling_window: int = Field(ge=2)

    @model_validator(mode="after")
    def _reject_rolling_zscore(self) -> ScalingConfig:
        if self.method == "rolling_zscore":
            raise ValueError(
                "scaling.method 'rolling_zscore' is not implemented in MVP"
            )
        return self


class StrategyConfig(_StrictBase):
    strategy_type: str
    name: str
    framework: str


class ThresholdingConfig(_StrictBase):
    method: str
    q_grid: list[float]
    objective: str
    mdd_cap: float = Field(gt=0, le=1)
    min_trades: int = Field(ge=0)

    @field_validator("q_grid")
    @classmethod
    def _validate_q_grid(cls, v: list[float]) -> list[float]:
        for val in v:
            if val < 0 or val > 1:
                raise ValueError(
                    f"q_grid values must be in [0, 1], got {val}"
                )
        if v != sorted(v):
            raise ValueError(
                f"q_grid must be sorted in ascending order, got {v}"
            )
        return v


class CostsConfig(_StrictBase):
    cost_model: str
    fee_rate_per_side: float = Field(ge=0)
    slippage_rate_per_side: float = Field(ge=0)


class BacktestConfig(_StrictBase):
    mode: str
    direction: str
    initial_equity: float = Field(gt=0)
    position_fraction: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def _validate_mvp_backtest(self) -> BacktestConfig:
        if self.mode != "one_at_a_time":
            raise ValueError(
                f"backtest.mode must be 'one_at_a_time' (MVP), got '{self.mode}'"
            )
        if self.direction != "long_only":
            raise ValueError(
                f"backtest.direction must be 'long_only' (MVP), got '{self.direction}'"
            )
        return self


class SmaConfig(_StrictBase):
    fast: int = Field(ge=2)
    slow: int


class BaselinesConfig(_StrictBase):
    sma: SmaConfig


class TrainingConfig(_StrictBase):
    loss: str
    optimizer: str
    learning_rate: float
    batch_size: int = Field(ge=1)
    max_epochs: int
    early_stopping_patience: int


# --- Per-model hyperparameters ------------------------------------------------


class XGBoostModelConfig(_StrictBase):
    max_depth: int
    n_estimators: int
    learning_rate: float
    subsample: float
    colsample_bytree: float
    reg_alpha: float
    reg_lambda: float


class CNN1DModelConfig(_StrictBase):
    n_conv_layers: int
    filters: int
    kernel_size: int
    dropout: float = Field(ge=0, lt=1)
    pool: str


class GRUModelConfig(_StrictBase):
    hidden_size: int
    num_layers: int = Field(ge=1)
    bidirectional: bool
    dropout: float = Field(ge=0, lt=1)


class LSTMModelConfig(_StrictBase):
    hidden_size: int
    num_layers: int = Field(ge=1)
    bidirectional: bool
    dropout: float = Field(ge=0, lt=1)


class PatchTSTModelConfig(_StrictBase):
    patch_size: int
    stride: int
    d_model: int
    n_heads: int
    n_layers: int = Field(ge=1)
    ff_dim: int
    dropout: float = Field(ge=0, lt=1)

    @model_validator(mode="after")
    def _validate_patchtst(self) -> PatchTSTModelConfig:
        if self.d_model % self.n_heads != 0:
            raise ValueError(
                f"models.patchtst.n_heads ({self.n_heads}) must divide "
                f"d_model ({self.d_model})"
            )
        if self.stride > self.patch_size:
            raise ValueError(
                f"models.patchtst.stride ({self.stride}) must be "
                f"<= patch_size ({self.patch_size})"
            )
        return self


class RLPPOModelConfig(_StrictBase):
    hidden_sizes: list[int]
    clip_epsilon: float
    gamma: float
    gae_lambda: float
    n_epochs_ppo: int
    max_episodes: int
    rollout_steps: int
    value_loss_coeff: float
    entropy_coeff: float
    learning_rate: float
    deterministic_eval: bool


class ModelsConfig(_StrictBase):
    xgboost: XGBoostModelConfig
    cnn1d: CNN1DModelConfig
    gru: GRUModelConfig
    lstm: LSTMModelConfig
    patchtst: PatchTSTModelConfig
    rl_ppo: RLPPOModelConfig


class MetricsConfig(_StrictBase):
    sharpe_annualized: bool
    sharpe_epsilon: float = Field(gt=0)


class ReproducibilityConfig(_StrictBase):
    global_seed: int = Field(ge=0)
    deterministic_torch: bool


class ArtifactsConfig(_StrictBase):
    output_dir: str = Field(min_length=1)
    save_model: bool
    save_equity_curve: bool
    save_predictions: bool


# ---------------------------------------------------------------------------
# Root model
# ---------------------------------------------------------------------------


class PipelineConfig(_StrictBase):
    logging: LoggingConfig
    dataset: DatasetConfig
    label: LabelConfig
    window: WindowConfig
    features: FeaturesConfig
    splits: SplitsConfig
    scaling: ScalingConfig
    strategy: StrategyConfig
    thresholding: ThresholdingConfig
    costs: CostsConfig
    backtest: BacktestConfig
    baselines: BaselinesConfig
    training: TrainingConfig
    models: ModelsConfig
    metrics: MetricsConfig
    reproducibility: ReproducibilityConfig
    artifacts: ArtifactsConfig

    @model_validator(mode="after")
    def _validate_cross_fields(self) -> PipelineConfig:
        errors: list[str] = []

        # --- MVP: single symbol ---
        if len(self.dataset.symbols) != 1:
            errors.append(
                f"MVP requires exactly 1 symbol, got {len(self.dataset.symbols)}"
            )

        # --- Warmup >= max(rsi_period, ema_slow, max(vol_windows)) ---
        feature_min = max(
            self.features.params.rsi_period,
            self.features.params.ema_slow,
            max(self.features.params.vol_windows),
        )
        if self.window.min_warmup < feature_min:
            errors.append(
                f"window.min_warmup ({self.window.min_warmup}) must be >= "
                f"max(rsi_period, ema_slow, max(vol_windows)) = {feature_min}"
            )

        # --- Warmup >= L ---
        if self.window.min_warmup < self.window.L:
            errors.append(
                f"window.min_warmup ({self.window.min_warmup}) must be >= "
                f"window.L ({self.window.L})"
            )

        # --- Anti-leak: embargo >= H ---
        if self.splits.embargo_bars < self.label.horizon_H_bars:
            errors.append(
                f"splits.embargo_bars ({self.splits.embargo_bars}) must be >= "
                f"label.horizon_H_bars ({self.label.horizon_H_bars})"
            )

        # --- Walk-forward: step_days >= test_days ---
        if self.splits.step_days < self.splits.test_days:
            errors.append(
                f"splits.step_days ({self.splits.step_days}) must be >= "
                f"splits.test_days ({self.splits.test_days})"
            )

        # --- Strategy coherence ---
        if self.strategy.name not in VALID_STRATEGIES:
            errors.append(
                f"strategy.name '{self.strategy.name}' is not in VALID_STRATEGIES: "
                f"{list(VALID_STRATEGIES.keys())}"
            )
        else:
            expected_type = VALID_STRATEGIES[self.strategy.name]
            if self.strategy.strategy_type != expected_type:
                errors.append(
                    f"strategy.name '{self.strategy.name}' requires "
                    f"strategy_type='{expected_type}', "
                    f"got '{self.strategy.strategy_type}'"
                )

        # --- SMA cross-constraint (only if sma_rule) ---
        if self.strategy.name == "sma_rule":
            if self.baselines.sma.fast >= self.baselines.sma.slow:
                errors.append(
                    f"baselines.sma.fast ({self.baselines.sma.fast}) must be < "
                    f"sma.slow ({self.baselines.sma.slow})"
                )
            elif self.baselines.sma.slow > self.window.min_warmup:
                errors.append(
                    f"baselines.sma.slow ({self.baselines.sma.slow}) must be <= "
                    f"window.min_warmup ({self.window.min_warmup})"
                )

        # --- Raise all collected errors ---
        if errors:
            raise ValueError(" | ".join(errors))

        # --- Warning: val_days < 7 ---
        val_days = math.floor(self.splits.train_days * self.splits.val_frac_in_train)
        if val_days < 7:
            logger.warning(
                "Validation window is very short: val_days=%d (< 7). "
                "Consider increasing train_days or val_frac_in_train.",
                val_days,
            )

        return self


# ---------------------------------------------------------------------------
# Dot-notation override helpers
# ---------------------------------------------------------------------------


def _apply_overrides(data: dict[str, Any], overrides: list[str]) -> dict[str, Any]:
    """Apply CLI dot-notation overrides to a raw config dict.

    Each override has the form ``key.subkey=value``.  The value is parsed
    via :func:`yaml.safe_load` so that ``"42"`` becomes ``int``,
    ``"true"`` becomes ``bool``, etc.

    Raises
    ------
    KeyError
        If any segment of the dot path does not exist in *data*.
    """
    for override in overrides:
        if "=" not in override:
            raise ValueError(
                f"Invalid override format (expected 'key.subkey=value'): {override!r}"
            )
        key_path, _, raw_value = override.partition("=")
        parts = key_path.split(".")
        if not parts or not all(parts):
            raise ValueError(f"Invalid dot-notation path: {key_path!r}")

        # Navigate to the parent dict
        node = data
        for part in parts[:-1]:
            if not isinstance(node, dict) or part not in node:
                raise KeyError(
                    f"Override path segment {part!r} not found "
                    f"in config (full path: {key_path!r})"
                )
            node = node[part]

        # Set the leaf value
        leaf = parts[-1]
        if not isinstance(node, dict) or leaf not in node:
            raise KeyError(
                f"Override key {leaf!r} not found in config "
                f"(full path: {key_path!r})"
            )
        node[leaf] = yaml.safe_load(raw_value)

    return data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_config(
    yaml_path: str,
    overrides: list[str] | None = None,
) -> PipelineConfig:
    """Load a YAML config file and return a validated :class:`PipelineConfig`.

    Parameters
    ----------
    yaml_path:
        Path to the YAML configuration file.
    overrides:
        Optional list of dot-notation overrides (``"key.sub=value"``).

    Raises
    ------
    FileNotFoundError
        If *yaml_path* does not point to an existing file.
    KeyError
        If an override path does not match the schema.
    pydantic.ValidationError
        If YAML content fails Pydantic validation (unknown keys, wrong types).
    """
    path = Path(yaml_path)
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {yaml_path}")

    with open(path, encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh)

    if not isinstance(raw, dict):
        raise ValueError(f"Expected a YAML mapping at top level, got {type(raw).__name__}")

    if overrides:
        _apply_overrides(raw, overrides)

    return PipelineConfig(**raw)
