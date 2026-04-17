"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import pandas as pd


def add_volume_features(
    df: pd.DataFrame,
    volume_window: int = 20,
    vol_window: int = 14,
) -> pd.DataFrame:
    """
    Add volume-based features to a DataFrame containing OHLCV data.

    Computes volume ratio relative to rolling average, volume return,
    and price volatility.

    Args:
        df: DataFrame with 'volume' and 'close' columns
        volume_window: Rolling window for volume ratio. Default 20 (1d).
                       For 1h use 480 (20×24).
        vol_window: Rolling window for volatility std. Default 14 (1d).
                    For 1h use 336 (14×24).

    Returns:
        DataFrame with added columns: 'volume_ratio', 'volume_return', 'volatility'
    """
    df = df.copy()

    df["volume_ratio"] = df["volume"] / df["volume"].rolling(volume_window).mean()
    df["volume_return"] = df["volume"].pct_change()
    df["volatility"] = df["close"].pct_change().rolling(vol_window).std()

    # ----- OBV (On-Balance Volume) normalisé -----
    direction = df["close"].diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    obv = (direction * df["volume"]).cumsum()
    obv_ma = obv.rolling(volume_window).mean()
    obv_std = obv.rolling(volume_window).std().replace(0, 1e-10)
    df["obv_normalized"] = (obv - obv_ma) / obv_std

    # ----- Volume directionnel : pression achat vs vente -----
    is_bullish = df["close"] > df["open"]
    buy_vol = df["volume"].where(is_bullish, 0).rolling(volume_window).sum()
    total_vol = df["volume"].rolling(volume_window).sum()
    df["volume_directional"] = buy_vol / (total_vol + 1e-10)

    return df
