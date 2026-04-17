import math

import torch
import torch.nn as nn

from data.features.pipeline import FEATURE_COLUMNS


class PositionalEncoding(nn.Module):
    """Encodage positionnel sinusoïdal (Vaswani et al., 2017)."""

    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2, dtype=torch.float) * (-math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        # (1, max_len, d_model) pour le broadcasting sur le batch
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x : (batch, seq_len, d_model)
        x = x + self.pe[:, : x.size(1)]
        return self.dropout(x)


class Transformer(nn.Module):
    """
    Transformer encoder pour la prédiction de retours financiers.

    Conserve la même interface que le CNN1D d'origine :
    - Même signature __init__ (window_size, n_features, …)
    - Même shape d'entrée/sortie : (batch, window, features) → (batch,)
    - Compatible avec training.py / evaluation.py / data_preparator.py sans modification

    Architecture :
        Input projection  →  Positional Encoding
        → N × TransformerEncoderLayer (multi-head self-attention + FFN)
        → AdaptiveAvgPool sur la dimension temporelle
        → MLP regression head  →  scalaire
    """

    def __init__(
        self,
        window_size: int = 30,
        n_features: int = len(FEATURE_COLUMNS),
        # Paramètres "channels" réutilisés pour d_model / nhead / num_layers
        channels: tuple = (16, 32, 64),
        kernel_sizes: tuple = (3, 3, 3),   # ignoré (gardé pour compatibilité checkpoint)
        dropout_conv: float = 0.2,          # → dropout du Transformer encoder
        dropout_fc: float = 0.3,            # → dropout de la tête MLP
        pool_size: int = 5,
    ):
        """
        Args:
            window_size:   Longueur de la séquence d'entrée.
            n_features:    Nombre de features par pas de temps.
            channels:      (d_model, nhead, num_layers).
                           d_model doit être divisible par nhead.
                           Défaut (16, 32, 64) → d_model=16, nhead=32 invalide ;
                           en pratique, config.py doit passer des valeurs cohérentes
                           (ex: (64, 4, 3) ou (128, 8, 4)).
            kernel_sizes:  Ignoré — conservé uniquement pour compatibilité de signature.
            dropout_conv:  Dropout interne des TransformerEncoderLayers.
            dropout_fc:    Dropout de la tête MLP.
            pool_size:     Nombre de timesteps conservés après AdaptiveAvgPool1d.
                           Contrainte MPS : window_size % pool_size == 0.
        """
        super().__init__()

        d_model, nhead, num_layers = channels

        # Vérification de divisibilité (exigée par nn.MultiheadAttention)
        if d_model % nhead != 0:
            raise ValueError(
                f"d_model ({d_model}) doit être divisible par nhead ({nhead}). "
                f"Corrigez 'channels' dans config.py."
            )

        self.d_model = d_model
        self.pool_size = pool_size

        # --- Projection d'entrée : n_features → d_model ---
        self.input_proj = nn.Linear(n_features, d_model)

        # --- Encodage positionnel ---
        self.pos_enc = PositionalEncoding(d_model, max_len=window_size + 1, dropout=dropout_conv)

        # --- Pile de TransformerEncoderLayers ---
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,   # convention FFN 4×
            dropout=dropout_conv,
            activation="relu",
            batch_first=True,              # (batch, seq, d_model)
            norm_first=True,               # Pre-LN : meilleure stabilité en entraînement
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers,
            enable_nested_tensor=False,    # évite des warnings PyTorch / MPS
        )

        # --- Pooling temporel (même logique que le CNN) ---
        # pool opère sur (batch, d_model, seq_len) donc on transpose avant
        self.pool = nn.AdaptiveAvgPool1d(pool_size)

        # --- Tête MLP de régression ---
        self.head = nn.Sequential(
            nn.Linear(d_model * pool_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout_fc),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x : (batch, window, n_features)

        # Projection vers l'espace du Transformer
        x = self.input_proj(x)                  # (batch, window, d_model)

        # Encodage positionnel
        x = self.pos_enc(x)                     # (batch, window, d_model)

        # Encodeur Transformer (batch_first=True)
        x = self.transformer_encoder(x)         # (batch, window, d_model)

        # Pooling temporel : AdaptiveAvgPool1d attend (batch, channels, seq_len)
        x = x.transpose(1, 2)                   # (batch, d_model, window)
        x = self.pool(x)                        # (batch, d_model, pool_size)

        # Régression
        x = x.flatten(1)                        # (batch, d_model × pool_size)
        x = self.head(x)                        # (batch, 1)
        return x.squeeze(-1)                    # (batch,)
