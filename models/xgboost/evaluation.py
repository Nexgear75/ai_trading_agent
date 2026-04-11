"""
Évaluation spécifique au modèle XGBoost.

Réutilise les fonctions de métriques et de plots de utils.evaluation,
mais sans passer par run_evaluation (couplé à PyTorch).
"""

from __future__ import annotations

import argparse
import os

import joblib
import numpy as np
import xgboost as xgb

from config import DEFAULT_TIMEFRAME, get_timeframe_config
from data.features.pipeline import get_feature_columns
from data.preprocessing.builder import build_windows
from utils.dataset_loader import load_symbol, load_all
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

    Charge les scalers/clip_bounds du checkpoint pour appliquer la même
    préproc que l'entraînement (pas de refit).

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
        scalers_path = paths["scalers"]
    else:
        # Dériver le chemin des scalers depuis le model_path
        scalers_path = os.path.join(os.path.dirname(model_path), "scalers.joblib")

    tf_config = get_timeframe_config(timeframe)
    results_dir = paths["results"]
    os.makedirs(results_dir, exist_ok=True)

    print(f"\n{'=' * 60}")
    print("  ÉVALUATION XGBOOST")
    print(f"  Timeframe: {timeframe}")
    print(f"  Model: {model_path}")
    print(f"{'=' * 60}\n")

    # Charger modèle et scalers du checkpoint
    model = load_model(model_path)
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
    skipped = 0
    for sym_name, group in df.groupby("symbol"):
        X_sym, y_sym, _ = build_windows(
            group, window_size=window_size, feature_columns=feature_cols
        )
        if len(X_sym) == 0:
            skipped += 1
            continue
        close_sym = group["close"].values[window_size:]
        n = len(X_sym)
        split = int(train_ratio * n)
        val_X.append(X_sym[split:])
        val_y.append(y_sym[split:])
        val_close.append(close_sym[split:])

    if skipped:
        print(f"  {skipped} symbole(s) ignoré(s) (historique insuffisant)")
    if not val_X:
        raise ValueError("No validation samples after windowing. Check data availability.")

    X_val = np.concatenate(val_X).reshape(-1, window_size * len(feature_cols))
    y_val = np.concatenate(val_y)
    close_val = np.concatenate(val_close)

    # Appliquer le clipping + scaling DU CHECKPOINT (pas de refit)
    lo_f = clip_bounds[:, 0]
    hi_f = clip_bounds[:, 1]
    X_val = np.clip(X_val, lo_f, hi_f)
    X_val = feature_scaler.transform(X_val)

    lo_t, hi_t = target_clip_bounds[0], target_clip_bounds[1]
    y_val = np.clip(y_val, lo_t, hi_t)
    y_val = target_scaler.transform(y_val.reshape(-1, 1)).ravel()

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
    plot_predictions_vs_actual(actuals, preds, results_dir)
    plot_scatter(actuals, preds, results_dir)
    plot_residuals(actuals, preds, results_dir)
    plot_direction_accuracy(actuals, preds, results_dir)

    if close_val is not None:
        plot_price_vs_predicted(
            close_val, actuals, preds,
            prediction_horizon=prediction_horizon,
            save_path=results_dir,
        )

    print(f"\n  Graphiques → {results_dir}/")

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
