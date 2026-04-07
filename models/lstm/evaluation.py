"""LSTM evaluation script."""
import argparse
import os
import joblib
import torch
from data.features.pipeline import FEATURE_COLUMNS
from models.lstm.LSTM import LSTMModel
from models.lstm.data_preparator import prepare_data
from utils.evaluation import run_evaluation, run_evaluation_by_crypto

CKPT_DIR = "models/lstm/checkpoints"
MODEL_PATH = os.path.join(CKPT_DIR, "best_model.pth")
SCALER_PATH = os.path.join(CKPT_DIR, "scalers.joblib")
RESULTS_DIR = "models/lstm/results"


def evaluate(sym=None, model_path=MODEL_PATH, hidden=128, layers=2):
    """Evaluate trained LSTM model."""
    dev = torch.device("mps" if torch.mps.is_available() else "cpu")
    print(f"Device: {dev}")

    # Charger les données avec les symboles pour évaluation par crypto
    result = prepare_data(symbol=sym, return_symbols=True)
    _, va_ld, _, _, val_symbols = result

    n_features = len(FEATURE_COLUMNS)
    mdl = LSTMModel(n_features=n_features, hidden=hidden, layers=layers).to(dev)
    ckpt = torch.load(model_path, weights_only=False, map_location=dev)
    mdl.load_state_dict(ckpt["model_state"])
    mdl.eval()
    scalers = joblib.load(SCALER_PATH)

    # Évaluation globale
    metrics = run_evaluation(
        mdl, va_ld, scalers["target_scaler"], ckpt["history"], RESULTS_DIR, dev
    )

    # Évaluation par crypto (si plusieurs cryptos)
    if sym is None:
        metrics_by_crypto = run_evaluation_by_crypto(
            mdl, va_ld, scalers["target_scaler"], val_symbols, RESULTS_DIR, dev
        )
        return metrics, metrics_by_crypto

    return metrics


if __name__ == "__main__":
    pa = argparse.ArgumentParser()
    pa.add_argument("--symbol", type=str, default=None)
    pa.add_argument("--model-path", type=str, default=MODEL_PATH)
    pa.add_argument("--hidden", type=int, default=128)
    pa.add_argument("--layers", type=int, default=2)
    a = pa.parse_args()
    evaluate(a.symbol, a.model_path, a.hidden, a.layers)
