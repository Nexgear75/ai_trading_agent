# CNN1D Model

Convolutional neural network for cryptocurrency forward-return regression. Processes fixed-length windows of normalized technical features as 1D time series to predict the N-bar forward return.

## Quick Start

```bash
# Train on all symbols (1d timeframe)
python -m models.cnn.training

# Train on all symbols (1h timeframe)
python -m models.cnn.training --timeframe 1h

# Train on a single symbol
python -m models.cnn.training --symbol BTC --timeframe 1d --epochs 100 --batch-size 32 --lr 1e-3 --patience 7

# Evaluate (uses auto-detected checkpoint path)
python -m models.cnn.evaluation --timeframe 1d
python -m models.cnn.evaluation --symbol BTC --timeframe 1h

# Evaluate from a specific checkpoint
python -m models.cnn.evaluation --timeframe 1h --model-path models/cnn/checkpoints/1h/best_model.pth
```

---

## Architecture

Input tensor shape: `(batch, window_size, n_features)`

The `forward()` method transposes internally to `(batch, n_features, window_size)` before passing to Conv1D layers.

```
Input (batch, window, features)
  └── 3-block Conv1D    →  (batch, 64, window)     local pattern features
  └── AdaptiveAvgPool   →  (batch, 64, pool_size)   temporal compression
  └── Flatten           →  (batch, 64 × pool_size)
  └── MLP head          →  (batch, 1)               predicted forward return
```

### Conv1D blocks

Each of the three blocks applies: `Conv1D → BatchNorm1D → ReLU → Dropout1D`

All convolutions use `padding="same"` — the temporal dimension is preserved through all three blocks.

| Block | in_channels | out_channels | kernel (1d) | kernel (1h) | Dropout |
|---|---|---|---|---|---|
| 1 | n_features | 16 | 3 | 5 | 0.2 |
| 2 | 16 | 32 | 3 | 5 | 0.2 |
| 3 | 32 | 64 | 3 | 3 | 0.1 |

Larger kernels for 1h (5 vs 3) capture wider short-term patterns in hourly data, where the market context spans more bars.

### Adaptive average pooling

`AdaptiveAvgPool1d(pool_size)` compresses the temporal axis from `window_size` to `pool_size` timesteps.

**MPS constraint**: `window_size % pool_size == 0` is required for Apple Silicon MPS compatibility. Pool sizes in `config.py` are chosen to satisfy this.

| Timeframe | window_size | pool_size | Compression |
|---|---|---|---|
| 1d | 30 | 5 | 6× |
| 1h | 72 | 8 | 9× |

### MLP regression head

After flattening to `64 × pool_size`:

```
Linear(64 × pool_size → 32) → ReLU → Dropout(0.3) → Linear(32 → 16) → ReLU → Linear(16 → 1)
```

Output is a single scalar: the predicted N-bar forward return in **scaled space** (requires `target_scaler.inverse_transform()` to convert to a real percentage).

---

## Training

### CLI arguments

| Argument | Default | Description |
|---|---|---|
| `--symbol` | None (all) | Single symbol to train on (e.g. BTC) |
| `--timeframe` | 1d | Timeframe |
| `--epochs` | 50 | Maximum training epochs |
| `--batch-size` | 16 | Batch size |
| `--lr` | 1e-3 | Initial learning rate |
| `--patience` | 7 | Early stopping patience |

### Hyperparameters

| Parameter | Value | Rationale |
|---|---|---|
| Loss | HuberLoss(delta=1.0) | Quadratic for small errors, linear for large — reduces outlier influence vs MSE |
| Optimizer | Adam | weight_decay=1e-4 |
| LR scheduler | ReduceLROnPlateau | factor=0.5, patience=5 — halves LR if val loss stagnates |
| Early stopping | patience=7 | Saves best checkpoint; halts when val loss does not improve |

### Data preprocessing pipeline (`data_preparator.py`)

1. Load processed CSVs via `utils.dataset_loader`
2. Compute N-bar forward return labels per symbol: `close[t+N] / close[t] - 1` (grouped by symbol to prevent cross-asset contamination)
3. Drop last `prediction_horizon` rows (no future price available)
4. Build sliding windows per symbol (`build_windows`)
5. Chronological 80/20 train/val split (no data shuffle on split boundary)
6. Winsorize features to 1st/99th percentile (train stats only — prevents look-ahead bias)
7. Winsorize targets to 1st/99th percentile
8. `RobustScaler` on features (median/IQR normalization — robust to remaining outliers after clipping)
9. `StandardScaler` on targets (centers returns around 0)
10. Scalers + clip bounds saved alongside checkpoint in `scalers.joblib`

The train `DataLoader` shuffles; the val `DataLoader` does not.

### Checkpoint format

`best_model.pth` is a PyTorch dict with keys:

| Key | Type | Content |
|---|---|---|
| `model_state` | OrderedDict | `model.state_dict()` |
| `history` | dict | `{"train_loss": [...], "val_loss": [...]}` |
| `timeframe` | str | e.g. "1d" |
| `window_size` | int | e.g. 30 |
| `cnn_cfg` | dict | Full architecture config (channels, kernels, pool_size, dropout) |
| `n_features` | int | Number of input features |

The architecture is fully reconstructable from the checkpoint — no external config needed.

---

## Evaluation

`evaluation.py` loads the checkpoint, reconstructs the model, and delegates to `utils.evaluation.run_evaluation()`.

**Metrics** (printed and returned as dict):

| Metric | Description |
|---|---|
| MSE | Mean Squared Error on returns |
| RMSE | Root MSE |
| MAE | Mean Absolute Error |
| R² | Coefficient of determination |
| Direction Accuracy | % of samples where `sign(pred) == sign(actual)` |

Direction Accuracy is the most trading-relevant metric: the model only needs to predict the correct direction, not the exact magnitude.

**Plots** saved to `models/cnn/results/{timeframe}/`:

| File | Description |
|---|---|
| `training_curves.png` | Train vs val loss per epoch |
| `predictions_vs_actual.png` | Predicted and actual returns over time |
| `scatter.png` | Predicted vs actual scatter with 45° ideal line |
| `residuals.png` | Residual histogram + temporal residual plot (detects bias drift) |
| `direction_accuracy.png` | Rolling 50-sample direction accuracy vs 50% baseline |
| `price_vs_predicted.png` | Price reconstructed from predicted returns vs actual price |

---

## File Structure

```
models/cnn/
  ├── CNN.py               # nn.Module: CNN1D
  ├── data_preparator.py   # prepare_data() → (train_loader, val_loader, scalers, ...)
  ├── training.py          # train() function + argparse __main__
  ├── evaluation.py        # evaluate() thin wrapper → utils.evaluation.run_evaluation()
  ├── checkpoints/
  │   └── {timeframe}/
  │       ├── best_model.pth
  │       └── scalers.joblib
  └── results/
      └── {timeframe}/
          └── *.png
```

---

## Design Notes

**Why HuberLoss over MSE?**
Crypto returns have fat tails — extreme events (exchange hacks, regulatory news) create outliers that would dominate MSE gradients and push the model toward predicting zero return for safety. HuberLoss with delta=1.0 treats errors larger than ~1 scaled return unit as linear rather than quadratic, capping their influence.

**Why AdaptiveAvgPool instead of MaxPool?**
Financial signals are smoother than image edges. Average pooling preserves the mean activation across a time segment, appropriate for trend-like features. MaxPool would overweight single-bar spike events.

**Why pool_size must divide window_size on MPS?**
Apple's Metal Performance Shaders backend for `AdaptiveAvgPool1d` requires the input length to be an integer multiple of the output length. This is a hardware backend constraint, not a mathematical one. All pool sizes in `config.py` are chosen to satisfy `window_size % pool_size == 0`.
