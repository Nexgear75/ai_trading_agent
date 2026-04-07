"""LSTM training script."""
import argparse
import os
import joblib
import torch
import torch.nn as nn
from dataclasses import dataclass
from data.features.pipeline import FEATURE_COLUMNS
from models.lstm.LSTM import LSTMModel
from models.lstm.data_preparator import prepare_data

CKPT_DIR = "models/lstm/checkpoints"
MODEL_PATH = os.path.join(CKPT_DIR, "best_model.pth")
SCALER_PATH = os.path.join(CKPT_DIR, "scalers.joblib")


@dataclass
class Cfg:
    sym: str = None
    epochs: int = 200
    bs: int = 32
    lr: float = 1e-3
    patience: int = 10
    hidden: int = 128
    layers: int = 2


class Trainer:
    def __init__(self, mdl, crit, opt, dev):
        self.mdl, self.crit, self.opt, self.dev = mdl, crit, opt, dev

    def run_epoch(self, loader, is_train):
        self.mdl.train() if is_train else self.mdl.eval()
        loss_sum = 0.0
        ctx = torch.enable_grad() if is_train else torch.no_grad()
        with ctx:
            for xb, yb in loader:
                xb, yb = xb.to(self.dev), yb.to(self.dev)
                if is_train:
                    self.opt.zero_grad()
                loss = self.crit(self.mdl(xb), yb)
                if is_train:
                    loss.backward()
                    nn.utils.clip_grad_norm_(self.mdl.parameters(), 1.0)
                    self.opt.step()
                loss_sum += loss.item() * len(xb)
        return loss_sum / len(loader.dataset)


def train(cfg: Cfg):
    """Train LSTM model with early stopping."""
    os.makedirs(CKPT_DIR, exist_ok=True)
    dev = torch.device("mps" if torch.mps.is_available() else "cpu")
    print(f"Device: {dev}")

    tr_ld, va_ld, f_sc, t_sc = prepare_data(symbol=cfg.sym, batch_size=cfg.bs)
    n_features = len(FEATURE_COLUMNS)
    mdl = LSTMModel(n_features=n_features, hidden=cfg.hidden, layers=cfg.layers).to(dev)
    crit, opt = nn.HuberLoss(delta=1.0), torch.optim.Adam(mdl.parameters(), lr=cfg.lr)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, "min", 0.5, patience=10)
    trainer = Trainer(mdl, crit, opt, dev)
    best, no_impr, hist = float("inf"), 0, {"train_loss": [], "val_loss": []}

    for ep in range(1, cfg.epochs + 1):
        tr_loss = trainer.run_epoch(tr_ld, True)
        va_loss = trainer.run_epoch(va_ld, False)
        hist["train_loss"].append(tr_loss)
        hist["val_loss"].append(va_loss)
        sched.step(va_loss)
        print(f"Ep {ep:3d}/{cfg.epochs} | Tr: {tr_loss:.6f} | Va: {va_loss:.6f}")
        if va_loss < best:
            best, no_impr = va_loss, 0
            torch.save({"model_state": mdl.state_dict(), "history": hist}, MODEL_PATH)
            joblib.dump({"feature_scaler": f_sc, "target_scaler": t_sc}, SCALER_PATH)
        else:
            no_impr += 1
            if no_impr >= cfg.patience:
                print(f"Early stop at epoch {ep}")
                break

    ckpt = torch.load(MODEL_PATH, weights_only=False)
    mdl.load_state_dict(ckpt["model_state"])
    print(f"Done. Best val: {best:.6f}")
    return mdl, f_sc, t_sc


if __name__ == "__main__":
    pa = argparse.ArgumentParser()
    pa.add_argument("--symbol", type=str, default=None)
    pa.add_argument("--epochs", type=int, default=50)
    pa.add_argument("--batch-size", type=int, default=32)
    pa.add_argument("--lr", type=float, default=1e-3)
    pa.add_argument("--patience", type=int, default=10)
    pa.add_argument("--hidden", type=int, default=128)
    pa.add_argument("--layers", type=int, default=2)
    a = pa.parse_args()
    train(Cfg(a.symbol, a.epochs, a.batch_size, a.lr, a.patience, a.hidden, a.layers))
