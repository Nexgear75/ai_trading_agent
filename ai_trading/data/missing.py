"""Missing candles policy — valid sample mask computation.

Detects timestamp gaps in OHLCV data and produces a boolean mask indicating
which sample positions are valid. A sample at index ``t`` requires contiguous
candles in its input window ``[t-L+1, t]`` and output/execution window
``[t+1, t+H]``, including the decision-to-execution transition ``t → t+1``.

No interpolation is performed: missing candles simply invalidate affected
samples.

Reference: spec §4.3, §6.6.
"""

import numpy as np
import pandas as pd

# Mapping from timeframe strings to pandas Timedelta (shared with qa.py).
_TIMEFRAME_DELTA: dict[str, pd.Timedelta] = {
    "1m": pd.Timedelta(minutes=1),
    "3m": pd.Timedelta(minutes=3),
    "5m": pd.Timedelta(minutes=5),
    "15m": pd.Timedelta(minutes=15),
    "30m": pd.Timedelta(minutes=30),
    "1h": pd.Timedelta(hours=1),
    "2h": pd.Timedelta(hours=2),
    "4h": pd.Timedelta(hours=4),
    "6h": pd.Timedelta(hours=6),
    "8h": pd.Timedelta(hours=8),
    "12h": pd.Timedelta(hours=12),
    "1d": pd.Timedelta(days=1),
    "3d": pd.Timedelta(days=3),
    "1w": pd.Timedelta(weeks=1),
}


def compute_valid_mask(
    timestamps: pd.Series,
    timeframe: str,
    seq_len: int,
    horizon: int,
) -> np.ndarray:
    """Compute a boolean mask marking valid sample positions.

    A sample at decision time ``t`` is valid when:

    - The input window ``[t - seq_len + 1, t]`` fits within the data bounds.
    - The output window ``[t + 1, t + horizon]`` fits within the data bounds.
    - No timestamp gap exists in the contiguous range
      ``[t - seq_len + 1, t + horizon]``.

    Parameters
    ----------
    timestamps : pd.Series
        Ordered timestamps of the candles (one per row in the OHLCV data).
    timeframe : str
        Expected candle interval (e.g. ``"1h"``, ``"4h"``).
    seq_len : int
        Input window length ``L`` (from ``window.L`` in config). Must be >= 1.
    horizon : int
        Prediction horizon ``H`` (from ``label.horizon_H_bars``). Must be >= 1.

    Returns
    -------
    np.ndarray
        Boolean array of shape ``(N,)`` where ``N = len(timestamps)``.

    Raises
    ------
    ValueError
        If timestamps is empty, timeframe is unsupported, or L/H < 1.
    """
    _validate_inputs(timestamps, timeframe, seq_len, horizon)

    expected_delta = _TIMEFRAME_DELTA[timeframe]
    n = len(timestamps)
    mask = np.ones(n, dtype=bool)

    # --- Edge invalidity: samples that can't form complete windows ----------
    # Need indices [t-L+1 .. t] → t >= L-1
    if seq_len - 1 > 0:
        mask[: seq_len - 1] = False
    # Need indices [t+1 .. t+H] → t+H <= N-1 → t <= N-1-H
    if horizon > 0:
        mask[n - horizon :] = False

    # --- Gap detection ------------------------------------------------------
    # diff()[i] = timestamps[i] - timestamps[i-1]; index 0 has NaT.
    deltas = timestamps.diff()
    # A gap exists after index (i-1) when deltas.iloc[i] > expected_delta.
    # Equivalently, gap_after_indices contains indices g where the transition
    # g → g+1 is non-contiguous.
    gap_flags = deltas > expected_delta
    gap_after_indices = np.where(gap_flags.values)[0] - 1

    # --- Invalidate samples affected by gaps --------------------------------
    # For a gap after index g, sample t is invalid if any transition in the
    # full window [t-L+1, t+H] crosses the gap, i.e.:
    #   t - L + 1 <= g <= t + H - 1
    # Solving for t:  g - H + 1 <= t <= g + L - 1
    for g in gap_after_indices:
        lo = max(0, g - horizon + 1)
        hi = min(n - 1, g + seq_len - 1)
        mask[lo : hi + 1] = False

    return mask


def _validate_inputs(
    timestamps: pd.Series,
    timeframe: str,
    seq_len: int,
    horizon: int,
) -> None:
    """Validate inputs, raising ValueError on any problem."""
    if len(timestamps) == 0:
        raise ValueError("Empty timestamp series: cannot compute valid mask.")

    if timeframe not in _TIMEFRAME_DELTA:
        raise ValueError(
            f"Timeframe '{timeframe}' is not supported. "
            f"Supported: {sorted(_TIMEFRAME_DELTA)}"
        )

    if seq_len < 1:
        raise ValueError(f"L (seq_len) must be >= 1, got {seq_len}")

    if horizon < 1:
        raise ValueError(f"H (horizon) must be >= 1, got {horizon}")
