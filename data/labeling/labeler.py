"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import pandas as pd
from config import LABEL_THRESHOLD, BASE_PREDICTION_DAYS, DEFAULT_TIMEFRAME, get_timeframe_config


def add_labels(df: pd.DataFrame, prediction_horizon: int = None, timeframe: str = None) -> pd.DataFrame:
    """
    Add classification labels to a DataFrame based on future price movement.

    Labels are assigned based on future returns over prediction_horizon periods:
    - 1: Future return > LABEL_THRESHOLD (bullish)
    - -1: Future return < -LABEL_THRESHOLD (bearish)
    - 0: Future return within threshold range (neutral)

    Args:
        df: DataFrame with a 'close' price column
        prediction_horizon: Number of periods to look ahead for prediction.
                            If None, will be computed from timeframe or use default.
        timeframe: Timeframe string (e.g., "1d", "1h") used to compute prediction_horizon
                   if prediction_horizon is None.

    Returns:
        DataFrame with added 'label' column and trailing NaN rows removed
    """
    df = df.copy()

    # Determine prediction_horizon
    if prediction_horizon is None:
        if timeframe is not None:
            config = get_timeframe_config(timeframe)
            prediction_horizon = config["prediction_horizon"]
        else:
            # Fallback to legacy default (3 periods)
            prediction_horizon = BASE_PREDICTION_DAYS

    future_return = df["close"].shift(-prediction_horizon) / df["close"] - 1

    df["label"] = 0
    df.loc[future_return > LABEL_THRESHOLD, "label"] = 1
    df.loc[future_return < -LABEL_THRESHOLD, "label"] = -1

    # ----- Remove last rows without label ----- #
    df = df[:-prediction_horizon]

    return df
