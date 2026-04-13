"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import ccxt
import pandas as pd
import os
import time
from config import START_DATE, get_timeframe_config, DEFAULT_TIMEFRAME


def fetch_ohlcv(symbol: str, timeframe: str = DEFAULT_TIMEFRAME) -> pd.DataFrame:
    """
    Download OHLCV data from Binance for a given trading pair.

    Fetches historical candlestick data (open, high, low, close, volume) from
    Binance exchange. Uses local CSV cache to avoid redundant API calls.

    Args:
        symbol: Trading pair symbol (e.g., "BTC/USDT", "ETH/USDT")
        timeframe: Timeframe for the data (e.g., "1d", "1h", "4h").
                   Defaults to DEFAULT_TIMEFRAME ("1d").

    Returns:
        DataFrame with OHLCV data indexed by timestamp

    Raises:
        Exception: If API request fails or data cannot be fetched
        ValueError: If timeframe is not supported
    """
    # Get config for this timeframe
    tf_config = get_timeframe_config(timeframe)
    raw_data_path = tf_config["raw_data_path"]

    filename = symbol.replace("/", "_") + "_raw.csv"
    filepath = os.path.join(raw_data_path, filename)

    if os.path.exists(filepath):
        print(f"  [CACHE] {symbol} [{timeframe}] chargé depuis {filepath}")
        df = pd.read_csv(filepath, index_col="timestamp", parse_dates=True)
        return df

    print(f"  [FETCH] Téléchargement de {symbol} [{timeframe}] depuis Binance...")
    exchange = ccxt.binance()
    since = exchange.parse8601(f"{START_DATE}T00:00:00Z")

    all_ohlcv = []
    while True:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        since = ohlcv[-1][0] + 1
        time.sleep(0.3)
        if len(ohlcv) < 1000:
            break

    df = pd.DataFrame(
        all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)

    os.makedirs(raw_data_path, exist_ok=True)
    df.to_csv(filepath)
    print(f"  [SAVE] Données brutes [{timeframe}] sauvegardées → {filepath}")

    return df
