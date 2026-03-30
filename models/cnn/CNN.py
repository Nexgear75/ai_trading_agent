import torch
import torch.nn as nn

from data.features.pipeline import FEATURE_COLUMNS

POOL_SIZE = 5  # doit diviser window_size (30) pour compatibilité MPS


class CNN1D(nn.Module):
    def __init__(self, window_size: int = 30, n_features: int = len(FEATURE_COLUMNS)):
        super().__init__()

        self.conv_blocks = nn.Sequential(
            # Block 1
            nn.Conv1d(
                in_channels=n_features, out_channels=32, kernel_size=3, padding="same"
            ),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout1d(0.2),
            # Block 2
            nn.Conv1d(in_channels=32, out_channels=64, kernel_size=3, padding="same"),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout1d(0.2),
            # Block 3
            nn.Conv1d(in_channels=64, out_channels=128, kernel_size=3, padding="same"),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout1d(0.2),
        )

        # Pooling partiel : conserve POOL_SIZE timesteps au lieu d'écraser tout en 1
        self.pool = nn.AdaptiveAvgPool1d(POOL_SIZE)

        self.head = nn.Sequential(
            nn.Linear(128 * POOL_SIZE, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch, window, features)
        # Conv1d attend (batch, channels, seq_len)
        x = x.transpose(1, 2)
        x = self.conv_blocks(x)
        x = self.pool(x)             # (batch, 128, POOL_SIZE)
        x = x.flatten(1)             # (batch, 128 * POOL_SIZE)
        x = self.head(x)
        return x.squeeze(-1)
