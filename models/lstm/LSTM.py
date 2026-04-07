"""LSTM model for crypto price prediction."""
import torch.nn as nn


class LSTMModel(nn.Module):
    def __init__(self, n_features=20, hidden=128, layers=2, drop=0.2):
        super().__init__()
        self.rnn = nn.LSTM(n_features, hidden, layers, batch_first=True,
                           dropout=drop if layers > 1 else 0)
        self.fc = nn.Sequential(
            nn.Linear(hidden, 64), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 1))

    def forward(self, x):
        _, (h, _) = self.rnn(x)
        return self.fc(h[-1]).squeeze(-1)
