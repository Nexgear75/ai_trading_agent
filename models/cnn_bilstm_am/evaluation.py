"""
Évaluation spécifique au modèle CNN-BiLSTM-AM.

Thin wrapper autour de utils.evaluation : gère le chargement du modèle
CNN-BiLSTM-AM et de ses scalers, puis délègue les métriques et graphiques
au module d'évaluation générique.
"""

import argparse
import os

import joblib
import numpy as np
import torch
from torch.utils.data import TensorDataset, DataLoader

from config import DEFAULT_TIMEFRAME, get_timeframe_config
from data.features.pipeline import FEATURE_COLUMNS, get_feature_columns
from data.preprocessing.builder import build_windows
from models.cnn_bilstm_am.CNN_BiLSTM_AM import CNNBiLSTMAM
from utils.dataset_loader import load_symbol, load_all
from utils.evaluation import run_evaluation


def _get_checkpoint_paths(timeframe: str):
    """Retourne les chemins de checkpoint pour un timeframe donné."""
    checkpoint_dir = f"models/cnn_bilstm_am/checkpoints/{timeframe}"
    return {
        "dir": checkpoint_dir,
        "model": os.path.join(checkpoint_dir, "best_model.pth"),
        "scalers": os.path.join(checkpoint_dir, "scalers.joblib"),
        "results": f"models/cnn_bilstm_am/results/{timeframe}",
    }


def load_model(model_path: str, device: torch.device, window_size: int = None) -> tuple[CNNBiLSTMAM, dict]:
    """Charge le modèle CNN-BiLSTM-AM et son historique d'entraînement.

    Args:
        model_path: Chemin vers le checkpoint .pth.
        device: Device cible.
        window_size: Ignoré — l'architecture est lue depuis le checkpoint.

    Returns:
        (model, history) avec le modèle en mode eval.
    """
    checkpoint = torch.load(model_path, weights_only=False, map_location=device)

    # Reconstruit l'architecture exacte depuis les paramètres sauvegardés
    ckpt_window_size = checkpoint.get("window_size", 30)
    ckpt_n_features = checkpoint.get("n_features", len(FEATURE_COLUMNS))
    ckpt_model_cfg = checkpoint.get("model_cfg", {})

    model = CNNBiLSTMAM(
        window_size=ckpt_window_size,
        n_features=ckpt_n_features,
        **ckpt_model_cfg,
    ).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model, checkpoint["history"]


def evaluate(
    symbol: str | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    model_path: str | None = None,
):
    """Évalue le modèle CNN-BiLSTM-AM et génère les graphiques.

    Args:
        symbol: Symbole évalué (ex: "BTC"). None = toutes les cryptos.
        timeframe: Timeframe du modèle (ex: "1d", "1h", "4h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").
        model_path: Chemin vers le checkpoint. Si None, utilise le chemin
                    par défaut pour le timeframe spécifié.
    """
    # Get paths for this timeframe
    paths = _get_checkpoint_paths(timeframe)

    if model_path is None:
        model_path = paths["model"]
        scalers_path = paths["scalers"]
    else:
        scalers_path = os.path.join(os.path.dirname(model_path), "scalers.joblib")

    device = torch.device("mps" if torch.mps.is_available() else "cpu")

    print(f"\n{'=' * 60}")
    print("  ÉVALUATION CNN-BiLSTM-AM")
    print(f"  Timeframe: {timeframe}")
    print(f"  Model: {model_path}")
    print(f"{'=' * 60}\n")

    tf_config = get_timeframe_config(timeframe)

    # Charger modèle, scalers et clip_bounds du checkpoint
    model, history = load_model(model_path, device)
    scalers = joblib.load(scalers_path)
    feature_scaler = scalers["feature_scaler"]
    target_scaler = scalers["target_scaler"]
    clip_bounds = scalers["clip_bounds"]
    target_clip_bounds = scalers.get("target_clip_bounds")
    if target_clip_bounds is None:
        raise KeyError(
            "Checkpoint missing 'target_clip_bounds'. "
            "Re-train the model to generate a compatible checkpoint."
        )

    # Validation de cohérence du timeframe
    if "timeframe" in scalers and scalers["timeframe"] != timeframe:
        raise ValueError(
            f"Timeframe mismatch: checkpoint trained with '{scalers['timeframe']}' "
            f"but evaluation requested with '{timeframe}'"
        )

    # Charger les données brutes et construire les fenêtres de validation
    # SANS refitter les scalers (utilise ceux du checkpoint)
    config_window_size = tf_config["window_size"]
    persisted_window_size = scalers.get("window_size")
    if persisted_window_size is not None and persisted_window_size != config_window_size:
        raise ValueError(
            f"Window size mismatch: checkpoint trained with "
            f"window_size={persisted_window_size} but config uses "
            f"window_size={config_window_size} for timeframe '{timeframe}'."
        )
    window_size = persisted_window_size if persisted_window_size is not None else config_window_size
    prediction_horizon = tf_config["prediction_horizon"]
    feature_cols = get_feature_columns(timeframe)

    df = load_symbol(symbol, timeframe=timeframe) if symbol else load_all(timeframe=timeframe)
    df["label"] = df.groupby("symbol")["close"].transform(
        lambda c: c.shift(-prediction_horizon) / c - 1
    )
    df = df.dropna(subset=["label"])

    # Fenêtres + split temporel par symbole
    if "train_ratio" not in scalers:
        raise KeyError(
            "Checkpoint missing 'train_ratio'. "
            "Re-train the model to generate a compatible checkpoint."
        )
    train_ratio = scalers["train_ratio"]
    val_X, val_y, val_close = [], [], []
    for _, group in df.groupby("symbol"):
        X_sym, y_sym, _ = build_windows(
            group, window_size=window_size, feature_columns=feature_cols
        )
        close_sym = group["close"].values[window_size:]
        n = len(X_sym)
        split = int(train_ratio * n)
        val_X.append(X_sym[split:])
        val_y.append(y_sym[split:])
        val_close.append(close_sym[split:])

    X_val = np.concatenate(val_X)
    y_val = np.concatenate(val_y)
    close_val = np.concatenate(val_close)

    # Appliquer le clipping + scaling DU CHECKPOINT (pas de refit)
    lo_t, hi_t = target_clip_bounds[0], target_clip_bounds[1]
    y_val = np.clip(y_val, lo_t, hi_t)

    n_val, ws, nf = X_val.shape
    X_val_flat = X_val.reshape(-1, nf)
    lo_f = clip_bounds[:, 0]
    hi_f = clip_bounds[:, 1]
    X_val_flat = np.clip(X_val_flat, lo_f, hi_f)
    X_val = feature_scaler.transform(X_val_flat).reshape(n_val, ws, nf)

    y_val = target_scaler.transform(y_val.reshape(-1, 1)).ravel()

    # Créer un DataLoader pour l'évaluation
    val_ds = TensorDataset(
        torch.tensor(X_val, dtype=torch.float32),
        torch.tensor(y_val, dtype=torch.float32),
    )
    val_loader = DataLoader(val_ds, batch_size=32, shuffle=False, num_workers=0)

    os.makedirs(paths["results"], exist_ok=True)

    # Déléguer à l'évaluation générique
    run_evaluation(
        model=model,
        dataloader=val_loader,
        target_scaler=target_scaler,
        history=history,
        results_dir=paths["results"],
        device=device,
        close_prices=close_val,
        prediction_horizon=prediction_horizon,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Évaluation CNN-BiLSTM-AM")
    parser.add_argument("--symbol", type=str, default=None, help="Symbole (ex: BTC)")
    parser.add_argument("--timeframe", type=str, default=DEFAULT_TIMEFRAME,
                        help=f"Timeframe (défaut: {DEFAULT_TIMEFRAME})")
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Chemin vers le checkpoint (défaut: auto selon timeframe)",
    )
    args = parser.parse_args()

    evaluate(symbol=args.symbol, timeframe=args.timeframe, model_path=args.model_path)
