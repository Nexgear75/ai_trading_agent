"""Scalers for 3D feature tensors (WS-5.1, WS-5.2).

Provides StandardScaler (§9.1) and RobustScaler (§9.2) for per-feature
normalisation. Statistics are estimated on train data only (anti-leak).
Factory function :func:`create_scaler` selects the scaler by config.

References:
    - Spec §9.1: standardisation par feature
    - Spec §9.2: scaling robuste ou clipping
    - Plan WS-5.1: standard scaler (fit-on-train)
    - Plan WS-5.2: robust scaler (option)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ai_trading.config import ScalingConfig

logger = logging.getLogger(__name__)

CONSTANT_FEATURE_SIGMA_THRESHOLD: float = 1e-8


# ------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------


def _validate_3d(x: np.ndarray, name: str) -> None:
    """Raise ValueError if *x* is not 3-D."""
    if x.ndim != 3:
        raise ValueError(
            f"{name} must be 3D (N, L, F), got {x.ndim}D with shape {x.shape}"
        )


def _validate_epsilon(epsilon: float) -> None:
    """Raise ValueError if *epsilon* is not finite or negative."""
    if not np.isfinite(epsilon) or epsilon < 0:
        raise ValueError(
            f"epsilon must be finite and >= 0, got {epsilon}"
        )


class StandardScaler:
    """Per-feature standard scaler for 3D tensors (N, L, F).

    Parameters
    ----------
    epsilon : float
        Small value added to σ in the denominator to avoid division by zero.
        Must be read from ``config.scaling.epsilon``.
    """

    def __init__(self, epsilon: float) -> None:
        _validate_epsilon(epsilon)
        self._epsilon = epsilon
        self.mean_: np.ndarray | None = None
        self.std_: np.ndarray | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, x_train: np.ndarray) -> StandardScaler:
        """Estimate μ and σ per feature on training data.

        Parameters
        ----------
        x_train : np.ndarray
            Training tensor of shape ``(N, L, F)``, dtype float32.

        Returns
        -------
        self
        """
        _validate_3d(x_train, "x_train")

        if np.isnan(x_train).any():
            raise ValueError("NaN in X_train before scaling")

        n, seq_len, f = x_train.shape
        flat = x_train.reshape(n * seq_len, f)

        mean = flat.mean(axis=0).astype(np.float64)
        std = flat.std(axis=0).astype(np.float64)
        self.mean_ = mean
        self.std_ = std

        # Guard: warn about constant features
        constant_mask = std < CONSTANT_FEATURE_SIGMA_THRESHOLD
        if constant_mask.any():
            indices = np.where(constant_mask)[0].tolist()
            logger.warning(
                "Constant feature(s) detected (σ < %s) at indices %s. "
                "These will be set to 0.0 after scaling.",
                CONSTANT_FEATURE_SIGMA_THRESHOLD,
                indices,
            )

        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        """Apply scaling: (x - μ) / (σ + ε).

        Parameters
        ----------
        x : np.ndarray
            Tensor of shape ``(N, L, F)``.

        Returns
        -------
        np.ndarray
            Scaled tensor, same shape, dtype float32.
        """
        if self.mean_ is None or self.std_ is None:
            raise RuntimeError("Scaler has not been fit yet. Call fit() first.")

        _validate_3d(x, "x")

        x_scaled = (x - self.mean_) / (self.std_ + self._epsilon)

        # Guard: constant features → 0.0
        constant_mask = self.std_ < CONSTANT_FEATURE_SIGMA_THRESHOLD
        if constant_mask.any():
            x_scaled[:, :, constant_mask] = 0.0

        return x_scaled.astype(np.float32)

    def fit_transform(self, x_train: np.ndarray) -> np.ndarray:
        """Fit on x_train and transform it in one call."""
        return self.fit(x_train).transform(x_train)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def save(self, path: str | Path) -> None:
        """Save scaler parameters (μ, σ, ε) to an .npz file."""
        if self.mean_ is None or self.std_ is None:
            raise RuntimeError("Scaler has not been fit yet. Call fit() first.")

        np.savez(
            path,
            mean=self.mean_,
            std=self.std_,
            epsilon=np.array(self._epsilon),
        )

    def load(self, path: str | Path) -> StandardScaler:
        """Load scaler parameters from an .npz file.

        Parameters
        ----------
        path : str or Path
            Path to the .npz file saved by :meth:`save`.

        Returns
        -------
        self
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Scaler parameter file not found: {path}")

        with np.load(path) as data:
            self.mean_ = data["mean"]
            self.std_ = data["std"]
            loaded_epsilon = float(data["epsilon"])

        if loaded_epsilon != self._epsilon:
            raise ValueError(
                f"Epsilon mismatch: file has {loaded_epsilon}, "
                f"instance has {self._epsilon}"
            )
        return self


# ======================================================================
# RobustScaler (§9.2)
# ======================================================================


class RobustScaler:
    """Per-feature robust scaler for 3D tensors (N, L, F).

    Centres by median and scales by IQR (quantile_high − quantile_low).
    After centering/scaling, values are clipped to the quantile bounds
    estimated on train.  If IQR < ``CONSTANT_FEATURE_SIGMA_THRESHOLD``
    for a feature, the feature is set to 0.0 (same guard as StandardScaler).

    Parameters
    ----------
    epsilon : float
        Small value added to IQR in the denominator.
    quantile_low : float
        Lower quantile (e.g. 0.005).
    quantile_high : float
        Upper quantile (e.g. 0.995).
    """

    def __init__(
        self,
        epsilon: float,
        quantile_low: float,
        quantile_high: float,
    ) -> None:
        _validate_epsilon(epsilon)
        if quantile_low >= quantile_high:
            raise ValueError(
                f"quantile_low ({quantile_low}) must be < "
                f"quantile_high ({quantile_high})"
            )
        self._epsilon = epsilon
        self._quantile_low = quantile_low
        self._quantile_high = quantile_high

        self.median_: np.ndarray | None = None
        self.iqr_: np.ndarray | None = None
        self.clip_low_: np.ndarray | None = None
        self.clip_high_: np.ndarray | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, x_train: np.ndarray) -> RobustScaler:
        """Estimate median, IQR and clipping bounds per feature.

        Parameters
        ----------
        x_train : np.ndarray
            Training tensor of shape ``(N, L, F)``, dtype float32.

        Returns
        -------
        self
        """
        _validate_3d(x_train, "x_train")

        if np.isnan(x_train).any():
            raise ValueError("NaN in X_train before scaling")

        n, seq_len, f = x_train.shape
        flat = x_train.reshape(n * seq_len, f)

        median = np.median(flat, axis=0).astype(np.float64)
        q_low = np.quantile(flat, self._quantile_low, axis=0).astype(np.float64)
        q_high = np.quantile(flat, self._quantile_high, axis=0).astype(np.float64)
        iqr = (q_high - q_low).astype(np.float64)

        self.median_ = median
        self.iqr_ = iqr

        # Compute clip bounds in *scaled* space: (q - median) / (iqr + eps)
        denom = iqr + self._epsilon
        self.clip_low_ = ((q_low - median) / denom).astype(np.float64)
        self.clip_high_ = ((q_high - median) / denom).astype(np.float64)

        # Guard: warn about constant features
        constant_mask = iqr < CONSTANT_FEATURE_SIGMA_THRESHOLD
        if constant_mask.any():
            indices = np.where(constant_mask)[0].tolist()
            logger.warning(
                "Constant feature(s) detected (IQR < %s) at indices %s. "
                "These will be set to 0.0 after scaling.",
                CONSTANT_FEATURE_SIGMA_THRESHOLD,
                indices,
            )

        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        """Apply robust scaling: centre, scale by IQR, then clip.

        Parameters
        ----------
        x : np.ndarray
            Tensor of shape ``(N, L, F)``.

        Returns
        -------
        np.ndarray
            Scaled and clipped tensor, same shape, dtype float32.
        """
        if self.median_ is None or self.iqr_ is None:
            raise RuntimeError("Scaler has not been fit yet. Call fit() first.")

        _validate_3d(x, "x")

        median = self.median_
        iqr = self.iqr_
        clip_low = self.clip_low_
        clip_high = self.clip_high_

        x_scaled = (x - median) / (iqr + self._epsilon)

        # Guard: constant features → 0.0
        constant_mask = iqr < CONSTANT_FEATURE_SIGMA_THRESHOLD
        if constant_mask.any():
            x_scaled[:, :, constant_mask] = 0.0

        # Clip non-constant features to quantile bounds
        non_constant = ~constant_mask
        if non_constant.any():
            x_scaled[:, :, non_constant] = np.clip(
                x_scaled[:, :, non_constant],
                clip_low[non_constant],
                clip_high[non_constant],
            )

        return x_scaled.astype(np.float32)

    def fit_transform(self, x_train: np.ndarray) -> np.ndarray:
        """Fit on x_train and transform it in one call."""
        return self.fit(x_train).transform(x_train)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def save(self, path: str | Path) -> None:
        """Save scaler parameters to an .npz file."""
        if self.median_ is None or self.iqr_ is None:
            raise RuntimeError("Scaler has not been fit yet. Call fit() first.")

        np.savez(
            path,
            median=self.median_,
            iqr=self.iqr_,
            clip_low=self.clip_low_,
            clip_high=self.clip_high_,
            epsilon=np.array(self._epsilon),
            quantile_low=np.array(self._quantile_low),
            quantile_high=np.array(self._quantile_high),
        )

    def load(self, path: str | Path) -> RobustScaler:
        """Load scaler parameters from an .npz file.

        Parameters
        ----------
        path : str or Path
            Path to the .npz file saved by :meth:`save`.

        Returns
        -------
        self
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Scaler parameter file not found: {path}")

        with np.load(path) as data:
            self.median_ = data["median"]
            self.iqr_ = data["iqr"]
            self.clip_low_ = data["clip_low"]
            self.clip_high_ = data["clip_high"]
            loaded_epsilon = float(data["epsilon"])
            loaded_quantile_low = float(data["quantile_low"])
            loaded_quantile_high = float(data["quantile_high"])

        if loaded_epsilon != self._epsilon:
            raise ValueError(
                f"Epsilon mismatch: file has {loaded_epsilon}, "
                f"instance has {self._epsilon}"
            )
        if loaded_quantile_low != self._quantile_low:
            raise ValueError(
                f"quantile_low mismatch: file has {loaded_quantile_low}, "
                f"instance has {self._quantile_low}"
            )
        if loaded_quantile_high != self._quantile_high:
            raise ValueError(
                f"quantile_high mismatch: file has {loaded_quantile_high}, "
                f"instance has {self._quantile_high}"
            )
        return self


# ======================================================================
# Factory
# ======================================================================


def create_scaler(scaling_config: ScalingConfig) -> StandardScaler | RobustScaler:
    """Create a scaler instance from the scaling configuration.

    Parameters
    ----------
    scaling_config : ScalingConfig
        The ``scaling`` section from :class:`PipelineConfig`.

    Returns
    -------
    StandardScaler or RobustScaler

    Raises
    ------
    ValueError
        If ``scaling_config.method`` is not ``"standard"`` or ``"robust"``.
    """
    method = scaling_config.method
    if method == "standard":
        return StandardScaler(epsilon=scaling_config.epsilon)
    if method == "robust":
        return RobustScaler(
            epsilon=scaling_config.epsilon,
            quantile_low=scaling_config.robust_quantile_low,
            quantile_high=scaling_config.robust_quantile_high,
        )
    raise ValueError(
        f"Unknown scaling method '{method}'. Expected 'standard' or 'robust'."
    )
