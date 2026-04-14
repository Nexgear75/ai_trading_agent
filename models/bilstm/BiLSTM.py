"""Bidirectional LSTM model for crypto price prediction."""
import torch.nn as nn

from data.features.pipeline import get_feature_columns


class BiLSTMModel(nn.Module):
    """BiLSTM with attention mechanism for better temporal pattern capture."""

    def __init__(self, n_features=None, hidden=128, layers=2, drop=0.2):
        if n_features is None:
            n_features = len(get_feature_columns())
        super().__init__()
        self.hidden = hidden
        self.layers = layers

        # Bidirectional LSTM
        self.rnn = nn.LSTM(
            n_features,
            hidden,
            layers,
            batch_first=True,
            dropout=drop if layers > 1 else 0,
            bidirectional=True,
        )

        # Attention layer
        self.attention = nn.Sequential(
            nn.Linear(hidden * 2, hidden),
            nn.Tanh(),
            nn.Linear(hidden, 1, bias=False),
        )

        # Output layers (hidden * 2 car bidirectional)
        self.fc = nn.Sequential(
            nn.Linear(hidden * 2, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1),
        )

    def forward(self, x):
        # x: (batch, seq_len, features)
        rnn_out, _ = self.rnn(x)  # (batch, seq_len, hidden*2)

        # Attention weights
        attn_weights = self.attention(rnn_out)  # (batch, seq_len, 1)
        attn_weights = nn.functional.softmax(attn_weights, dim=1)

        # Weighted sum
        context = (rnn_out * attn_weights).sum(dim=1)  # (batch, hidden*2)

        return self.fc(context).squeeze(-1)
