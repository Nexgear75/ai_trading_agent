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
           RobustScaler, StandardScaler, np.ndarray, np.ndarray]:
    """Prépare les données tabulaires pour XGBoost.

    Même pipeline que CNN (fenêtres glissantes, clipping, scaling)
    mais aplatit les fenêtres 3D en vecteurs 2D.

    Args:
        symbol: Symbole à charger (ex: "BTC"). None = toutes les cryptos.
        timeframe: Timeframe du dataset (ex: "1d", "1h", "4h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").
        train_ratio: Proportion des données pour l'entraînement.

    Returns:
        (X_train, X_val, y_train, y_val,
         feature_scaler, target_scaler, clip_bounds, close_val)
    """
    tf_config = get_timeframe_config(timeframe)
    window_size = tf_config["window_size"]
    prediction_horizon = tf_config["prediction_horizon"]
    feature_cols = get_feature_columns(timeframe)

    print(f"  [Data Prep] Timeframe: {timeframe}, Window size: {window_size}, "
          f"Horizon: {prediction_horizon}, Features: {len(feature_cols)}")

    df = load_symbol(symbol, timeframe=timeframe) if symbol else load_all(timeframe=timeframe)

    # Calcul du forward return PAR SYMBOLE pour éviter la contamination
    # entre cryptos aux frontières du DataFrame concaténé
    df["label"] = df.groupby("symbol")["close"].transform(
        lambda c: c.shift(-prediction_horizon) / c - 1
    )
    df = df.dropna(subset=["label"])

    # Construction des fenêtres glissantes PAR SYMBOLE
    all_X, all_y, all_close = [], [], []
    for _, group in df.groupby("symbol"):
        X_sym, y_sym, _ = build_windows(
            group, window_size=window_size, feature_columns=feature_cols
        )
        close_sym = group["close"].values[window_size:]
        all_X.append(X_sym)
        all_y.append(y_sym)
        all_close.append(close_sym)

    X = np.concatenate(all_X)       # shape: [n, window, n_features]
    y = np.concatenate(all_y)
    close_prices = np.concatenate(all_close)

    # Aplatir les fenêtres → [n, window × n_features]
    n_samples = X.shape[0]
    nf = len(feature_cols)
    X_flat = X.reshape(n_samples, -1)

    # Split temporel (pas de shuffle)
    split = int(train_ratio * n_samples)
    X_train, X_val = X_flat[:split], X_flat[split:]
    y_train, y_val = y[:split], y[split:]
    close_val = close_prices[split:]

    # Clipping targets (fit sur train uniquement)
    lo, hi = np.percentile(y_train, 1.0), np.percentile(y_train, 99.0)
    y_train = np.clip(y_train, lo, hi)
    y_val = np.clip(y_val, lo, hi)

    # Clipping features (fit sur train uniquement)
    n_flat_features = X_train.shape[1]
    clip_bounds = np.zeros((n_flat_features, 2))
    for i in range(n_flat_features):
        lo_f = np.percentile(X_train[:, i], 1.0)
        hi_f = np.percentile(X_train[:, i], 99.0)
        clip_bounds[i] = [lo_f, hi_f]
        X_train[:, i] = np.clip(X_train[:, i], lo_f, hi_f)
        X_val[:, i] = np.clip(X_val[:, i], lo_f, hi_f)

    # RobustScaler pour les features
    feature_scaler = RobustScaler()
    X_train = feature_scaler.fit_transform(X_train)
    X_val = feature_scaler.transform(X_val)

    # StandardScaler pour les targets
    target_scaler = StandardScaler()
    y_train = target_scaler.fit_transform(y_train.reshape(-1, 1)).ravel()
    y_val = target_scaler.transform(y_val.reshape(-1, 1)).ravel()

    print(f"  Train: {len(X_train)} samples | Val: {len(X_val)} samples")
    print(f"  Features: {n_flat_features} ({window_size} × {nf})")

    return (X_train, X_val, y_train, y_val,
            feature_scaler, target_scaler, clip_bounds, close_val)
