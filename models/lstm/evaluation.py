"""LSTM evaluation script."""
import argparse
import os

import joblib
import torch

from config import DEFAULT_TIMEFRAME, get_timeframe_config
from data.features.pipeline import get_feature_columns
from models.lstm.LSTM import LSTMModel
from models.lstm.data_preparator import prepare_data
from utils.evaluation import run_evaluation

RESULTS_BASE = "models/lstm/results"


def _get_checkpoint_paths(timeframe: str) -> dict:
    checkpoint_dir = f"models/lstm/checkpoints/{timeframe}"
    return {
        "model": os.path.join(checkpoint_dir, "best_model.pth"),
        "scalers": os.path.join(checkpoint_dir, "scalers.joblib"),
        "results": os.path.join(RESULTS_BASE, timeframe),
    }


def load_model(model_path: str, device: torch.device) -> tuple[LSTMModel, dict]:
    """Charge le modèle LSTM et son historique depuis un checkpoint.

    L'architecture est lue directement depuis le checkpoint.
    """
    checkpoint = torch.load(model_path, weights_only=False, map_location=device)
    model = LSTMModel(
        n_features=checkpoint.get("n_features", len(get_feature_columns())),
        hidden=checkpoint.get("hidden", 128),
        layers=checkpoint.get("layers", 2),
    ).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model, checkpoint["history"]


def evaluate(
    symbol: str | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    model_path: str | None = None,
):
    """Évalue le modèle LSTM et génère les graphiques.

    Args:
        symbol: Symbole évalué (ex: "BTC"). None = toutes les cryptos.
        timeframe: Timeframe du modèle (ex: "1d", "1h", "4h").
        model_path: Chemin vers le checkpoint. Si None, utilise le chemin
                    par défaut pour le timeframe spécifié.
    """
    paths = _get_checkpoint_paths(timeframe)
    if model_path is None:
        model_path = paths["model"]

    device = torch.device("mps" if torch.mps.is_available() else "cpu")

    print(f"\n{'=' * 60}")
    print(f"  ÉVALUATION LSTM")
    print(f"  Timeframe: {timeframe}")
    print(f"  Model: {model_path}")
    print(f"{'=' * 60}\n")

    tf_config = get_timeframe_config(timeframe)

    model, history = load_model(model_path, device)
    _, val_loader, _, _, _, close_val = prepare_data(symbol=symbol, timeframe=timeframe)
    scalers = joblib.load(paths["scalers"])

    os.makedirs(paths["results"], exist_ok=True)

    run_evaluation(
        model=model,
        dataloader=val_loader,
        target_scaler=scalers["target_scaler"],
        history=history,
        results_dir=paths["results"],
        device=device,
        close_prices=close_val,
        prediction_horizon=tf_config["prediction_horizon"],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Évaluation LSTM")
    parser.add_argument("--symbol", type=str, default=None)
    parser.add_argument("--timeframe", type=str, default=DEFAULT_TIMEFRAME)
    parser.add_argument("--model-path", type=str, default=None)
    args = parser.parse_args()

    evaluate(symbol=args.symbol, timeframe=args.timeframe, model_path=args.model_path)
