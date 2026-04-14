from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class Prediction:
    """Unified prediction output for all trading models.

    Attributes:
        signal: Trading signal — "buy", "sell", or "hold".
        confidence: Model confidence in the signal, 0.0 to 1.0.
        raw_value: Model's raw output (e.g. predicted return for supervised,
                   action id for RL).
    """
    signal: str
    confidence: float
    raw_value: float


class BasePredictor(ABC):
    """Unified prediction interface for all trading models.

    Every model (CNN, XGBoost, RL, etc.) implements this interface so that
    a single backtester can test any model with the same code path:

        model = get_predictor("rl")
        model.load("checkpoints/best_agent.pth")
        pred = model.predict(market_window, portfolio_state)
        # pred.signal == "buy" | "sell" | "hold"
    """

    @abstractmethod
    def load(self, checkpoint_path: str) -> None:
        """Load model weights and preprocessing artifacts from checkpoint."""
        ...

    @abstractmethod
    def predict(
        self,
        market_data: np.ndarray,
        portfolio_state: Optional[np.ndarray] = None,
    ) -> Prediction:
        """Generate a trading signal from current market state.

        Args:
            market_data: Scaled feature window, shape (window_size, n_features).
            portfolio_state: Portfolio state vector for RL models (7,).
                Supervised models ignore this. If None and the model requires it,
                a neutral default (no position, 100% cash) is used.

        Returns:
            Prediction with signal, confidence, and raw_value.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable model name."""
        ...

    @property
    @abstractmethod
    def timeframe(self) -> str:
        """Native timeframe this model operates on (e.g. '1d', '6h')."""
        ...

    @property
    @abstractmethod
    def requires_portfolio_state(self) -> bool:
        """Whether this model needs portfolio_state in predict()."""
        ...
