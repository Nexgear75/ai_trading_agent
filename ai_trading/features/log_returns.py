"""Log-return features: logret_1, logret_2, logret_4.

Implements three log-return features as ``BaseFeature`` subclasses, registered
in ``FEATURE_REGISTRY`` via ``@register_feature``.

Formulas (spec §6.2):
- ``logret_1(t) = log(C_t / C_{t-1})``
- ``logret_2(t) = log(C_t / C_{t-2})``
- ``logret_4(t) = log(C_t / C_{t-4})``

Each feature produces NaN at positions ``t < k`` (no forward-fill or zero-fill).
All computations are strictly causal: value at *t* depends only on data at
indices ``<= t``.
"""

import numpy as np
import pandas as pd

from ai_trading.features.registry import BaseFeature, register_feature


@register_feature("logret_1")
class LogReturn1(BaseFeature):
    """Log-return over 1 bar: ``log(C_t / C_{t-1})``."""

    required_params: list[str] = []

    @property
    def min_periods(self) -> int:
        return 1

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        """Compute 1-bar log-return from close prices."""
        close = ohlcv["close"]
        return np.log(close / close.shift(1))


@register_feature("logret_2")
class LogReturn2(BaseFeature):
    """Log-return over 2 bars: ``log(C_t / C_{t-2})``."""

    required_params: list[str] = []

    @property
    def min_periods(self) -> int:
        return 2

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        """Compute 2-bar log-return from close prices."""
        close = ohlcv["close"]
        return np.log(close / close.shift(2))


@register_feature("logret_4")
class LogReturn4(BaseFeature):
    """Log-return over 4 bars: ``log(C_t / C_{t-4})``."""

    required_params: list[str] = []

    @property
    def min_periods(self) -> int:
        return 4

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        """Compute 4-bar log-return from close prices."""
        close = ohlcv["close"]
        return np.log(close / close.shift(4))
