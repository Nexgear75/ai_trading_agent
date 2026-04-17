"""LSTM model for crypto price prediction."""
import math

import torch
import torch.nn as nn

from data.features.pipeline import get_feature_columns


class LSTMModel(nn.Module):
    """LSTM with layer norm, scaled attention, and lightweight MLP head."""

    def __init__(self, n_features=None, hidden=32, layers=1, drop=0.6):
        if n_features is None:
            n_features = len(get_feature_columns())
        super().__init__()
        self.hidden = hidden
        self.layers = layers

        self.input_proj = nn.Sequential(
            nn.Linear(n_features, hidden),
            nn.LayerNorm(hidden),
            nn.GELU(),
            nn.Dropout(drop),
        )

        self.rnn = nn.LSTM(
            hidden, hidden, layers, batch_first=True,
            dropout=drop if layers > 1 else 0,
        )
        self.rnn_norm = nn.LayerNorm(hidden)

        self.attn_q = nn.Linear(hidden, hidden // 2, bias=False)
        self.attn_k = nn.Linear(hidden, hidden // 2, bias=False)
        self.attn_scale = math.sqrt(hidden // 2)

        self.fc1 = nn.Linear(hidden, hidden)
        self.norm1 = nn.LayerNorm(hidden)
        self.out = nn.Linear(hidden, 1)
        self.drop = nn.Dropout(drop)
        self.act = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_proj(x)                         # (B, T, hidden)
        rnn_out, _ = self.rnn(x)                       # (B, T, hidden)
        rnn_out = self.rnn_norm(rnn_out)

        q = self.attn_q(rnn_out[:, -1:, :])            # (B, 1, hidden//2)
        k = self.attn_k(rnn_out)                       # (B, T, hidden//2)
        scores = torch.bmm(q, k.transpose(1, 2)) / self.attn_scale
        weights = torch.softmax(scores, dim=-1)
        context = torch.bmm(weights, rnn_out).squeeze(1)  # (B, hidden)

        h = self.drop(self.act(self.norm1(self.fc1(context))))
        return self.out(h).squeeze(-1)
