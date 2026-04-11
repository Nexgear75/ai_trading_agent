from __future__ import annotations

import argparse
import gc
import os

import joblib
import torch
import torch.nn as nn
from tqdm import tqdm

from config import DEFAULT_TIMEFRAME, get_timeframe_config, get_patchtst_config
from data.features.pipeline import get_feature_columns
from models.patch_tst.PatchTST import PatchTST
from models.patch_tst.data_preparator import prepare_data


def _get_checkpoint_paths(timeframe: str):
    """Retourne les chemins de checkpoint pour un timeframe donné."""
    checkpoint_dir = f"models/patch_tst/checkpoints/{timeframe}"
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
    lr: float = 1e-4,
    patience: int = 15,
):
    """Entraîne le modèle PatchTST.

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
    patchtst_cfg = get_patchtst_config(timeframe)
    feature_cols = get_feature_columns(timeframe)

    # Setup checkpoint paths for this timeframe
    paths = _get_checkpoint_paths(timeframe)
    os.makedirs(paths["dir"], exist_ok=True)

    num_patches = (window_size - patchtst_cfg["patch_len"]) // patchtst_cfg["stride"] + 1

    print(f"\n{'=' * 60}")
    print("  ENTRAÎNEMENT PatchTST")
    print(f"  Timeframe: {timeframe}")
    print(f"  Window size: {window_size}  |  Features: {len(feature_cols)}")
    print(f"  Patch: len={patchtst_cfg['patch_len']}  stride={patchtst_cfg['stride']}"
          f"  → {num_patches} patches")
    print(f"  Transformer: d_model={patchtst_cfg['d_model']}  heads={patchtst_cfg['n_heads']}"
          f"  layers={patchtst_cfg['n_layers']}")
    print(f"  Checkpoint: {paths['dir']}")
    print(f"{'=' * 60}\n")

    device = torch.device("mps" if torch.mps.is_available() else "cpu")
    print(f"Device: {device}")

    # Données
    train_loader, val_loader, feature_scaler, target_scaler, clip_bounds, target_clip_bounds, _ = prepare_data(
        symbol=symbol, timeframe=timeframe, batch_size=batch_size
    )

    # Modèle
    model = PatchTST(
        window_size=window_size,
        n_features=len(feature_cols),
        **patchtst_cfg,
    ).to(device)
    criterion = nn.HuberLoss(delta=1.0)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-3)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

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
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            train_loss += loss.item() * len(X_batch)
            pbar.set_postfix(loss=f"{loss.item():.5f}")

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

                correct_dir += ((preds > 0) == (y_batch > 0)).sum().item()

                if device.type == "mps":
                    torch.mps.empty_cache()

        val_loss /= len(val_loader.dataset)
        dir_acc = correct_dir / len(val_loader.dataset)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        scheduler.step()

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
                    "patchtst_cfg": patchtst_cfg,
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
                    "train_ratio": 0.8,
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
    parser = argparse.ArgumentParser(description="Entraînement PatchTST")
    parser.add_argument("--symbol", type=str, default=None, help="Symbole (ex: BTC)")
    parser.add_argument("--timeframe", type=str, default=DEFAULT_TIMEFRAME,
                        help=f"Timeframe (défaut: {DEFAULT_TIMEFRAME})")
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--patience", type=int, default=15)
    args = parser.parse_args()

    train(
        symbol=args.symbol,
        timeframe=args.timeframe,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        patience=args.patience,
    )
