"""BiLSTM training script."""
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
from models.bilstm.BiLSTM import BiLSTMModel
from models.bilstm.data_preparator import prepare_data


@dataclass
class TrainCfg:
    epochs: int = 200
    batch_size: int = 32
    lr: float = 5e-4
    patience: int = 15
    hidden: int = 32
    layers: int = 1


@dataclass
class _Ctx:
    """Bundles model, criterion, optimizer, device, and run-time artefacts."""
    model: nn.Module
    criterion: nn.Module
    optimizer: torch.optim.Optimizer
    device: torch.device
    paths: dict
    meta: dict
    scalers: dict


def _get_checkpoint_paths(timeframe: str) -> dict:
    d = f"models/bilstm/checkpoints/{timeframe}"
    return {"dir": d, "model": os.path.join(d, "best_model.pth"), "scalers": os.path.join(d, "scalers.joblib")}


def _run_train_epoch(ctx: _Ctx, loader, epoch: int, total: int) -> float:
    ctx.model.train()
    total_loss = 0.0
    pbar = tqdm(loader, desc=f"Epoch {epoch:3d}/{total} [Train]", leave=False)
    for X, y in pbar:
        X, y = X.to(ctx.device), y.to(ctx.device)
        ctx.optimizer.zero_grad()
        preds = ctx.model(X)
        loss = ctx.criterion(preds, y)
        loss.backward()
        nn.utils.clip_grad_norm_(ctx.model.parameters(), 1.0)
        ctx.optimizer.step()
        total_loss += loss.item() * len(X)
        pbar.set_postfix(loss=f"{loss.item():.5f}")
        del preds, loss
        if ctx.device.type == "mps":
            torch.mps.empty_cache()
    return total_loss / len(loader.dataset)


def _run_val_epoch(ctx: _Ctx, loader) -> tuple[float, float]:
    ctx.model.eval()
    total_loss, correct_dir = 0.0, 0
    with torch.no_grad():
        for X, y in loader:
            X, y = X.to(ctx.device), y.to(ctx.device)
            preds = ctx.model(X)
            total_loss += ctx.criterion(preds, y).item() * len(X)
            correct_dir += ((preds > 0) == (y > 0)).sum().item()
            if ctx.device.type == "mps":
                torch.mps.empty_cache()
    return total_loss / len(loader.dataset), correct_dir / len(loader.dataset)


def _save_checkpoint(ctx: _Ctx, history: dict) -> None:
    torch.save({**ctx.meta, "model_state": ctx.model.state_dict(), "history": history}, ctx.paths["model"])
    joblib.dump(ctx.scalers, ctx.paths["scalers"])
    print(f"  [SAVE] Checkpoint saved → {ctx.paths['model']}")


def _run_loop(ctx: _Ctx, train_loader, val_loader, cfg: TrainCfg) -> float:
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(ctx.optimizer, factor=0.5, patience=7, min_lr=1e-6)
    history = {"train_loss": [], "val_loss": []}
    best_val, no_improve = float("inf"), 0

    for epoch in range(1, cfg.epochs + 1):
        train_loss = _run_train_epoch(ctx, train_loader, epoch, cfg.epochs)
        val_loss, dir_acc = _run_val_epoch(ctx, val_loader)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        scheduler.step(val_loss)

        if epoch % 5 == 0:
            gc.collect()
            if ctx.device.type == "mps":
                torch.mps.empty_cache()

        tqdm.write(
            f"Epoch {epoch:3d}/{cfg.epochs} | Train: {train_loss:.6f} | "
            f"Val: {val_loss:.6f} | Dir Acc: {dir_acc:.1%} | LR: {ctx.optimizer.param_groups[0]['lr']:.1e}"
        )

        if val_loss < best_val:
            best_val, no_improve = val_loss, 0
            _save_checkpoint(ctx, history)
        else:
            no_improve += 1
            if no_improve >= cfg.patience:
                print(f"Early stopping at epoch {epoch}")
                break

    return best_val


def train(symbol: str | None = None, timeframe: str = "1h", cfg: TrainCfg | None = None):
    """Entraîne le modèle BiLSTM avec early stopping."""
    if cfg is None:
        cfg = TrainCfg()

    tf_config = get_timeframe_config(timeframe)
    window_size = tf_config["window_size"]
    feature_cols = get_feature_columns(timeframe)
    paths = _get_checkpoint_paths(timeframe)
    os.makedirs(paths["dir"], exist_ok=True)

    print(f"\n{'=' * 60}\n  ENTRAÎNEMENT BiLSTM  |  Timeframe: {timeframe}")
    print(f"  Window: {window_size}  |  Features: {len(feature_cols)}")
    print(f"  Hidden: {cfg.hidden}  |  Layers: {cfg.layers}\n{'=' * 60}\n")

    device = torch.device("mps" if torch.mps.is_available() else "cpu")
    print(f"Device: {device}")

    train_loader, val_loader, feature_scaler, target_scaler, clip_bounds, _ = prepare_data(
        symbol=symbol, timeframe=timeframe, batch_size=cfg.batch_size
    )

    model = BiLSTMModel(n_features=len(feature_cols), hidden=cfg.hidden, layers=cfg.layers).to(device)
    print(f"BiLSTM parameters: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

    ctx = _Ctx(
        model=model,
        criterion=nn.HuberLoss(delta=1.0),
        optimizer=torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=5e-3),
        device=device,
        paths=paths,
        meta={"timeframe": timeframe, "window_size": window_size, "n_features": len(feature_cols),
              "hidden": cfg.hidden, "layers": cfg.layers},
        scalers={"feature_scaler": feature_scaler, "target_scaler": target_scaler,
                 "clip_bounds": clip_bounds, "timeframe": timeframe, "window_size": window_size},
    )

    best_val = _run_loop(ctx, train_loader, val_loader, cfg)

    checkpoint = torch.load(paths["model"], weights_only=False)
    model.load_state_dict(checkpoint["model_state"])
    saved = joblib.load(paths["scalers"])
    print(f"\nTraining terminé. Best val loss: {best_val:.6f}")
    return model, saved["feature_scaler"], saved["target_scaler"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entraînement BiLSTM")
    parser.add_argument("--symbol", type=str, default=None)
    parser.add_argument("--timeframe", type=str, default="1h")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--patience", type=int, default=15)
    parser.add_argument("--hidden", type=int, default=32)
    parser.add_argument("--layers", type=int, default=1)
    a = parser.parse_args()
    train(symbol=a.symbol, timeframe=a.timeframe,
          cfg=TrainCfg(a.epochs, a.batch_size, a.lr, a.patience, a.hidden, a.layers))
