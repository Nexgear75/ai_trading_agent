"""
Évaluation spécifique au modèle PatchTST.

Thin wrapper autour de utils.evaluation : gère le chargement du modèle
PatchTST et de ses scalers, puis délègue les métriques et graphiques
au module d'évaluation générique.
"""

from __future__ import annotations

import argparse
import os

import numpy as np
import torch
from torch.utils.data import TensorDataset, DataLoader

from config import DEFAULT_TIMEFRAME, get_timeframe_config
from models.patch_tst.PatchTST import PatchTST
from utils.evaluation import build_val_from_checkpoint, run_evaluation


def _get_checkpoint_paths(timeframe: str):
    """Retourne les chemins de checkpoint pour un timeframe donné."""
    checkpoint_dir = f"models/patch_tst/checkpoints/{timeframe}"
    return {
        "dir": checkpoint_dir,
        "model": os.path.join(checkpoint_dir, "best_model.pth"),
        "scalers": os.path.join(checkpoint_dir, "scalers.joblib"),
        "results": f"models/patch_tst/results/{timeframe}",
    }


def load_model(model_path: str, device: torch.device) -> tuple[PatchTST, dict]:
    """Charge le modèle PatchTST et son historique d'entraînement.

    Args:
        model_path: Chemin vers le checkpoint .pth.
        device: Device cible.

    Returns:
        (model, history) avec le modèle en mode eval.
    """
    checkpoint = torch.load(model_path, weights_only=False, map_location=device)

    # Reconstruit l'architecture exacte depuis les paramètres sauvegardés
    required_keys = ("model_state", "history", "window_size", "n_features", "patchtst_cfg")
    missing = [k for k in required_keys if k not in checkpoint]
    if missing:
        raise KeyError(
            f"Checkpoint missing required key(s): {', '.join(missing)}. "
            "Re-train the model to generate a compatible checkpoint."
        )
    ckpt_window_size = checkpoint["window_size"]
    ckpt_n_features = checkpoint["n_features"]
    ckpt_patchtst_cfg = checkpoint["patchtst_cfg"]

    model = PatchTST(
        window_size=ckpt_window_size,
        n_features=ckpt_n_features,
        **ckpt_patchtst_cfg,
    ).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model, checkpoint["history"]


def evaluate(
    symbol: str | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    model_path: str | None = None,
):
    """Évalue le modèle PatchTST et génère les graphiques.

    Charge les scalers/clip_bounds du checkpoint pour appliquer la même
    préproc que l'entraînement (pas de refit).

    Args:
        symbol: Symbole évalué (ex: "BTC"). None = toutes les cryptos.
        timeframe: Timeframe du modèle (ex: "1d", "1h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").
        model_path: Chemin vers le checkpoint. Si None, utilise le chemin
                    par défaut pour le timeframe spécifié.
    """
    paths = _get_checkpoint_paths(timeframe)
    if model_path is None:
        model_path = paths["model"]
        scalers_path = paths["scalers"]
    else:
        scalers_path = os.path.join(os.path.dirname(model_path), "scalers.joblib")

    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")

    print(f"\n{'=' * 60}")
    print("  ÉVALUATION PatchTST")
    print(f"  Timeframe: {timeframe}")
    print(f"  Model: {model_path}")
    print(f"{'=' * 60}\n")

    tf_config = get_timeframe_config(timeframe)

    # Charger modèle
    model, history = load_model(model_path, device)

    # Charger scalers du checkpoint et construire les fenêtres de validation
    # SANS refitter les scalers (utilise ceux du checkpoint)
    X_val, y_val, close_val, scalers, prediction_horizon = build_val_from_checkpoint(
        scalers_path, timeframe, tf_config, symbol
    )

    # Vérifier la compatibilité des dimensions features
    expected_nf = scalers["clip_bounds"].shape[0]
    if X_val.shape[2] != expected_nf:
        raise ValueError(
            f"Feature dimension mismatch: checkpoint expects {expected_nf} features "
            f"but data has {X_val.shape[2]}. Check timeframe/feature pipeline."
        )

    feature_scaler = scalers["feature_scaler"]
    target_scaler = scalers["target_scaler"]
    clip_bounds = scalers["clip_bounds"]
    target_clip_bounds = scalers["target_clip_bounds"]

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

    # Create results directory for this timeframe
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
    parser = argparse.ArgumentParser(description="Évaluation PatchTST")
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