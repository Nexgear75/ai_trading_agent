import torch
import torch.nn as nn
from torch.distributions import Categorical

from data.features.pipeline import FEATURE_COLUMNS
from models.rl.risk_manager import N_ACTIONS

PORTFOLIO_STATE_DIM = 7

POOL_SIZE = 5  # Must divide WINDOW_SIZE (30)


class FeatureExtractor(nn.Module):
    """Shared CNN backbone for processing market observation windows.

    Architecture mirrors models/cnn/CNN.py conv_blocks + pool, with
    lower dropout (0.1) for RL stability.
    """

    def __init__(self, window_size: int = 30, n_features: int = len(FEATURE_COLUMNS)):
        super().__init__()

        self.conv_blocks = nn.Sequential(
            # Block 1
            nn.Conv1d(n_features, 32, kernel_size=3, padding="same"),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout1d(0.1),
            # Block 2
            nn.Conv1d(32, 64, kernel_size=3, padding="same"),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout1d(0.1),
            # Block 3
            nn.Conv1d(64, 128, kernel_size=3, padding="same"),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout1d(0.1),
        )

        self.pool = nn.AdaptiveAvgPool1d(POOL_SIZE)
        self.output_dim = 128 * POOL_SIZE  # 640

    def forward(self, market_obs: torch.Tensor) -> torch.Tensor:
        """
        Args:
            market_obs: (batch, window_size, n_features)
        Returns:
            (batch, 640)
        """
        x = market_obs.transpose(1, 2)   # (batch, n_features, window_size)
        x = self.conv_blocks(x)
        x = self.pool(x)                 # (batch, 128, POOL_SIZE)
        return x.flatten(1)              # (batch, 640)

    @classmethod
    def from_pretrained_cnn(cls, checkpoint_path: str, **kwargs):
        """Initialize from a pretrained CNN1D checkpoint.

        Loads conv_blocks and pool weights from the supervised model.
        """
        extractor = cls(**kwargs)
        state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=True)

        # Filter to only conv_blocks and pool keys
        filtered = {}
        for key, value in state_dict.items():
            if key.startswith("conv_blocks.") or key.startswith("pool."):
                filtered[key] = value

        if filtered:
            extractor.load_state_dict(filtered, strict=False)
            print(f"Loaded {len(filtered)} pretrained weights from {checkpoint_path}")

        return extractor


class PolicyNetwork(nn.Module):
    """Actor network: outputs action distribution given market + portfolio state."""

    def __init__(
        self,
        feature_extractor: FeatureExtractor,
        portfolio_dim: int = PORTFOLIO_STATE_DIM,
        n_actions: int = N_ACTIONS,
    ):
        super().__init__()
        self.feature_extractor = feature_extractor
        combined_dim = feature_extractor.output_dim + portfolio_dim  # 647

        self.policy_head = nn.Sequential(
            nn.Linear(combined_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, n_actions),
        )

    def forward(self, market_obs: torch.Tensor, portfolio_obs: torch.Tensor) -> Categorical:
        """
        Args:
            market_obs: (batch, window_size, n_features)
            portfolio_obs: (batch, portfolio_dim)
        Returns:
            Categorical distribution over actions.
        """
        features = self.feature_extractor(market_obs)
        combined = torch.cat([features, portfolio_obs], dim=-1)
        logits = self.policy_head(combined)
        return Categorical(logits=logits)

    def get_action(self, market_obs: torch.Tensor, portfolio_obs: torch.Tensor, deterministic: bool = False):
        """Sample an action and return (action, log_prob).

        Args:
            deterministic: If True, return argmax instead of sampling.
        """
        dist = self.forward(market_obs, portfolio_obs)
        if deterministic:
            action = dist.probs.argmax(dim=-1)
        else:
            action = dist.sample()
        return action, dist.log_prob(action)


class ValueNetwork(nn.Module):
    """Critic network: estimates state value given market + portfolio state."""

    def __init__(
        self,
        feature_extractor: FeatureExtractor,
        portfolio_dim: int = PORTFOLIO_STATE_DIM,
    ):
        super().__init__()
        self.feature_extractor = feature_extractor  # Shared with PolicyNetwork
        combined_dim = feature_extractor.output_dim + portfolio_dim

        self.value_head = nn.Sequential(
            nn.Linear(combined_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
        )

    def forward(self, market_obs: torch.Tensor, portfolio_obs: torch.Tensor) -> torch.Tensor:
        """
        Args:
            market_obs: (batch, window_size, n_features)
            portfolio_obs: (batch, portfolio_dim)
        Returns:
            (batch,) scalar state values.
        """
        features = self.feature_extractor(market_obs)
        combined = torch.cat([features, portfolio_obs], dim=-1)
        return self.value_head(combined).squeeze(-1)
