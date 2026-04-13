import numpy as np


class RewardCalculator:
    """Computes step-wise rewards for the RL trading agent.

    Supports multiple reward modes:
        - "dsr"        : Differential Sharpe Ratio (default)
        - "log_return" : Simple log-return of portfolio
        - "sortino"    : Differential Sortino Ratio

    Reward components (all subtracted from base):
        - Drawdown penalty (above threshold)
        - Churn penalty (transaction costs, heavily weighted)
        - Action-flip penalty (penalize switching action between steps)
        - Opportunity-cost penalty (penalize HOLD-cash when asset is rising)
    """

    def __init__(
        self,
        mode: str = "dsr",
        eta: float = 0.01,
        drawdown_threshold: float = 0.10,
        drawdown_penalty_coeff: float = 2.0,
        churn_penalty_coeff: float = 2.0,        # punish over-trading without killing all trades
        action_flip_penalty: float = 0.001,      # penalty for changing buy/sell stance each step
        opportunity_cost_coeff: float = 1.5,     # strongly penalize missing upside while in cash
        position_bonus_coeff: float = 0.5,       # reward holding a position while asset rises
        reward_scale: float = 1.0,
    ):
        self.mode = mode
        self.eta = eta
        self.drawdown_threshold = drawdown_threshold
        self.drawdown_penalty_coeff = drawdown_penalty_coeff
        self.churn_penalty_coeff = churn_penalty_coeff
        self.action_flip_penalty = action_flip_penalty
        self.opportunity_cost_coeff = opportunity_cost_coeff
        self.position_bonus_coeff = position_bonus_coeff
        self.reward_scale = reward_scale

        # Running statistics for differential Sharpe / Sortino
        self._running_mean = 0.0
        self._running_var = 0.0
        self._running_downside_var = 0.0
        self._prev_action_side = 0  # -1 sell, 0 hold, +1 buy

    def reset(self):
        """Reset running statistics at the start of a new episode."""
        self._running_mean = 0.0
        self._running_var = 0.0
        self._running_downside_var = 0.0
        self._prev_action_side = 0

    def compute(
        self,
        portfolio_return: float,
        prev_portfolio_return: float,
        drawdown: float,
        transaction_cost: float,
        has_position: bool = False,
        asset_return: float = 0.0,
        action: int = 0,
    ) -> float:
        """Compute the reward for the current step.

        Args:
            portfolio_return: Cumulative portfolio return at time t.
            prev_portfolio_return: Cumulative portfolio return at time t-1.
            drawdown: Current drawdown from peak (negative value, e.g. -0.15).
            transaction_cost: Transaction cost incurred this step (positive).
            has_position: Whether the agent currently holds a position.
            asset_return: Return of the underlying asset this step (for opportunity cost).
            action: Action taken this step (0=hold, 1-3=buy, 4-6=sell).

        Returns:
            Scalar reward value.
        """
        delta_return = portfolio_return - prev_portfolio_return

        if self.mode == "dsr":
            base_reward = self._differential_sharpe(delta_return)
        elif self.mode == "sortino":
            base_reward = self._differential_sortino(delta_return)
        elif self.mode == "log_return":
            base_reward = np.log1p(delta_return) if delta_return > -1.0 else -10.0
        else:
            raise ValueError(f"Unknown reward mode: {self.mode}")

        # Drawdown penalty (kicks in above threshold)
        dd_penalty = max(0.0, abs(drawdown) - self.drawdown_threshold) * self.drawdown_penalty_coeff

        # Churn penalty: heavily punishes excessive trading
        churn_penalty = transaction_cost * self.churn_penalty_coeff

        # Action-flip penalty: discourage switching buy/sell stance every step
        action_side = self._action_to_side(action)
        flip_penalty = 0.0
        if action_side != 0 and self._prev_action_side != 0 and action_side != self._prev_action_side:
            flip_penalty = self.action_flip_penalty
        if action_side != 0:
            self._prev_action_side = action_side

        # Opportunity-cost penalty: only penalize cash-holding when asset is rising
        # (no penalty if asset is flat or falling — cash is correct then)
        if not has_position and asset_return > 0:
            opp_penalty = self.opportunity_cost_coeff * asset_return
        else:
            opp_penalty = 0.0

        # Position bonus: reward holding a position while the asset is rising.
        # This is the *positive* counterpart to opportunity cost — together they
        # create a strong gradient toward "be in position when market is up".
        if has_position and asset_return > 0:
            position_bonus = self.position_bonus_coeff * asset_return
        else:
            position_bonus = 0.0

        return (
            base_reward - dd_penalty - churn_penalty - flip_penalty - opp_penalty + position_bonus
        ) * self.reward_scale

    @staticmethod
    def _action_to_side(action: int) -> int:
        """Map discrete action to side: -1 sell, 0 hold, +1 buy."""
        if action == 0:
            return 0
        if action in (1, 2, 3):
            return 1
        return -1

    def _differential_sharpe(self, delta_return: float) -> float:
        """Differential Sharpe Ratio (Moody & Saffell, 2001).

        Incrementally updates running mean/variance and returns the
        marginal contribution to the Sharpe ratio.
        """
        new_mean = self._running_mean + self.eta * (delta_return - self._running_mean)
        new_var = self._running_var + self.eta * (delta_return**2 - self._running_var)

        if new_var > 1e-12:
            numerator = new_var * (delta_return - new_mean) - 0.5 * new_mean * (delta_return**2 - new_var)
            dsr = numerator / (new_var**1.5)
        else:
            dsr = 0.0

        self._running_mean = new_mean
        self._running_var = new_var
        return dsr

    def _differential_sortino(self, delta_return: float) -> float:
        """Differential Sortino Ratio — like DSR but only penalizes downside."""
        new_mean = self._running_mean + self.eta * (delta_return - self._running_mean)

        downside_sq = min(delta_return, 0.0) ** 2
        new_downside_var = self._running_downside_var + self.eta * (downside_sq - self._running_downside_var)

        if new_downside_var > 1e-12:
            numerator = new_downside_var * (delta_return - new_mean) - 0.5 * new_mean * (downside_sq - new_downside_var)
            ds = numerator / (new_downside_var**1.5)
        else:
            ds = 0.0

        self._running_mean = new_mean
        self._running_downside_var = new_downside_var
        return ds
