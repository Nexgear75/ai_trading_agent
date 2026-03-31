import argparse
import os

import joblib
import torch
import torch.nn as nn

from config import WINDOW_SIZE
from data.features.pipeline import FEATURE_COLUMNS
from models.cnn.CNN import CNN1D
from models.cnn.data_preparator import prepare_data

CHECKPOINT_DIR = "models/cnn/checkpoints"
CHECKPOINT_PATH = os.path.join(CHECKPOINT_DIR, "best_model.pth")
SCALERS_PATH = os.path.join(CHECKPOINT_DIR, "scalers.joblib")


def train(
    symbol: str | None = None,
    epochs: int = 200,
    batch_size: int = 32,
    lr: float = 1e-3,
    patience: int = 10,
):
    """Entraîne le modèle CNN1D.

    Args:
        symbol: Symbole à utiliser (ex: "BTC"). None = toutes les cryptos.
        epochs: Nombre maximum d'epochs.
        batch_size: Taille des batchs.
        lr: Learning rate initial.
        patience: Nombre d'epochs sans amélioration avant arrêt.
    """
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    device = torch.device("mps" if torch.mps.is_available() else "cpu")
    print(f"Device: {device}")

    # Données
    train_loader, val_loader, feature_scaler, target_scaler = prepare_data(
        symbol=symbol, batch_size=batch_size
    )

    # Modèle
    model = CNN1D(window_size=WINDOW_SIZE, n_features=len(FEATURE_COLUMNS)).to(device)
    criterion = nn.HuberLoss(delta=1.0)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=10
    )

    # Training loop
    best_val_loss = float("inf")
    epochs_without_improvement = 0
    history = {"train_loss": [], "val_loss": []}

    for epoch in range(1, epochs + 1):
        # --- Train ---
        model.train()
        train_loss = 0.0
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)

            optimizer.zero_grad()
            preds = model(X_batch)
            loss = criterion(preds, y_batch)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * len(X_batch)

        train_loss /= len(train_loader.dataset)

        # --- Validation ---
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                preds = model(X_batch)
                loss = criterion(preds, y_batch)
                val_loss += loss.item() * len(X_batch)

        val_loss /= len(val_loader.dataset)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        scheduler.step(val_loss)

        current_lr = optimizer.param_groups[0]["lr"]
        print(
            f"Epoch {epoch:3d}/{epochs} | "
            f"Train Loss: {train_loss:.6f} | "
            f"Val Loss: {val_loss:.6f} | "
            f"LR: {current_lr:.1e}"
        )

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            epochs_without_improvement = 0
            torch.save(
                {"model_state": model.state_dict(), "history": history},
                CHECKPOINT_PATH,
            )
            joblib.dump(
                {"feature_scaler": feature_scaler, "target_scaler": target_scaler},
                SCALERS_PATH,
            )
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= patience:
                print(f"Early stopping at epoch {epoch}")
                break

    # Charger les meilleurs poids et scalers
    checkpoint = torch.load(CHECKPOINT_PATH, weights_only=False)
    model.load_state_dict(checkpoint["model_state"])
    scalers = joblib.load(SCALERS_PATH)
    print(f"Training terminé. Best val loss: {best_val_loss:.6f}")

    return model, scalers["feature_scaler"], scalers["target_scaler"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entraînement CNN1D")
    parser.add_argument("--symbol", type=str, default=None, help="Symbole (ex: BTC)")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=10)
    args = parser.parse_args()

    train(
        symbol=args.symbol,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        patience=args.patience,
    )
