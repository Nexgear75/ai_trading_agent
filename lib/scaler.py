"""Standard and robust scalers for feature normalization."""

from __future__ import annotations

import logging

import numpy as np

from lib.config import ScalingConfig

logger = logging.getLogger(__name__)

CONSTANT_FEATURE_SIGMA_THRESHOLD: float = 1e-8


def _validate_3d(x: np.ndarray, name: str) -> None:
    if x.ndim != 3:
        raise ValueError(
            f"{name} must be 3D (N, L, F), got {x.ndim}D with shape {x.shape}"
        )


def _validate_epsilon(epsilon: float) -> None:
    if not np.isfinite(epsilon) or epsilon < 0:
        raise ValueError(f"epsilon must be finite and >= 0, got {epsilon}")


class StandardScaler:
    def __init__(self, epsilon: float) -> None:
        _validate_epsilon(epsilon)
        self._epsilon = epsilon
        self.mean_: np.ndarray | None = None
        self.std_: np.ndarray | None = None

    def fit(self, x_train: np.ndarray) -> StandardScaler:
        _validate_3d(x_train, "x_train")
        if np.isnan(x_train).any():
            raise ValueError("NaN in X_train before scaling")
        n, seq_len, f = x_train.shape
        flat = x_train.reshape(n * seq_len, f)
        mean = flat.mean(axis=0).astype(np.float64)
        std = flat.std(axis=0, ddof=0).astype(np.float64)
        self.mean_ = mean
        self.std_ = std
        constant_mask = std < CONSTANT_FEATURE_SIGMA_THRESHOLD
        if constant_mask.any():
            indices = np.where(constant_mask)[0].tolist()
            logger.warning(
                "Constant feature(s) detected (σ < %s) at indices %s.",
                CONSTANT_FEATURE_SIGMA_THRESHOLD, indices,
            )
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.std_ is None:
            raise RuntimeError("Scaler has not been fit yet. Call fit() first.")
        _validate_3d(x, "x")
        x_scaled = (x - self.mean_) / (self.std_ + self._epsilon)
        constant_mask = self.std_ < CONSTANT_FEATURE_SIGMA_THRESHOLD
        if constant_mask.any():
            x_scaled[:, :, constant_mask] = 0.0
        return x_scaled.astype(np.float32)

    def fit_transform(self, x_train: np.ndarray) -> np.ndarray:
        return self.fit(x_train).transform(x_train)


class RobustScaler:
    def __init__(
        self,
        epsilon: float,
        quantile_low: float,
        quantile_high: float,
    ) -> None:
        _validate_epsilon(epsilon)
        if quantile_low >= quantile_high:
            raise ValueError(
                f"quantile_low ({quantile_low}) must be < quantile_high ({quantile_high})"
            )
        self._epsilon = epsilon
        self._quantile_low = quantile_low
        self._quantile_high = quantile_high
        self.median_: np.ndarray | None = None
        self.iqr_: np.ndarray | None = None
        self.clip_low_: np.ndarray | None = None
        self.clip_high_: np.ndarray | None = None

    def fit(self, x_train: np.ndarray) -> RobustScaler:
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
        denom = iqr + self._epsilon
        self.clip_low_ = ((q_low - median) / denom).astype(np.float64)
        self.clip_high_ = ((q_high - median) / denom).astype(np.float64)
        constant_mask = iqr < CONSTANT_FEATURE_SIGMA_THRESHOLD
        if constant_mask.any():
            indices = np.where(constant_mask)[0].tolist()
            logger.warning(
                "Constant feature(s) detected (IQR < %s) at indices %s.",
                CONSTANT_FEATURE_SIGMA_THRESHOLD, indices,
            )
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        if self.median_ is None or self.iqr_ is None:
            raise RuntimeError("Scaler has not been fit yet. Call fit() first.")
        _validate_3d(x, "x")
        median = self.median_
        iqr = self.iqr_
        clip_low = self.clip_low_
        clip_high = self.clip_high_
        x_scaled = (x - median) / (iqr + self._epsilon)
        constant_mask = iqr < CONSTANT_FEATURE_SIGMA_THRESHOLD
        if constant_mask.any():
            x_scaled[:, :, constant_mask] = 0.0
        non_constant = ~constant_mask
        if non_constant.any():
            x_scaled[:, :, non_constant] = np.clip(
                x_scaled[:, :, non_constant],
                clip_low[non_constant],
                clip_high[non_constant],
            )
        return x_scaled.astype(np.float32)

    def fit_transform(self, x_train: np.ndarray) -> np.ndarray:
        return self.fit(x_train).transform(x_train)


def create_scaler(scaling_config: ScalingConfig) -> StandardScaler | RobustScaler:
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
