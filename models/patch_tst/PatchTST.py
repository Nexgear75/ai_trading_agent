from __future__ import annotations

import torch
import torch.nn as nn

from data.features.pipeline import FEATURE_COLUMNS


class PatchTST(nn.Module):
    def __init__(
        self,
        window_size: int = 30,
        n_features: int = len(FEATURE_COLUMNS),
        patch_len: int = 6,
        stride: int = 3,
        d_model: int = 64,
        n_heads: int = 4,
        n_layers: int = 3,
        d_ff: int = 128,
        dropout: float = 0.2,
        dropout_fc: float = 0.3,
    ):
        """
        PatchTST pour la prédiction de retours financiers.

        Découpe la séquence temporelle en patches chevauchants, projette
        chaque patch dans un espace latent, puis applique un Transformer
        Encoder pour capturer les dépendances inter-patches.

        Args:
            window_size: Longueur de la séquence d'entrée.
            n_features: Nombre de features par pas de temps.
            patch_len: Nombre de pas de temps par patch.
            stride: Pas entre deux patches consécutifs.
            d_model: Dimension du modèle Transformer.
            n_heads: Nombre de têtes d'attention (d_model % n_heads == 0).
            n_layers: Nombre de couches Transformer Encoder.
            d_ff: Dimension de la couche feed-forward.
            dropout: Dropout dans le Transformer.
            dropout_fc: Dropout dans la tête MLP.
        """
        super().__init__()

        if patch_len > window_size:
            raise ValueError(
                f"patch_len ({patch_len}) must be <= window_size ({window_size})."
            )
        if stride <= 0:
            raise ValueError(f"stride must be positive, got {stride}.")

        self.patch_len = patch_len
        self.stride = stride
        self.num_patches = (window_size - patch_len) // stride + 1
        if self.num_patches < 1:
            raise ValueError(
                f"Invalid patch config: num_patches={self.num_patches} "
                f"(window_size={window_size}, patch_len={patch_len}, stride={stride})."
            )
        patch_dim = patch_len * n_features

        # ----- Projection linéaire des patches -----
        self.patch_proj = nn.Linear(patch_dim, d_model)

        # ----- Positional embedding apprenable -----
        self.pos_embed = nn.Parameter(torch.zeros(1, self.num_patches, d_model))
        nn.init.trunc_normal_(self.pos_embed, std=0.02)

        # ----- Transformer Encoder -----
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_ff,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)

        # ----- Tête de régression (MLP) -----
        self.head = nn.Sequential(
            nn.LayerNorm(self.num_patches * d_model),
            nn.Linear(self.num_patches * d_model, d_model),
            nn.GELU(),
            nn.Dropout(dropout_fc),
            nn.Linear(d_model, 32),
            nn.GELU(),
            nn.Linear(32, 1),
        )

        self._init_weights()

    def _init_weights(self):
        """Initialisation Xavier/Kaiming pour une meilleure propagation du signal."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
        # Dernière couche : variance plus grande pour couvrir la plage des targets
        last_linear = self.head[-1]
        nn.init.xavier_normal_(last_linear.weight, gain=2.0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch, window_size, n_features)
        batch_size = x.shape[0]

        # ----- Patching -----
        # Unfold sur la dimension temporelle (dim=1)
        # (batch, window_size, n_features) → (batch, num_patches, n_features, patch_len)
        patches = x.unfold(1, self.patch_len, self.stride)  # (B, num_patches, n_feat, patch_len)
        patches = patches.permute(0, 1, 3, 2)               # (B, num_patches, patch_len, n_feat)
        patches = patches.reshape(batch_size, self.num_patches, -1)  # (B, num_patches, patch_dim)

        # ----- Projection + positional embedding -----
        z = self.patch_proj(patches)       # (B, num_patches, d_model)
        z = z + self.pos_embed             # (B, num_patches, d_model)

        # ----- Transformer Encoder -----
        z = self.encoder(z)                # (B, num_patches, d_model)

        # ----- Flatten + MLP head -----
        z = z.flatten(1)                   # (B, num_patches * d_model)
        out = self.head(z)                 # (B, 1)
        return out.squeeze(-1)             # (B,)
