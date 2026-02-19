"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import os
import pandas as pd
from config import SYMBOLS, OUTPUT_PATH
from data.fetcher import fetch_ohlcv
from data.features.pipeline import build_features
from data.labeling.labeler import add_labels


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
    print(f"\n{'-' * 50}")
    print(f"  Traitement de {symbol}")
    print(f"{'-' * 50}")

    df = fetch_ohlcv(symbol)
    df = build_features(df)
    df = add_labels(df)
    df.insert(0, "symbol", symbol.replace("/", "_"))

    print(f"  Lignes générées : {len(df)}")
    print(f"  Colonnes        : {list(df.columns)}")
    print(f"  Période         : {df.index[0].date()} → {df.index[-1].date()}")
    print(
        f"  Distribution    : +1={(df['label'] == 1).sum()} | "
        f"0={(df['label'] == 0).sum()} | -1={(df['label'] == -1).sum()}"
    )

    return df


def main():
    """
    Main entry point for data processing pipeline.

    Processes all symbols defined in config, builds datasets,
    and saves individual and consolidated .npz files.
    """
    os.makedirs(OUTPUT_PATH, exist_ok=True)

    all_dfs = []

    for symbol in SYMBOLS:
        df = process_symbol(symbol)

        # Sauvegarde CSV individuel
        filename = symbol.replace("/", "_") + ".csv"
        filepath = os.path.join(OUTPUT_PATH, filename)
        df.to_csv(filepath)
        print(f"  Sauvegardé → {filepath}")

        all_dfs.append(df)

    # Sauvegarde CSV global
    full_df = pd.concat(all_dfs)
    full_path = os.path.join(OUTPUT_PATH, "full_dataset.csv")
    full_df.to_csv(full_path)

    print(f"\n{'-' * 50}")
    print("  Dataset complet généré !")
    print(f"  Fichiers individuels : {len(SYMBOLS)} CSVs")
    print(f"  Dataset global       : {full_path}")
    print(f"  Lignes totales       : {len(full_df)}")
    print(f"  Colonnes             : {len(full_df.columns)}")
    print(f"{'-' * 50}\n")


if __name__ == "__main__":
    main()
