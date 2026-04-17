"""XGBoost predictor.

XGBoost was trained on flat (window_size * n_features) inputs, so clip_bounds
has shape (window_size * n_features, 2) — different from the PyTorch models
where clip_bounds has shape (n_features, 2). _scale_window is overridden
to handle this flat layout.
"""

from __future__ import annotations

import os

# Must be set before xgboost is imported to avoid OpenMP conflict with PyTorch on Apple Silicon
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import xgboost as xgb

from config import DEFAULT_TIMEFRAME
from models.supervised_predictor import SupervisedPredictor


class XGBoostPredictor(SupervisedPredictor):
    def __init__(self, timeframe: str = DEFAULT_TIMEFRAME) -> None:
        super().__init__(timeframe)
        self._model: xgb.Booster | None = None

    @property
    def name(self) -> str:
        return f"XGBoost-{self._timeframe}"

    def _load_model(self, checkpoint_path: str) -> None:
        self._model = xgb.Booster(params={"nthread": 1})
        self._model.load_model(checkpoint_path)

    def _scale_window(self, raw_window: np.ndarray) -> np.ndarray:
        """Flatten to 1D then clip+scale (XGBoost flat feature layout)."""
        X_flat = raw_window.flatten().astype(np.float32).reshape(1, -1)
        if self._clip_bounds is not None:
            X_flat = np.clip(X_flat, self._clip_bounds[:, 0], self._clip_bounds[:, 1])
        return self._feature_scaler.transform(X_flat)

    def _forward(self, scaled_window: np.ndarray) -> float:
        dmat = xgb.DMatrix(scaled_window)
        return float(self._model.predict(dmat)[0])

    def _predict_batch_scaled(self, X_scaled: np.ndarray) -> np.ndarray:
        n = X_scaled.shape[0]
        dmat = xgb.DMatrix(X_scaled.reshape(n, -1))
        return self._model.predict(dmat)

    def predict_batch(self, X_raw: np.ndarray) -> np.ndarray:
        """Vectorised batch prediction for XGBoost flat layout."""
        if self._feature_scaler is None:
            raise RuntimeError("Call load() before predict_batch()")

        n_samples = X_raw.shape[0]
        X_flat = X_raw.reshape(n_samples, -1).astype(np.float32)

        if self._clip_bounds is not None:
            X_flat = np.clip(X_flat, self._clip_bounds[:, 0], self._clip_bounds[:, 1])

        X_scaled = self._feature_scaler.transform(X_flat)
        dmat = xgb.DMatrix(X_scaled)
        preds_scaled = self._model.predict(dmat)
        return self._target_scaler.inverse_transform(
            preds_scaled.reshape(-1, 1)
        ).ravel()
