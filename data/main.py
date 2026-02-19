"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import numpy as np
import os
from config import SYMBOLS, OUTPUT_PATH
from data.fetcher import fetch_ohlcv
from data.features.pipeline import build_features
from data.labeling.labeler import add_labels
from data.preprocessing.builder import build_windows


def process_symbol(symbol: str):
    """
    Process a single symbol through the full pipeline.

    Fetches data, builds features, adds labels, and creates windows
    for a given cryptocurrency trading pair.

    Args:
        symbol: Trading pair symbol (e.g., "BTC/USDT")

    Returns:
        Tuple of (X, y, dates) where:
            - X: 3D array of features
            - y: 1D array of labels
            - dates: Timestamps for each sample
    """
    print(f"\n{'-' * 10}")
    print(f"Working on {symbol}")
    print(f"{'-' * 10}")

    df = fetch_ohlcv(symbol)
    df = build_features(df)
    df = add_labels(df)
    X, y, dates = build_windows(df)

    print(f"Shape X : {X.shape}")
    print(f"Shape y : {y.shape}")
    print(
        f"Distribution : +1={np.sum(y == 1)} | 0={np.sum(y == 0)} | -1={np.sum(y == -1)}"
    )

    return X, y, dates


def main():
    """
    Main entry point for data processing pipeline.

    Processes all symbols defined in config, builds datasets,
    and saves individual and consolidated .npz files.
    """
    os.makedirs(OUTPUT_PATH, exist_ok=True)

    all_X, all_y = [], []

    for symbol in SYMBOLS:
        X, y, dates = process_symbol(symbol)

        # ----- Individual save per crypto ----- #
        filename = symbol.replace("/", "_")
        np.savez(
            os.path.join(OUTPUT_PATH, f"{filename}_dataset.npz"),
            X=X,
            y=y,
            dates=dates.astype(str),
        )

        all_X.append(X)
        all_y.append(y)

    # ----- Save full dataset ----- #
    full_X = np.concatenate(all_X, axis=0)
    full_y = np.concatenate(all_y, axis=0)

    np.savez(os.path.join(OUTPUT_PATH, "full_dataset.npz"), X=full_X, y=full_y)

    print("\nDataset complet généré !")
    print(f"   Shape final X : {full_X.shape}")
    print(f"   Shape final y : {full_y.shape}")


if __name__ == "__main__":
    main()
