"""
Évaluation spécifique au modèle CNN1D.

Thin wrapper autour de utils.evaluation : gère le chargement du modèle
CNN et de ses scalers, puis délègue les métriques et graphiques au
module d'évaluation générique.
"""

import argparse
import os

import joblib
import torch

from config import DEFAULT_TIMEFRAME, get_timeframe_config
from data.features.pipeline import FEATURE_COLUMNS
from models.cnn.CNN import CNN1D
from models.cnn.data_preparator import prepare_data
from utils.evaluation import run_evaluation


def _get_checkpoint_paths(timeframe: str):
    """Retourne les chemins de checkpoint pour un timeframe donné."""
    checkpoint_dir = f"models/cnn/checkpoints/{timeframe}"
    return {
        "dir": checkpoint_dir,
        "model": os.path.join(checkpoint_dir, "best_model.pth"),
        "scalers": os.path.join(checkpoint_dir, "scalers.joblib"),
        "results": f"models/cnn/results/{timeframe}",
    }


def load_model(model_path: str, device: torch.device, window_size: int = None) -> tuple[CNN1D, dict]:
    """Charge le modèle CNN1D et son historique d'entraînement.

    Args:
        model_path: Chemin vers le checkpoint .pth.
        device: Device cible.
        window_size: Taille de la fenêtre (si None, extrait du checkpoint).

    Returns:
        (model, history) avec le modèle en mode eval.
    """
    checkpoint = torch.load(model_path, weights_only=False, map_location=device)

    # Extract window_size from checkpoint or use default
    if window_size is None:
        window_size = checkpoint.get("window_size", 30)

    model = CNN1D(window_size=window_size, n_features=len(FEATURE_COLUMNS)).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model, checkpoint["history"]


def evaluate(
    symbol: str | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    model_path: str | None = None,
):
    """Évalue le modèle CNN1D et génère les graphiques.

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

    device = torch.device("mps" if torch.mps.is_available() else "cpu")

    print(f"\n{'=' * 60}")
    print(f"  ÉVALUATION CNN1D")
    print(f"  Timeframe: {timeframe}")
    print(f"  Model: {model_path}")
    print(f"{'=' * 60}\n")

    # Get timeframe config for window_size
    tf_config = get_timeframe_config(timeframe)
    window_size = tf_config["window_size"]

    # Charger modèle, données, et scalers
    model, history = load_model(model_path, device, window_size=window_size)
    _, val_loader, _, _ = prepare_data(symbol=symbol, timeframe=timeframe)
    scalers = joblib.load(paths["scalers"])

    # Create results directory for this timeframe
    os.makedirs(paths["results"], exist_ok=True)

    # Déléguer à l'évaluation générique
    run_evaluation(
        model=model,
        dataloader=val_loader,
        target_scaler=scalers["target_scaler"],
        history=history,
        results_dir=paths["results"],
        device=device,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Évaluation CNN1D")
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
