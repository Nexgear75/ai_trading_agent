from __future__ import annotations

import gc

import numpy as np
import torch
from sklearn.preprocessing import RobustScaler, StandardScaler
from torch.utils.data import TensorDataset, DataLoader

from config import DEFAULT_TIMEFRAME, get_timeframe_config
from data.features.pipeline import get_feature_columns
from data.preprocessing.builder import build_windows
from utils.dataset_loader import load_symbol, load_all


def prepare_data(
    symbol: str | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    train_ratio: float = 0.8,
    batch_size: int = 32,
) -> tuple[DataLoader, DataLoader, RobustScaler, StandardScaler, np.ndarray, np.ndarray, np.ndarray | None]:
    """Prépare les DataLoaders d'entraînement et de validation.

    Args:
        symbol: Symbole à charger (ex: "BTC"). None = toutes les cryptos.
        timeframe: Timeframe du dataset (ex: "1d", "1h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").
        train_ratio: Proportion des données pour l'entraînement.
        batch_size: Taille des batchs.

    Returns:
        (train_loader, val_loader, feature_scaler, target_scaler,
         clip_bounds, target_clip_bounds, close_val)
    """
    if not (0 < train_ratio < 1):
        raise ValueError(
            f"Invalid train_ratio={train_ratio}. "
            "Expected a value strictly between 0 and 1."
        )

    # Get timeframe-specific configuration
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
    train_X, val_X, train_y, val_y = [], [], [], []
    val_close_list = []
    skipped = 0
    for _, group in df.groupby("symbol"):
        X_sym, y_sym, _ = build_windows(group, window_size=window_size,
                                        feature_columns=feature_cols)
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
            val_close_list.append(close_sym[split:])

    if skipped:
        print(f"  {skipped} symbole(s) ignoré(s) (historique insuffisant)")
    if not train_X:
        raise ValueError("No training samples after windowing. Check data availability.")

    X_train = np.concatenate(train_X)
    X_val = np.concatenate(val_X)
    y_train = np.concatenate(train_y)
    y_val = np.concatenate(val_y)
    close_val = np.concatenate(val_close_list) if symbol is not None else None

    # Clipping des outliers sur les targets (winsorize 1er/99e percentile)
    # Fitté sur train uniquement, appliqué à train et val
    lo = np.percentile(y_train, 1.0)
    hi = np.percentile(y_train, 99.0)
    target_clip_bounds = np.array([lo, hi])
    y_train = np.clip(y_train, lo, hi)
    y_val = np.clip(y_val, lo, hi)

    # Clipping des outliers sur les features (par feature, sur train) — vectorisé
    n_train, ws, nf = X_train.shape
    n_val = X_val.shape[0]
    X_train_flat = X_train.reshape(-1, nf)
    X_val_flat = X_val.reshape(-1, nf)
    lo_f, hi_f = np.percentile(X_train_flat, [1.0, 99.0], axis=0)
    clip_bounds = np.column_stack((lo_f, hi_f))
    X_train_flat = np.clip(X_train_flat, lo_f, hi_f)
    X_val_flat = np.clip(X_val_flat, lo_f, hi_f)

    # RobustScaler (median/IQR) pour les features — insensible aux outliers restants
    feature_scaler = RobustScaler()
    X_train = feature_scaler.fit_transform(X_train_flat).reshape(n_train, ws, nf)
    X_val = feature_scaler.transform(X_val_flat).reshape(n_val, ws, nf)

    # StandardScaler pour les targets (returns centrés ~0)
    target_scaler = StandardScaler()
    y_train = target_scaler.fit_transform(y_train.reshape(-1, 1)).ravel()
    y_val = target_scaler.transform(y_val.reshape(-1, 1)).ravel()

    # Libération mémoire des arrays intermédiaires
    del X_train_flat, X_val_flat
    gc.collect()

    # Vérification NaN
    nan_x = np.isnan(X_train).sum() + np.isnan(X_val).sum()
    nan_y = np.isnan(y_train).sum() + np.isnan(y_val).sum()
    if nan_x > 0 or nan_y > 0:
        print(f"Warning: NaN détectés (X: {nan_x}, y: {nan_y})")

    # Conversion en tenseurs PyTorch
    train_ds = TensorDataset(
        torch.tensor(X_train, dtype=torch.float32),
        torch.tensor(y_train, dtype=torch.float32),
    )
    val_ds = TensorDataset(
        torch.tensor(X_val, dtype=torch.float32),
        torch.tensor(y_val, dtype=torch.float32),
    )

    # Libération des arrays numpy originaux
    del X_train, X_val, y_train, y_val
    gc.collect()

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    print(f"Train: {len(train_ds)} samples | Val: {len(val_ds)} samples")

    return train_loader, val_loader, feature_scaler, target_scaler, clip_bounds, target_clip_bounds, close_val
