from __future__ import annotations

import numpy as np
from sklearn.preprocessing import RobustScaler, StandardScaler

from config import DEFAULT_TIMEFRAME, get_timeframe_config
from data.features.pipeline import get_feature_columns
from data.preprocessing.builder import build_windows
from utils.dataset_loader import load_symbol, load_all


def prepare_data(
    symbol: str | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    train_ratio: float = 0.8,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray,
           RobustScaler, StandardScaler, np.ndarray, np.ndarray, np.ndarray | None]:
    """Prépare les données tabulaires pour XGBoost.

    Même pipeline que CNN (fenêtres glissantes, clipping, scaling)
    mais aplatit les fenêtres 3D en vecteurs 2D.

    Args:
        symbol: Symbole à charger (ex: "BTC"). None = toutes les cryptos.
        timeframe: Timeframe du dataset (ex: "1d", "1h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").
        train_ratio: Proportion des données pour l'entraînement.

    Returns:
        (X_train, X_val, y_train, y_val,
         feature_scaler, target_scaler, clip_bounds, target_clip_bounds, close_val)
    """
    if not (0 < train_ratio < 1):
        raise ValueError(
            f"Invalid train_ratio={train_ratio}. "
            "Expected a value strictly between 0 and 1."
        )

    tf_config = get_timeframe_config(timeframe)
    window_size = tf_config["window_size"]
    prediction_horizon = tf_config["prediction_horizon"]
    feature_cols = get_feature_columns(timeframe)

    print(f"  [Data Prep] Timeframe: {timeframe}, Window size: {window_size}, "
          f"Horizon: {prediction_horizon}, Features: {len(feature_cols)}")

    df = load_symbol(symbol, timeframe=timeframe) if symbol is not None else load_all(timeframe=timeframe)

    # Calcul du forward return PAR SYMBOLE pour éviter la contamination
    # entre cryptos aux frontières du DataFrame concaténé
    df["label"] = df.groupby("symbol")["close"].transform(
        lambda c: c.shift(-prediction_horizon) / c - 1
    )
    df = df.dropna(subset=["label"])

    # Construction des fenêtres glissantes PAR SYMBOLE
    # Split temporel par symbole puis concaténation pour garantir
    # que train < val en chronologie (même avec multi-symbole)
    train_X, val_X, train_y, val_y, val_close = [], [], [], [], []
    skipped = 0
    for sym_name, group in df.groupby("symbol"):
        X_sym, y_sym, _ = build_windows(
            group, window_size=window_size, feature_columns=feature_cols
        )
        if len(X_sym) == 0:
            skipped += 1
            continue
        n = len(X_sym)
        split = int(train_ratio * n)
        if split == 0 or split == n:
            skipped += 1
            continue
        train_X.append(X_sym[:split])
        val_X.append(X_sym[split:])
        train_y.append(y_sym[:split])
        val_y.append(y_sym[split:])
        if symbol is not None:
            close_sym = group["close"].values[window_size:]
            val_close.append(close_sym[split:])

    if skipped:
        print(f"  {skipped} symbole(s) ignoré(s) (historique insuffisant)")
    if not train_X:
        raise ValueError("No training samples after windowing. Check data availability.")

    X_train_3d = np.concatenate(train_X)
    X_val_3d = np.concatenate(val_X)
    y_train = np.concatenate(train_y)
    y_val = np.concatenate(val_y)
    close_val = np.concatenate(val_close) if symbol is not None else None

    # Aplatir les fenêtres → [n, window × n_features]
    X_train = X_train_3d.reshape(X_train_3d.shape[0], -1)
    X_val = X_val_3d.reshape(X_val_3d.shape[0], -1)

    # Clipping targets (fit sur train uniquement)
    lo, hi = np.percentile(y_train, 1.0), np.percentile(y_train, 99.0)
    target_clip_bounds = np.array([lo, hi])
    y_train = np.clip(y_train, lo, hi)
    y_val = np.clip(y_val, lo, hi)

    # Clipping features (fit sur train uniquement) — vectorisé
    lo_f, hi_f = np.percentile(X_train, [1.0, 99.0], axis=0)
    clip_bounds = np.column_stack((lo_f, hi_f))
    X_train = np.clip(X_train, lo_f, hi_f)
    X_val = np.clip(X_val, lo_f, hi_f)

    # RobustScaler pour les features
    feature_scaler = RobustScaler()
    X_train = feature_scaler.fit_transform(X_train)
    X_val = feature_scaler.transform(X_val)

    # StandardScaler pour les targets
    target_scaler = StandardScaler()
    y_train = target_scaler.fit_transform(y_train.reshape(-1, 1)).ravel()
    y_val = target_scaler.transform(y_val.reshape(-1, 1)).ravel()

    print(f"  Train: {len(X_train)} samples | Val: {len(X_val)} samples")
    print(f"  Features: {X_train.shape[1]} ({window_size} × {len(feature_cols)})")

    return (X_train, X_val, y_train, y_val,
            feature_scaler, target_scaler, clip_bounds, target_clip_bounds, close_val)
