"""Labels, valid mask, sample builder, and flatten utilities."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from lib.config import LabelConfig, WindowConfig
from lib.timeframes import TIMEFRAME_DELTA

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# LABELS
# ═══════════════════════════════════════════════════════════════════════════

_VALID_TARGET_TYPES = {"log_return_trade", "log_return_close_to_close"}


def compute_labels(
    ohlcv: pd.DataFrame,
    config: LabelConfig,
    candle_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    target_type = config.target_type
    if target_type not in _VALID_TARGET_TYPES:
        raise ValueError(
            f"Unknown target_type '{target_type}'. "
            f"Must be one of {sorted(_VALID_TARGET_TYPES)}."
        )
    h = config.horizon_H_bars
    n = len(ohlcv)
    if candle_mask.shape != (n,):
        raise ValueError(
            f"candle_mask shape {candle_mask.shape} does not match ohlcv length ({n},)."
        )
    if candle_mask.dtype != bool:
        raise ValueError(f"candle_mask dtype must be bool, got {candle_mask.dtype}.")

    close = ohlcv["close"].values.astype(np.float64)
    open_ = ohlcv["open"].values.astype(np.float64)
    y = np.full(n, np.nan, dtype=np.float64)
    label_mask = np.zeros(n, dtype=bool)

    for t in range(n):
        if target_type == "log_return_trade":
            if t + h >= n:
                continue
            if t + 1 >= n:
                continue
            if not np.all(candle_mask[t + 1: t + h + 1]):
                continue
            y[t] = np.log(close[t + h] / open_[t + 1])
            label_mask[t] = True
        else:
            if t + h >= n:
                continue
            if not candle_mask[t]:
                continue
            if h >= 1 and not np.all(candle_mask[t + 1: t + h + 1]):
                continue
            y[t] = np.log(close[t + h] / close[t])
            label_mask[t] = True

    return y, label_mask


# ═══════════════════════════════════════════════════════════════════════════
# MISSING CANDLES / VALID MASK
# ═══════════════════════════════════════════════════════════════════════════

def compute_valid_mask(
    timestamps: pd.Series,
    timeframe: str,
    seq_len: int,
    horizon: int,
) -> np.ndarray:
    _validate_valid_mask_inputs(timestamps, timeframe, seq_len, horizon)
    expected_delta = TIMEFRAME_DELTA[timeframe]
    n = len(timestamps)
    mask = np.ones(n, dtype=bool)
    if seq_len - 1 > 0:
        mask[: seq_len - 1] = False
    if horizon > 0:
        mask[max(0, n - horizon):] = False
    deltas = timestamps.diff()
    gap_flags = deltas > expected_delta
    gap_after_indices = np.where(gap_flags.values)[0] - 1
    for g in gap_after_indices:
        lo = max(0, g - horizon + 1)
        hi = min(n - 1, g + seq_len - 1)
        mask[lo: hi + 1] = False
    return mask


def _validate_valid_mask_inputs(
    timestamps: pd.Series,
    timeframe: str,
    seq_len: int,
    horizon: int,
) -> None:
    if len(timestamps) == 0:
        raise ValueError("Empty timestamp series: cannot compute valid mask.")
    if timeframe not in TIMEFRAME_DELTA:
        raise ValueError(
            f"Timeframe '{timeframe}' is not supported. "
            f"Supported: {sorted(TIMEFRAME_DELTA)}"
        )
    if seq_len < 1:
        raise ValueError(f"L (seq_len) must be >= 1, got {seq_len}")
    if horizon < 1:
        raise ValueError(f"H (horizon) must be >= 1, got {horizon}")


# ═══════════════════════════════════════════════════════════════════════════
# DATASET / SAMPLE BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def build_samples(
    features_df: pd.DataFrame,
    y: np.ndarray,
    final_mask: np.ndarray,
    config: WindowConfig,
) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    n_bars = len(features_df)
    n_features = features_df.shape[1]
    seq_len = config.L

    if n_features == 0:
        raise ValueError("features_df must have at least one feature column, got 0.")
    if y.shape != (n_bars,):
        raise ValueError(f"y length {y.shape} does not match features_df length ({n_bars},).")
    if final_mask.shape != (n_bars,):
        raise ValueError(
            f"final_mask length {final_mask.shape} does not match features_df length ({n_bars},)."
        )
    if final_mask.dtype != bool:
        raise ValueError(f"final_mask dtype must be bool, got {final_mask.dtype}.")
    if not np.issubdtype(y.dtype, np.floating):
        raise ValueError(f"y must be a floating-point array, got {y.dtype}.")

    if n_bars < seq_len:
        return (
            np.empty((0, seq_len, n_features), dtype=np.float32),
            np.empty((0,), dtype=np.float32),
            pd.DatetimeIndex([]),
        )

    features_values = features_df.values
    mask_cumsum = np.cumsum(final_mask.astype(np.int64))
    window_all_valid = np.zeros(n_bars, dtype=bool)
    window_all_valid[seq_len - 1] = mask_cumsum[seq_len - 1] == seq_len
    if n_bars > seq_len:
        window_all_valid[seq_len:] = (
            mask_cumsum[seq_len:] - mask_cumsum[: n_bars - seq_len]
        ) == seq_len
    y_valid = ~np.isnan(y)
    candidates = window_all_valid & y_valid
    valid_indices: list[int] = []
    for t in range(seq_len - 1, n_bars):
        if not candidates[t]:
            continue
        window = features_values[t - seq_len + 1: t + 1]
        if np.any(np.isnan(window)):
            continue
        valid_indices.append(t)
    n_samples = len(valid_indices)

    if n_samples == 0:
        return (
            np.empty((0, seq_len, n_features), dtype=np.float32),
            np.empty((0,), dtype=np.float32),
            pd.DatetimeIndex([]),
        )

    idx = np.array(valid_indices, dtype=np.intp)
    offsets = np.arange(seq_len)
    row_indices = idx[:, np.newaxis] - seq_len + 1 + offsets[np.newaxis, :]
    x_seq = features_values[row_indices].astype(np.float32)
    y_out = y[idx].astype(np.float32)
    timestamps = pd.DatetimeIndex(features_df.index[idx])
    return x_seq, y_out, timestamps


def flatten_seq_to_tab(
    x_seq: np.ndarray,
    feature_names: list[str],
) -> tuple[np.ndarray, list[str]]:
    if x_seq.ndim != 3:
        raise ValueError(
            f"x_seq must be 3D (N, L, F), got {x_seq.ndim}D with shape {x_seq.shape}."
        )
    n_samples, seq_len, n_features = x_seq.shape
    if len(feature_names) != n_features:
        raise ValueError(
            f"feature_names length ({len(feature_names)}) does not match "
            f"F={n_features} from x_seq shape {x_seq.shape}."
        )
    x_tab = np.reshape(x_seq, (n_samples, seq_len * n_features))
    column_names = [
        f"{feat}_{lag}"
        for lag in range(seq_len)
        for feat in feature_names
    ]
    return x_tab, column_names
