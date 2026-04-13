import torch
import torch.nn as nn

from data.features.pipeline import FEATURE_COLUMNS


class CNN1D(nn.Module):
    def __init__(
        self,
        window_size: int = 30,
        n_features: int = len(FEATURE_COLUMNS),
        channels: tuple = (16, 32, 64),
        kernel_sizes: tuple = (3, 3, 3),
        dropout_conv: float = 0.2,
        dropout_fc: float = 0.3,
        pool_size: int = 5,
    ):
        """
        CNN1D pour la prédiction de retours financiers.

        L'architecture est entièrement paramétrable pour supporter des profils
        distincts par timeframe (voir CNN_CONFIGS dans config.py).

        Args:
            window_size: Longueur de la séquence d'entrée.
            n_features: Nombre de features par pas de temps.
            channels: Nombre de canaux pour chacun des 3 blocs conv.
            kernel_sizes: Taille du kernel pour chacun des 3 blocs conv.
            dropout_conv: Dropout appliqué après chaque bloc conv.
            dropout_fc: Dropout appliqué dans la tête MLP.
            pool_size: Sortie de AdaptiveAvgPool1d. Doit diviser window_size
                       (contrainte MPS : window_size % pool_size == 0).
        """
        super().__init__()

        c1, c2, c3 = channels
        k1, k2, k3 = kernel_sizes

        self.conv_blocks = nn.Sequential(
            # Block 1
            nn.Conv1d(in_channels=n_features, out_channels=c1,
                      kernel_size=k1, padding="same"),
            nn.BatchNorm1d(c1),
            nn.ReLU(),
            nn.Dropout1d(dropout_conv),
            # Block 2
            nn.Conv1d(in_channels=c1, out_channels=c2,
                      kernel_size=k2, padding="same"),
            nn.BatchNorm1d(c2),
            nn.ReLU(),
            nn.Dropout1d(dropout_conv),
            # Block 3
            nn.Conv1d(in_channels=c2, out_channels=c3,
                      kernel_size=k3, padding="same"),
            nn.BatchNorm1d(c3),
            nn.ReLU(),
            nn.Dropout1d(dropout_conv / 2),
        )

        # Pooling partiel : conserve pool_size timesteps (doit diviser window_size sur MPS)
        self.pool = nn.AdaptiveAvgPool1d(pool_size)

        self.head = nn.Sequential(
            nn.Linear(c3 * pool_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout_fc),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch, window, features)
        # Conv1d attend (batch, channels, seq_len)
        x = x.transpose(1, 2)
        x = self.conv_blocks(x)
        x = self.pool(x)
        x = x.flatten(1)
        x = self.head(x)
        return x.squeeze(-1)
