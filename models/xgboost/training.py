from __future__ import annotations

import argparse
import os

import joblib
import xgboost as xgb

from config import DEFAULT_TIMEFRAME, get_timeframe_config, get_xgboost_config
from data.features.pipeline import get_feature_columns
from models.xgboost.data_preparator import prepare_data


def _get_checkpoint_paths(timeframe: str):
    """Retourne les chemins de checkpoint pour un timeframe donné."""
    checkpoint_dir = f"models/xgboost/checkpoints/{timeframe}"
    return {
        "dir": checkpoint_dir,
        "model": os.path.join(checkpoint_dir, "best_model.json"),
        "scalers": os.path.join(checkpoint_dir, "scalers.joblib"),
    }


DEFAULT_SEED = 42


def train(
    symbol: str | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    seed: int = DEFAULT_SEED,
):
    """Entraîne le modèle XGBoost.

    Les hyperparamètres sont lus depuis config.py (XGBOOST_CONFIGS)
    pour chaque timeframe.

    Args:
        symbol: Symbole à utiliser (ex: "BTC"). None = toutes les cryptos.
        timeframe: Timeframe pour l'entraînement (ex: "1d", "1h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").
        seed: Seed pour la reproductibilité (numpy, xgboost).
    """
    tf_config = get_timeframe_config(timeframe)
    xgb_cfg = get_xgboost_config(timeframe)
    feature_cols = get_feature_columns(timeframe)
    paths = _get_checkpoint_paths(timeframe)
    os.makedirs(paths["dir"], exist_ok=True)

    print(f"\n{'=' * 60}")
    print("  ENTRAÎNEMENT XGBOOST")
    print(f"  Timeframe: {timeframe}  |  Features (flat): "
          f"{tf_config['window_size']} × {len(feature_cols)}")
    print(f"  n_estimators: {xgb_cfg['n_estimators']}  |  "
          f"max_depth: {xgb_cfg['max_depth']}  |  "
          f"lr: {xgb_cfg['learning_rate']}")
    print(f"  Checkpoint: {paths['dir']}")
    print(f"{'=' * 60}\n")

    train_ratio = 0.8

    X_train, X_val, y_train, y_val, feature_scaler, target_scaler, clip_bounds, target_clip_bounds, _ = (
        prepare_data(symbol=symbol, timeframe=timeframe, train_ratio=train_ratio)
    )

    model = xgb.XGBRegressor(
        n_estimators=xgb_cfg["n_estimators"],
        max_depth=xgb_cfg["max_depth"],
        learning_rate=xgb_cfg["learning_rate"],
        objective="reg:squarederror",
        tree_method="hist",
        random_state=seed,
        early_stopping_rounds=xgb_cfg["early_stopping_rounds"],
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_val, y_val)],
        verbose=50,
    )

    # Sauvegarde modèle
    model.save_model(paths["model"])

    # Sauvegarde scalers et métadonnées
    joblib.dump({
        "feature_scaler": feature_scaler,
        "target_scaler": target_scaler,
        "clip_bounds": clip_bounds,
        "target_clip_bounds": target_clip_bounds,
        "timeframe": timeframe,
        "window_size": tf_config["window_size"],
        "train_ratio": train_ratio,
        "prediction_horizon": tf_config["prediction_horizon"],
        "n_features": len(feature_cols),
        "feature_columns": list(feature_cols),
        "xgb_cfg": xgb_cfg,
        "seed": seed,
        "n_train_samples": len(X_train),
        "n_val_samples": len(X_val),
    }, paths["scalers"])

    print(f"\nBest iteration: {model.best_iteration}")
    print(f"Best val score: {model.best_score:.6f}")
    print(f"Model saved → {paths['model']}")

    return model, feature_scaler, target_scaler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entraînement XGBoost")
    parser.add_argument("--symbol", type=str, default=None,
                        help="Symbole (ex: BTC). None = toutes les cryptos.")
    parser.add_argument("--timeframe", type=str, default=DEFAULT_TIMEFRAME,
                        help=f"Timeframe (défaut: {DEFAULT_TIMEFRAME})")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed")
    args = parser.parse_args()

    train(symbol=args.symbol, timeframe=args.timeframe, seed=args.seed)
