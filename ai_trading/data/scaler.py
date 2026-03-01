"""Standard scaler for 3D feature tensors (WS-5.1).

Normalises features by removing the mean and scaling to unit variance.
Statistics (μ, σ) are estimated on train data only (anti-leak).

References:
    - Spec §9.1: standardisation par feature
    - Plan WS-5.1: standard scaler (fit-on-train)
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

CONSTANT_FEATURE_SIGMA_THRESHOLD: float = 1e-8


class StandardScaler:
    """Per-feature standard scaler for 3D tensors (N, L, F).

    Parameters
    ----------
    epsilon : float
        Small value added to σ in the denominator to avoid division by zero.
        Must be read from ``config.scaling.epsilon``.
    """

    def __init__(self, epsilon: float) -> None:
        if not np.isfinite(epsilon) or epsilon < 0:
            raise ValueError(
                f"epsilon must be finite and >= 0, got {epsilon}"
            )
        self._epsilon = epsilon
        self.mean_: np.ndarray | None = None
        self.std_: np.ndarray | None = None

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_3d(x: np.ndarray, name: str) -> None:
        if x.ndim != 3:
            raise ValueError(
                f"{name} must be 3D (N, L, F), got {x.ndim}D with shape {x.shape}"
            )

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
        self._validate_3d(x_train, "x_train")

        if np.isnan(x_train).any():
            raise ValueError("NaN in X_train before scaling")

        n, seq_len, f = x_train.shape
        flat = x_train.reshape(n * seq_len, f)

        mean = flat.mean(axis=0).astype(np.float32)
        std = flat.std(axis=0).astype(np.float32)
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

        self._validate_3d(x, "x")

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
