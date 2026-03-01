"""Label target y_t computation.

Task #015 — WS-4: two label variants driven by config.

- ``log_return_trade``: y_t = log(Close[t+H] / Open[t+1])
- ``log_return_close_to_close``: y_t = log(Close[t+H] / Close[t])

Samples with gaps in [t+1, t+H] (for trade) or at t or in [t+1, t+H]
(for close-to-close) are invalidated via ``label_mask``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ai_trading.config import LabelConfig

_VALID_TARGET_TYPES = {"log_return_trade", "log_return_close_to_close"}


def compute_labels(
    ohlcv: pd.DataFrame,
    config: LabelConfig,
    valid_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute label targets and validity mask.

    Parameters
    ----------
    ohlcv:
        OHLCV DataFrame with columns ``open``, ``close`` (at minimum).
    config:
        Label configuration with ``horizon_H_bars`` and ``target_type``.
    valid_mask:
        Boolean array of shape ``(N,)`` — ``True`` where the candle is present
        (not a gap).

    Returns
    -------
    y:
        Float64 array of shape ``(N,)`` with label values. NaN where invalid.
    label_mask:
        Boolean array of shape ``(N,)`` — ``True`` where the label is computable.
    """
    target_type = config.target_type
    if target_type not in _VALID_TARGET_TYPES:
        raise ValueError(
            f"Unknown target_type '{target_type}'. "
            f"Must be one of {sorted(_VALID_TARGET_TYPES)}."
        )

    h = config.horizon_H_bars
    n = len(ohlcv)

    close = ohlcv["close"].values.astype(np.float64)
    open_ = ohlcv["open"].values.astype(np.float64)

    y = np.full(n, np.nan, dtype=np.float64)
    label_mask = np.zeros(n, dtype=bool)

    for t in range(n):
        # Check that all positions in the required range are within bounds
        # and not gaps.
        if target_type == "log_return_trade":
            # Need Open[t+1] and Close[t+H], plus no gaps in [t+1, t+H]
            if t + h >= n:
                continue
            if t + 1 >= n:
                continue
            # Check no gap in [t+1, t+h]
            if not np.all(valid_mask[t + 1 : t + h + 1]):
                continue
            y[t] = np.log(close[t + h] / open_[t + 1])
            label_mask[t] = True

        else:  # log_return_close_to_close
            # Need Close[t] and Close[t+H], plus no gaps at t or in [t+1, t+H]
            if t + h >= n:
                continue
            if not valid_mask[t]:
                continue
            # Check no gap in [t+1, t+h] (if h >= 1, range is non-empty)
            if h >= 1 and not np.all(valid_mask[t + 1 : t + h + 1]):
                continue
            y[t] = np.log(close[t + h] / close[t])
            label_mask[t] = True

    return y, label_mask
