"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import pandas as pd
from config import LABEL_THRESHOLD, PREDICTION_HORIZON


def add_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add classification labels to a DataFrame based on future price movement.

    Labels are assigned based on future returns over PREDICTION_HORIZON periods:
    - 1: Future return > LABEL_THRESHOLD (bullish)
    - -1: Future return < -LABEL_THRESHOLD (bearish)
    - 0: Future return within threshold range (neutral)

    Args:
        df: DataFrame with a 'close' price column

    Returns:
        DataFrame with added 'label' column and trailing NaN rows removed
    """
    df = df.copy()

    future_return = df["close"].shift(-PREDICTION_HORIZON) / df["close"] - 1

    df["label"] = 0
    df.loc[future_return > LABEL_THRESHOLD, "label"] = 1
    df.loc[future_return < -LABEL_THRESHOLD, "label"] = -1

    # ----- Remove last lign without label ----- #
    df = df[:-PREDICTION_HORIZON]

    return df
