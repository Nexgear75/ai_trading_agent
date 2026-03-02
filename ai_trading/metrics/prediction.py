"""Prediction metrics — MAE, RMSE, Directional Accuracy, Spearman IC.

Spec §14.1: computed on test period vectors y_true / y_hat
for ``output_type == "regression"`` models. Returns all ``None``
for ``output_type == "signal"`` (baselines, RL).
"""

import math

import numpy as np
from scipy import stats

# Valid output types (mirrors ai_trading.models.base.VALID_OUTPUT_TYPES).
_VALID_OUTPUT_TYPES = frozenset({"regression", "signal"})


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_vectors(
    y_true: np.ndarray,
    y_hat: np.ndarray,
    *,
    min_length: int = 1,
) -> None:
    """Validate paired prediction vectors.

    Raises
    ------
    ValueError
        If arrays are empty, have different lengths, or contain non-finite values.
    """
    if y_true.ndim != 1 or y_hat.ndim != 1:
        raise ValueError(
            f"y_true and y_hat must be 1-D arrays, "
            f"got ndim={y_true.ndim} and ndim={y_hat.ndim}."
        )
    if len(y_true) != len(y_hat):
        raise ValueError(
            f"y_true and y_hat must have the same length, "
            f"got {len(y_true)} and {len(y_hat)}."
        )
    if len(y_true) < min_length:
        raise ValueError(
            f"y_true must have at least {min_length} element(s), got {len(y_true)}."
        )
    if not np.all(np.isfinite(y_true)):
        raise ValueError("y_true contains non-finite values (NaN or ±inf).")
    if not np.all(np.isfinite(y_hat)):
        raise ValueError("y_hat contains non-finite values (NaN or ±inf).")


# ---------------------------------------------------------------------------
# Individual metrics
# ---------------------------------------------------------------------------


def compute_mae(y_true: np.ndarray, y_hat: np.ndarray) -> float:
    """Mean Absolute Error: mean(|y - ŷ|).

    Parameters
    ----------
    y_true, y_hat : np.ndarray (1-D, float64)

    Returns
    -------
    float
        MAE value (float64).
    """
    _validate_vectors(y_true, y_hat)
    return float(np.mean(np.abs(y_true - y_hat)))


def compute_rmse(y_true: np.ndarray, y_hat: np.ndarray) -> float:
    """Root Mean Squared Error: sqrt(mean((y - ŷ)²)).

    Parameters
    ----------
    y_true, y_hat : np.ndarray (1-D, float64)

    Returns
    -------
    float
        RMSE value (float64).
    """
    _validate_vectors(y_true, y_hat)
    return float(np.sqrt(np.mean((y_true - y_hat) ** 2)))


def compute_directional_accuracy(
    y_true: np.ndarray,
    y_hat: np.ndarray,
) -> float | None:
    """Directional Accuracy: mean(1[sign(y)==sign(ŷ)]) on eligible samples.

    Samples with ``y_true == 0`` or ``y_hat == 0`` are excluded.
    Returns ``None`` if no eligible samples remain.

    Parameters
    ----------
    y_true, y_hat : np.ndarray (1-D, float64)

    Returns
    -------
    float | None
        DA ∈ [0, 1] or None.
    """
    _validate_vectors(y_true, y_hat)
    eligible = (y_true != 0.0) & (y_hat != 0.0)
    n_eligible = int(np.sum(eligible))
    if n_eligible == 0:
        return None
    sign_match = np.sign(y_true[eligible]) == np.sign(y_hat[eligible])
    return float(np.mean(sign_match))


def compute_spearman_ic(y_true: np.ndarray, y_hat: np.ndarray) -> float:
    """Spearman rank correlation (Information Coefficient).

    Parameters
    ----------
    y_true, y_hat : np.ndarray (1-D, float64)

    Returns
    -------
    float
        Spearman IC value (float64).

    Raises
    ------
    ValueError
        If fewer than 2 samples, or if one input is constant (zero variance).
    """
    _validate_vectors(y_true, y_hat, min_length=2)
    if np.all(y_true == y_true[0]):
        raise ValueError("y_true is constant — Spearman IC is undefined.")
    if np.all(y_hat == y_hat[0]):
        raise ValueError("y_hat is constant — Spearman IC is undefined.")
    result = stats.spearmanr(y_true, y_hat)
    ic = float(result.statistic)  # type: ignore[union-attr]
    if not math.isfinite(ic):
        raise ValueError(f"Spearman IC returned non-finite value: {ic}.")
    return ic


# ---------------------------------------------------------------------------
# Aggregated prediction metrics
# ---------------------------------------------------------------------------


def compute_prediction_metrics(
    y_true: np.ndarray,
    y_hat: np.ndarray,
    *,
    output_type: str,
) -> dict[str, float | None]:
    """Compute all prediction metrics for a fold's test period.

    Parameters
    ----------
    y_true, y_hat : np.ndarray (1-D, float64)
        True and predicted values.
    output_type : str
        ``"regression"`` or ``"signal"``.

    Returns
    -------
    dict[str, float | None]
        Keys: ``mae``, ``rmse``, ``directional_accuracy``, ``spearman_ic``.
        All values are ``None`` when ``output_type == "signal"``.
    """
    if output_type not in _VALID_OUTPUT_TYPES:
        raise ValueError(
            f"output_type must be one of {sorted(_VALID_OUTPUT_TYPES)}, "
            f"got {output_type!r}."
        )
    if output_type == "signal":
        return {
            "mae": None,
            "rmse": None,
            "directional_accuracy": None,
            "spearman_ic": None,
        }
    # output_type == "regression"
    return {
        "mae": compute_mae(y_true, y_hat),
        "rmse": compute_rmse(y_true, y_hat),
        "directional_accuracy": compute_directional_accuracy(y_true, y_hat),
        "spearman_ic": compute_spearman_ic(y_true, y_hat),
    }
