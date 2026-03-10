"""Feature registry, implementations, pipeline, and warmup."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

VALID_OUTPUT_TYPES = frozenset({"regression", "signal"})

# ═══════════════════════════════════════════════════════════════════════════
# FEATURE REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

FEATURE_REGISTRY: dict[str, type[BaseFeature]] = {}


class BaseFeature(ABC):
    required_params: list[str] = []

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if "required_params" not in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must explicitly declare 'required_params' "
                f"(e.g. required_params: list[str] = []). "
                f"Inheriting the base default silently is not allowed."
            )

    @abstractmethod
    def min_periods(self, params: dict) -> int: ...

    @abstractmethod
    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series: ...


def register_feature(name: str):
    def decorator(cls: type[BaseFeature]) -> type[BaseFeature]:
        if not (isinstance(cls, type) and issubclass(cls, BaseFeature)):
            raise TypeError(
                f"@register_feature('{name}'): {cls!r} is not a BaseFeature subclass."
            )
        if name in FEATURE_REGISTRY:
            raise ValueError(
                f"Feature '{name}' is already registered in FEATURE_REGISTRY."
            )
        FEATURE_REGISTRY[name] = cls
        return cls
    return decorator


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════

# --- Log returns ---

def _make_log_return_class(k: int) -> type[BaseFeature]:
    class _LogReturn(BaseFeature):
        required_params: list[str] = []

        def min_periods(self, params: dict) -> int:
            return k

        def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
            close = ohlcv["close"]
            result = np.log(close / close.shift(k))
            return result.rename(f"logret_{k}")

    _LogReturn.__name__ = f"LogReturn{k}"
    _LogReturn.__qualname__ = f"LogReturn{k}"
    return _LogReturn


LogReturn1 = register_feature("logret_1")(_make_log_return_class(1))
LogReturn2 = register_feature("logret_2")(_make_log_return_class(2))
LogReturn4 = register_feature("logret_4")(_make_log_return_class(4))


# --- Volatility ---

def _compute_rolling_volatility(
    close: pd.Series,
    window: int,
    ddof: int,
) -> pd.Series:
    logret = np.log(close / close.shift(1))
    result = logret.rolling(window=window, min_periods=window).std(ddof=ddof)
    return result.rename(f"vol_{window}")


@register_feature("vol_24")
class Volatility24(BaseFeature):
    _WINDOW: int = 24
    required_params: list[str] = ["volatility_ddof"]

    def min_periods(self, params: dict) -> int:
        return self._WINDOW

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        ddof = params["volatility_ddof"]
        return _compute_rolling_volatility(ohlcv["close"], self._WINDOW, ddof)


@register_feature("vol_72")
class Volatility72(BaseFeature):
    _WINDOW: int = 72
    required_params: list[str] = ["volatility_ddof"]

    def min_periods(self, params: dict) -> int:
        return self._WINDOW

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        ddof = params["volatility_ddof"]
        return _compute_rolling_volatility(ohlcv["close"], self._WINDOW, ddof)


# --- Volume ---

def _validated_logvol(volume: pd.Series, epsilon: float) -> pd.Series:
    if epsilon <= 0.0:
        raise ValueError(f"logvol_epsilon must be > 0, got {epsilon}")
    return pd.Series(np.log(volume + epsilon), index=volume.index)


@register_feature("logvol")
class LogVolume(BaseFeature):
    required_params: list[str] = ["logvol_epsilon"]

    def min_periods(self, params: dict) -> int:
        return 0

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        epsilon: float = params["logvol_epsilon"]
        result = _validated_logvol(ohlcv["volume"], epsilon)
        return result.rename("logvol")


@register_feature("dlogvol")
class DLogVolume(BaseFeature):
    required_params: list[str] = ["logvol_epsilon"]

    def min_periods(self, params: dict) -> int:
        return 1

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        epsilon: float = params["logvol_epsilon"]
        logvol = _validated_logvol(ohlcv["volume"], epsilon)
        result = logvol - logvol.shift(1)
        return result.rename("dlogvol")


# --- RSI ---

def _rsi_from_ag_al(ag: float, al: float, epsilon: float) -> float:
    if ag < epsilon and al < epsilon:
        return 50.0
    rs = ag / (al + epsilon)
    return 100.0 - 100.0 / (1.0 + rs)


@register_feature("rsi_14")
class RSI14(BaseFeature):
    required_params: list[str] = ["rsi_period", "rsi_epsilon"]

    def min_periods(self, params: dict) -> int:
        return params["rsi_period"]

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        n: int = params["rsi_period"]
        epsilon: float = params["rsi_epsilon"]
        if n < 1:
            raise ValueError(f"rsi_period must be >= 1, got {n}")
        if epsilon <= 0.0:
            raise ValueError(f"rsi_epsilon must be > 0, got {epsilon}")

        close = ohlcv["close"].to_numpy(dtype=np.float64)
        length = len(close)
        result = np.full(length, np.nan, dtype=np.float64)

        if length < n + 1:
            return pd.Series(result, index=ohlcv.index, name="rsi_14")

        deltas = np.diff(close)
        gains = np.maximum(deltas, 0.0)
        losses = np.maximum(-deltas, 0.0)

        ag: float = float(np.mean(gains[:n]))
        al: float = float(np.mean(losses[:n]))
        result[n] = _rsi_from_ag_al(ag, al, epsilon)

        for i in range(n, len(gains)):
            ag = ((n - 1) * ag + gains[i]) / n
            al = ((n - 1) * al + losses[i]) / n
            result[i + 1] = _rsi_from_ag_al(ag, al, epsilon)

        return pd.Series(result, index=ohlcv.index, name="rsi_14")


# --- EMA ---

def _compute_ema(close: np.ndarray, span: int) -> np.ndarray:
    n = len(close)
    result = np.full(n, np.nan, dtype=np.float64)
    if n < span:
        return result
    alpha = 2.0 / (span + 1)
    sma = np.mean(close[:span])
    result[span - 1] = sma
    for i in range(span, n):
        result[i] = alpha * close[i] + (1.0 - alpha) * result[i - 1]
    return result


@register_feature("ema_ratio_12_26")
class EmaRatio1226(BaseFeature):
    required_params: list[str] = ["ema_fast", "ema_slow"]

    def min_periods(self, params: dict) -> int:
        return params["ema_slow"] - 1

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        fast: int = params["ema_fast"]
        slow: int = params["ema_slow"]
        if fast <= 0:
            raise ValueError(f"ema_fast must be >= 1, got {fast}")
        if slow <= 0:
            raise ValueError(f"ema_slow must be >= 1, got {slow}")
        if fast >= slow:
            raise ValueError(f"ema_fast ({fast}) must be < ema_slow ({slow})")

        close = ohlcv["close"].to_numpy(dtype=np.float64)
        length = len(close)
        if length == 0:
            return pd.Series([], dtype=np.float64, index=ohlcv.index)

        ema_fast_arr = _compute_ema(close, fast)
        ema_slow_arr = _compute_ema(close, slow)
        result = np.full(length, np.nan, dtype=np.float64)
        for i in range(slow - 1, length):
            result[i] = ema_fast_arr[i] / ema_slow_arr[i] - 1.0
        return pd.Series(result, index=ohlcv.index, name="ema_ratio_12_26")


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

def _to_params_dict(params_obj: object) -> dict:
    if isinstance(params_obj, dict):
        return params_obj
    if hasattr(params_obj, "model_dump"):
        return params_obj.model_dump()
    return vars(params_obj)


def resolve_features(config: object) -> list[BaseFeature]:
    feature_list: list[str] = config.features.feature_list

    if not feature_list:
        raise ValueError("features.feature_list is empty — at least one feature required.")

    if len(feature_list) != len(set(feature_list)):
        seen: set[str] = set()
        for name in feature_list:
            if name in seen:
                raise ValueError(f"Duplicate feature in feature_list: '{name}'.")
            seen.add(name)

    if not FEATURE_REGISTRY:
        raise ValueError(
            "FEATURE_REGISTRY is empty — feature modules have not been imported."
        )

    params_dict = _to_params_dict(config.features.params)
    instances: list[BaseFeature] = []
    for name in feature_list:
        if name not in FEATURE_REGISTRY:
            raise ValueError(
                f"Feature '{name}' not found in FEATURE_REGISTRY. "
                f"Available: {sorted(FEATURE_REGISTRY.keys())}."
            )
        cls = FEATURE_REGISTRY[name]
        instance = cls()
        for param_name in instance.required_params:
            if param_name not in params_dict:
                raise ValueError(
                    f"Feature '{name}' requires param '{param_name}' but it is "
                    f"missing from config.features.params."
                )
        instances.append(instance)
    return instances


def compute_features(ohlcv: pd.DataFrame, config: object) -> pd.DataFrame:
    feature_version: str = config.features.feature_version
    logger.info("Computing features (version=%s)", feature_version)

    instances = resolve_features(config)
    feature_list: list[str] = config.features.feature_list
    params_dict = _to_params_dict(config.features.params)

    columns: list[pd.Series] = []
    for name, instance in zip(feature_list, instances, strict=True):
        series = instance.compute(ohlcv, params_dict)
        if len(series) != len(ohlcv):
            raise ValueError(
                f"Feature '{name}' returned {len(series)} rows, "
                f"expected {len(ohlcv)} (same as OHLCV input)."
            )
        series = series.rename(name)
        columns.append(series)

    result = pd.DataFrame({s.name: s for s in columns}, index=ohlcv.index)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# WARMUP
# ═══════════════════════════════════════════════════════════════════════════

def apply_warmup(
    features_df: pd.DataFrame,
    valid_mask: np.ndarray,
    min_warmup: int,
    feature_instances: list,
    params: dict,
) -> np.ndarray:
    n = len(features_df)
    if len(feature_instances) == 0:
        raise ValueError(
            "feature_instances is empty — at least one feature required "
            "to compute warmup validation."
        )
    if len(valid_mask) != n:
        raise ValueError(
            f"valid_mask length ({len(valid_mask)}) does not match "
            f"features_df length ({n})."
        )
    params_dict = params
    try:
        max_min_periods = max(
            inst.min_periods(params_dict) for inst in feature_instances
        )
    except KeyError as exc:
        raise ValueError(
            f"params is missing a key required by min_periods(): {exc}. "
            f"Pass the full config.features.params dict."
        ) from exc
    if min_warmup < max_min_periods:
        raise ValueError(
            f"min_warmup ({min_warmup}) must be >= max(min_periods) "
            f"({max_min_periods}). The warmup zone does not cover all "
            f"feature NaN prefixes."
        )
    warmup_mask = np.zeros(n, dtype=bool)
    if min_warmup < n:
        warmup_mask[min_warmup:] = True
    final_mask = warmup_mask & valid_mask
    valid_zone = features_df.values[final_mask]
    nan_mask = np.isnan(valid_zone)
    if np.any(nan_mask):
        nan_count = int(np.sum(nan_mask))
        raise ValueError(
            f"NaN values detected in the valid zone (post-warmup, post-gap mask): "
            f"{nan_count} NaN(s) found. This indicates a feature computation bug "
            f"or insufficient warmup."
        )
    return final_mask
