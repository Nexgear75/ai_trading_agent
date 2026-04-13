"""
Created on 31 march 2026

@author: Alex Fougeroux
"""

import numpy as np
import pandas as pd


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add cyclical temporal features encoding hour of day and day of week.

    Uses sine/cosine encoding to preserve the cyclical nature of time
    (e.g., hour 23 is close to hour 0). Only meaningful for intraday
    timeframes (1h, 4h, etc.).

    Args:
        df: DataFrame with a DatetimeIndex

    Returns:
        DataFrame with added columns: 'hour_sin', 'hour_cos', 'dow_sin', 'dow_cos'
    """
    df = df.copy()
    hour = df.index.hour
    dow = df.index.dayofweek

    df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    df["dow_sin"]  = np.sin(2 * np.pi * dow / 7)
    df["dow_cos"]  = np.cos(2 * np.pi * dow / 7)

    return df
