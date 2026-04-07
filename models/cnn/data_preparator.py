import numpy as np
import torch
from sklearn.preprocessing import RobustScaler, StandardScaler
from torch.utils.data import TensorDataset, DataLoader

from config import DEFAULT_TIMEFRAME, get_timeframe_config
from data.features.pipeline import FEATURE_COLUMNS
from data.preprocessing.builder import build_windows
from utils.dataset_loader import load_symbol, load_all


def _clip_outliers(arr: np.ndarray, lower: float = 1.0, upper: float = 99.0) -> np.ndarray:
    """Winsorize un array aux percentiles donnés."""
    lo = np.percentile(arr, lower)
    hi = np.percentile(arr, upper)
    return np.clip(arr, lo, hi)


def prepare_data(
    symbol: str | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    train_ratio: float = 0.8,
    batch_size: int = 32,
) -> tuple[DataLoader, DataLoader, RobustScaler, StandardScaler, np.ndarray]:
    """Prépare les DataLoaders d'entraînement et de validation.

    Args:
        symbol: Symbole à charger (ex: "BTC"). None = toutes les cryptos.
        timeframe: Timeframe du dataset (ex: "1d", "1h", "4h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").
        train_ratio: Proportion des données pour l'entraînement.
        batch_size: Taille des batchs.

    Returns:
        (train_loader, val_loader, feature_scaler, target_scaler, clip_bounds)
    """
    # Get timeframe-specific configuration
    tf_config = get_timeframe_config(timeframe)
    window_size = tf_config["window_size"]
    prediction_horizon = tf_config["prediction_horizon"]

    print(f"  [Data Prep] Timeframe: {timeframe}, Window size: {window_size}, Horizon: {prediction_horizon}")

    df = load_symbol(symbol, timeframe=timeframe) if symbol else load_all(timeframe=timeframe)

    # Calcul du forward return PAR SYMBOLE pour éviter la contamination
    # entre cryptos aux frontières du DataFrame concaténé
    df["label"] = df.groupby("symbol")["close"].transform(
        lambda c: c.shift(-prediction_horizon) / c - 1
    )
    df = df.dropna(subset=["label"])

    # Construction des fenêtres glissantes PAR SYMBOLE
    # pour ne jamais créer de fenêtre à cheval sur deux cryptos
    all_X, all_y = [], []
    for _, group in df.groupby("symbol"):
        X_sym, y_sym, _ = build_windows(group, window_size=window_size)
        all_X.append(X_sym)
        all_y.append(y_sym)
    X = np.concatenate(all_X)
    y = np.concatenate(all_y)

    # Vérification NaN
    nan_x, nan_y = np.isnan(X).sum(), np.isnan(y).sum()
    if nan_x > 0 or nan_y > 0:
        print(f"Warning: NaN détectés (X: {nan_x}, y: {nan_y})")

    # Split temporel (pas de shuffle pour respecter l'ordre chronologique)
    split = int(train_ratio * len(X))
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    # Clipping des outliers sur les targets (winsorize 1er/99e percentile)
    # Fitté sur train uniquement, appliqué à train et val
    lo = np.percentile(y_train, 1.0)
    hi = np.percentile(y_train, 99.0)
    y_train = np.clip(y_train, lo, hi)
    y_val = np.clip(y_val, lo, hi)

    # Clipping des outliers sur les features (par feature, sur train)
    n_train, ws, nf = X_train.shape
    n_val = X_val.shape[0]
    X_train_flat = X_train.reshape(-1, nf)
    X_val_flat = X_val.reshape(-1, nf)
    clip_bounds = np.zeros((nf, 2))
    for i in range(nf):
        lo_f = np.percentile(X_train_flat[:, i], 1.0)
        hi_f = np.percentile(X_train_flat[:, i], 99.0)
        clip_bounds[i] = [lo_f, hi_f]
        X_train_flat[:, i] = np.clip(X_train_flat[:, i], lo_f, hi_f)
        X_val_flat[:, i] = np.clip(X_val_flat[:, i], lo_f, hi_f)

    # RobustScaler (median/IQR) pour les features — insensible aux outliers restants
    feature_scaler = RobustScaler()
    X_train = feature_scaler.fit_transform(X_train_flat).reshape(n_train, ws, nf)
    X_val = feature_scaler.transform(X_val_flat).reshape(n_val, ws, nf)

    # StandardScaler pour les targets (returns centrés ~0)
    target_scaler = StandardScaler()
    y_train = target_scaler.fit_transform(y_train.reshape(-1, 1)).ravel()
    y_val = target_scaler.transform(y_val.reshape(-1, 1)).ravel()

    # Conversion en tenseurs PyTorch
    train_ds = TensorDataset(
        torch.tensor(X_train, dtype=torch.float32),
        torch.tensor(y_train, dtype=torch.float32),
    )
    val_ds = TensorDataset(
        torch.tensor(X_val, dtype=torch.float32),
        torch.tensor(y_val, dtype=torch.float32),
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    print(f"Train: {len(train_ds)} samples | Val: {len(val_ds)} samples")

    return train_loader, val_loader, feature_scaler, target_scaler, clip_bounds
