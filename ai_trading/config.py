"""Config loader — YAML → Pydantic v2 model.

Provides :func:`load_config` to load a YAML configuration file into a
fully-typed :class:`PipelineConfig` Pydantic model, with optional CLI
dot-notation overrides.  All sub-models use ``extra="forbid"`` to reject
unknown keys.

Task #002 — WS-1.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Strict base — every sub-model inherits extra="forbid"
# ---------------------------------------------------------------------------


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
    horizon_H_bars: int  # noqa: N815
    target_type: str


class WindowConfig(_StrictBase):
    L: int  # noqa: N815
    min_warmup: int


class FeaturesParamsConfig(_StrictBase):
    rsi_period: int
    rsi_epsilon: float
    ema_fast: int
    ema_slow: int
    vol_windows: list[int]
    logvol_epsilon: float
    volatility_ddof: int


class FeaturesConfig(_StrictBase):
    feature_version: str
    feature_list: list[str]
    params: FeaturesParamsConfig


class SplitsConfig(_StrictBase):
    scheme: str
    train_days: int
    test_days: int
    step_days: int
    val_frac_in_train: float
    embargo_bars: int
    min_samples_train: int
    min_samples_test: int


class ScalingConfig(_StrictBase):
    method: str
    epsilon: float
    robust_quantile_low: float
    robust_quantile_high: float
    rolling_window: int


class StrategyConfig(_StrictBase):
    strategy_type: str
    name: str
    framework: str


class ThresholdingConfig(_StrictBase):
    method: str
    q_grid: list[float]
    objective: str
    mdd_cap: float
    min_trades: int


class CostsConfig(_StrictBase):
    cost_model: str
    fee_rate_per_side: float
    slippage_rate_per_side: float


class BacktestConfig(_StrictBase):
    mode: str
    direction: str
    initial_equity: float
    position_fraction: float


class SmaConfig(_StrictBase):
    fast: int
    slow: int


class BaselinesConfig(_StrictBase):
    sma: SmaConfig


class TrainingConfig(_StrictBase):
    loss: str
    optimizer: str
    learning_rate: float
    batch_size: int
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
    dropout: float
    pool: str


class GRUModelConfig(_StrictBase):
    hidden_size: int
    num_layers: int
    bidirectional: bool
    dropout: float


class LSTMModelConfig(_StrictBase):
    hidden_size: int
    num_layers: int
    bidirectional: bool
    dropout: float


class PatchTSTModelConfig(_StrictBase):
    patch_size: int
    stride: int
    d_model: int
    n_heads: int
    n_layers: int
    ff_dim: int
    dropout: float


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
    sharpe_epsilon: float


class ReproducibilityConfig(_StrictBase):
    global_seed: int
    deterministic_torch: bool


class ArtifactsConfig(_StrictBase):
    output_dir: str
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
