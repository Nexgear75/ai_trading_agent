"""LSTM training script."""
import argparse
import gc
import os
from dataclasses import dataclass, field

import joblib
import torch
import torch.nn as nn
from tqdm import tqdm

from config import DEFAULT_TIMEFRAME, get_timeframe_config
from data.features.pipeline import get_feature_columns
from models.lstm.LSTM import LSTMModel
from models.lstm.data_preparator import prepare_data


@dataclass
class TrainCfg:
    epochs: int = 200
    batch_size: int = 32
    lr: float = 1e-3
    patience: int = 10
    hidden: int = 128
    layers: int = 2


def _get_checkpoint_paths(timeframe: str) -> dict:
    checkpoint_dir = f"models/lstm/checkpoints/{timeframe}"
    return {
        "dir": checkpoint_dir,
        "model": os.path.join(checkpoint_dir, "best_model.pth"),
        "scalers": os.path.join(checkpoint_dir, "scalers.joblib"),
    }


def _run_train_epoch(model, loader, criterion, optimizer, device, epoch, total):
    model.train()
    total_loss = 0.0
    pbar = tqdm(loader, desc=f"Epoch {epoch:3d}/{total} [Train]", leave=False)
    for X, y in pbar:
        X, y = X.to(device), y.to(device)
        optimizer.zero_grad()
        preds = model(X)
        loss = criterion(preds, y)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        total_loss += loss.item() * len(X)
        pbar.set_postfix(loss=f"{loss.item():.5f}")
        del preds, loss
        if device.type == "mps":
            torch.mps.empty_cache()
    return total_loss / len(loader.dataset)


def _run_val_epoch(model, loader, criterion, device):
    model.eval()
    total_loss, correct_dir = 0.0, 0
    with torch.no_grad():
        for X, y in loader:
            X, y = X.to(device), y.to(device)
            preds = model(X)
            total_loss += criterion(preds, y).item() * len(X)
            correct_dir += ((preds > 0) == (y > 0)).sum().item()
            if device.type == "mps":
                torch.mps.empty_cache()
    return total_loss / len(loader.dataset), correct_dir / len(loader.dataset)


def train(
    symbol: str | None = None,
    timeframe: str = "1h",
    cfg: TrainCfg | None = None,
):
    """Entraîne le modèle LSTM avec early stopping."""
    if cfg is None:
        cfg = TrainCfg()

    tf_config = get_timeframe_config(timeframe)
    window_size = tf_config["window_size"]
    feature_cols = get_feature_columns(timeframe)
    paths = _get_checkpoint_paths(timeframe)
    os.makedirs(paths["dir"], exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"  ENTRAÎNEMENT LSTM  |  Timeframe: {timeframe}")
    print(f"  Window: {window_size}  |  Features: {len(feature_cols)}")
    print(f"  Hidden: {cfg.hidden}  |  Layers: {cfg.layers}")
    print(f"{'=' * 60}\n")

    device = torch.device("mps" if torch.mps.is_available() else "cpu")
    print(f"Device: {device}")

    train_loader, val_loader, feature_scaler, target_scaler, clip_bounds, _ = prepare_data(
        symbol=symbol, timeframe=timeframe, batch_size=cfg.batch_size
    )

    model = LSTMModel(n_features=len(feature_cols), hidden=cfg.hidden, layers=cfg.layers).to(device)
    print(f"LSTM parameters: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

    criterion = nn.HuberLoss(delta=1.0)
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=5)

    best_val_loss = float("inf")
    no_improve = 0
    history = {"train_loss": [], "val_loss": []}

    for epoch in range(1, cfg.epochs + 1):
        train_loss = _run_train_epoch(model, train_loader, criterion, optimizer, device, epoch, cfg.epochs)
        val_loss, dir_acc = _run_val_epoch(model, val_loader, criterion, device)

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        scheduler.step(val_loss)

        if epoch % 5 == 0:
            gc.collect()
            if device.type == "mps":
                torch.mps.empty_cache()

        tqdm.write(
            f"Epoch {epoch:3d}/{cfg.epochs} | Train: {train_loss:.6f} | "
            f"Val: {val_loss:.6f} | Dir Acc: {dir_acc:.1%} | LR: {optimizer.param_groups[0]['lr']:.1e}"
        )

        if val_loss < best_val_loss:
            best_val_loss, no_improve = val_loss, 0
            torch.save(
                {"model_state": model.state_dict(), "history": history,
                 "timeframe": timeframe, "window_size": window_size,
                 "n_features": len(feature_cols), "hidden": cfg.hidden, "layers": cfg.layers},
                paths["model"],
            )
            joblib.dump(
                {"feature_scaler": feature_scaler, "target_scaler": target_scaler,
                 "clip_bounds": clip_bounds, "timeframe": timeframe, "window_size": window_size},
                paths["scalers"],
            )
            print(f"  [SAVE] Checkpoint saved → {paths['model']}")
        else:
            no_improve += 1
            if no_improve >= cfg.patience:
                print(f"Early stopping at epoch {epoch}")
                break

    checkpoint = torch.load(paths["model"], weights_only=False)
    model.load_state_dict(checkpoint["model_state"])
    scalers = joblib.load(paths["scalers"])
    print(f"\nTraining terminé. Best val loss: {best_val_loss:.6f}")
    return model, scalers["feature_scaler"], scalers["target_scaler"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entraînement LSTM")
    parser.add_argument("--symbol", type=str, default=None)
    parser.add_argument("--timeframe", type=str, default="1h")
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--layers", type=int, default=2)
    a = parser.parse_args()

    train(
        symbol=a.symbol,
        timeframe=a.timeframe,
        cfg=TrainCfg(a.epochs, a.batch_size, a.lr, a.patience, a.hidden, a.layers),
    )
