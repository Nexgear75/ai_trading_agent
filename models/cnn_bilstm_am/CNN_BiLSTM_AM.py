import torch
import torch.nn as nn
import torch.nn.functional as F

from data.features.pipeline import FEATURE_COLUMNS


class CNNBiLSTMAM(nn.Module):
    def __init__(
        self,
        window_size: int = 30,
        n_features: int = len(FEATURE_COLUMNS),
        channels: tuple = (16, 32, 64),
        kernel_sizes: tuple = (3, 3, 3),
        dropout_conv: float = 0.2,
        pool_size: int = 5,
        lstm_hidden: int = 64,
        lstm_layers: int = 1,
        dropout_lstm: float = 0.0,
        dropout_fc: float = 0.3,
        task: str = "regression",
    ):
        """
        Modèle hybride CNN-BiLSTM-AM pour la prédiction de retours financiers.

        Architecture :
            1. CNN : extraction de features locales (3 blocs conv1d)
            2. BiLSTM : capture des dépendances temporelles bidirectionnelles
            3. Attention Mechanism : pondération des pas de temps pertinents
            4. Couche de sortie : régression linéaire ou classification binaire

        Args:
            window_size: Longueur de la séquence d'entrée.
            n_features: Nombre de features par pas de temps.
            channels: Nombre de canaux pour chacun des 3 blocs conv.
            kernel_sizes: Taille du kernel pour chacun des 3 blocs conv.
            dropout_conv: Dropout appliqué après chaque bloc conv.
            pool_size: Sortie de AdaptiveAvgPool1d (contrainte MPS :
                       window_size % pool_size == 0).
            lstm_hidden: Nombre d'unités cachées BiLSTM (par direction).
            lstm_layers: Nombre de couches LSTM empilées.
            dropout_lstm: Dropout inter-couches LSTM (ignoré si lstm_layers=1).
            dropout_fc: Dropout appliqué au vecteur de contexte avant la sortie.
            task: "regression" ou "classification" (binaire).
        """
        super().__init__()
        self.task = task

        c1, c2, c3 = channels
        k1, k2, k3 = kernel_sizes

        # ----- CNN : extraction de features locales -----
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

        self.pool = nn.AdaptiveAvgPool1d(pool_size)

        # ----- BiLSTM : dépendances temporelles bidirectionnelles -----
        self.bilstm = nn.LSTM(
            input_size=c3,
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout_lstm if lstm_layers > 1 else 0.0,
        )
        self.lstm_norm = nn.LayerNorm(2 * lstm_hidden)

        # ----- Attention Mechanism (avec couche cachée) -----
        self.attn = nn.Sequential(
            nn.Linear(2 * lstm_hidden, lstm_hidden),
            nn.Tanh(),
            nn.Linear(lstm_hidden, 1),
        )

        # ----- Couche de sortie (MLP head) -----
        self.head = nn.Sequential(
            nn.Linear(2 * lstm_hidden, lstm_hidden),
            nn.ReLU(),
            nn.Dropout(dropout_fc),
            nn.Linear(lstm_hidden, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

        # Initialisation des poids pour éviter le mean-predictor
        self._init_weights()

    def _init_weights(self):
        """Initialisation Xavier/Kaiming pour une meilleure propagation du signal."""
        for m in self.modules():
            if isinstance(m, nn.Conv1d):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
            elif isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
        # Dernière couche : initialisation avec plus grande variance
        # pour que les prédictions initiales couvrent la plage des targets
        last_linear = self.head[-1]
        nn.init.xavier_normal_(last_linear.weight, gain=2.0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch, window, features)

        # CNN
        x = x.transpose(1, 2)              # (batch, features, window)
        x = self.conv_blocks(x)            # (batch, c3, window)
        x = self.pool(x)                   # (batch, c3, pool_size)

        # Préparer l'entrée BiLSTM
        x = x.transpose(1, 2)              # (batch, pool_size, c3)

        # BiLSTM
        lstm_out, _ = self.bilstm(x)       # (batch, pool_size, 2*lstm_hidden)
        lstm_out = self.lstm_norm(lstm_out)

        # Attention
        e = self.attn(lstm_out)                  # (batch, pool_size, 1)
        alpha = F.softmax(e, dim=1)              # (batch, pool_size, 1)
        context = (alpha * lstm_out).sum(dim=1)  # (batch, 2*lstm_hidden)

        # Sortie
        out = self.head(context)           # (batch, 1)
        return out.squeeze(-1)             # (batch,)
