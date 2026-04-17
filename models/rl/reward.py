import numpy as np


class RewardCalculator:
    """Computes step-wise rewards for the RL trading agent.

    Supports three reward modes:
        - "log_return" : log(1 + delta_return)  (default, cleanest signal)
        - "dsr"        : Differential Sharpe Ratio (Moody & Saffell 2001)
        - "sortino"    : Differential Sortino Ratio

    Transaction costs and drawdowns are already reflected in portfolio_return
    (the environment subtracts them from cash on each trade), so there is no
    additional reward shaping. The agent sees the same thing a real P&L curve
    would show — and PPO's job is to maximize expected log-growth.
    """

    def __init__(
        self,
        mode: str = "log_return",
        eta: float = 0.01,
        reward_scale: float = 1.0,
        directional_coeff: float = 1.0,
    ):
        self.mode = mode
        self.eta = eta
        self.reward_scale = reward_scale
        self.directional_coeff = directional_coeff

        # Running statistics for DSR / Sortino
        self._running_mean = 0.0
        self._running_var = 0.0
        self._running_downside_var = 0.0

    def reset(self):
        """Reset running statistics at the start of a new episode."""
        self._running_mean = 0.0
        self._running_var = 0.0
        self._running_downside_var = 0.0

    def compute(
        self,
        portfolio_return: float,
        prev_portfolio_return: float,
        asset_return: float = 0.0,
        has_position: bool = False,
    ) -> float:
        """Compute the reward for the current step.

        Args:
            portfolio_return: Cumulative portfolio return at time t.
            prev_portfolio_return: Cumulative portfolio return at time t-1.
            asset_return: Single-step return of the underlying asset.
            has_position: Whether the agent currently holds a long position.

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

        # Directional signal: the only shaping term.
        # Without it, HOLD = 0 reward is the only risk-free attractor and the
        # policy collapses to do-nothing. With it, the agent has a gradient
        # aligned with market direction on each rising candle.
        if asset_return > 0:
            directional = self.directional_coeff * asset_return
            if has_position:
                base_reward += directional   # caught the upmove
            else:
                base_reward -= directional   # missed the upmove

        return base_reward * self.reward_scale

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
