"""
Time-based cyclical features for hourly data.

@author: Alex Fougeroux
"""

import numpy as np
import pandas as pd


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add cyclical time features from a DatetimeIndex.

    Encodes hour-of-day and day-of-week as sin/cos pairs to capture
    intraday and weekly trading patterns without discontinuities.

    Args:
        df: DataFrame with a DatetimeIndex

    Returns:
        DataFrame with added columns: 'hour_sin', 'hour_cos',
        'dow_sin', 'dow_cos'
    """
    df = df.copy()

    hour = df.index.hour
    dow = df.index.dayofweek

    df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    df["dow_sin"] = np.sin(2 * np.pi * dow / 7)
    df["dow_cos"] = np.cos(2 * np.pi * dow / 7)

    return df
