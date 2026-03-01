"""EMA ratio feature: ema_ratio_12_26.

Implements the EMA ratio feature as specified in §6.4 of the specification.

Formula:
    alpha_n = 2 / (n + 1)
    EMA_n(t) = alpha_n * C_t + (1 - alpha_n) * EMA_n(t-1)
    Initialisation: EMA_n(n-1) = SMA(C[0..n-1])
    ema_ratio(t) = EMA_fast(t) / EMA_slow(t) - 1

The feature is strictly causal: the value at index t depends only on
close prices at indices <= t.
"""

import numpy as np
import pandas as pd

from ai_trading.features.registry import BaseFeature, register_feature


def _compute_ema(close: np.ndarray, span: int) -> np.ndarray:
    """Compute EMA with SMA initialisation.

    Parameters
    ----------
    close : np.ndarray
        Close prices as float64.
    span : int
        EMA period (e.g. 12 or 26).

    Returns
    -------
    np.ndarray
        EMA values. NaN for indices < span - 1.
    """
    n = len(close)
    result = np.full(n, np.nan, dtype=np.float64)

    if n < span:
        return result

    alpha = 2.0 / (span + 1)

    # SMA initialisation: average of first `span` values
    sma = np.mean(close[:span])
    result[span - 1] = sma

    # Exponential smoothing from index `span` onward
    for i in range(span, n):
        result[i] = alpha * close[i] + (1.0 - alpha) * result[i - 1]

    return result


@register_feature("ema_ratio_12_26")
class EmaRatio1226(BaseFeature):
    """EMA ratio feature: EMA_fast / EMA_slow - 1 (spec §6.4).

    Required params (from config.features.params):
        ema_fast : int — fast EMA period (default config: 12).
        ema_slow : int — slow EMA period (default config: 26).
    """

    required_params: list[str] = ["ema_fast", "ema_slow"]

    @property
    def min_periods(self) -> int:
        """Number of leading NaN values: 25 (spec-default ``ema_slow=26``).

        ``compute()`` produces its first non-NaN value at index
        ``ema_slow - 1`` (i.e. 25 leading NaN for the default period of 26,
        since the first valid value is at index 25).

        .. note::
            This value is valid only for the spec-default ``ema_slow=26``.
            If a different ``ema_slow`` is configured, the actual leading
            NaN count will be ``ema_slow - 1``, which may differ from this
            hard-coded return value.
        """
        return 25

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        """Compute EMA ratio from close prices.

        Parameters
        ----------
        ohlcv : pd.DataFrame
            OHLCV data with at least a ``close`` column.
        params : dict
            Must contain ``ema_fast`` (int) and ``ema_slow`` (int).

        Returns
        -------
        pd.Series
            EMA ratio values indexed by ohlcv timestamps.
            First non-NaN value at index ``ema_slow - 1``; NaN for ``t < ema_slow - 1``.

        Raises
        ------
        KeyError
            If ``ema_fast`` or ``ema_slow`` is missing from params.
        ValueError
            If ``ema_fast`` or ``ema_slow`` <= 0, or if ema_fast > ema_slow.
        """
        fast: int = params["ema_fast"]
        slow: int = params["ema_slow"]

        if fast <= 0:
            msg = f"ema_fast must be >= 1, got {fast}"
            raise ValueError(msg)
        if slow <= 0:
            msg = f"ema_slow must be >= 1, got {slow}"
            raise ValueError(msg)
        if fast > slow:
            msg = f"ema_fast ({fast}) must be <= ema_slow ({slow})"
            raise ValueError(msg)

        close = ohlcv["close"].to_numpy(dtype=np.float64)
        length = len(close)

        if length == 0:
            return pd.Series([], dtype=np.float64, index=ohlcv.index)

        ema_fast_arr = _compute_ema(close, fast)
        ema_slow_arr = _compute_ema(close, slow)

        result = np.full(length, np.nan, dtype=np.float64)

        for i in range(slow - 1, length):
            result[i] = ema_fast_arr[i] / ema_slow_arr[i] - 1.0

        return pd.Series(result, index=ohlcv.index)
