"""EnsemblePredictor: runs N supervised models and aggregates their signals.

Usage example:
    from models.ensemble import EnsemblePredictor
    from models.cnn.predictor import CNNPredictor
    from models.bilstm.predictor import BiLSTMPredictor

    ensemble = EnsemblePredictor(
        models=[CNNPredictor("1d"), BiLSTMPredictor("1d")],
        strategy="weighted_average",
        weights=[0.6, 0.4],
        timeframe="1d",
    )
    ensemble.load_models([
        "models/cnn/checkpoints/1d/best_model.pth",
        "models/bilstm/checkpoints/1d/best_model.pth",
    ])
    pred = ensemble.predict(raw_window)   # raw_window: (30, 16)
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from config import DEFAULT_TIMEFRAME, SIGNAL_THRESHOLDS
from models.base_predictor import BasePredictor, Prediction
from models.ensemble.strategies import (
    AVAILABLE_STRATEGIES,
    confidence_weighted,
    majority_vote,
    unanimous,
    weighted_average,
)


class EnsemblePredictor(BasePredictor):
    """Aggregate predictions from multiple supervised models via a voting strategy.

    Each constituent model must implement ``predict(raw_window)`` where
    ``raw_window`` is an unscaled (window_size, n_features) array.
    Every model handles its own clipping and scaling internally.
    """

    def __init__(
        self,
        models: list[BasePredictor],
        strategy: str = "weighted_average",
        weights: list[float] | None = None,
        timeframe: str = DEFAULT_TIMEFRAME,
    ) -> None:
        if not models:
            raise ValueError("At least one model is required")
        if strategy not in AVAILABLE_STRATEGIES:
            raise ValueError(f"Unknown strategy '{strategy}'. Choose from: {AVAILABLE_STRATEGIES}")
        if weights is not None and len(weights) != len(models):
            raise ValueError(f"weights length {len(weights)} != models length {len(models)}")

        self._models = models
        self._strategy = strategy
        self._weights = weights if weights is not None else [1.0] * len(models)
        self._timeframe = timeframe

    # ----- BasePredictor interface -----

    @property
    def name(self) -> str:
        names = "+".join(m.name for m in self._models)
        return f"Ensemble[{names}]/{self._strategy}"

    @property
    def timeframe(self) -> str:
        return self._timeframe

    @property
    def requires_portfolio_state(self) -> bool:
        return False

    def load(self, checkpoint_path: str) -> None:
        # No-op: use load_models() to load each constituent model.
        pass

    # ----- Ensemble-specific API -----

    def load_models(self, checkpoint_paths: list[str]) -> None:
        """Load each constituent model from its checkpoint path.

        Args:
            checkpoint_paths: One path per model, in the same order as ``models``.
        """
        if len(checkpoint_paths) != len(self._models):
            raise ValueError(
                f"Expected {len(self._models)} checkpoint paths, got {len(checkpoint_paths)}"
            )
        for model, path in zip(self._models, checkpoint_paths):
            print(f"  Loading {model.name} from {path}")
            model.load(path)

    @property
    def constituent_models(self) -> list[BasePredictor]:
        return list(self._models)

    @property
    def strategy(self) -> str:
        return self._strategy

    # ----- Prediction -----

    def predict(
        self,
        market_data: np.ndarray,
        portfolio_state: Optional[np.ndarray] = None,
    ) -> Prediction:
        """Aggregate N model predictions into one signal.

        Args:
            market_data: Raw (unscaled) feature window, shape (window_size, n_features).
            portfolio_state: Ignored.
        """
        predictions = [m.predict(market_data) for m in self._models]
        return self._aggregate(predictions)

    def predict_with_breakdown(self, market_data: np.ndarray) -> tuple[Prediction, list[dict]]:
        """Return ensemble decision plus each model's individual prediction.

        Useful for diagnostics and logging.

        Returns:
            (ensemble_prediction, breakdown) where breakdown is a list of dicts
            with keys: model, signal, confidence, raw_value.
        """
        predictions = [m.predict(market_data) for m in self._models]
        breakdown = [
            {
                "model": m.name,
                "signal": p.signal,
                "confidence": round(p.confidence, 4),
                "raw_value": round(p.raw_value, 6),
            }
            for m, p in zip(self._models, predictions)
        ]
        ensemble = self._aggregate(predictions)
        return ensemble, breakdown

    def predict_batch_per_model(self, X_raw: np.ndarray) -> dict[str, np.ndarray]:
        """Return per-model raw return predictions without aggregation.

        Args:
            X_raw: Raw feature windows, shape (N, window_size, n_features).

        Returns:
            Dict mapping model.name → array of predicted returns (%), shape (N,).
        """
        from models.supervised_predictor import SupervisedPredictor

        result = {}
        for model in self._models:
            if isinstance(model, SupervisedPredictor):
                preds = model.predict_batch(X_raw)
            else:
                preds = np.array([model.predict(X_raw[i]).raw_value for i in range(len(X_raw))])
            result[model.name] = preds
        return result

    def predict_batch(self, X_raw: np.ndarray) -> np.ndarray:
        """Vectorised ensemble prediction over N raw windows.

        Args:
            X_raw: Raw feature windows, shape (N, window_size, n_features).

        Returns:
            Array of predicted returns (%) after aggregation, shape (N,).
        """
        ensemble_preds, _ = self.predict_batch_full(X_raw)
        return ensemble_preds

    def predict_batch_full(
        self, X_raw: np.ndarray
    ) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        """Single-pass prediction returning ensemble array AND per-model breakdown.

        Runs each model exactly once.

        Args:
            X_raw: Raw feature windows, shape (N, window_size, n_features).

        Returns:
            (ensemble_preds, per_model_preds) where:
              - ensemble_preds: (N,) aggregated predictions
              - per_model_preds: {model_name: (N,) predictions}
        """
        threshold = SIGNAL_THRESHOLDS.get(self._timeframe, 0.01)
        per_model = self.predict_batch_per_model(X_raw)
        preds_matrix = np.array(list(per_model.values()))  # (n_models, N)

        if self._strategy == "majority_vote":
            ensemble = self._majority_vote_batch(preds_matrix, threshold)
        elif self._strategy == "unanimous":
            ensemble = self._unanimous_batch(preds_matrix, threshold)
        else:
            weights = np.array(self._weights)
            if self._strategy == "confidence_weighted":
                confidences = np.clip(
                    np.abs(preds_matrix) / max(threshold * 2, 1e-9), 0.0, 1.0
                )
                row_sums = np.where(confidences.sum(axis=0) == 0, 1.0, confidences.sum(axis=0))
                ensemble = (preds_matrix * (confidences / row_sums)).sum(axis=0)
            else:
                weights = weights / weights.sum()
                ensemble = (preds_matrix * weights[:, None]).sum(axis=0)

        return ensemble, per_model

    # ----- Private helpers -----

    def _aggregate(self, predictions: list[Prediction]) -> Prediction:
        threshold = SIGNAL_THRESHOLDS.get(self._timeframe, 0.01)
        if self._strategy == "majority_vote":
            return majority_vote(predictions)
        elif self._strategy == "weighted_average":
            return weighted_average(predictions, self._weights, threshold)
        elif self._strategy == "confidence_weighted":
            return confidence_weighted(predictions, threshold)
        elif self._strategy == "unanimous":
            return unanimous(predictions)
        raise ValueError(f"Unknown strategy: {self._strategy}")

    @staticmethod
    def _majority_vote_batch(preds_matrix: np.ndarray, threshold: float) -> np.ndarray:
        """Return raw mean of agreeing models, or 0 on tie."""
        n_models, n = preds_matrix.shape
        signals = np.sign(np.where(np.abs(preds_matrix) > threshold, preds_matrix, 0.0))
        # signals: -1=sell, 0=hold, +1=buy per model per timestep
        vote_sum = signals.sum(axis=0)
        # Majority requires strictly more than half
        majority = np.ceil(n_models / 2)
        result = np.where(
            vote_sum >= majority, preds_matrix.mean(axis=0),
            np.where(vote_sum <= -majority, preds_matrix.mean(axis=0), 0.0)
        )
        return result

    @staticmethod
    def _unanimous_batch(preds_matrix: np.ndarray, threshold: float) -> np.ndarray:
        """Return mean only when all models agree; else 0."""
        signals = np.sign(np.where(np.abs(preds_matrix) > threshold, preds_matrix, 0.0))
        all_buy = (signals == 1).all(axis=0)
        all_sell = (signals == -1).all(axis=0)
        mean_preds = preds_matrix.mean(axis=0)
        return np.where(all_buy | all_sell, mean_preds, 0.0)
