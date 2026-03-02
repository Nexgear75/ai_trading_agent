"""SmaRuleBaseline — SMA crossover signal baseline for backtest comparison.

Generates Go/No-Go signals based on the crossover of two simple moving averages
(SMA fast and SMA slow) computed on close prices.  ``rolling().mean()`` is
backward-looking by construction, guaranteeing strict causality.

Task #039 — WS-9.
Spec reference: §13.3, Annexe E.2.4.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ai_trading.baselines._base import BaselinePersistenceMixin
from ai_trading.models.base import BaseModel, register_model


@register_model("sma_rule")
class SmaRuleBaseline(BaselinePersistenceMixin, BaseModel):
    """Baseline that trades on SMA fast/slow crossover.

    - ``output_type = "signal"`` — binary Go/No-Go, bypasses θ calibration.
    - ``execution_mode = "standard"`` — standard trade execution.
    - ``fit()`` stores config parameters (no-op otherwise).
    - ``predict()`` computes SMA crossover on ``ohlcv["close"]``.
    """

    output_type = "signal"
    execution_mode = "standard"
    _model_filename = "sma_rule_baseline.json"
    _model_name = "sma_rule"

    def __init__(self) -> None:
        self._fast: int | None = None
        self._slow: int | None = None

    def fit(
        self,
        X_train: np.ndarray,  # noqa: N803
        y_train: np.ndarray,
        X_val: np.ndarray,  # noqa: N803
        y_val: np.ndarray,
        config: Any,
        run_dir: Path,
        meta_train: Any = None,
        meta_val: Any = None,
        ohlcv: Any = None,
    ) -> dict:
        """Store SMA parameters from config. No learning takes place.

        Raises
        ------
        ValueError
            If ``config.baselines.sma.fast >= config.baselines.sma.slow``.
        """
        fast: int = config.baselines.sma.fast
        slow: int = config.baselines.sma.slow
        if fast >= slow:
            raise ValueError(
                f"baselines.sma.fast ({fast}) must be strictly less than "
                f"baselines.sma.slow ({slow})"
            )
        self._fast = fast
        self._slow = slow
        return {}

    def predict(
        self,
        X: np.ndarray,  # noqa: N803
        meta: Any = None,
        ohlcv: Any = None,
    ) -> np.ndarray:
        """Generate Go/No-Go signals from SMA crossover on close prices.

        Parameters
        ----------
        X : np.ndarray
            Input features, shape ``(N, L, F)``, dtype float32.
            Used only for shape; the signal is derived from *ohlcv*.
        meta : dict
            Must contain ``'decision_time'`` — a DatetimeIndex or array of
            timestamps identifying which OHLCV bars correspond to *X* samples.
        ohlcv : pd.DataFrame
            Full OHLCV DataFrame with a ``'close'`` column and DatetimeIndex.

        Returns
        -------
        np.ndarray
            Signal array of shape ``(N,)``, dtype float32.
            1.0 = Go (SMA_fast > SMA_slow), 0.0 = No-Go.

        Raises
        ------
        ValueError
            If *ohlcv* or *meta* is ``None``, or if ``fit()`` has not been called.
        """
        if self._fast is None or self._slow is None:
            raise ValueError(
                "SmaRuleBaseline.predict() called before fit(). "
                "Call fit() first to configure SMA parameters."
            )
        if ohlcv is None:
            raise ValueError("SmaRuleBaseline.predict() requires ohlcv (got None).")
        if meta is None:
            raise ValueError("SmaRuleBaseline.predict() requires meta (got None).")

        close: pd.Series = ohlcv["close"]
        sma_fast: pd.Series = close.rolling(window=self._fast).mean()
        sma_slow: pd.Series = close.rolling(window=self._slow).mean()

        # Go when SMA_fast strictly above SMA_slow; NaN → No-Go
        raw_signal: pd.Series = (sma_fast > sma_slow).astype(np.float32)
        # NaN in sma_slow (or sma_fast) → No-Go
        nan_mask = sma_fast.isna() | sma_slow.isna()
        raw_signal[nan_mask] = 0.0

        # Temporal alignment: decision_time is close_time (open_time + interval).
        # raw_signal is indexed by ohlcv.index (open_time), so we must map
        # decision_times back to open_times before indexing.
        decision_times = meta["decision_time"]
        if len(ohlcv.index) < 2:
            raise ValueError(
                "Cannot infer bar interval from ohlcv index with fewer than 2 bars."
            )
        interval = ohlcv.index[1] - ohlcv.index[0]
        open_times = decision_times - interval
        aligned = raw_signal.loc[open_times].values.astype(np.float32)

        return aligned
