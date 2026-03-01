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

    if not np.issubdtype(y.dtype, np.floating):
        raise ValueError(
            f"y must be a floating-point array, got {y.dtype}."
        )

    # --- Early exit for trivial cases ------------------------------------
    if n_bars < seq_len:
        return (
            np.empty((0, seq_len, n_features), dtype=np.float32),
            np.empty((0,), dtype=np.float32),
            pd.DatetimeIndex([]),
        )

    # --- Pre-compute feature values ----------------------------------------
    features_values = features_df.values  # (T, F)

    # --- Build valid sample indices ---------------------------------------
    # A sample at decision t (t >= L-1) is valid iff:
    #   - entire window [t-L+1 .. t] has final_mask True
    #   - y[t] is not NaN
    #   - no NaN in features window [t-L+1 .. t]

    # Compute rolling mask: True at t iff all of [t-L+1..t] are True
    # Vectorized via cumulative sum.
    mask_cumsum = np.cumsum(final_mask.astype(np.int64))
    window_all_valid = np.zeros(n_bars, dtype=bool)
    # t == seq_len - 1: first possible window (sum from index 0)
    window_all_valid[seq_len - 1] = mask_cumsum[seq_len - 1] == seq_len
    # t >= seq_len: rolling difference
    if n_bars > seq_len:
        window_all_valid[seq_len:] = (
            mask_cumsum[seq_len:] - mask_cumsum[: n_bars - seq_len]
        ) == seq_len

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

    # --- Build output arrays (vectorized gather) ----------------------------
    idx = np.array(valid_indices, dtype=np.intp)
    # Window offsets: for each valid t, gather rows [t-L+1 .. t]
    offsets = np.arange(seq_len)  # (L,)
    # row_indices[i, j] = valid_indices[i] - seq_len + 1 + j
    row_indices = idx[:, np.newaxis] - seq_len + 1 + offsets[np.newaxis, :]  # (N, L)
    x_seq = features_values[row_indices].astype(np.float32)  # (N, L, F)
    y_out = y[idx].astype(np.float32)  # (N,)

    timestamps = pd.DatetimeIndex(features_df.index[idx])

    return x_seq, y_out, timestamps


def flatten_seq_to_tab(
    x_seq: np.ndarray,
    feature_names: list[str],
) -> tuple[np.ndarray, list[str]]:
    """Flatten a 3D tensor ``(N, L, F)`` to 2D ``(N, L*F)`` for XGBoost.

    The flattening uses C-order (``np.reshape``), so for each lag the
    features are laid out contiguously:
    ``[feat0_lag0, feat1_lag0, ..., feat0_lag1, feat1_lag1, ...]``.

    Column names follow the ``{feature}_{lag}`` convention with lag 0
    being the oldest timestep and lag L−1 being the most recent.

    Task #017 — WS-4.

    Parameters
    ----------
    x_seq:
        Float array of shape ``(N, L, F)``.
    feature_names:
        List of feature names with exactly ``F`` elements.

    Returns
    -------
    x_tab:
        Array of shape ``(N, L*F)`` with the same dtype as *x_seq*.
    column_names:
        List of ``L*F`` strings: ``{feature}_{lag}``.

    Raises
    ------
    ValueError
        If *x_seq* is not 3D or ``len(feature_names) != F``.
    """
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
