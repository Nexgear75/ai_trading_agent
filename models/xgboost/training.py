import argparse
import os

import joblib
import xgboost as xgb

from config import DEFAULT_TIMEFRAME, get_timeframe_config
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


def train(
    symbol: str | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    n_estimators: int = 1000,
    max_depth: int = 6,
    learning_rate: float = 0.05,
    early_stopping_rounds: int = 50,
):
    """Entraîne le modèle XGBoost.

    Args:
        symbol: Symbole à utiliser (ex: "BTC"). None = toutes les cryptos.
        timeframe: Timeframe pour l'entraînement (ex: "1d", "1h", "4h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").
        n_estimators: Nombre maximum d'arbres.
        max_depth: Profondeur maximale des arbres.
        learning_rate: Taux d'apprentissage (shrinkage).
        early_stopping_rounds: Arrêt si pas d'amélioration pendant N rounds.
    """
    tf_config = get_timeframe_config(timeframe)
    feature_cols = get_feature_columns(timeframe)
    paths = _get_checkpoint_paths(timeframe)
    os.makedirs(paths["dir"], exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"  ENTRAÎNEMENT XGBOOST")
    print(f"  Timeframe: {timeframe}  |  Features (flat): "
          f"{tf_config['window_size']} × {len(feature_cols)}")
    print(f"  n_estimators: {n_estimators}  |  max_depth: {max_depth}  |  "
          f"lr: {learning_rate}")
    print(f"  Checkpoint: {paths['dir']}")
    print(f"{'=' * 60}\n")

    X_train, X_val, y_train, y_val, feature_scaler, target_scaler, clip_bounds, _ = (
        prepare_data(symbol=symbol, timeframe=timeframe)
    )

    model = xgb.XGBRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        objective="reg:squarederror",
        tree_method="hist",
        random_state=42,
        early_stopping_rounds=early_stopping_rounds,
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
        "timeframe": timeframe,
        "window_size": tf_config["window_size"],
        "n_features": len(feature_cols),
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
    parser.add_argument("--n-estimators", type=int, default=1000)
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--lr", type=float, default=0.05)
    parser.add_argument("--early-stopping", type=int, default=50)
    args = parser.parse_args()

    train(
        symbol=args.symbol,
        timeframe=args.timeframe,
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        learning_rate=args.lr,
        early_stopping_rounds=args.early_stopping,
    )
