"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import argparse
import os
import pandas as pd
from config import SYMBOLS, BACKTEST_SYMBOLS, DEFAULT_TIMEFRAME, get_timeframe_config
from data.fetcher import fetch_ohlcv
from data.features.pipeline import build_features
from data.labeling.labeler import add_labels


def process_symbol(symbol: str, timeframe: str = DEFAULT_TIMEFRAME):
    """
    Process a single symbol through the full pipeline.

    Fetches data, builds features, adds labels, and creates windows
    for a given cryptocurrency trading pair.

    Args:
        symbol: Trading pair symbol (e.g., "BTC/USDT")
        timeframe: Timeframe for the data (e.g., "1d", "1h", "4h").
                   Defaults to DEFAULT_TIMEFRAME ("1d").

    Returns:
        DataFrame with features and labels
    """
    print(f"\n{'-' * 50}")
    print(f"  Traitement de {symbol} [{timeframe}]")
    print(f"{'-' * 50}")

    df = fetch_ohlcv(symbol, timeframe=timeframe)
    df = build_features(df, timeframe=timeframe)
    df = add_labels(df, timeframe=timeframe)
    df.insert(0, "symbol", symbol.replace("/", "_"))

    print(f"  Lignes générées : {len(df)}")
    print(f"  Colonnes        : {list(df.columns)}")
    print(f"  Période         : {df.index[0]} → {df.index[-1]}")
    print(
        f"  Distribution    : +1={(df['label'] == 1).sum()} | "
        f"0={(df['label'] == 0).sum()} | -1={(df['label'] == -1).sum()}"
    )

    return df


def main(timeframe: str = DEFAULT_TIMEFRAME):
    """
    Main entry point for data processing pipeline.

    Processes all symbols defined in config, builds datasets,
    and saves individual and consolidated CSV files.

    Args:
        timeframe: Timeframe for the data (e.g., "1d", "1h", "4h").
                   Defaults to DEFAULT_TIMEFRAME ("1d").
    """
    # Get config for this timeframe
    tf_config = get_timeframe_config(timeframe)
    output_path = tf_config["output_path"]

    # Create output directory for this timeframe
    os.makedirs(output_path, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"  GÉNÉRATION DE DATASET - TIMEFRAME: {timeframe}")
    print(f"  Output path: {output_path}")
    print(f"{'=' * 60}")

    all_dfs = []

    for symbol in SYMBOLS:
        df = process_symbol(symbol, timeframe=timeframe)

        # Sauvegarde CSV individuel
        filename = symbol.replace("/", "_") + ".csv"
        filepath = os.path.join(output_path, filename)
        df.to_csv(filepath)
        print(f"  Sauvegardé → {filepath}")

        all_dfs.append(df)

    # Sauvegarde CSV global (entraînement uniquement — pas les BACKTEST_SYMBOLS)
    full_df = pd.concat(all_dfs)
    full_path = os.path.join(output_path, "full_dataset.csv")
    full_df.to_csv(full_path)

    print(f"\n{'-' * 50}")
    print("  Dataset complet généré !")
    print(f"  Timeframe            : {timeframe}")
    print(f"  Fichiers individuels : {len(SYMBOLS)} CSVs")
    print(f"  Dataset global       : {full_path}")
    print(f"  Lignes totales       : {len(full_df)}")
    print(f"  Colonnes             : {len(full_df.columns)}")
    print(f"{'-' * 50}\n")

    # Backtest symbols (out-of-sample, NON inclus dans full_dataset.csv)
    if BACKTEST_SYMBOLS:
        print(f"\n{'=' * 50}")
        print("  Symboles backtest (out-of-sample)")
        print(f"{'=' * 50}")

        for symbol in BACKTEST_SYMBOLS:
            df = process_symbol(symbol, timeframe=timeframe)

            filename = symbol.replace("/", "_") + ".csv"
            filepath = os.path.join(output_path, filename)
            df.to_csv(filepath)
            print(f"  Sauvegardé → {filepath}")

        print(f"\n  {len(BACKTEST_SYMBOLS)} symbole(s) backtest générés (exclus du dataset d'entraînement)")
        print(f"{'=' * 50}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate datasets for cryptocurrency price prediction"
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default=DEFAULT_TIMEFRAME,
        help=f"Timeframe for the data (default: {DEFAULT_TIMEFRAME}). "
             f"Available: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M"
    )
    args = parser.parse_args()

    main(timeframe=args.timeframe)
