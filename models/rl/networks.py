import torch
import torch.nn as nn
from torch.distributions import Categorical

from data.features.pipeline import FEATURE_COLUMNS
from models.rl.risk_manager import N_ACTIONS

PORTFOLIO_STATE_DIM = 7


class ResidualConvBlock(nn.Module):
    """Conv1d block with residual connection and LayerNorm."""

    def __init__(self, in_channels, out_channels, kernel_size=3):
        super().__init__()
        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size, padding="same")
        self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size, padding="same")
        self.norm1 = nn.GroupNorm(1, out_channels)  # equivalent to LayerNorm for Conv1d
        self.norm2 = nn.GroupNorm(1, out_channels)
        self.act = nn.GELU()
        self.dropout = nn.Dropout1d(0.1)

        # Project residual if channel mismatch
        self.residual = nn.Conv1d(in_channels, out_channels, 1) if in_channels != out_channels else nn.Identity()

    def forward(self, x):
        residual = self.residual(x)
        x = self.act(self.norm1(self.conv1(x)))
        x = self.dropout(self.norm2(self.conv2(x)))
        return self.act(x + residual)


class SelfAttention(nn.Module):
    """Multi-head self-attention with residual connection."""

    def __init__(self, embed_dim, n_heads=4, dropout=0.1):
        super().__init__()
        self.attn = nn.MultiheadAttention(embed_dim, n_heads, dropout=dropout, batch_first=True)
        self.norm = nn.LayerNorm(embed_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        # x: (batch, seq_len, embed_dim)
        attn_out, _ = self.attn(x, x, x)
        return self.norm(x + self.dropout(attn_out))


class FeatureExtractor(nn.Module):
    """CNN-LSTM-Attention backbone for processing market observation windows.

    Architecture:
        1. Residual CNN blocks (local pattern extraction): 64→128→256
        2. Temporal pooling: 120 → 30 timesteps (4x reduction)
        3. Bidirectional LSTM (sequential dependencies)
        4. Multi-head self-attention (selective focus on key moments)
        5. Global average pooling → feature vector
    """

    def __init__(self, window_size: int = 120, n_features: int = len(FEATURE_COLUMNS)):
        super().__init__()
        self._window_size = window_size

        # CNN blocks with increasing channels
        self.conv_blocks = nn.Sequential(
            ResidualConvBlock(n_features, 64, kernel_size=3),
            ResidualConvBlock(64, 128, kernel_size=3),
            ResidualConvBlock(128, 256, kernel_size=5),
        )

        # Temporal pooling: reduce sequence length (120 → 30)
        self.temporal_pool = nn.AvgPool1d(kernel_size=4, stride=4)

        # Bidirectional LSTM
        lstm_input_dim = 256
        self.lstm_hidden = 128
        self.lstm = nn.LSTM(
            input_size=lstm_input_dim,
            hidden_size=self.lstm_hidden,
            num_layers=2,
            batch_first=True,
            bidirectional=True,
            dropout=0.1,
        )

        # Self-attention on LSTM output
        lstm_out_dim = self.lstm_hidden * 2  # bidirectional
        self.attention = SelfAttention(lstm_out_dim, n_heads=4, dropout=0.1)

        self.output_dim = lstm_out_dim  # 256

    def forward(self, market_obs: torch.Tensor) -> torch.Tensor:
        """
        Args:
            market_obs: (batch, window_size, n_features)
        Returns:
            (batch, 256) feature vector
        """
        x = market_obs.transpose(1, 2)   # (batch, n_features, window_size)
        x = self.conv_blocks(x)          # (batch, 256, window_size)
        x = self.temporal_pool(x)        # (batch, 256, window_size//4)
        x = x.transpose(1, 2)           # (batch, seq_len, 256)

        # LSTM
        x, _ = self.lstm(x)             # (batch, seq_len, 256)

        # Self-attention
        x = self.attention(x)           # (batch, seq_len, 256)

        # Global average pooling over time
        x = x.mean(dim=1)              # (batch, 256)

        return x

    @classmethod
    def from_pretrained_cnn(cls, checkpoint_path: str, **kwargs):
        """Initialize from a pretrained CNN1D checkpoint.

        Loads compatible conv weights from the supervised model where possible.
        """
        extractor = cls(**kwargs)
        state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=True)

        # Try to load matching keys
        filtered = {}
        own_state = extractor.state_dict()
        for key, value in state_dict.items():
            if key in own_state and own_state[key].shape == value.shape:
                filtered[key] = value

        if filtered:
            extractor.load_state_dict(filtered, strict=False)
            print(f"Loaded {len(filtered)} pretrained weights from {checkpoint_path}")

        return extractor


PORTFOLIO_ENCODED_DIM = 64  # portfolio state projected to this before fusion


def _make_portfolio_encoder(portfolio_dim: int) -> nn.Sequential:
    """MLP that expands the raw portfolio state to a richer representation.

    Without this encoder, the 7-dim portfolio vector is drowned out by the
    256-dim market feature vector (~2.7% of the fused input), and the policy
    head learns to ignore it. Expanding to 64 dims raises its weight to ~20%.

    Input LayerNorm standardizes the raw portfolio features (position_frac,
    drawdown, volatility, …) so wildly different natural scales all enter
    the MLP on equal footing. Output LayerNorm ensures the encoder output
    sits at the same scale (~std 1) as the market features after the CNN-LSTM
    pipeline; otherwise the portfolio branch gets swamped at the concat step.
    """
    return nn.Sequential(
        nn.LayerNorm(portfolio_dim),
        nn.Linear(portfolio_dim, 32),
        nn.GELU(),
        nn.Linear(32, PORTFOLIO_ENCODED_DIM),
        nn.LayerNorm(PORTFOLIO_ENCODED_DIM),
    )


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
        self.portfolio_encoder = _make_portfolio_encoder(portfolio_dim)
        combined_dim = feature_extractor.output_dim + PORTFOLIO_ENCODED_DIM

        self.policy_head = nn.Sequential(
            nn.Linear(combined_dim, 256),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(256, 128),
            nn.GELU(),
            nn.Linear(128, n_actions),
        )

    def forward(self, market_obs: torch.Tensor, portfolio_obs: torch.Tensor) -> Categorical:
        features = self.feature_extractor(market_obs)
        portfolio_encoded = self.portfolio_encoder(portfolio_obs)
        combined = torch.cat([features, portfolio_encoded], dim=-1)
        logits = self.policy_head(combined)
        return Categorical(logits=logits)

    def get_action(self, market_obs: torch.Tensor, portfolio_obs: torch.Tensor, deterministic: bool = False):
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
        self.feature_extractor = feature_extractor
        self.portfolio_encoder = _make_portfolio_encoder(portfolio_dim)
        combined_dim = feature_extractor.output_dim + PORTFOLIO_ENCODED_DIM

        self.value_head = nn.Sequential(
            nn.Linear(combined_dim, 256),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(256, 128),
            nn.GELU(),
            nn.Linear(128, 1),
        )

    def forward(self, market_obs: torch.Tensor, portfolio_obs: torch.Tensor) -> torch.Tensor:
        features = self.feature_extractor(market_obs)
        portfolio_encoded = self.portfolio_encoder(portfolio_obs)
        combined = torch.cat([features, portfolio_encoded], dim=-1)
        return self.value_head(combined).squeeze(-1)
