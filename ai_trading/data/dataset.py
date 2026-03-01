"""Sample builder — sliding-window dataset construction.

Transforms a 2D features DataFrame and label vector into aligned 3D
tensors for model training: ``X_seq (N, L, F)``, ``y (N,)``, and
a ``timestamps`` index of decision timestamps.

Task #016 — WS-4.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ai_trading.config import WindowConfig


def build_samples(
    features_df: pd.DataFrame,
    y: np.ndarray,
    final_mask: np.ndarray,
    config: WindowConfig,
) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    """Build sliding-window samples from features and labels.

    For each valid decision timestamp *t*, constructs a window
    ``X_t = features[t-L+1 : t+1]`` of shape ``(L, F)``.  A sample is
    retained only when:

    1. ``final_mask[t]`` is True **and** the entire window
       ``[t-L+1 .. t]`` has ``final_mask`` True,
    2. ``y[t]`` is not NaN,
    3. no NaN exists in the feature window.

    Parameters
    ----------
    features_df:
        DataFrame of shape ``(T, F)`` with feature columns indexed by
        timestamp.  Must have at least one column.
    y:
        Float64 label array of shape ``(T,)``.
    final_mask:
        Boolean array of shape ``(T,)`` — ``True`` where the bar is valid.
    config:
        Window configuration with ``L`` (sequence length).

    Returns
    -------
    X_seq:
        Float32 array of shape ``(N, L, F)``.
    y_out:
        Float32 array of shape ``(N,)``.
    timestamps:
        DatetimeIndex of length ``N`` — the decision timestamps.

    Raises
    ------
    ValueError
        If inputs are inconsistent (length mismatches, wrong dtype,
        no feature columns).
    """
    n_bars = len(features_df)
    n_features = features_df.shape[1]
    seq_len = config.L  # noqa: N806

    # --- Input validation -------------------------------------------------
    if n_features == 0:
        raise ValueError(
            "features_df must have at least one feature column, got 0."
        )

    if y.shape != (n_bars,):
        raise ValueError(
            f"y length {y.shape} does not match features_df length ({n_bars},)."
        )

    if final_mask.shape != (n_bars,):
        raise ValueError(
            f"final_mask length {final_mask.shape} does not match "
            f"features_df length ({n_bars},)."
        )

    if final_mask.dtype != bool:
        raise ValueError(
            f"final_mask dtype must be bool, got {final_mask.dtype}."
        )

    # --- Early exit for trivial cases ------------------------------------
    if n_bars < seq_len:
        return (
            np.empty((0, seq_len, n_features), dtype=np.float32),
            np.empty((0,), dtype=np.float32),
            pd.DatetimeIndex([]),
        )

    # --- Pre-compute feature values as float64 array ----------------------
    features_values = features_df.values  # (T, F)

    # --- Build valid sample indices ---------------------------------------
    # A sample at decision t (t >= L-1) is valid iff:
    #   - entire window [t-L+1 .. t] has final_mask True
    #   - y[t] is not NaN
    #   - no NaN in features window [t-L+1 .. t]

    # Compute rolling mask: True at t iff all of [t-L+1..t] are True
    # Using cumulative sum to efficiently compute this.
    mask_cumsum = np.cumsum(final_mask.astype(np.int64))
    # For t >= L-1: window_all_valid[t] = (cumsum[t] - cumsum[t-L]) == L
    # For t < L-1: not enough bars
    window_all_valid = np.zeros(n_bars, dtype=bool)
    for t in range(seq_len - 1, n_bars):
        if t - seq_len >= 0:
            window_sum = mask_cumsum[t] - mask_cumsum[t - seq_len]
        else:
            window_sum = mask_cumsum[t]
        window_all_valid[t] = window_sum == seq_len

    # Filter by y not NaN
    y_valid = ~np.isnan(y)

    # Candidate positions: window valid AND y valid
    candidates = window_all_valid & y_valid

    # Now check for NaN in features within each candidate window
    valid_indices: list[int] = []
    for t in range(seq_len - 1, n_bars):
        if not candidates[t]:
            continue
        window = features_values[t - seq_len + 1 : t + 1]
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

    # --- Build output arrays -----------------------------------------------
    x_seq = np.empty((n_samples, seq_len, n_features), dtype=np.float32)
    y_out = np.empty(n_samples, dtype=np.float32)

    for i, t in enumerate(valid_indices):
        x_seq[i] = features_values[t - seq_len + 1 : t + 1].astype(np.float32)
        y_out[i] = np.float32(y[t])

    timestamps = features_df.index[valid_indices]

    return x_seq, y_out, timestamps
