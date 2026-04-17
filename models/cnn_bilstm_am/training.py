import argparse
import gc
import os

import joblib
import torch
import torch.nn as nn
from tqdm import tqdm

from config import DEFAULT_TIMEFRAME, get_timeframe_config, get_cnn_bilstm_am_config
from data.features.pipeline import get_feature_columns
from models.cnn_bilstm_am.CNN_BiLSTM_AM import CNNBiLSTMAM
from models.cnn_bilstm_am.data_preparator import prepare_data


def _get_checkpoint_paths(timeframe: str):
    """Retourne les chemins de checkpoint pour un timeframe donné."""
    checkpoint_dir = f"models/cnn_bilstm_am/checkpoints/{timeframe}"
    return {
        "dir": checkpoint_dir,
        "model": os.path.join(checkpoint_dir, "best_model.pth"),
        "scalers": os.path.join(checkpoint_dir, "scalers.joblib"),
    }


def train(
    symbol: str | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    epochs: int = 200,
    batch_size: int = 32,
    lr: float = 1e-3,
    patience: int = 7,
    task: str = "regression",
    classification_threshold: float = 0.005,
):
    """Entraîne le modèle CNN-BiLSTM-AM.

    Args:
        symbol: Symbole à utiliser (ex: "BTC"). None = toutes les cryptos.
        timeframe: Timeframe pour l'entraînement (ex: "1d", "1h", "4h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").
        epochs: Nombre maximum d'epochs.
        batch_size: Taille des batchs.
        lr: Learning rate initial.
        patience: Nombre d'epochs sans amélioration avant arrêt.
        task: "regression" ou "classification" (binaire).
        classification_threshold: Seuil pour la classe positive (défaut: 0.5%).
    """
    # Get timeframe configuration
    tf_config = get_timeframe_config(timeframe)
    window_size = tf_config["window_size"]
    model_cfg = get_cnn_bilstm_am_config(timeframe)
    feature_cols = get_feature_columns(timeframe)

    # Setup checkpoint paths for this timeframe
    paths = _get_checkpoint_paths(timeframe)
    os.makedirs(paths["dir"], exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"  ENTRAÎNEMENT CNN-BiLSTM-AM ({task.upper()})")
    print(f"  Timeframe: {timeframe}")
    print(f"  Window size: {window_size}  |  Features: {len(feature_cols)}")
    print(
        f"  CNN: channels={model_cfg['channels']}  kernels={model_cfg['kernel_sizes']}"
    )
    print(
        f"  BiLSTM: hidden={model_cfg['lstm_hidden']}  layers={model_cfg['lstm_layers']}"
    )
    print(f"  Dropout: conv={model_cfg['dropout_conv']}  fc={model_cfg['dropout_fc']}")
    if task == "classification":
        print(f"  Classification threshold: {classification_threshold:.1%}")
    print(f"  Checkpoint: {paths['dir']}")
    print(f"{'=' * 60}\n")

    # Détection automatique du device : CUDA > MPS > CPU
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"Device: {device}")

    # Données
    (
        train_loader,
        val_loader,
        feature_scaler,
        target_scaler,
        clip_bounds,
        _,
        pos_weight,
    ) = prepare_data(
        symbol=symbol,
        timeframe=timeframe,
        batch_size=batch_size,
        task=task,
        classification_threshold=classification_threshold,
    )

    # Modèle
    model = CNNBiLSTMAM(
        window_size=window_size,
        n_features=len(feature_cols),
        task=task,
        **model_cfg,
    ).to(device)

    if task == "classification":
        pw = torch.tensor([pos_weight], dtype=torch.float32).to(device)
        criterion = nn.BCEWithLogitsLoss(pos_weight=pw)
    else:
        criterion = nn.SmoothL1Loss(beta=2.0)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-3)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=10
    )

    # Training loop — early stopping on val_auc (classif) or val_loss (regression)
    best_val_metric = float("-inf") if task == "classification" else float("inf")
    epochs_without_improvement = 0
    history = {"train_loss": [], "val_loss": []}
    if task == "classification":
        history["val_auc"] = []
        patience = max(patience, 15)  # Classification needs more patience

    for epoch in range(1, epochs + 1):
        # --- Train ---
        model.train()
        train_loss = 0.0
        pbar = tqdm(
            train_loader, desc=f"Epoch {epoch:3d}/{epochs} [Train]", leave=False
        )
        for X_batch, y_batch in pbar:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)

            optimizer.zero_grad()
            preds = model(X_batch)
            loss = criterion(preds, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            train_loss += loss.item() * len(X_batch)
            pbar.set_postfix(loss=f"{loss.item():.5f}")

        # Libération mémoire explicite pour éviter OOM
        del preds, loss
        if device.type == "mps" and hasattr(torch.mps, "empty_cache"):
            torch.mps.empty_cache()
        elif device.type == "cuda" and hasattr(torch.cuda, "empty_cache"):
            torch.cuda.empty_cache()

        train_loss /= len(train_loader.dataset)

        # --- Validation ---
        model.eval()
        val_loss = 0.0
        correct_dir = 0
        all_probs = []
        all_targets = []
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                preds = model(X_batch)
                loss = criterion(preds, y_batch)
                val_loss += loss.item() * len(X_batch)

                if task == "classification":
                    probs = torch.sigmoid(preds)
                    correct_dir += ((probs > 0.5) == (y_batch > 0.5)).sum().item()
                    all_probs.append(probs.cpu())
                    all_targets.append(y_batch.cpu())
                else:
                    correct_dir += ((preds > 0) == (y_batch > 0)).sum().item()

                if device.type == "mps":
                    torch.mps.empty_cache()

        val_loss /= len(val_loader.dataset)
        dir_acc = correct_dir / len(val_loader.dataset)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

        # Garbage collection périodique
        if epoch % 5 == 0:
            gc.collect()
            if device.type == "mps" and hasattr(torch.mps, "empty_cache"):
                torch.mps.empty_cache()
            elif device.type == "cuda" and hasattr(torch.cuda, "empty_cache"):
                torch.cuda.empty_cache()
            elif device.type == "cuda" and hasattr(torch.cuda, "empty_cache"):
                torch.cuda.empty_cache()

        current_lr = optimizer.param_groups[0]["lr"]
        log_msg = (
            f"Epoch {epoch:3d}/{epochs} | "
            f"Train Loss: {train_loss:.6f} | "
            f"Val Loss: {val_loss:.6f} | "
            f"{'Acc' if task == 'classification' else 'Dir Acc'}: {dir_acc:.1%}"
        )
        if task == "classification" and all_probs:
            from sklearn.metrics import roc_auc_score  # noqa: E402

            probs_cat = torch.cat(all_probs).numpy()
            targets_cat = torch.cat(all_targets).numpy()
            try:
                val_auc = roc_auc_score(targets_cat, probs_cat)
                log_msg += f" | AUC: {val_auc:.3f}"
            except ValueError:
                val_auc = 0.0
        log_msg += f" | LR: {current_lr:.1e}"
        tqdm.write(log_msg)

        # Early stopping metric
        if task == "classification":
            current_metric = val_auc if all_probs else 0.0
            history["val_auc"].append(current_metric)
            improved = current_metric > best_val_metric + 0.001  # min_delta
            scheduler.step(-current_metric)  # ReduceLROnPlateau mode='min' → negate AUC
        else:
            current_metric = val_loss
            improved = current_metric < best_val_metric
            scheduler.step(val_loss)

        if improved:
            best_val_metric = current_metric
            epochs_without_improvement = 0
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "history": history,
                    "timeframe": timeframe,
                    "window_size": window_size,
                    "model_cfg": model_cfg,
                    "n_features": len(feature_cols),
                    "task": task,
                    "classification_threshold": classification_threshold
                    if task == "classification"
                    else None,
                },
                paths["model"],
            )
            joblib.dump(
                {
                    "feature_scaler": feature_scaler,
                    "target_scaler": target_scaler,
                    "clip_bounds": clip_bounds,
                    "timeframe": timeframe,
                    "window_size": window_size,
                },
                paths["scalers"],
            )
            print(f"  [SAVE] Checkpoint saved → {paths['model']}")
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= patience:
                print(f"Early stopping at epoch {epoch}")
                break

    # Charger les meilleurs poids et scalers
    checkpoint = torch.load(paths["model"], weights_only=False)
    model.load_state_dict(checkpoint["model_state"])
    scalers = joblib.load(paths["scalers"])
    metric_name = "val AUC" if task == "classification" else "val loss"
    print(f"\nTraining terminé. Best {metric_name}: {best_val_metric:.6f}")
    print(f"Checkpoint: {paths['model']}")

    return model, scalers["feature_scaler"], scalers["target_scaler"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entraînement CNN-BiLSTM-AM")
    parser.add_argument("--symbol", type=str, default=None, help="Symbole (ex: BTC)")
    parser.add_argument(
        "--timeframe",
        type=str,
        default=DEFAULT_TIMEFRAME,
        help=f"Timeframe (défaut: {DEFAULT_TIMEFRAME})",
    )
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=7)
    parser.add_argument(
        "--task",
        type=str,
        default="regression",
        choices=["regression", "classification"],
        help="Mode: regression (return %) ou classification (binaire)",
    )
    parser.add_argument(
        "--classification-threshold",
        type=float,
        default=0.005,
        help="Seuil pour la classe positive (défaut: 0.5%%)",
    )
    args = parser.parse_args()

    train(
        symbol=args.symbol,
        timeframe=args.timeframe,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        patience=args.patience,
        task=args.task,
        classification_threshold=args.classification_threshold,
    )
