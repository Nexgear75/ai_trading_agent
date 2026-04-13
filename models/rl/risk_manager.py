import numpy as np
from dataclasses import dataclass


# Transaction cost model (Binance taker + estimated slippage)
TAKER_FEE = 0.001      # 0.1%
SLIPPAGE = 0.0005      # 0.05%
TOTAL_TRADE_COST = TAKER_FEE + SLIPPAGE  # 0.15% per trade

# Action mapping for 7 discrete actions
ACTION_HOLD = 0
ACTION_BUY_10 = 1
ACTION_BUY_25 = 2
ACTION_BUY_50 = 3
ACTION_SELL_25 = 4
ACTION_SELL_50 = 5
ACTION_SELL_100 = 6

BUY_ACTIONS = {ACTION_BUY_10, ACTION_BUY_25, ACTION_BUY_50}
SELL_ACTIONS = {ACTION_SELL_25, ACTION_SELL_50, ACTION_SELL_100}

N_ACTIONS = 7

BUY_FRACTIONS = {
    ACTION_BUY_10: 0.10,
    ACTION_BUY_25: 0.25,
    ACTION_BUY_50: 0.50,
}
SELL_FRACTIONS = {
    ACTION_SELL_25: 0.25,
    ACTION_SELL_50: 0.50,
    ACTION_SELL_100: 1.00,
}


@dataclass
class RiskConfig:
    """Configuration for risk management limits."""
    max_position: float = 1.0       # Maximum position as fraction of portfolio
    max_drawdown: float = 0.25      # 25% max drawdown before forced liquidation
    take_profit: float = 0.30       # 30% unrealized gain triggers take-profit (let winners run)
    trade_cost: float = TOTAL_TRADE_COST
    # Adaptive stop-loss parameters
    stop_loss_atr_mult: float = 2.0     # Stop-loss = ATR * this multiplier
    stop_loss_min: float = 0.02         # Minimum stop-loss (2%)
    stop_loss_max: float = 0.10         # Maximum stop-loss (10%)
    # Buy cooldown: max consecutive buys without an intervening sell
    max_consecutive_buys: int = 3


class RiskManager:
    """Enforces risk limits and computes position sizes.

    Uses volatility-adaptive stop-loss based on rolling ATR instead of
    a fixed threshold. In low-vol markets the stop is tighter, in high-vol
    markets it gives more room to breathe.
    """

    def __init__(self, config: RiskConfig | None = None):
        self.config = config or RiskConfig()

    def compute_adaptive_stop_loss(self, volatility: float) -> float:
        """Compute stop-loss threshold based on current market volatility.

        Args:
            volatility: Rolling realized volatility (e.g. 14-day std of returns).

        Returns:
            Stop-loss threshold as a positive fraction (e.g. 0.04 = 4%).
        """
        # ATR-style: stop = volatility * multiplier, clamped to [min, max]
        stop = volatility * self.config.stop_loss_atr_mult
        return float(np.clip(stop, self.config.stop_loss_min, self.config.stop_loss_max))

    def validate_action(
        self,
        action: int,
        position: float,
        unrealized_pnl: float,
        drawdown: float,
        volatility: float = 0.02,
        consecutive_buys: int = 0,
    ) -> int:
        """Override agent action if risk limits are breached.

        Args:
            action: Raw action from the agent (0-6).
            position: Current position as fraction of portfolio.
            unrealized_pnl: Unrealized P&L of current position (fractional).
            drawdown: Current drawdown from peak (negative, e.g. -0.20).
            volatility: Current rolling volatility for adaptive stop-loss.
            consecutive_buys: How many buy actions executed since last sell.

        Returns:
            Validated action (may differ from input).
        """
        # Hard stop: drawdown exceeds limit → force close everything
        if abs(drawdown) >= self.config.max_drawdown and position > 0:
            return ACTION_SELL_100

        # Adaptive stop-loss
        adaptive_sl = self.compute_adaptive_stop_loss(volatility)
        if unrealized_pnl < -adaptive_sl and position > 0:
            return ACTION_SELL_100

        # Take-profit: unrealized gain exceeds limit
        if unrealized_pnl > self.config.take_profit and position > 0:
            return ACTION_SELL_100

        # Prevent buying when already at max position
        if action in BUY_ACTIONS and position >= self.config.max_position:
            return ACTION_HOLD

        # Buy cooldown: cap consecutive buys without an intervening sell
        if action in BUY_ACTIONS and consecutive_buys >= self.config.max_consecutive_buys:
            return ACTION_HOLD

        # Prevent selling when no position
        if action in SELL_ACTIONS and position <= 0:
            return ACTION_HOLD

        return action

    def compute_trade(
        self,
        action: int,
        cash: float,
        position_value: float,
        price: float,
    ) -> tuple[float, float]:
        """Convert discrete action to trade amount and compute cost.

        Args:
            action: Validated action (0-6).
            cash: Available cash in portfolio.
            position_value: Current position value.
            price: Current asset price.

        Returns:
            (trade_amount, transaction_cost) where:
                trade_amount: Positive = buy, negative = sell (in asset units).
                transaction_cost: Cost deducted from portfolio.
        """
        if action == ACTION_HOLD:
            return 0.0, 0.0

        if action in BUY_FRACTIONS:
            spend = cash * BUY_FRACTIONS[action]
        elif action in SELL_FRACTIONS:
            spend = -(position_value * SELL_FRACTIONS[action])
        else:
            return 0.0, 0.0

        notional = abs(spend)
        cost = notional * self.config.trade_cost

        if spend > 0:
            # Buying: subtract cost from amount spent
            effective_spend = spend - cost
            trade_amount = effective_spend / price if price > 0 else 0.0
        else:
            # Selling: cost is deducted from proceeds
            trade_amount = spend / price if price > 0 else 0.0

        return trade_amount, cost
