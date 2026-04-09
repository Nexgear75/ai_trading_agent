import numpy as np


class RewardCalculator:
    """Computes step-wise rewards for the RL trading agent.

    Supports multiple reward modes:
        - "dsr"        : Differential Sharpe Ratio (default)
        - "log_return" : Simple log-return of portfolio
        - "sortino"    : Differential Sortino Ratio
    """

    def __init__(
        self,
        mode: str = "dsr",
        eta: float = 0.01,
        drawdown_threshold: float = 0.10,
        drawdown_penalty_coeff: float = 2.0,
        churn_penalty_coeff: float = 0.1,
        inactivity_penalty: float = 0.0005,
        reward_scale: float = 1.0,
    ):
        self.mode = mode
        self.eta = eta
        self.drawdown_threshold = drawdown_threshold
        self.drawdown_penalty_coeff = drawdown_penalty_coeff
        self.churn_penalty_coeff = churn_penalty_coeff
        self.inactivity_penalty = inactivity_penalty
        self.reward_scale = reward_scale

        # Running statistics for differential Sharpe / Sortino
        self._running_mean = 0.0
        self._running_var = 0.0
        self._running_downside_var = 0.0
        self._steps_without_position = 0

    def reset(self):
        """Reset running statistics at the start of a new episode."""
        self._running_mean = 0.0
        self._running_var = 0.0
        self._running_downside_var = 0.0
        self._steps_without_position = 0

    def compute(
        self,
        portfolio_return: float,
        prev_portfolio_return: float,
        drawdown: float,
        transaction_cost: float,
        has_position: bool = False,
    ) -> float:
        """Compute the reward for the current step.

        Args:
            portfolio_return: Cumulative portfolio return at time t.
            prev_portfolio_return: Cumulative portfolio return at time t-1.
            drawdown: Current drawdown from peak (negative value, e.g. -0.15).
            transaction_cost: Transaction cost incurred this step (positive).
            has_position: Whether the agent currently holds a position.

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

        # Churn penalty to discourage excessive trading
        churn_penalty = transaction_cost * self.churn_penalty_coeff

        # Inactivity penalty: penalize sitting in cash while the market moves
        if not has_position:
            self._steps_without_position += 1
            # Ramp up: gets worse the longer you sit idle
            inactivity = self.inactivity_penalty * min(self._steps_without_position / 10.0, 1.0)
        else:
            self._steps_without_position = 0
            inactivity = 0.0

        return (base_reward - dd_penalty - churn_penalty - inactivity) * self.reward_scale

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
