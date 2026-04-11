"""
Module d'évaluation générique pour tous les modèles du projet.

Fournit des métriques de régression, des graphiques de diagnostic,
et un orchestrateur `run_evaluation` réutilisable par n'importe quel
modèle (CNN, LSTM, GRU, Transformer, etc.).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

if TYPE_CHECKING:
    import torch
    import torch.nn as nn


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
    import torch  # lazy import — pas nécessaire pour XGBoost

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
