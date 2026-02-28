"""RSI feature with Wilder smoothing.

Implements the Relative Strength Index (RSI) as specified in §6.3 of
the specification. Uses Wilder's exponential smoothing with SMA
initialisation.

Formula:
    G_t = max(0, C_t - C_{t-1})
    L_t = max(0, C_{t-1} - C_t)
    AG_n = mean(G[1..n])   (SMA initialisation)
    AL_n = mean(L[1..n])
    AG_t = ((n-1) * AG_{t-1} + G_t) / n   (Wilder smoothing)
    AL_t = ((n-1) * AL_{t-1} + L_t) / n
    RS_t = AG_t / (AL_t + epsilon)
    RSI_t = 100 - 100 / (1 + RS_t)
"""

import numpy as np
import pandas as pd

from ai_trading.features.registry import BaseFeature, register_feature


@register_feature("rsi_14")
class RSI14(BaseFeature):
    """RSI-14 with Wilder smoothing (spec §6.3).

    Required params (from config.features.params):
        rsi_period : int — RSI lookback period (default config: 14).
        rsi_epsilon : float — small constant to avoid division by zero.
    """

    required_params: list[str] = ["rsi_period", "rsi_epsilon"]

    @property
    def min_periods(self) -> int:
        """Minimum bars needed: rsi_period + 1 (n+1 closes for n deltas)."""
        return 15  # 14 + 1 per spec default

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        """Compute RSI with Wilder smoothing.

        Parameters
        ----------
        ohlcv : pd.DataFrame
            OHLCV data with at least a ``close`` column.
        params : dict
            Must contain ``rsi_period`` (int) and ``rsi_epsilon`` (float).

        Returns
        -------
        pd.Series
            RSI values indexed by ohlcv timestamps. NaN for t < rsi_period.
        """
        n: int = params["rsi_period"]
        epsilon: float = params["rsi_epsilon"]

        close = ohlcv["close"].to_numpy(dtype=np.float64)
        length = len(close)

        result = np.full(length, np.nan, dtype=np.float64)

        if length < n + 1:
            return pd.Series(result, index=ohlcv.index, name="rsi_14")

        # Compute deltas: delta[i] = close[i+1] - close[i]
        # gains[i] and losses[i] correspond to bar i+1
        deltas = np.diff(close)  # length - 1 elements
        gains = np.maximum(deltas, 0.0)
        losses = np.maximum(-deltas, 0.0)

        # SMA initialisation over first n periods (indices 0..n-1)
        ag = np.mean(gains[:n])
        al = np.mean(losses[:n])

        # RSI at bar n (first valid value)
        result[n] = _rsi_from_ag_al(ag, al, epsilon)

        # Wilder smoothing for bars n+1, n+2, ...
        for i in range(n, len(gains)):
            ag = ((n - 1) * ag + gains[i]) / n
            al = ((n - 1) * al + losses[i]) / n
            result[i + 1] = _rsi_from_ag_al(ag, al, epsilon)

        return pd.Series(result, index=ohlcv.index, name="rsi_14")


def _rsi_from_ag_al(ag: float, al: float, epsilon: float) -> float:
    """Compute RSI from average gain and average loss.

    Edge cases per spec §6.3:
        AG ≈ 0 and AL ≈ 0 → RSI = 50
        AL ≈ 0 and AG > 0 → RSI → 100  (handled by epsilon)
        AG ≈ 0 and AL > 0 → RSI → 0    (handled by epsilon)
    """
    if ag < epsilon and al < epsilon:
        return 50.0
    rs = ag / (al + epsilon)
    return 100.0 - 100.0 / (1.0 + rs)
