"""Rolling volatility features: vol_24 and vol_72.

Task #009: Features de volatilité rolling.

Each feature computes the rolling standard deviation (population, ddof from
config) of log-returns over a causal window. Log-returns are recomputed
internally from close prices, without depending on the ``logret_1`` feature.

Formulas
--------
- ``logret_1(t) = log(close(t) / close(t-1))``
- ``vol_n(t) = std(logret_1(t-i), i in [0, n-1], ddof=config)``

The window is strictly backward-looking: value at *t* depends only on
close prices at indices ``<= t``.
"""

import numpy as np
import pandas as pd

from ai_trading.features.registry import BaseFeature, register_feature


def _compute_rolling_volatility(
    close: pd.Series,
    window: int,
    ddof: int,
) -> pd.Series:
    """Compute rolling std of log-returns over a causal window.

    Parameters
    ----------
    close : pd.Series
        Close prices indexed by timestamp.
    window : int
        Number of log-returns in the rolling window.
    ddof : int
        Delta degrees of freedom for std computation.

    Returns
    -------
    pd.Series
        Rolling volatility. NaN where the window is incomplete.
    """
    logret = np.log(close / close.shift(1))
    return logret.rolling(window=window, min_periods=window).std(ddof=ddof)


@register_feature("vol_24")
class Volatility24(BaseFeature):
    """Rolling volatility over a fixed 24-bar window (spec §6.5).

    The window is always 24, matching the feature name and the spec formula::

        vol_24(t) = std(logret_1(t-i), i=0..23, ddof=config)
    """

    _WINDOW: int = 24

    required_params: list[str] = ["volatility_ddof"]

    def min_periods(self, params: dict) -> int:
        """Minimum bars before first valid value: 24."""
        return self._WINDOW

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        """Compute vol_24 using a fixed 24-bar rolling window.

        Parameters
        ----------
        ohlcv : pd.DataFrame
            OHLCV data with a ``close`` column.
        params : dict
            Must contain ``volatility_ddof`` (int).

        Returns
        -------
        pd.Series
            Rolling volatility values.

        Raises
        ------
        KeyError
            If required params are missing.
        """
        ddof = params["volatility_ddof"]
        return _compute_rolling_volatility(ohlcv["close"], self._WINDOW, ddof)


@register_feature("vol_72")
class Volatility72(BaseFeature):
    """Rolling volatility over a fixed 72-bar window (spec §6.5).

    The window is always 72, matching the feature name and the spec formula::

        vol_72(t) = std(logret_1(t-i), i=0..71, ddof=config)
    """

    _WINDOW: int = 72

    required_params: list[str] = ["volatility_ddof"]

    def min_periods(self, params: dict) -> int:
        """Minimum bars before first valid value: 72."""
        return self._WINDOW

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        """Compute vol_72 using a fixed 72-bar rolling window.

        Parameters
        ----------
        ohlcv : pd.DataFrame
            OHLCV data with a ``close`` column.
        params : dict
            Must contain ``volatility_ddof`` (int).

        Returns
        -------
        pd.Series
            Rolling volatility values.

        Raises
        ------
        KeyError
            If required params are missing.
        """
        ddof = params["volatility_ddof"]
        return _compute_rolling_volatility(ohlcv["close"], self._WINDOW, ddof)
