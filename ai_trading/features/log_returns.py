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

The three classes are generated via ``_make_log_return_class(k)`` to avoid
duplication of identical logic.
"""

import numpy as np
import pandas as pd

from ai_trading.features.registry import BaseFeature, register_feature


def _make_log_return_class(k: int) -> type[BaseFeature]:
    """Factory: create a log-return feature class for lag *k*.

    Parameters
    ----------
    k : int
        Number of bars for the log-return lag (1, 2, or 4).

    Returns
    -------
    type[BaseFeature]
        A concrete ``BaseFeature`` subclass computing
        ``log(C_t / C_{t-k})``.
    """

    class _LogReturn(BaseFeature):
        __doc__ = f"""Log-return over {k} bar(s): ``log(C_t / C_{{t-{k}}})``."""

        required_params: list[str] = []

        def min_periods(self, params: dict) -> int:
            return k

        def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
            """Compute k-bar log-return from close prices."""
            close = ohlcv["close"]
            result = np.log(close / close.shift(k))
            if isinstance(result, pd.Series):
                result = result.rename(f"logret_{k}")
            return result

    _LogReturn.__name__ = f"LogReturn{k}"
    _LogReturn.__qualname__ = f"LogReturn{k}"
    return _LogReturn


LogReturn1 = register_feature("logret_1")(_make_log_return_class(1))
LogReturn2 = register_feature("logret_2")(_make_log_return_class(2))
LogReturn4 = register_feature("logret_4")(_make_log_return_class(4))


def load_builtin_features() -> None:
    """Ensure log-return features are registered in FEATURE_REGISTRY.

    This function is intended to be called at pipeline startup so that the
    built-in log-return features are registered even if this module has not
    been imported elsewhere in the codebase.
    """
    # Access the feature classes to make the registration relationship explicit
    # for static analysis tools and human readers. Registration itself happens
    # at module import time via the decorators above.
    _ = (LogReturn1, LogReturn2, LogReturn4)
