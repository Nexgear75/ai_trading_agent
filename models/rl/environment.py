import gymnasium as gym
import numpy as np
from gymnasium import spaces
from sklearn.preprocessing import RobustScaler

from config import WINDOW_SIZE
from models.rl.features import FEATURE_COLUMNS
from models.rl.reward import RewardCalculator
from models.rl.risk_manager import RiskManager, RiskConfig, N_ACTIONS


N_FEATURES = len(FEATURE_COLUMNS)
PORTFOLIO_STATE_DIM = 7
MAX_EPISODE_STEPS = 112  # ~4 weeks of 6h data (4 candles/day * 7d * 4w)


class TradingEnv(gym.Env):
    """Gymnasium-compatible cryptocurrency trading environment.

    Observation:
        market  : (WINDOW_SIZE, N_FEATURES) — sliding window of scaled features
        portfolio : (7,) — position, unrealized_pnl, cash_ratio, time_in_position,
                           drawdown, portfolio_return, volatility_regime

    Actions (Discrete(7)):
        0: Hold
        1: Buy 10% of available cash
        2: Buy 25% of available cash
        3: Buy 50% of available cash
        4: Sell 25% of position
        5: Sell 50% of position
        6: Sell 100% (close position)
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        df,
        feature_scaler: RobustScaler,
        clip_bounds: dict | None = None,
        reward_mode: str = "dsr",
        risk_config: RiskConfig | None = None,
        initial_cash: float = 10_000.0,
        max_steps: int = MAX_EPISODE_STEPS,
        randomize_start: bool = True,
        noise_std: float = 0.0,
    ):
        """
        Args:
            df: DataFrame with FEATURE_COLUMNS + 'close' + 'symbol' columns.
                Must be sorted by timestamp.
            feature_scaler: Fitted RobustScaler for feature normalization.
            clip_bounds: Dict of {col: (lo, hi)} for winsorization. Optional.
            reward_mode: Reward function type ("dsr", "sortino", "log_return").
            risk_config: Risk management configuration.
            initial_cash: Starting portfolio cash.
            max_steps: Maximum steps per episode.
            randomize_start: Whether to randomize episode starting point.
            noise_std: Gaussian noise std added to features (domain randomization).
        """
        super().__init__()

        self.df = df.copy()
        self.feature_scaler = feature_scaler
        self.clip_bounds = clip_bounds or {}
        self.initial_cash = initial_cash
        self.max_steps = max_steps
        self.randomize_start = randomize_start
        self.noise_std = noise_std

        # Extract raw arrays for fast access
        self.features = self.df[FEATURE_COLUMNS].values.astype(np.float32)
        self.close_prices = self.df["close"].values.astype(np.float64)

        # Precompute scaled features
        self._precompute_scaled_features()

        # Compute rolling volatility for portfolio state
        returns = np.diff(self.close_prices) / self.close_prices[:-1]
        self.rolling_vol = np.zeros(len(self.close_prices), dtype=np.float32)
        vol_window = 28  # 7 days of 6h data (4 candles/day * 7d)
        for i in range(vol_window, len(returns)):
            self.rolling_vol[i + 1] = np.std(returns[i - vol_window : i])

        self.reward_calculator = RewardCalculator(mode=reward_mode)
        self.risk_manager = RiskManager(risk_config)

        # Spaces
        self.action_space = spaces.Discrete(N_ACTIONS)
        self.observation_space = spaces.Dict({
            "market": spaces.Box(
                low=-np.inf, high=np.inf,
                shape=(WINDOW_SIZE, N_FEATURES), dtype=np.float32,
            ),
            "portfolio": spaces.Box(
                low=-np.inf, high=np.inf,
                shape=(PORTFOLIO_STATE_DIM,), dtype=np.float32,
            ),
        })

        # State variables (set in reset)
        self._current_step = 0
        self._start_idx = 0
        self._cash = initial_cash
        self._position_units = 0.0
        self._entry_price = 0.0
        self._peak_value = initial_cash
        self._episode_step = 0
        self._time_in_position = 0
        self._prev_portfolio_return = 0.0
        self._consecutive_buys = 0

    def _precompute_scaled_features(self):
        """Apply clipping and scaling to all features upfront."""
        feats = self.features.copy()

        # Winsorize
        for i, col in enumerate(FEATURE_COLUMNS):
            if col in self.clip_bounds:
                lo, hi = self.clip_bounds[col]
                feats[:, i] = np.clip(feats[:, i], lo, hi)

        # Scale using fitted scaler
        self.scaled_features = self.feature_scaler.transform(feats).astype(np.float32)

    def _get_market_window(self) -> np.ndarray:
        """Get the (WINDOW_SIZE, N_FEATURES) observation window."""
        start = self._current_step - WINDOW_SIZE
        window = self.scaled_features[start : self._current_step].copy()

        if self.noise_std > 0:
            window += np.random.normal(0, self.noise_std, window.shape).astype(np.float32)

        return window

    def _get_portfolio_state(self) -> np.ndarray:
        """Get the 7-dim portfolio state vector."""
        price = self.close_prices[self._current_step]
        position_value = self._position_units * price
        portfolio_value = self._cash + position_value
        total = max(portfolio_value, 1e-8)

        # Unrealized P&L
        if self._position_units > 0 and self._entry_price > 0:
            unrealized_pnl = (price - self._entry_price) / self._entry_price
        else:
            unrealized_pnl = 0.0

        # Drawdown from peak
        drawdown = (portfolio_value - self._peak_value) / self._peak_value if self._peak_value > 0 else 0.0

        # Portfolio return since episode start
        portfolio_return = (portfolio_value - self.initial_cash) / self.initial_cash

        state = np.array([
            position_value / total,                                     # position fraction
            unrealized_pnl,                                             # unrealized P&L
            self._cash / total,                                         # cash ratio
            min(self._time_in_position / 120.0, 1.0),                   # normalized time in position (~30 days in 6h candles)
            drawdown,                                                   # drawdown from peak
            portfolio_return,                                           # cumulative return
            self.rolling_vol[self._current_step],                       # volatility regime
        ], dtype=np.float32)

        return state

    def _get_obs(self) -> dict:
        return {
            "market": self._get_market_window(),
            "portfolio": self._get_portfolio_state(),
        }

    @property
    def _portfolio_value(self) -> float:
        price = self.close_prices[self._current_step]
        return self._cash + self._position_units * price

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self.reward_calculator.reset()

        # Determine starting index (must leave room for window + episode)
        min_start = WINDOW_SIZE
        max_start = len(self.close_prices) - self.max_steps - 1

        if max_start <= min_start:
            max_start = len(self.close_prices) - 2
            min_start = WINDOW_SIZE

        if self.randomize_start and max_start > min_start:
            self._start_idx = self.np_random.integers(min_start, max_start)
        else:
            self._start_idx = min_start

        self._current_step = self._start_idx
        self._cash = self.initial_cash
        self._position_units = 0.0
        self._entry_price = 0.0
        self._peak_value = self.initial_cash
        self._episode_step = 0
        self._time_in_position = 0
        self._prev_portfolio_return = 0.0
        self._consecutive_buys = 0

        return self._get_obs(), {}

    def step(self, action: int):
        prev_price = self.close_prices[self._current_step]
        price = prev_price
        position_value = self._position_units * price
        portfolio_value_before = self._cash + position_value

        # Portfolio state for risk validation
        position_frac = position_value / max(portfolio_value_before, 1e-8)
        unrealized_pnl = ((price - self._entry_price) / self._entry_price) if self._position_units > 0 and self._entry_price > 0 else 0.0
        drawdown = (portfolio_value_before - self._peak_value) / self._peak_value if self._peak_value > 0 else 0.0

        # Risk manager may override the action (with adaptive stop-loss + buy cooldown)
        current_vol = self.rolling_vol[self._current_step]
        validated_action = self.risk_manager.validate_action(
            action, position_frac, unrealized_pnl, drawdown,
            volatility=current_vol,
            consecutive_buys=self._consecutive_buys,
        )

        # Execute trade
        trade_units, cost = self.risk_manager.compute_trade(
            validated_action, self._cash, position_value, price
        )

        if trade_units != 0:
            self._cash -= cost
            if trade_units > 0:
                # Buying
                spend = trade_units * price
                self._cash -= spend
                # Update entry price (weighted average)
                total_units = self._position_units + trade_units
                if total_units > 0:
                    self._entry_price = (
                        (self._position_units * self._entry_price + trade_units * price) / total_units
                    )
                self._position_units = total_units
                self._time_in_position = 0
                self._consecutive_buys += 1
            else:
                # Selling
                sell_units = min(abs(trade_units), self._position_units)
                proceeds = sell_units * price
                self._cash += proceeds
                self._position_units -= sell_units
                if self._position_units < 1e-10:
                    self._position_units = 0.0
                    self._entry_price = 0.0
                    self._time_in_position = 0
                self._consecutive_buys = 0  # selling resets buy streak
        else:
            cost = 0.0

        # Advance time
        self._current_step += 1
        self._episode_step += 1
        if self._position_units > 0:
            self._time_in_position += 1

        # Asset return for the directional signal
        new_price = self.close_prices[self._current_step]
        asset_return = (new_price - prev_price) / max(prev_price, 1e-8)

        # Update peak portfolio value
        new_portfolio_value = self._portfolio_value
        self._peak_value = max(self._peak_value, new_portfolio_value)

        # Compute reward — log-return of the portfolio plus a directional
        # signal that pulls the agent off HOLD in rising markets.
        portfolio_return = (new_portfolio_value - self.initial_cash) / self.initial_cash
        new_drawdown = (new_portfolio_value - self._peak_value) / self._peak_value if self._peak_value > 0 else 0.0

        reward = self.reward_calculator.compute(
            portfolio_return=portfolio_return,
            prev_portfolio_return=self._prev_portfolio_return,
            asset_return=asset_return,
            has_position=self._position_units > 0,
        )
        self._prev_portfolio_return = portfolio_return

        # Check termination
        terminated = False
        truncated = False

        # Hard stop on max drawdown — no extra reward penalty, the
        # accumulated log-return is already deeply negative here.
        if abs(new_drawdown) >= self.risk_manager.config.max_drawdown:
            terminated = True

        # End of data
        if self._current_step >= len(self.close_prices) - 1:
            truncated = True

        # Max episode length
        if self._episode_step >= self.max_steps:
            truncated = True

        # Can't form a valid window
        if self._current_step < WINDOW_SIZE:
            truncated = True

        obs = self._get_obs() if not (terminated or truncated) else self._get_obs()

        info = {
            "portfolio_value": new_portfolio_value,
            "portfolio_return": portfolio_return,
            "drawdown": new_drawdown,
            "position": self._position_units,
            "cash": self._cash,
            "action_taken": validated_action,
            "transaction_cost": cost,
        }

        return obs, reward, terminated, truncated, info
