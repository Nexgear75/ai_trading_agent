import numpy as np
from sklearn.preprocessing import RobustScaler

from data.features.pipeline import FEATURE_COLUMNS
from utils.dataset_loader import load_symbol, load_all


def prepare_rl_data(
        symbol: str | None = None,
        train_ratio: float = 0.8,
        verbose: bool = True,
) -> tuple:
    """Prepare data for the RL trading environment.

    Unlike the CNN data preparator, this does NOT pre-build windows or scale
    targets. The environment constructs windows on-the-fly during step(),
    and rewards replace target labels.

    Args:
        verbose: 
        symbol: Crypto symbol (e.g. "BTC"). None = all cryptos.
        train_ratio: Fraction of data for training.

    Returns:
        (df_train, df_val, feature_scaler, clip_bounds) where:
            - df_train: Training DataFrame with features + close + symbol.
            - df_val: Validation DataFrame.
            - feature_scaler: Fitted RobustScaler for features.
            - clip_bounds: Dict of {column: (lo, hi)} for winsorization.
    """
    df = load_symbol(symbol, timeframe="6h") if symbol else load_all(timeframe="6h")

    # Ensure we have required columns
    required = set(FEATURE_COLUMNS) | {"close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in dataset: {missing}")

    if "symbol" not in df.columns:
        if symbol:
            df["symbol"] = symbol.upper().replace("/", "_")
        else:
            df["symbol"] = "UNKNOWN"

    df = df.sort_index()

    # Temporal split
    split_idx = int(len(df) * train_ratio)
    df_train = df.iloc[:split_idx].copy()
    df_val = df.iloc[split_idx:].copy()

    # Compute winsorization bounds from training data
    clip_bounds = {}
    for col in FEATURE_COLUMNS:
        lo = np.percentile(df_train[col].values, 1.0)
        hi = np.percentile(df_train[col].values, 99.0)
        clip_bounds[col] = (lo, hi)

    # Fit RobustScaler on clipped training features
    train_feats = df_train[FEATURE_COLUMNS].values.copy()
    for i, col in enumerate(FEATURE_COLUMNS):
        lo, hi = clip_bounds[col]
        train_feats[:, i] = np.clip(train_feats[:, i], lo, hi)

    feature_scaler = RobustScaler()
    feature_scaler.fit(train_feats)

    if verbose:
        print(f"RL data prepared — Train: {len(df_train)} rows | Val: {len(df_val)} rows")

    return df_train, df_val, feature_scaler, clip_bounds


def prepare_multi_symbol_data(
        symbols: list[str] | None = None,
        train_ratio: float = 0.8,
) -> dict:
    """Prepare per-symbol data for parallel environments.

    Args:
        symbols: List of symbols. None = use all from config.
        train_ratio: Fraction for training.

    Returns:
        Dict with keys:
            - "train_dfs": Dict[symbol, DataFrame]
            - "val_dfs": Dict[symbol, DataFrame]
            - "feature_scaler": Single RobustScaler fitted on all training data.
            - "clip_bounds": Single clip bounds from all training data.
    """
    from config import SYMBOLS

    if symbols is None:
        symbols = [s.replace("/", "_") for s in SYMBOLS]

    # Load all data first for a unified scaler
    all_train_dfs = {}
    all_val_dfs = {}
    all_train_feats = []

    for sym in symbols:
        df = load_symbol(sym, timeframe="6h")
        if "symbol" not in df.columns:
            df["symbol"] = sym.upper().replace("/", "_")
        df = df.sort_index()

        split_idx = int(len(df) * train_ratio)
        df_train = df.iloc[:split_idx].copy()
        df_val = df.iloc[split_idx:].copy()

        all_train_dfs[sym] = df_train
        all_val_dfs[sym] = df_val
        all_train_feats.append(df_train[FEATURE_COLUMNS].values)

    # Unified clip bounds and scaler across all symbols
    combined_feats = np.concatenate(all_train_feats, axis=0)
    clip_bounds = {}
    for i, col in enumerate(FEATURE_COLUMNS):
        lo = np.percentile(combined_feats[:, i], 1.0)
        hi = np.percentile(combined_feats[:, i], 99.0)
        clip_bounds[col] = (lo, hi)
        combined_feats[:, i] = np.clip(combined_feats[:, i], lo, hi)

    feature_scaler = RobustScaler()
    feature_scaler.fit(combined_feats)

    total_train = sum(len(d) for d in all_train_dfs.values())
    total_val = sum(len(d) for d in all_val_dfs.values())
    print(f"Multi-symbol RL data — {len(symbols)} symbols | Train: {total_train} | Val: {total_val}")

    return {
        "train_dfs": all_train_dfs,
        "val_dfs": all_val_dfs,
        "feature_scaler": feature_scaler,
        "clip_bounds": clip_bounds,
    }
