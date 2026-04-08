"""
Évaluation spécifique au modèle XGBoost.

Réutilise les fonctions de métriques et de plots de utils.evaluation,
mais sans passer par run_evaluation (couplé à PyTorch).
"""

from __future__ import annotations

import argparse
import os

import joblib
import xgboost as xgb

from config import DEFAULT_TIMEFRAME, get_timeframe_config
from models.xgboost.data_preparator import prepare_data
from utils.evaluation import (
    compute_metrics,
    plot_predictions_vs_actual,
    plot_scatter,
    plot_residuals,
    plot_price_vs_predicted,
    plot_direction_accuracy,
)


def _get_checkpoint_paths(timeframe: str):
    """Retourne les chemins de checkpoint pour un timeframe donné."""
    checkpoint_dir = f"models/xgboost/checkpoints/{timeframe}"
    return {
        "dir": checkpoint_dir,
        "model": os.path.join(checkpoint_dir, "best_model.json"),
        "scalers": os.path.join(checkpoint_dir, "scalers.joblib"),
        "results": f"models/xgboost/results/{timeframe}",
    }


def load_model(model_path: str) -> xgb.XGBRegressor:
    """Charge le modèle XGBoost depuis un fichier JSON.

    Args:
        model_path: Chemin vers le fichier best_model.json.

    Returns:
        Modèle XGBRegressor chargé.
    """
    model = xgb.XGBRegressor()
    model.load_model(model_path)
    return model


def evaluate(
    symbol: str | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    model_path: str | None = None,
):
    """Évalue le modèle XGBoost et génère les graphiques.

    Args:
        symbol: Symbole évalué (ex: "BTC"). None = toutes les cryptos.
        timeframe: Timeframe du modèle (ex: "1d", "1h", "4h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").
        model_path: Chemin vers le checkpoint. Si None, utilise le chemin
                    par défaut pour le timeframe spécifié.
    """
    paths = _get_checkpoint_paths(timeframe)
    if model_path is None:
        model_path = paths["model"]

    tf_config = get_timeframe_config(timeframe)
    os.makedirs(paths["results"], exist_ok=True)

    print(f"\n{'=' * 60}")
    print("  ÉVALUATION XGBOOST")
    print(f"  Timeframe: {timeframe}")
    print(f"  Model: {model_path}")
    print(f"{'=' * 60}\n")

    # Charger modèle et données
    model = load_model(model_path)
    _, X_val, _, y_val, _, _, _, close_val = prepare_data(
        symbol=symbol, timeframe=timeframe
    )
    scalers = joblib.load(paths["scalers"])
    target_scaler = scalers["target_scaler"]

    # Prédictions
    preds_scaled = model.predict(X_val)
    preds = target_scaler.inverse_transform(preds_scaled.reshape(-1, 1)).ravel()
    actuals = target_scaler.inverse_transform(y_val.reshape(-1, 1)).ravel()

    # Métriques
    metrics = compute_metrics(actuals, preds)
    print("  Métriques :")
    for name, value in metrics.items():
        print(f"    {name}: {value:.6f}")

    # Graphiques
    plot_predictions_vs_actual(actuals, preds, paths["results"])
    plot_scatter(actuals, preds, paths["results"])
    plot_residuals(actuals, preds, paths["results"])
    plot_direction_accuracy(actuals, preds, paths["results"])

    if close_val is not None:
        plot_price_vs_predicted(
            close_val, actuals, preds,
            prediction_horizon=tf_config["prediction_horizon"],
            save_path=paths["results"],
        )

    print(f"\n  Graphiques → {paths['results']}/")

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Évaluation XGBoost")
    parser.add_argument("--symbol", type=str, default=None,
                        help="Symbole (ex: BTC). None = toutes les cryptos.")
    parser.add_argument("--timeframe", type=str, default=DEFAULT_TIMEFRAME,
                        help=f"Timeframe (défaut: {DEFAULT_TIMEFRAME})")
    parser.add_argument("--model-path", type=str, default=None,
                        help="Chemin vers le checkpoint (défaut: auto selon timeframe)")
    args = parser.parse_args()

    evaluate(symbol=args.symbol, timeframe=args.timeframe, model_path=args.model_path)
