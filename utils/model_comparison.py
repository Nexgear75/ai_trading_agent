"""Compare multiple models on the same validation data."""
import os
import argparse
import joblib
import torch
import numpy as np
import matplotlib.pyplot as plt
from models.cnn.CNN import CNN1D
from models.cnn.data_preparator import prepare_data
from models.lstm.LSTM import LSTMModel
from utils.evaluation import predict, compute_metrics

RESULTS_DIR = "results/comparison"
MODEL_CONFIGS = {
    "CNN": {"cls": CNN1D, "ckpt": "models/cnn/checkpoints/best_model.pth", "kwargs": {}},
    "LSTM": {"cls": LSTMModel, "ckpt": "models/lstm/checkpoints/best_model.pth", "kwargs": {"n_features": 20}},
}


def load_model(name, dev):
    """Load a trained model by name."""
    cfg = MODEL_CONFIGS[name]
    mdl = cfg["cls"](**cfg["kwargs"]).to(dev)
    ckpt = torch.load(cfg["ckpt"], weights_only=False, map_location=dev)
    mdl.load_state_dict(ckpt["model_state"])
    mdl.eval()
    return mdl, ckpt["history"]


def plot_metrics_comparison(metrics_dict, save_path):
    """Bar chart comparing metrics across models."""
    models, metric_names = list(metrics_dict.keys()), list(metrics_dict[list(metrics_dict.keys())[0]].keys())
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
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(y_true[:200], label="Actual", linewidth=2, color="black")
    colors = ["blue", "red", "green", "orange"]
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


def compare(sym=None):
    """Compare CNN and LSTM models."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    dev = torch.device("mps" if torch.mps.is_available() else "cpu")
    print(f"Device: {dev}")

    _, va_ld, _, _ = prepare_data(symbol=sym)
    t_sc = joblib.load("models/cnn/checkpoints/scalers.joblib")["target_scaler"]

    models_data = {name: load_model(name, dev) for name in MODEL_CONFIGS}
    predictions, histories = {}, {}
    y_true_scaled = None

    for name, (mdl, hist) in models_data.items():
        pred_s, yt_s = predict(mdl, va_ld, dev)
        predictions[name] = t_sc.inverse_transform(pred_s.reshape(-1, 1)).ravel()
        histories[name] = hist
        if y_true_scaled is None:
            y_true_scaled = yt_s

    y_true = t_sc.inverse_transform(y_true_scaled.reshape(-1, 1)).ravel()
    metrics = {name: compute_metrics(y_true, pred) for name, pred in predictions.items()}

    print("\n" + "=" * 60 + "\nMODEL COMPARISON RESULTS\n" + "=" * 60)
    print(f"{'Metric':<25}" + "".join(f"{m:<15}" for m in metrics.keys()))
    print("-" * 60)
    for metric_name in list(metrics.values())[0].keys():
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
    compare(pa.parse_args().symbol)
