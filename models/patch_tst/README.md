# PatchTST Model

Transformer-based architecture for cryptocurrency forward-return regression. Segments the input time series into overlapping patches, projects each patch into a latent space, then applies a Transformer Encoder to capture inter-patch dependencies before regressing the predicted return.

## Quick Start

```bash
# Train on all symbols (1d timeframe)
python -m models.patch_tst.training

# Train on all symbols (1h timeframe)
python -m models.patch_tst.training --timeframe 1h

# Train on a single symbol
python -m models.patch_tst.training --symbol BTC --timeframe 1d --epochs 200 --batch-size 32 --lr 1e-4 --patience 15

# Evaluate (uses auto-detected checkpoint path)
python -m models.patch_tst.evaluation --timeframe 1d
python -m models.patch_tst.evaluation --symbol BTC --timeframe 1h

# Evaluate from a specific checkpoint
python -m models.patch_tst.evaluation --timeframe 1d --model-path models/patch_tst/checkpoints/1d/best_model.pth
```

---

## Architecture

Input tensor shape: `(batch, window_size, n_features)`

```
Input (batch, window, features)
  └── Patching           →  (batch, num_patches, patch_len × n_features)
  └── Linear projection  →  (batch, num_patches, d_model)
  └── + Positional embed  →  (batch, num_patches, d_model)
  └── Transformer Encoder →  (batch, num_patches, d_model)
  └── Flatten             →  (batch, num_patches × d_model)
  └── MLP head            →  (batch, 1)   predicted forward return
```

### Patching

The input sequence is split into overlapping patches using `torch.Tensor.unfold()`:

| Timeframe | window_size | patch_len | stride | num_patches | patch_dim |
|---|---|---|---|---|---|
| 1d | 30 | 6 | 3 | 9 | 96 (6 × 16) |
| 1h | 72 | 12 | 6 | 11 | 288 (12 × 24) |

Each patch captures `patch_len` consecutive timesteps with all features for the selected timeframe (`n_features=16` in `1d`, `n_features=24` in `1h`), and adjacent patches overlap by `patch_len - stride` timesteps. This overlap ensures no information is lost at patch boundaries.

### Projection + positional embedding

Each flattened patch vector is linearly projected to `d_model` dimensions. A learnable positional embedding (initialized with truncated normal, std=0.02) is added to encode patch ordering.

### Transformer Encoder

| Parameter | 1d | 1h |
|---|---|---|
| d_model | 64 | 64 |
| n_heads | 4 | 4 |
| n_layers | 3 | 3 |
| d_ff | 128 | 128 |
| dropout | 0.2 | 0.2 |
| activation | GELU | GELU |

Uses `nn.TransformerEncoderLayer` with `batch_first=True`. Self-attention allows each patch to attend to all other patches, capturing long-range dependencies across the window.

### MLP regression head

After flattening to `num_patches × d_model`:

```
LayerNorm(num_patches × d_model)
  → Linear(num_patches × d_model → d_model) → GELU → Dropout(0.3)
  → Linear(d_model → 32) → GELU
  → Linear(32 → 1)
```

Output is a single scalar: the predicted N-bar forward return in **scaled space**.

### Weight initialization

- All linear layers: Xavier normal initialization
- Last linear layer: Xavier normal with `gain=2.0` (larger variance to cover the target range)
- Positional embedding: truncated normal (std=0.02)

---

## Training

### CLI arguments

| Argument | Default | Description |
|---|---|---|
| `--symbol` | None (all) | Single symbol to train on (e.g. BTC) |
| `--timeframe` | 1d | Timeframe |
| `--epochs` | 200 | Maximum training epochs |
| `--batch-size` | 32 | Batch size |
| `--lr` | 1e-4 | Initial learning rate |
| `--patience` | 15 | Early stopping patience |
| `--seed` | 42 | Random seed (random, numpy, torch) |

### Hyperparameters

| Parameter | Value | Rationale |
|---|---|---|
| Loss | HuberLoss(delta=1.0) | Quadratic for small errors, linear for large — reduces outlier influence |
| Optimizer | AdamW | weight_decay=1e-3 (stronger regularization than CNN due to more parameters) |
| LR scheduler | CosineAnnealingLR | T_max=epochs — smooth decay to near-zero LR |
| Gradient clipping | max_norm=1.0 | Prevents gradient explosion in Transformer layers |
| Early stopping | patience=15 | More patient than CNN (Transformers converge slower) |

### Data preprocessing pipeline (`data_preparator.py`)

1. Load processed CSVs via `utils.dataset_loader`
2. Compute N-bar forward return labels per symbol: `close[t+N] / close[t] - 1` (grouped by symbol to prevent cross-asset contamination)
3. Drop rows with no future price available
4. Build sliding windows per symbol (`build_windows`)
5. Chronological 80/20 train/val split per symbol (symbols with insufficient history are skipped)
6. Winsorize targets to 1st/99th percentile (train stats only)
7. Winsorize features to 1st/99th percentile per feature (train stats only, applied on flattened view)
8. `RobustScaler` on features (median/IQR normalization, fitted on flattened train features)
9. `StandardScaler` on targets (centers returns around 0)
10. Convert to PyTorch `float32` tensors via `TensorDataset`/`DataLoader`
11. Scalers + clip bounds saved alongside checkpoint in `scalers.joblib`

The train `DataLoader` shuffles; the val `DataLoader` does not.

### Checkpoint format

`best_model.pth` is a PyTorch dict with keys:

| Key | Type | Content |
|---|---|---|
| `model_state` | OrderedDict | `model.state_dict()` |
| `history` | dict | `{"train_loss": [...], "val_loss": [...]}` |
| `timeframe` | str | e.g. "1d" |
| `window_size` | int | e.g. 30 |
| `patchtst_cfg` | dict | Full architecture config (patch_len, stride, d_model, n_heads, n_layers, d_ff, dropout) |
| `n_features` | int | Number of input features per timestep |
| `seed` | int | Random seed used |

The architecture is fully reconstructable from the checkpoint — no external config needed.

---

## Evaluation

`evaluation.py` loads the checkpoint, reconstructs the model via `load_model()`, and delegates to `utils.evaluation.run_evaluation()`.

**Metrics** (printed and returned as dict):

| Metric | Description |
|---|---|
| MSE | Mean Squared Error on returns |
| RMSE | Root MSE |
| MAE | Mean Absolute Error |
| R² | Coefficient of determination |
| Direction Accuracy | % of samples where `sign(pred) == sign(actual)` |

**Plots** saved to `models/patch_tst/results/{timeframe}/`:

| File | Description |
|---|---|
| `training_curves.png` | Train vs val loss per epoch |
| `predictions_vs_actual.png` | Predicted and actual returns over time |
| `scatter.png` | Predicted vs actual scatter with 45° ideal line |
| `residuals.png` | Residual histogram + temporal residual plot |
| `direction_accuracy.png` | Rolling 50-sample direction accuracy vs 50% baseline |
| `price_vs_predicted.png` | Price reconstructed from predicted returns vs actual price |

---

## File Structure

```
models/patch_tst/
  ├── __init__.py
  ├── PatchTST.py          # nn.Module: PatchTST
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

**Why patches instead of per-timestep tokens?**
Tokenizing each timestep individually produces `window_size` tokens (30 for 1d, 72 for 1h), leading to expensive O(n²) self-attention. Patching reduces the sequence length to 9–11 tokens while preserving local temporal structure within each patch. This makes training faster and more memory-efficient.

**Why overlapping patches?**
With `stride < patch_len`, adjacent patches share timesteps. This prevents information loss at patch boundaries — a pattern spanning the boundary of two non-overlapping patches would be split across tokens with no shared context.

**Why CosineAnnealingLR instead of ReduceLROnPlateau?**
Transformers benefit from smooth, predictable LR schedules. CosineAnnealing provides a monotonic decay that avoids the abrupt LR drops of plateau-based schedulers, which can destabilize attention weight updates.

**Why AdamW instead of Adam?**
Decoupled weight decay (AdamW) is the standard for Transformer training. Unlike L2 regularization in Adam, AdamW applies weight decay directly to parameters regardless of gradient magnitude, providing more consistent regularization across layers with different gradient scales.

**Why gradient clipping at 1.0?**
Transformer attention scores can produce sharp gradients during early training, especially with small datasets. Clipping at max_norm=1.0 prevents catastrophic gradient spikes without significantly slowing convergence.
