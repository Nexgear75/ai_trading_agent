"""Bidirectional LSTM model for crypto price prediction."""
import math

import torch
import torch.nn as nn

from data.features.pipeline import get_feature_columns


class BiLSTMModel(nn.Module):
    """BiLSTM with layer norm, scaled attention, and residual MLP head."""

    def __init__(self, n_features=None, hidden=32, layers=1, drop=0.6):
        if n_features is None:
            n_features = len(get_feature_columns())
        super().__init__()
        self.hidden = hidden
        self.layers = layers
        d = hidden * 2  # bidirectional output dim

        # Project input to stable embedding before LSTM
        self.input_proj = nn.Sequential(
            nn.Linear(n_features, hidden),
            nn.LayerNorm(hidden),
            nn.GELU(),
            nn.Dropout(drop),
        )

        self.rnn = nn.LSTM(
            hidden,
            hidden,
            layers,
            batch_first=True,
            dropout=drop if layers > 1 else 0,
            bidirectional=True,
        )
        self.rnn_norm = nn.LayerNorm(d)

        # Single-head attention with temperature scaling
        self.attn_q = nn.Linear(d, d // 2, bias=False)
        self.attn_k = nn.Linear(d, d // 2, bias=False)
        self.attn_scale = math.sqrt(d // 2)

        # Lightweight MLP head
        self.fc1 = nn.Linear(d, hidden)
        self.norm1 = nn.LayerNorm(hidden)
        self.out = nn.Linear(hidden, 1)
        self.drop = nn.Dropout(drop)
        self.act = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, n_features)
        x = self.input_proj(x)                        # (B, T, hidden)
        rnn_out, _ = self.rnn(x)                      # (B, T, d)
        rnn_out = self.rnn_norm(rnn_out)

        # Scaled attention: use last step as query, all steps as keys
        q = self.attn_q(rnn_out[:, -1:, :])           # (B, 1, d//2)
        k = self.attn_k(rnn_out)                      # (B, T, d//2)
        scores = torch.bmm(q, k.transpose(1, 2)) / self.attn_scale  # (B, 1, T)
        weights = torch.softmax(scores, dim=-1)
        context = torch.bmm(weights, rnn_out).squeeze(1)  # (B, d)

        h = self.drop(self.act(self.norm1(self.fc1(context))))
        return self.out(h).squeeze(-1)
