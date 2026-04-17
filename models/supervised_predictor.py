"""Abstract base for supervised regression predictors.

All models that predict a continuous forward return (CNN, BiLSTM, XGBoost, etc.)
extend this class. Each predictor owns its scalers and handles clipping/scaling
internally so the ensemble can pass the same raw feature window to every model.
"""

from __future__ import annotations

import os
from abc import abstractmethod
from typing import Optional

import joblib
import numpy as np

from config import DEFAULT_TIMEFRAME, SIGNAL_THRESHOLDS
from models.base_predictor import BasePredictor, Prediction


class SupervisedPredictor(BasePredictor):
    """Regression-based predictor that converts predicted return % → signal.

    Subclasses implement ``_load_model`` and ``_forward``.
    ``predict()`` handles clip → scale → forward → inverse-transform → threshold.
    """

    def __init__(self, timeframe: str = DEFAULT_TIMEFRAME) -> None:
        self._timeframe = timeframe
        self._feature_scaler = None
        self._target_scaler = None
        self._clip_bounds: np.ndarray | None = None

    # ----- BasePredictor properties -----

    @property
    def timeframe(self) -> str:
        return self._timeframe

    @property
    def requires_portfolio_state(self) -> bool:
        return False

    # ----- Abstract interface for subclasses -----

    @abstractmethod
    def _load_model(self, checkpoint_path: str) -> None:
        """Load model weights from checkpoint_path."""
        ...

    @abstractmethod
    def _forward(self, scaled_window: np.ndarray) -> float:
        """Run inference on a scaled window; return scaled target prediction."""
        ...

    # ----- Shared loading logic -----

    def load(self, checkpoint_path: str) -> None:
        """Load model weights and scalers.

        Scalers are expected at ``scalers.joblib`` in the same directory.
        """
        self._load_model(checkpoint_path)
        scalers_path = os.path.join(os.path.dirname(checkpoint_path), "scalers.joblib")
        scalers = joblib.load(scalers_path)
        self._feature_scaler = scalers["feature_scaler"]
        self._target_scaler = scalers["target_scaler"]
        self._clip_bounds = scalers.get("clip_bounds")

    # ----- Shared scaling helpers -----

    def _n_model_features(self) -> int | None:
        """Features the model was trained on, inferred from its scaler.

        Returns None when the scaler has no metadata (use all features).
        If the raw window has more features than this (e.g. new columns were
        added to the pipeline after training), only the first N are used.
        """
        if hasattr(self._feature_scaler, "n_features_in_"):
            return int(self._feature_scaler.n_features_in_)
        if self._clip_bounds is not None:
            return self._clip_bounds.shape[0]
        return None

    def _scale_window(self, raw_window: np.ndarray) -> np.ndarray:
        """Clip outliers + apply feature scaler to a (window_size, n_features) window.

        Silently truncates to the feature count the model was trained on when
        the window contains extra columns (e.g. pipeline extended after training).
        """
        X = raw_window.copy().astype(np.float32)
        n_model = self._n_model_features()
        if n_model is not None and X.shape[1] > n_model:
            X = X[:, :n_model]
        if self._clip_bounds is not None:
            for i in range(X.shape[1]):
                X[:, i] = np.clip(X[:, i], self._clip_bounds[i, 0], self._clip_bounds[i, 1])
        return self._feature_scaler.transform(X)

    def _inverse_target(self, pred_scaled: float) -> float:
        return float(self._target_scaler.inverse_transform([[pred_scaled]]).ravel()[0])

    # ----- Prediction -----

    def predict(
        self,
        market_data: np.ndarray,
        portfolio_state: Optional[np.ndarray] = None,
    ) -> Prediction:
        """Generate a trading signal from raw (unscaled) market data.

        Args:
            market_data: Raw feature window, shape (window_size, n_features).
                         Clipping and scaling are applied internally.
            portfolio_state: Ignored for supervised models.

        Returns:
            Prediction with signal, confidence, and raw_value (predicted return %).
        """
        if self._feature_scaler is None:
            raise RuntimeError("Call load() before predict()")

        scaled = self._scale_window(market_data)
        pred_scaled = self._forward(scaled)
        pred = self._inverse_target(pred_scaled)

        threshold = SIGNAL_THRESHOLDS.get(self._timeframe, 0.01)
        confidence = min(1.0, abs(pred) / max(threshold * 2, 1e-9))

        if pred > threshold:
            signal = "buy"
        elif pred < -threshold:
            signal = "sell"
        else:
            signal = "hold"

        return Prediction(signal=signal, confidence=confidence, raw_value=pred)

    def predict_batch(self, X_raw: np.ndarray) -> np.ndarray:
        """Vectorised prediction over N raw windows.

        Args:
            X_raw: Raw windows, shape (N, window_size, n_features).

        Returns:
            Array of predicted returns (%), shape (N,).
        """
        if self._feature_scaler is None:
            raise RuntimeError("Call load() before predict_batch()")

        n_samples, window_size, n_raw = X_raw.shape
        n_model = self._n_model_features() or n_raw

        # Truncate extra features produced by a newer pipeline
        X_flat = X_raw.reshape(-1, n_raw)[:, :n_model].astype(np.float32)

        actual_n = X_flat.shape[1]
        if self._clip_bounds is not None:
            for i in range(actual_n):
                X_flat[:, i] = np.clip(
                    X_flat[:, i], self._clip_bounds[i, 0], self._clip_bounds[i, 1]
                )

        X_scaled_flat = self._feature_scaler.transform(X_flat)
        X_scaled = X_scaled_flat.reshape(n_samples, window_size, n_model)

        preds_scaled = self._predict_batch_scaled(X_scaled)
        return self._target_scaler.inverse_transform(
            preds_scaled.reshape(-1, 1)
        ).ravel()

    def _predict_batch_scaled(self, X_scaled: np.ndarray) -> np.ndarray:
        """Run batch inference on scaled (N, window_size, n_features) array.

        Default implementation loops over windows; subclasses can override
        for vectorised/GPU inference.
        """
        return np.array([self._forward(X_scaled[i]) for i in range(len(X_scaled))])
