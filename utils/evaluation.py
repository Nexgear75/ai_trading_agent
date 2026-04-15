"""
Module d'évaluation générique pour tous les modèles du projet.

Fournit des métriques de régression, des graphiques de diagnostic,
et un orchestrateur `run_evaluation` réutilisable par n'importe quel
modèle (CNN, LSTM, GRU, Transformer, etc.).
"""

from __future__ import annotations

import os

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def predict(
    model: nn.Module, dataloader: torch.utils.data.DataLoader, device: torch.device
) -> tuple[np.ndarray, np.ndarray]:
    """Génère les prédictions sur un DataLoader.

    Args:
        model: Modèle PyTorch (déjà en mode eval).
        dataloader: DataLoader contenant (X, y).
        device: Device sur lequel exécuter le modèle.

    Returns:
        (predictions, targets) en arrays numpy.
    """
    all_preds, all_targets = [], []
    with torch.no_grad():
        for X_batch, y_batch in dataloader:
            preds = model(X_batch.to(device))
            all_preds.append(preds.cpu().numpy())
            all_targets.append(y_batch.numpy())
    return np.concatenate(all_preds), np.concatenate(all_targets)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Calcule les métriques de régression + direction accuracy.

    Args:
        y_true: Valeurs réelles (inverse-transformées).
        y_pred: Valeurs prédites (inverse-transformées).

    Returns:
        Dict avec MSE, RMSE, MAE, R², Direction Accuracy.
    """
    mse = mean_squared_error(y_true, y_pred)
    direction_true = np.sign(y_true)
    direction_pred = np.sign(y_pred)
    direction_acc = np.mean(direction_true == direction_pred)

    return {
        "MSE": mse,
        "RMSE": np.sqrt(mse),
        "MAE": mean_absolute_error(y_true, y_pred),
        "R²": r2_score(y_true, y_pred),
        "Direction Accuracy": direction_acc,
    }


# ----- Plotting functions ----- #


def plot_training_curves(history: dict, save_path: str):
    """Courbes de loss train/val."""
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(history["train_loss"], label="Train")
    ax.plot(history["val_loss"], label="Validation")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("MSE Loss")
    ax.set_title("Training & Validation Loss")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(save_path, "training_curves.png"), dpi=150)
    plt.close(fig)


def plot_predictions_vs_actual(
    y_true: np.ndarray, y_pred: np.ndarray, save_path: str
):
    """Prédictions vs valeurs réelles sur la timeline."""
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(y_true, label="Actual", linewidth=1)
    ax.plot(y_pred, label="Predicted", alpha=0.7, linewidth=1)
    ax.set_xlabel("Sample")
    ax.set_ylabel("Forward Return")
    ax.set_title("Predicted vs Actual")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(save_path, "predictions_vs_actual.png"), dpi=150)
    plt.close(fig)


def plot_scatter(y_true: np.ndarray, y_pred: np.ndarray, save_path: str):
    """Scatter plot prédictions vs réel avec ligne de régression parfaite."""
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(y_true, y_pred, alpha=0.3, s=10)
    limits = [
        min(y_true.min(), y_pred.min()),
        max(y_true.max(), y_pred.max()),
    ]
    ax.plot(limits, limits, "r--", linewidth=1, label="Perfect prediction")
    ax.set_xlabel("Actual")
    ax.set_ylabel("Predicted")
    ax.set_title("Scatter: Predicted vs Actual")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(os.path.join(save_path, "scatter.png"), dpi=150)
    plt.close(fig)


def plot_residuals(y_true: np.ndarray, y_pred: np.ndarray, save_path: str):
    """Distribution des résidus (erreurs de prédiction)."""
    residuals = y_true - y_pred

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    # Histogramme
    axes[0].hist(residuals, bins=50, edgecolor="black", alpha=0.7)
    axes[0].axvline(0, color="r", linestyle="--")
    axes[0].set_xlabel("Residual (actual - predicted)")
    axes[0].set_ylabel("Frequency")
    axes[0].set_title("Residuals Distribution")

    # Résidus vs index (détecte les biais temporels)
    axes[1].scatter(range(len(residuals)), residuals, alpha=0.3, s=10)
    axes[1].axhline(0, color="r", linestyle="--")
    axes[1].set_xlabel("Sample")
    axes[1].set_ylabel("Residual")
    axes[1].set_title("Residuals Over Time")

    fig.tight_layout()
    fig.savefig(os.path.join(save_path, "residuals.png"), dpi=150)
    plt.close(fig)


def plot_price_vs_predicted(
    close_prices: np.ndarray,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    prediction_horizon: int,
    save_path: str,
):
    """Prix réel vs prix prédit par le modèle.

    Pour chaque sample t, le modèle prédit le return à horizon h.
    On reconstruit : predicted_price[t] = close[t] * (1 + predicted_return[t])
    et on compare à : actual_price[t] = close[t] * (1 + actual_return[t]).

    Args:
        close_prices: Prix close au moment de chaque prédiction.
        y_true: Forward returns réels (inverse-transformés, en %).
        y_pred: Forward returns prédits (inverse-transformés, en %).
        prediction_horizon: Horizon de prédiction (ex: 3 jours).
        save_path: Dossier de sauvegarde.
    """
    actual_future = close_prices * (1 + y_true)
    predicted_future = close_prices * (1 + y_pred)

    fig, axes = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[3, 1])

    # ----- Panel 1 : Prix réel vs prédit -----
    ax = axes[0]
    ax.plot(actual_future, label="Prix réel (futur)", linewidth=1)
    ax.plot(predicted_future, label="Prix prédit", alpha=0.7, linewidth=1)
    ax.set_ylabel("Prix ($)")
    ax.set_title(f"Prix réel vs prédit (horizon = {prediction_horizon})")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # ----- Panel 2 : Erreur absolue -----
    ax2 = axes[1]
    error = np.abs(actual_future - predicted_future)
    ax2.fill_between(range(len(error)), error, alpha=0.5, color="red")
    ax2.set_xlabel("Sample")
    ax2.set_ylabel("Erreur absolue ($)")
    ax2.set_title("Écart prix réel vs prédit")
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(save_path, "price_vs_predicted.png"), dpi=150)
    plt.close(fig)


def plot_direction_accuracy(
    y_true: np.ndarray, y_pred: np.ndarray, save_path: str
):
    """Rolling direction accuracy (fenêtre glissante de 50 samples)."""
    window = 50
    correct = (np.sign(y_true) == np.sign(y_pred)).astype(float)
    rolling_acc = np.convolve(correct, np.ones(window) / window, mode="valid")

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(rolling_acc, linewidth=1)
    ax.axhline(0.5, color="r", linestyle="--", label="Random (50%)")
    ax.set_xlabel("Sample")
    ax.set_ylabel("Direction Accuracy")
    ax.set_title(f"Rolling Direction Accuracy (window={window})")
    ax.set_ylim(0, 1)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(save_path, "direction_accuracy.png"), dpi=150)
    plt.close(fig)


# ----- Per-crypto plotting functions ----- #


def plot_metrics_by_crypto(metrics_by_symbol: dict, save_path: str):
    """Bar chart des métriques par crypto."""
    symbols = list(metrics_by_symbol.keys())
    metric_names = ["RMSE", "MAE", "R²", "Direction Accuracy"]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for idx, metric in enumerate(metric_names):
        values = [metrics_by_symbol[s][metric] for s in symbols]
        colors = plt.cm.tab10(np.linspace(0, 1, len(symbols)))
        axes[idx].bar(symbols, values, color=colors)
        axes[idx].set_ylabel(metric)
        axes[idx].set_title(f"{metric} par Crypto")
        axes[idx].tick_params(axis="x", rotation=45)
        axes[idx].grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    fig.savefig(os.path.join(save_path, "metrics_by_crypto.png"), dpi=150)
    plt.close(fig)


def plot_predictions_by_crypto(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    symbols: np.ndarray,
    save_path: str,
):
    """Graphique predictions vs actual pour chaque crypto (subplots)."""
    unique_symbols = np.unique(symbols)
    n_symbols = len(unique_symbols)
    n_cols = 2
    n_rows = (n_symbols + 1) // 2

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, 4 * n_rows))
    axes = axes.flatten() if n_symbols > 1 else [axes]

    for idx, sym in enumerate(unique_symbols):
        mask = symbols == sym
        ax = axes[idx]
        ax.plot(y_true[mask], label="Actual", linewidth=1, alpha=0.8)
        ax.plot(y_pred[mask], label="Predicted", linewidth=1, alpha=0.7)
        ax.set_title(f"{sym}")
        ax.set_xlabel("Sample")
        ax.set_ylabel("Forward Return")
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)

    # Masquer les axes vides
    for idx in range(n_symbols, len(axes)):
        axes[idx].set_visible(False)

    fig.tight_layout()
    fig.savefig(os.path.join(save_path, "predictions_by_crypto.png"), dpi=150)
    plt.close(fig)


def plot_scatter_by_crypto(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    symbols: np.ndarray,
    save_path: str,
):
    """Scatter plot par crypto avec couleurs différentes."""
    unique_symbols = np.unique(symbols)
    colors = plt.cm.tab10(np.linspace(0, 1, len(unique_symbols)))

    fig, ax = plt.subplots(figsize=(10, 10))

    for idx, sym in enumerate(unique_symbols):
        mask = symbols == sym
        ax.scatter(y_true[mask], y_pred[mask], alpha=0.3, s=10, c=[colors[idx]], label=sym)

    limits = [min(y_true.min(), y_pred.min()), max(y_true.max(), y_pred.max())]
    ax.plot(limits, limits, "r--", linewidth=1, label="Perfect")
    ax.set_xlabel("Actual")
    ax.set_ylabel("Predicted")
    ax.set_title("Scatter par Crypto")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")

    fig.tight_layout()
    fig.savefig(os.path.join(save_path, "scatter_by_crypto.png"), dpi=150)
    plt.close(fig)


def plot_direction_accuracy_by_crypto(metrics_by_symbol: dict, save_path: str):
    """Bar chart de la direction accuracy par crypto avec ligne 50%."""
    symbols = list(metrics_by_symbol.keys())
    values = [metrics_by_symbol[s]["Direction Accuracy"] for s in symbols]
    colors = plt.cm.tab10(np.linspace(0, 1, len(symbols)))

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(symbols, values, color=colors)
    ax.axhline(0.5, color="r", linestyle="--", linewidth=2, label="Random (50%)")
    ax.set_ylabel("Direction Accuracy")
    ax.set_title("Direction Accuracy par Crypto")
    ax.set_ylim(0, 1)
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    # Ajouter les valeurs sur les barres
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{val:.1%}", ha="center", va="bottom", fontsize=9)

    fig.tight_layout()
    fig.savefig(os.path.join(save_path, "direction_accuracy_by_crypto.png"), dpi=150)
    plt.close(fig)


# ----- Checkpoint validation ----- #


def build_val_from_checkpoint(
    scalers_path: str,
    timeframe: str,
    tf_config: dict,
    symbol: str | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict, int]:
    """Validate checkpoint metadata and build raw validation arrays.

    Loads scalers from checkpoint, validates consistency (timeframe,
    window_size, prediction_horizon), then rebuilds validation windows
    from raw data WITHOUT refitting any scaler.

    Args:
        scalers_path: Path to the scalers.joblib checkpoint file.
        timeframe: Requested timeframe (must match checkpoint).
        tf_config: Timeframe config dict (from get_timeframe_config).
        symbol: Symbol to evaluate (e.g. "BTC"). None = all symbols.

    Returns:
        (X_val, y_val, close_val, scalers, prediction_horizon) where
        X_val has shape (n_val, window_size, n_features) — raw, NOT
        clipped or scaled. scalers dict contains all checkpoint artifacts.
    """
    import joblib
    import logging

    from data.features.pipeline import get_feature_columns
    from data.preprocessing.builder import build_windows
    from utils.dataset_loader import load_symbol, load_all

    scalers = joblib.load(scalers_path)

    # Validate checkpoint structure
    if not hasattr(scalers, "get"):
        raise TypeError(
            "Invalid checkpoint format: expected a dict-like object containing "
            "preprocessing artifacts. Re-train the model to generate a compatible "
            "checkpoint."
        )

    required_artifacts = (
        "feature_scaler",
        "target_scaler",
        "clip_bounds",
        "target_clip_bounds",
    )
    missing_artifacts = [key for key in required_artifacts if scalers.get(key) is None]
    if missing_artifacts:
        missing_str = ", ".join(f"'{k}'" for k in missing_artifacts)
        raise KeyError(
            f"Checkpoint missing required preprocessing artifact(s): {missing_str}. "
            "Re-train the model to generate a compatible checkpoint."
        )

    # Validate required metadata
    required_metadata = ("timeframe", "window_size", "prediction_horizon")
    missing_metadata = [key for key in required_metadata if key not in scalers]
    if missing_metadata:
        missing_str = ", ".join(f"'{key}'" for key in missing_metadata)
        raise KeyError(
            f"Checkpoint missing required metadata: {missing_str}. "
            "Re-train the model to generate a compatible checkpoint."
        )

    persisted_timeframe = scalers["timeframe"]
    persisted_window_size = scalers["window_size"]
    persisted_horizon = scalers["prediction_horizon"]

    # Validate timeframe consistency
    if persisted_timeframe != timeframe:
        raise ValueError(
            f"Timeframe mismatch: checkpoint trained with '{persisted_timeframe}' "
            f"but evaluation requested with '{timeframe}'"
        )

    # Validate window_size consistency
    config_window_size = tf_config["window_size"]
    if persisted_window_size != config_window_size:
        raise ValueError(
            f"Window size mismatch: checkpoint trained with "
            f"window_size={persisted_window_size} but config uses "
            f"window_size={config_window_size} for timeframe '{timeframe}'."
        )
    window_size = persisted_window_size

    # Validate prediction_horizon consistency
    prediction_horizon = tf_config["prediction_horizon"]
    if persisted_horizon != prediction_horizon:
        raise ValueError(
            f"Prediction horizon mismatch: checkpoint trained with "
            f"prediction_horizon={persisted_horizon} but config uses "
            f"prediction_horizon={prediction_horizon} for timeframe '{timeframe}'."
        )

    feature_cols = get_feature_columns(timeframe)

    # Validate feature schema if persisted in checkpoint
    if "feature_columns" in scalers:
        persisted_cols = scalers["feature_columns"]
        if list(persisted_cols) != list(feature_cols):
            raise ValueError(
                f"Feature columns mismatch: checkpoint was trained with "
                f"{persisted_cols} but current pipeline produces {list(feature_cols)}. "
                "Re-train the model or align the feature pipeline."
            )

    # Load raw data and compute forward returns
    df = load_symbol(symbol, timeframe=timeframe) if symbol else load_all(timeframe=timeframe)
    df["label"] = df.groupby("symbol")["close"].transform(
        lambda c: c.shift(-prediction_horizon) / c - 1
    )
    df = df.dropna(subset=["label"])

    # Build validation windows per symbol
    if "train_ratio" not in scalers:
        raise KeyError(
            "Checkpoint missing 'train_ratio'. "
            "Re-train the model to generate a compatible checkpoint."
        )
    train_ratio = scalers["train_ratio"]
    if not (0 < train_ratio < 1):
        raise ValueError(
            f"Invalid train_ratio={train_ratio} in checkpoint. "
            "Expected a value strictly between 0 and 1."
        )
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
        if split == 0 or split == n:
            skipped += 1
            continue
        val_X.append(X_sym[split:])
        val_y.append(y_sym[split:])
        val_close.append(close_sym[split:])

    if skipped:
        logging.warning("%d symbole(s) ignoré(s) (historique insuffisant)", skipped)
    if not val_X:
        raise ValueError("No validation samples after windowing. Check data availability.")

    X_val = np.concatenate(val_X)
    y_val = np.concatenate(val_y)

    # Validate dataset consistency against checkpoint fingerprint
    if "n_val_samples" in scalers:
        expected = scalers["n_val_samples"]
        actual = len(X_val)
        if actual != expected:
            raise ValueError(
                f"Validation set size mismatch: checkpoint expected {expected} "
                f"samples but current data produces {actual}. "
                "The underlying data may have changed since training. "
                "Re-train the model to generate a consistent checkpoint."
            )

    # close_val is only meaningful for single-symbol evaluation;
    # mixing prices from different symbols produces a misleading series.
    close_val = np.concatenate(val_close) if symbol else None

    return X_val, y_val, close_val, scalers, prediction_horizon


# ----- Orchestrateur ----- #


def run_evaluation(
    model: nn.Module,
    dataloader: torch.utils.data.DataLoader,
    target_scaler,
    history: dict,
    results_dir: str,
    device: torch.device,
    close_prices: np.ndarray | None = None,
    prediction_horizon: int | None = None,
) -> dict:
    """Évalue un modèle et génère tous les graphiques.

    Fonction générique utilisable par n'importe quel modèle PyTorch.

    Args:
        model: Modèle PyTorch déjà chargé et en mode eval.
        dataloader: DataLoader de validation.
        target_scaler: Scaler pour inverse-transformer les prédictions
                       (doit avoir une méthode inverse_transform).
        history: Dict avec clés 'train_loss' et 'val_loss'.
        results_dir: Dossier où sauvegarder les graphiques.
        device: Device (mps, cuda, cpu).

    Returns:
        Dict des métriques calculées.
    """
    os.makedirs(results_dir, exist_ok=True)

    # Prédictions (en espace scalé)
    y_pred_scaled, y_true_scaled = predict(model, dataloader, device)

    # Inverse transform pour retrouver les vrais pourcentages
    y_pred = target_scaler.inverse_transform(y_pred_scaled.reshape(-1, 1)).ravel()
    y_true = target_scaler.inverse_transform(y_true_scaled.reshape(-1, 1)).ravel()

    # Métriques
    metrics = compute_metrics(y_true, y_pred)
    print("\n===== Evaluation Metrics =====")
    for name, value in metrics.items():
        print(f"  {name:>20s}: {value:.4f}")

    # Graphiques
    plot_training_curves(history, results_dir)
    plot_predictions_vs_actual(y_true, y_pred, results_dir)
    plot_scatter(y_true, y_pred, results_dir)
    plot_residuals(y_true, y_pred, results_dir)
    plot_direction_accuracy(y_true, y_pred, results_dir)

    if close_prices is not None and prediction_horizon is not None:
        plot_price_vs_predicted(close_prices, y_true, y_pred, prediction_horizon, results_dir)

    print(f"\nGraphiques sauvegardés dans {results_dir}/")

    return metrics


def run_evaluation_by_crypto(
    model: nn.Module,
    dataloader: torch.utils.data.DataLoader,
    target_scaler,
    symbols: np.ndarray,
    results_dir: str,
    device: torch.device,
) -> dict:
    """Évalue un modèle par crypto et génère les graphiques par symbole.

    Args:
        model: Modèle PyTorch déjà chargé et en mode eval.
        dataloader: DataLoader de validation.
        target_scaler: Scaler pour inverse-transformer les prédictions.
        symbols: Array des symboles correspondant à chaque sample.
        results_dir: Dossier où sauvegarder les graphiques.
        device: Device (mps, cuda, cpu).

    Returns:
        Dict des métriques par symbole.
    """
    os.makedirs(results_dir, exist_ok=True)

    # Prédictions globales
    y_pred_scaled, y_true_scaled = predict(model, dataloader, device)
    y_pred = target_scaler.inverse_transform(y_pred_scaled.reshape(-1, 1)).ravel()
    y_true = target_scaler.inverse_transform(y_true_scaled.reshape(-1, 1)).ravel()

    # Métriques par crypto
    metrics_by_symbol = {}
    unique_symbols = np.unique(symbols)

    print("\n===== Metrics par Crypto =====")
    for sym in unique_symbols:
        mask = symbols == sym
        sym_metrics = compute_metrics(y_true[mask], y_pred[mask])
        metrics_by_symbol[sym] = sym_metrics
        print(f"\n  {sym}:")
        for name, value in sym_metrics.items():
            print(f"    {name:>20s}: {value:.4f}")

    # Graphiques par crypto
    plot_metrics_by_crypto(metrics_by_symbol, results_dir)
    plot_predictions_by_crypto(y_true, y_pred, symbols, results_dir)
    plot_scatter_by_crypto(y_true, y_pred, symbols, results_dir)
    plot_direction_accuracy_by_crypto(metrics_by_symbol, results_dir)

    print(f"\nGraphiques par crypto sauvegardés dans {results_dir}/")

    return metrics_by_symbol