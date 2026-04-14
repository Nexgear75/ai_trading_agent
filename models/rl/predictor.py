import numpy as np
import torch
from typing import Optional

from models.base_predictor import BasePredictor, Prediction
from models.rl.agent import PPOAgent
from models.rl.risk_manager import (
    RiskManager, RiskConfig,
    BUY_ACTIONS, SELL_ACTIONS, ACTION_HOLD,
    ACTION_BUY_10, ACTION_BUY_25, ACTION_BUY_50,
    ACTION_SELL_25, ACTION_SELL_50, ACTION_SELL_100,
)

ACTION_NAMES = {
    ACTION_HOLD: "hold",
    ACTION_BUY_10: "buy_10%",
    ACTION_BUY_25: "buy_25%",
    ACTION_BUY_50: "buy_50%",
    ACTION_SELL_25: "sell_25%",
    ACTION_SELL_50: "sell_50%",
    ACTION_SELL_100: "sell_100%",
}

# Neutral portfolio state: no position, 100% cash, no drawdown
_NEUTRAL_PORTFOLIO = np.array(
    [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32
)


class RLPredictor(BasePredictor):
    """Prediction wrapper for the PPO reinforcement learning agent.

    Includes the risk manager that was active during training, so predictions
    match production behavior (e.g. no sell when position=0, buy cooldown).
    """

    def __init__(self):
        self._agent: PPOAgent | None = None
        self._risk_manager = RiskManager(RiskConfig())
        self._consecutive_buys = 0

    @property
    def name(self) -> str:
        return "PPO-RL"

    @property
    def timeframe(self) -> str:
        return "6h"

    @property
    def requires_portfolio_state(self) -> bool:
        return True

    def load(self, checkpoint_path: str) -> None:
        self._agent = PPOAgent()
        self._agent.load(checkpoint_path, verbose=False)
        self._agent.policy.eval()
        self._agent.value.eval()
        self._consecutive_buys = 0

    def predict(
        self,
        market_data: np.ndarray,
        portfolio_state: Optional[np.ndarray] = None,
    ) -> Prediction:
        """Generate a trading signal.

        Args:
            market_data: Scaled feature window, shape (window_size, n_features).
            portfolio_state: (7,) vector —
                [position_frac, unrealized_pnl, cash_ratio,
                 time_in_position_norm, drawdown, portfolio_return, volatility].
                If None, uses neutral state (no position, 100% cash).

        Returns:
            Prediction with signal, confidence, raw_value, and action_probs
            in raw_value as the validated action id.
        """
        if self._agent is None:
            raise RuntimeError("Call load() before predict()")

        if portfolio_state is None:
            portfolio_state = _NEUTRAL_PORTFOLIO.copy()

        # Get probability distribution from policy
        with torch.no_grad():
            market_t = torch.tensor(
                market_data, dtype=torch.float32, device=self._agent.device
            ).unsqueeze(0)
            portfolio_t = torch.tensor(
                portfolio_state, dtype=torch.float32, device=self._agent.device
            ).unsqueeze(0)

            dist = self._agent.policy(market_t, portfolio_t)
            probs = dist.probs.squeeze(0).cpu().numpy()

        raw_action = int(probs.argmax())

        # Apply risk manager (same guardrails as during training)
        position_frac = float(portfolio_state[0])
        unrealized_pnl = float(portfolio_state[1])
        drawdown = float(portfolio_state[4])
        volatility = float(portfolio_state[6])

        validated_action = self._risk_manager.validate_action(
            raw_action, position_frac, unrealized_pnl, drawdown,
            volatility=volatility,
            consecutive_buys=self._consecutive_buys,
        )

        # Track consecutive buys for cooldown
        if validated_action in BUY_ACTIONS:
            self._consecutive_buys += 1
            signal = "buy"
        elif validated_action in SELL_ACTIONS:
            self._consecutive_buys = 0
            signal = "sell"
        else:
            signal = "hold"

        confidence = float(probs[raw_action])

        return Prediction(
            signal=signal,
            confidence=confidence,
            raw_value=float(validated_action),
        )

    def get_action_probs(self, market_data: np.ndarray, portfolio_state: Optional[np.ndarray] = None) -> dict:
        """Return the full probability distribution over actions (for debugging)."""
        if self._agent is None:
            raise RuntimeError("Call load() before get_action_probs()")

        if portfolio_state is None:
            portfolio_state = _NEUTRAL_PORTFOLIO.copy()

        with torch.no_grad():
            market_t = torch.tensor(
                market_data, dtype=torch.float32, device=self._agent.device
            ).unsqueeze(0)
            portfolio_t = torch.tensor(
                portfolio_state, dtype=torch.float32, device=self._agent.device
            ).unsqueeze(0)

            dist = self._agent.policy(market_t, portfolio_t)
            probs = dist.probs.squeeze(0).cpu().numpy()

        return {ACTION_NAMES[i]: float(probs[i]) for i in range(len(probs))}
