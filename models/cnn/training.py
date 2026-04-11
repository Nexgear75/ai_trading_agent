import argparse
import gc
import os

import joblib
import torch
import torch.nn as nn
from tqdm import tqdm

from config import DEFAULT_TIMEFRAME, get_timeframe_config, get_cnn_config
from data.features.pipeline import get_feature_columns
from models.cnn.CNN import CNN1D
from models.cnn.data_preparator import prepare_data


def _get_checkpoint_paths(timeframe: str):
    """Retourne les chemins de checkpoint pour un timeframe donné."""
    checkpoint_dir = f"models/cnn/checkpoints/{timeframe}"
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
):
    """Entraîne le modèle CNN1D.

    Args:
        symbol: Symbole à utiliser (ex: "BTC"). None = toutes les cryptos.
        timeframe: Timeframe pour l'entraînement (ex: "1d", "1h", "4h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").
        epochs: Nombre maximum d'epochs.
        batch_size: Taille des batchs.
        lr: Learning rate initial.
        patience: Nombre d'epochs sans amélioration avant arrêt.
    """
    # Get timeframe configuration
    tf_config = get_timeframe_config(timeframe)
    window_size = tf_config["window_size"]
    cnn_cfg = get_cnn_config(timeframe)
    feature_cols = get_feature_columns(timeframe)

    # Setup checkpoint paths for this timeframe
    paths = _get_checkpoint_paths(timeframe)
    os.makedirs(paths["dir"], exist_ok=True)

    print(f"\n{'=' * 60}")
    print("  ENTRAÎNEMENT CNN1D")
    print(f"  Timeframe: {timeframe}")
    print(f"  Window size: {window_size}  |  Features: {len(feature_cols)}")
    print(f"  Channels: {cnn_cfg['channels']}  |  Kernels: {cnn_cfg['kernel_sizes']}")
    print(f"  Dropout: conv={cnn_cfg['dropout_conv']}  fc={cnn_cfg['dropout_fc']}")
    print(f"  Checkpoint: {paths['dir']}")
    print(f"{'=' * 60}\n")

    device = torch.device("mps" if torch.mps.is_available() else "cpu")
    print(f"Device: {device}")

    # Données
    train_ratio = 0.8
    train_loader, val_loader, feature_scaler, target_scaler, clip_bounds, target_clip_bounds, _ = prepare_data(
        symbol=symbol, timeframe=timeframe, batch_size=batch_size, train_ratio=train_ratio
    )

    # Modèle
    model = CNN1D(
        window_size=window_size,
        n_features=len(feature_cols),
        **cnn_cfg,
    ).to(device)
    criterion = nn.HuberLoss(delta=1.0)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5
    )

    # Training loop
    best_val_loss = float("inf")
    epochs_without_improvement = 0
    history = {"train_loss": [], "val_loss": []}

    for epoch in range(1, epochs + 1):
        # --- Train ---
        model.train()
        train_loss = 0.0
        pbar = tqdm(train_loader, desc=f"Epoch {epoch:3d}/{epochs} [Train]", leave=False)
        for X_batch, y_batch in pbar:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)

            optimizer.zero_grad()
            preds = model(X_batch)
            loss = criterion(preds, y_batch)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * len(X_batch)
            pbar.set_postfix(loss=f"{loss.item():.5f}")

            # Libération mémoire explicite pour éviter OOM
            del preds, loss
            if device.type == "mps":
                torch.mps.empty_cache()

        train_loss /= len(train_loader.dataset)

        # --- Validation ---
        model.eval()
        val_loss = 0.0
        correct_dir = 0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                preds = model(X_batch)
                loss = criterion(preds, y_batch)
                val_loss += loss.item() * len(X_batch)

                # Direction accuracy : % de fois où signe(pred) == signe(target)
                correct_dir += ((preds > 0) == (y_batch > 0)).sum().item()

                # Libération mémoire explicite
                if device.type == "mps":
                    torch.mps.empty_cache()

        val_loss /= len(val_loader.dataset)
        dir_acc = correct_dir / len(val_loader.dataset)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        scheduler.step(val_loss)

        # Garbage collection périodique
        if epoch % 5 == 0:
            gc.collect()
            if device.type == "mps":
                torch.mps.empty_cache()

        current_lr = optimizer.param_groups[0]["lr"]
        tqdm.write(
            f"Epoch {epoch:3d}/{epochs} | "
            f"Train Loss: {train_loss:.6f} | "
            f"Val Loss: {val_loss:.6f} | "
            f"Dir Acc: {dir_acc:.1%} | "
            f"LR: {current_lr:.1e}"
        )

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            epochs_without_improvement = 0
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "history": history,
                    "timeframe": timeframe,
                    "window_size": window_size,
                    "cnn_cfg": cnn_cfg,
                    "n_features": len(feature_cols),
                },
                paths["model"],
            )
            joblib.dump(
                {
                    "feature_scaler": feature_scaler,
                    "target_scaler": target_scaler,
                    "clip_bounds": clip_bounds,
                    "target_clip_bounds": target_clip_bounds,
                    "timeframe": timeframe,
                    "window_size": window_size,
                    "train_ratio": train_ratio,
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
    checkpoint = torch.load(paths["model"], weights_only=False, map_location=device)
    model.load_state_dict(checkpoint["model_state"])
    scalers = joblib.load(paths["scalers"])
    print(f"\nTraining terminé. Best val loss: {best_val_loss:.6f}")
    print(f"Checkpoint: {paths['model']}")

    return model, scalers["feature_scaler"], scalers["target_scaler"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entraînement CNN1D")
    parser.add_argument("--symbol", type=str, default=None, help="Symbole (ex: BTC)")
    parser.add_argument("--timeframe", type=str, default=DEFAULT_TIMEFRAME,
                        help=f"Timeframe (défaut: {DEFAULT_TIMEFRAME})")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=7)
    args = parser.parse_args()

    train(
        symbol=args.symbol,
        timeframe=args.timeframe,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        patience=args.patience,
    )
