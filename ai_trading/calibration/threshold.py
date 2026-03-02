"""Quantile-grid threshold calibration (§11.2)."""

import math

import numpy as np
from numpy.typing import NDArray


def compute_quantile_thresholds(
    y_hat_val: NDArray[np.floating],
    q_grid: list[float],
) -> dict[float, float]:
    """Compute threshold θ(q) = quantile_q(y_hat_val) for each q in q_grid.

    Parameters
    ----------
    y_hat_val : 1D array of validation predictions.
    q_grid : list of quantile levels, each in [0, 1].

    Returns
    -------
    dict mapping each q to its computed threshold θ(q) as a Python float.

    Raises
    ------
    ValueError
        If y_hat_val is not 1D, is empty, q_grid is empty, or q values
        are outside [0, 1].
    """
    if y_hat_val.ndim != 1:
        raise ValueError(
            f"y_hat_val must be 1D, got shape {y_hat_val.shape}"
        )
    if y_hat_val.size == 0:
        raise ValueError("y_hat_val must not be empty")
    if len(q_grid) == 0:
        raise ValueError("q_grid must not be empty")
    if len(q_grid) != len(set(q_grid)):
        raise ValueError("q_grid must not contain duplicates")
    for q in q_grid:
        if not math.isfinite(q):
            raise ValueError(
                f"q_grid values must be finite, got {q}"
            )
        if q < 0.0 or q > 1.0:
            raise ValueError(
                f"q_grid values must be in [0, 1], got {q}"
            )

    thresholds = np.quantile(y_hat_val, q_grid)
    return dict(zip(q_grid, thresholds.tolist()))


def apply_threshold(
    y_hat: NDArray[np.floating],
    theta: float,
) -> NDArray[np.signedinteger]:
    """Generate binary Go/No-Go signals: 1 if y_hat[t] > theta, else 0.

    Parameters
    ----------
    y_hat : 1D array of predictions.
    theta : threshold value.

    Returns
    -------
    1D int32 array of same shape as y_hat.

    Raises
    ------
    ValueError
        If y_hat is not 1D.
    """
    if y_hat.ndim != 1:
        raise ValueError(
            f"y_hat must be 1D, got shape {y_hat.shape}"
        )
    return (y_hat > theta).astype(np.int32)
