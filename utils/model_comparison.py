"""Compare multiple models on the same validation data."""
import argparse
import os

import joblib
import matplotlib.pyplot as plt
import numpy as np
import torch

from config import DEFAULT_TIMEFRAME
from models.cnn.CNN import CNN1D
from models.cnn.data_preparator import prepare_data
from models.cnn.evaluation import load_model as load_cnn
from models.lstm.evaluation import load_model as load_lstm
from utils.evaluation import compute_metrics, predict

RESULTS_DIR = "results/comparison"


def _get_model_loaders(timeframe: str) -> dict:
    return {
        "CNN":  {"load_fn": load_cnn,  "ckpt": f"models/cnn/checkpoints/{timeframe}/best_model.pth",
                 "scalers": f"models/cnn/checkpoints/{timeframe}/scalers.joblib"},
        "LSTM": {"load_fn": load_lstm, "ckpt": f"models/lstm/checkpoints/{timeframe}/best_model.pth",
                 "scalers": f"models/lstm/checkpoints/{timeframe}/scalers.joblib"},
    }


def plot_metrics_comparison(metrics_dict, save_path):
    """Bar chart comparing metrics across models."""
    models = list(metrics_dict.keys())
    metric_names = list(metrics_dict[models[0]].keys())
    x, width = np.arange(len(metric_names)), 0.35
    fig, ax = plt.subplots(figsize=(12, 5))
    for i, model in enumerate(models):
        ax.bar(x + i * width, [metrics_dict[model][m] for m in metric_names], width, label=model)
    ax.set_ylabel("Value")
    ax.set_title("Model Comparison")
    ax.set_xticks(x + width / 2)
    ax.set_xticklabels(metric_names, rotation=15)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(save_path, "metrics_comparison.png"), dpi=150)
    plt.close(fig)


def plot_loss_curves(histories, save_path):
    """Compare training curves across models."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for name, hist in histories.items():
        axes[0].plot(hist["train_loss"], label=name)
        axes[1].plot(hist["val_loss"], label=name)
    axes[0].set_title("Training Loss")
    axes[1].set_title("Validation Loss")
    for ax in axes:
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Loss")
        ax.legend()
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(save_path, "loss_comparison.png"), dpi=150)
    plt.close(fig)


def plot_predictions(preds_dict, y_true, save_path):
    """Compare predictions from different models."""
    colors = ["blue", "red", "green", "orange"]
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(y_true[:200], label="Actual", linewidth=2, color="black")
    for i, (name, preds) in enumerate(preds_dict.items()):
        ax.plot(preds[:200], label=name, alpha=0.7, color=colors[i % len(colors)])
    ax.set_xlabel("Sample")
    ax.set_ylabel("Forward Return")
    ax.set_title("Predictions Comparison (first 200 samples)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(save_path, "predictions_comparison.png"), dpi=150)
    plt.close(fig)


def compare(symbol: str | None = None, timeframe: str = DEFAULT_TIMEFRAME):
    """Compare CNN and LSTM models on the same validation data."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    device = torch.device("mps" if torch.mps.is_available() else "cpu")
    print(f"Device: {device}  |  Timeframe: {timeframe}")

    _, val_loader, _, _, _, _ = prepare_data(symbol=symbol, timeframe=timeframe)
    model_loaders = _get_model_loaders(timeframe)

    predictions, histories = {}, {}
    y_true_scaled = None

    for name, cfg in model_loaders.items():
        if not os.path.exists(cfg["ckpt"]):
            print(f"  [SKIP] {name}: checkpoint not found ({cfg['ckpt']})")
            continue
        model, history = cfg["load_fn"](cfg["ckpt"], device)
        t_sc = joblib.load(cfg["scalers"])["target_scaler"]
        pred_s, yt_s = predict(model, val_loader, device)
        predictions[name] = t_sc.inverse_transform(pred_s.reshape(-1, 1)).ravel()
        histories[name] = history
        if y_true_scaled is None:
            y_true_scaled = yt_s
            global_t_sc = t_sc

    if not predictions:
        print("No models found. Train at least one model first.")
        return {}

    y_true = global_t_sc.inverse_transform(y_true_scaled.reshape(-1, 1)).ravel()
    metrics = {name: compute_metrics(y_true, pred) for name, pred in predictions.items()}

    print("\n" + "=" * 60 + "\nMODEL COMPARISON RESULTS\n" + "=" * 60)
    print(f"{'Metric':<25}" + "".join(f"{m:<15}" for m in metrics))
    print("-" * 60)
    for metric_name in list(metrics.values())[0]:
        print(f"{metric_name:<25}" + "".join(f"{metrics[m][metric_name]:<15.4f}" for m in metrics))
    print("=" * 60)

    plot_metrics_comparison(metrics, RESULTS_DIR)
    plot_loss_curves(histories, RESULTS_DIR)
    plot_predictions(predictions, y_true, RESULTS_DIR)
    print(f"\nPlots saved to {RESULTS_DIR}/")
    return metrics


if __name__ == "__main__":
    pa = argparse.ArgumentParser(description="Compare CNN and LSTM models")
    pa.add_argument("--symbol", type=str, default=None)
    pa.add_argument("--timeframe", type=str, default=DEFAULT_TIMEFRAME)
    a = pa.parse_args()
    compare(symbol=a.symbol, timeframe=a.timeframe)
