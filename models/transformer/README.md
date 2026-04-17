!!!AI Generated README (because i don't have much time)!!!
# Transformer Model

Transformer encoder for cryptocurrency forward-return regression. Processes fixed-length windows of normalized technical features as sequences to predict the N-bar forward return.


## Quick Start

```bash
# Train on all symbols (1d timeframe)
python -m models.transformer.training

# Train on all symbols (1h timeframe)
python -m models.transformer.training --timeframe 1h

# Train on a single symbol
python -m models.transformer.training --symbol BTC --timeframe 1d --epochs 100 --batch-size 32 --lr 1e-3 --patience 7

# Evaluate (uses auto-detected checkpoint path)
python -m models.transformer.evaluation --timeframe 1d
python -m models.transformer.evaluation --symbol BTC --timeframe 1h

# Evaluate from a specific checkpoint
python -m models.transformer.evaluation --timeframe 1h --model-path models/transformer/checkpoints/1h/best_model.pth
```

---

## Architecture

Input tensor shape: `(batch, window_size, n_features)`

```
Input (batch, window, n_features)
  └── Linear projection     →  (batch, window, d_model)    feature embedding
  └── Positional Encoding   →  (batch, window, d_model)    temporal position
  └── N × Encoder Layer     →  (batch, window, d_model)    self-attention + FFN
  └── AdaptiveAvgPool       →  (batch, d_model, pool_size) temporal compression
  └── Flatten               →  (batch, d_model × pool_size)
  └── MLP head              →  (batch, 1)                  predicted forward return
```

### Input projection

A single `nn.Linear(n_features → d_model)` maps raw feature vectors into the Transformer's embedding space before positional encoding.

### Positional encoding

Standard sinusoidal encoding (Vaswani et al., 2017) added to the projected embeddings.  
Shape: `(1, window_size, d_model)` — broadcast over batch.

### Transformer encoder layers

`channels` tuple reused as `(d_model, nhead, num_layers)` — ensures config.py compatibility.

Each layer applies: **Pre-LN** variant (`norm_first=True`) for training stability:
`LayerNorm → Multi-Head Self-Attention → residual → LayerNorm → FFN(d_model × 4) → residual`

| Config key | 1d default | 1h default | Description |
|---|---|---|---|
| `d_model` | 64 | 128 | Embedding / attention dimension |
| `nhead` | 4 | 8 | Number of attention heads (must divide d_model) |
| `num_layers` | 3 | 4 | Number of stacked encoder layers |
| `dropout_conv` | 0.1 | 0.1 | Dropout inside encoder layers |

> **Constraint**: `d_model % nhead == 0` is required by `nn.MultiheadAttention`.  
> All default configs in `config.py` satisfy this.

### Adaptive average pooling

Same as the CNN: `AdaptiveAvgPool1d(pool_size)` compresses the temporal axis.  
**MPS constraint**: `window_size % pool_size == 0`.

| Timeframe | window_size | pool_size | Compression |
|---|---|---|---|
| 1d | 30 | 5 | 6× |
| 1h | 72 | 8 | 9× |

### MLP regression head

Identical to the CNN head:

```
Linear(d_model × pool_size → 32) → ReLU → Dropout(0.3) → Linear(32 → 16) → ReLU → Linear(16 → 1)
```

Output: single scalar in **scaled space** (requires `target_scaler.inverse_transform()`).

---

## config.py — Required Changes

The `channels` tuple now encodes `(d_model, nhead, num_layers)` instead of CNN channel counts.  
Update `CNN_CONFIGS` (or add a `TRANSFORMER_CONFIGS` dict) accordingly:

```python
TRANSFORMER_CONFIGS = {
    "1d": {
        "channels": (64, 4, 3),      # d_model=64, nhead=4, num_layers=3
        "kernel_sizes": (3, 3, 3),   # ignored — kept for checkpoint compat
        "dropout_conv": 0.1,
        "dropout_fc": 0.3,
        "pool_size": 5,
    },
    "1h": {
        "channels": (128, 8, 4),     # d_model=128, nhead=8, num_layers=4
        "kernel_sizes": (5, 5, 3),   # ignored
        "dropout_conv": 0.1,
        "dropout_fc": 0.3,
        "pool_size": 8,
    },
}
```

The `kernel_sizes` field is accepted but silently ignored by `Transformer.py` — it is only stored in the checkpoint for forward compatibility.

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

Identical to the CNN:

| Parameter | Value | Rationale |
|---|---|---|
| Loss | HuberLoss(delta=1.0) | Reduces outlier influence vs MSE |
| Optimizer | Adam | weight_decay=1e-4 |
| LR scheduler | ReduceLROnPlateau | factor=0.5, patience=5 |
| Early stopping | patience=7 | Saves best checkpoint |

### Data preprocessing pipeline

Unchanged — `data_preparator.py` is identical to the CNN version.

### Checkpoint format

`best_model.pth` keys are identical to the CNN checkpoint:

| Key | Type | Content |
|---|---|---|
| `model_state` | OrderedDict | `model.state_dict()` |
| `history` | dict | `{"train_loss": [...], "val_loss": [...]}` |
| `timeframe` | str | e.g. "1d" |
| `window_size` | int | e.g. 30 |
| `cnn_cfg` | dict | Full architecture config (channels, pool_size, dropout…) |
| `n_features` | int | Number of input features |

The model is fully reconstructable from the checkpoint alone.

---

## Evaluation

`evaluation.py` is a thin wrapper around `utils.evaluation.run_evaluation()` — identical behavior to the CNN evaluator.

**Metrics**: MSE, RMSE, MAE, R², Direction Accuracy  
**Plots** saved to `models/transformer/results/{timeframe}/`: same set as the CNN (training curves, scatter, residuals, rolling direction accuracy, price reconstruction).

---

## File Structure

```
models/transformer/
  ├── Transformer.py       # nn.Module: CNN1D (Transformer encoder, same interface)
  ├── data_preparator.py   # prepare_data() — identical to CNN version
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

**Why keep the class named `CNN1D`?**  
Preserves full compatibility with `training.py`, `evaluation.py`, and saved checkpoints. The name is an implementation detail; the interface and checkpoint format are unchanged.

**Why Pre-LN (`norm_first=True`)?**  
Post-LN Transformers (original paper) are prone to gradient instability in early training. Pre-LN applies LayerNorm before the attention and FFN sub-layers, providing smoother gradients and removing the need for learning rate warm-up.

**Why sinusoidal positional encoding over learned?**  
Financial windows have a fixed, meaningful temporal structure — each position represents a real time step. Sinusoidal encoding is parameter-free, generalizes to unseen sequence lengths, and avoids over-fitting position embeddings to training data distribution shifts.

**Why AdaptiveAvgPool instead of [CLS] token pooling?**  
A [CLS] token aggregates via attention, which requires the model to learn how to pool. `AdaptiveAvgPool1d` provides deterministic, inductive pooling that mirrors the CNN baseline and avoids adding extra parameters. It also satisfies the MPS `window_size % pool_size == 0` constraint.

**Parameter count comparison (1d, default configs)**

| Model | d_model / channels | Params (approx.) |
|---|---|---|
| CNN1D | (16, 32, 64) | ~45 k |
| Transformer | (64, 4, 3) | ~180 k |

The Transformer has more parameters. Increase dropout or reduce `num_layers`/`d_model` if overfitting is observed on small datasets.
