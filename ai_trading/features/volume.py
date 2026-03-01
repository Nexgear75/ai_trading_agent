"""Volume features: logvol and dlogvol.

Implements two volume features as ``BaseFeature`` subclasses, registered
in ``FEATURE_REGISTRY`` via ``@register_feature``.

Formulas (spec §6.2):
- ``logvol(t) = log(V_t + ε)``  with ε = ``logvol_epsilon`` from config.
- ``dlogvol(t) = logvol(t) - logvol(t-1)``

``logvol`` produces no NaN (available from the first bar).
``dlogvol`` produces NaN at t=0 (requires two bars).
All computations are strictly causal.
"""

import numpy as np
import pandas as pd

from ai_trading.features.registry import BaseFeature, register_feature


def _validated_logvol(volume: pd.Series, epsilon: float) -> pd.Series:
    """Compute log(V + ε) with explicit epsilon validation."""
    if epsilon <= 0.0:
        raise ValueError(f"logvol_epsilon must be > 0, got {epsilon}")
    return np.log(volume + epsilon)


@register_feature("logvol")
class LogVolume(BaseFeature):
    """Log-volume: ``log(V_t + ε)``."""

    required_params: list[str] = ["logvol_epsilon"]

    def min_periods(self, params: dict) -> int:
        return 1

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        """Compute log-volume from OHLCV volume column."""
        epsilon: float = params["logvol_epsilon"]
        result = _validated_logvol(ohlcv["volume"], epsilon)
        return result.rename("logvol")


@register_feature("dlogvol")
class DLogVolume(BaseFeature):
    """Differential log-volume: ``logvol(t) - logvol(t-1)``."""

    required_params: list[str] = ["logvol_epsilon"]

    def min_periods(self, params: dict) -> int:
        return 2

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        """Compute differential log-volume from OHLCV volume column."""
        epsilon: float = params["logvol_epsilon"]
        logvol = _validated_logvol(ohlcv["volume"], epsilon)
        result = logvol - logvol.shift(1)
        return result.rename("dlogvol")
