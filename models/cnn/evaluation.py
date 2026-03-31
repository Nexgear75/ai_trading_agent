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

from config import WINDOW_SIZE
from data.features.pipeline import FEATURE_COLUMNS
from models.cnn.CNN import CNN1D
from models.cnn.data_preparator import prepare_data
from utils.evaluation import run_evaluation

CHECKPOINT_DIR = "models/cnn/checkpoints"
SCALERS_PATH = os.path.join(CHECKPOINT_DIR, "scalers.joblib")
RESULTS_DIR = "models/cnn/results"


def load_model(model_path: str, device: torch.device) -> tuple[CNN1D, dict]:
    """Charge le modèle CNN1D et son historique d'entraînement.

    Args:
        model_path: Chemin vers le checkpoint .pth.
        device: Device cible.

    Returns:
        (model, history) avec le modèle en mode eval.
    """
    checkpoint = torch.load(model_path, weights_only=False, map_location=device)
    model = CNN1D(window_size=WINDOW_SIZE, n_features=len(FEATURE_COLUMNS)).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model, checkpoint["history"]


def evaluate(
    symbol: str | None = None,
    model_path: str = os.path.join(CHECKPOINT_DIR, "best_model.pth"),
):
    """Évalue le modèle CNN1D et génère les graphiques.

    Args:
        symbol: Symbole évalué (ex: "BTC"). None = toutes les cryptos.
        model_path: Chemin vers le checkpoint.
    """
    device = torch.device("mps" if torch.mps.is_available() else "cpu")

    # Charger modèle, données, et scalers
    model, history = load_model(model_path, device)
    _, val_loader, _, _ = prepare_data(symbol=symbol)
    scalers = joblib.load(SCALERS_PATH)

    # Déléguer à l'évaluation générique
    run_evaluation(
        model=model,
        dataloader=val_loader,
        target_scaler=scalers["target_scaler"],
        history=history,
        results_dir=RESULTS_DIR,
        device=device,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Évaluation CNN1D")
    parser.add_argument("--symbol", type=str, default=None, help="Symbole (ex: BTC)")
    parser.add_argument(
        "--model-path",
        type=str,
        default=os.path.join(CHECKPOINT_DIR, "best_model.pth"),
    )
    args = parser.parse_args()

    evaluate(symbol=args.symbol, model_path=args.model_path)
