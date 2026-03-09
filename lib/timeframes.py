"""Timeframe constants and parsing utilities."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

TIMEFRAME_DELTA: dict[str, pd.Timedelta] = {
    "1m": pd.Timedelta(minutes=1),
    "3m": pd.Timedelta(minutes=3),
    "5m": pd.Timedelta(minutes=5),
    "15m": pd.Timedelta(minutes=15),
    "30m": pd.Timedelta(minutes=30),
    "1h": pd.Timedelta(hours=1),
    "2h": pd.Timedelta(hours=2),
    "4h": pd.Timedelta(hours=4),
    "6h": pd.Timedelta(hours=6),
    "8h": pd.Timedelta(hours=8),
    "12h": pd.Timedelta(hours=12),
    "1d": pd.Timedelta(days=1),
    "3d": pd.Timedelta(days=3),
    "1w": pd.Timedelta(weeks=1),
}


def parse_timeframe(tf: str) -> timedelta:
    delta = TIMEFRAME_DELTA.get(tf)
    if delta is None:
        raise ValueError(
            f"Unsupported timeframe: {tf!r}. "
            f"Valid options: {sorted(TIMEFRAME_DELTA)}"
        )
    return delta.to_pytimedelta()
