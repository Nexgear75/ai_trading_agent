# CNN-BiLSTM-AM Model

Hybrid architecture combining a **CNN1D feature extractor**, a **bidirectional LSTM**, and a **2-layer additive attention mechanism**. Designed to capture both local pattern structure (convolutions) and long-range temporal dependencies (BiLSTM) with learned weighting over which timesteps matter most (attention).

## Quick Start

```bash
# Train on all symbols (1d timeframe)
python -m models.cnn_bilstm_am.training

# Train on all symbols (1h timeframe)
python -m models.cnn_bilstm_am.training --timeframe 1h

# Train on a single symbol
python -m models.cnn_bilstm_am.training --symbol BTC --timeframe 1h --epochs 100 --batch-size 16

# Evaluate
python -m models.cnn_bilstm_am.evaluation --timeframe 1d
python -m models.cnn_bilstm_am.evaluation --symbol BTC --timeframe 1h
```

---

## Architecture

Input tensor shape: `(batch, window_size, n_features)`

```
Input  (batch, window, features)
  └── Stage 1: CNN backbone   →  (batch, 64, pool_size)   local pattern extraction
  └── Stage 2: BiLSTM         →  (batch, pool_size, 128)  bidirectional sequences
  └── Stage 3: Attention      →  (batch, 128)             weighted context vector
  └── Stage 4: MLP head       →  (batch, 1)               predicted forward return
```

### Stage 1 — CNN backbone

Identical block structure to CNN1D (Conv1D → BatchNorm1D → ReLU → Dropout1D), channels 16→32→64.

**Key difference from standalone CNN1D**: `pool_size` is larger to preserve more timesteps for the LSTM.

| Timeframe | window_size | CNN1D pool_size | BiLSTM-AM pool_size | Timesteps → LSTM |
|---|---|---|---|---|
| 1d | 30 | 5 | 15 | 15 |
| 1h | 72 | 8 | 24 | 24 |

The BiLSTM needs more sequential context to learn temporal patterns; averaging down to only 5 timesteps would discard too much structure.

### Stage 2 — Bidirectional LSTM

```python
nn.LSTM(input_size=64, hidden_size=64, num_layers=1, bidirectional=True, batch_first=True)
```

- Processes the `pool_size` CNN feature vectors as a sequence
- Output: `(batch, pool_size, 128)` — 128 = 2 × 64 (forward hidden + backward hidden concatenated at each timestep)
- Single layer (`lstm_layers=1`), no inter-layer dropout

**Why bidirectional?** Within a fixed window, the model has access to the full sequence. Bidirectionality lets the LSTM learn patterns that are clearer in both directions — e.g., a local peak is also a reversal baseline when scanned right-to-left. This is not future data leakage; it is context within the already-observed window.

### Stage 3 — Two-layer additive attention (Bahdanau-style)

```python
# Score computation
scores = tanh(Linear(128 → 64)(lstm_out))    # (batch, pool_size, 64)
scores = Linear(64 → 1)(scores)              # (batch, pool_size, 1) — logits
alpha  = softmax(scores, dim=1)              # (batch, pool_size, 1) — weights sum to 1
context = sum(alpha × lstm_out, dim=1)       # (batch, 128) — weighted average
```

The `alpha` weights are interpretable: a score near 1.0 for timestep `t` means the model treats that timestep as most informative. This gives CNN-BiLSTM-AM a transparency advantage over the plain CNN, where all timesteps are averaged equally.

**Why 2-layer instead of dot-product attention?** The intermediate `tanh` layer allows attention scores to be non-linear functions of LSTM outputs, enabling more expressive weighting of complex temporal patterns.

### Stage 4 — MLP regression head

```
Linear(128 → 64) → ReLU → Dropout(0.3) → Linear(64 → 32) → ReLU → Linear(32 → 1)
```

The head is deeper and wider than CNN1D's head (128→64→32→1 vs 64×pool→32→16→1) to match the richer 128-dimensional context vector from the BiLSTM.

---

## Weight Initialization

CNN-BiLSTM-AM uses explicit weight initialization (CNN1D does not):

| Layer type | Initialization | Reason |
|---|---|---|
| `Conv1D` | Kaiming Normal (`nonlinearity="relu"`) | Accounts for ReLU's half-rectification; preserves signal variance through deep conv stacks |
| `Linear` | Xavier Normal | Balances variance across linear/tanh layers |
| Output `Linear` | Xavier Normal with `gain=2.0` | Prevents mean-predictor collapse at initialization |

**Why gain=2.0 on the output layer?** Without this, fresh models produce near-zero outputs and collapse to predicting the mean return (~0%) for all inputs. The "mean predictor" trap causes the loss to be near-zero immediately, giving the optimizer almost no gradient signal to work with. The higher gain pushes initial predictions into the return distribution so the optimizer has meaningful gradients from epoch 1.

---

## Training

### CLI arguments

Same as CNN1D: `--symbol`, `--timeframe`, `--epochs` (default 50), `--batch-size` (default 16), `--lr` (default 1e-3), `--patience` (default 7).

### Differences from CNN1D

| Parameter | CNN1D | CNN-BiLSTM-AM | Reason |
|---|---|---|---|
| Loss | HuberLoss(delta=1.0) | SmoothL1Loss(beta=2.0) | Larger beta stays quadratic for errors < 2% (expected return range); less harsh near zero |
| Optimizer | Adam | AdamW | AdamW applies weight decay correctly (decoupled from gradient norm, unlike Adam) |
| LR scheduler patience | 5 | 10 | BiLSTM training dynamics are slower to plateau — needs more epochs to validate improvement |
| Gradient clipping | None | `clip_grad_norm_(max_norm=5.0)` | LSTMs are susceptible to exploding gradients; clipping rescales the gradient vector if its norm exceeds 5.0 |

`SmoothL1Loss(beta=2.0)` is mathematically equivalent to `HuberLoss(delta=2.0)`. The choice of name follows PyTorch convention for this model but the behavior is identical.

### Data preprocessing

Identical pipeline to CNN1D — see `models/cnn/README.md`. The `data_preparator.py` for this model imports `prepare_data` directly from `models.cnn.data_preparator` (shared preprocessing).

### Checkpoint format

`best_model.pth` is a PyTorch dict with keys:

| Key | Type | Content |
|---|---|---|
| `model_state` | OrderedDict | `model.state_dict()` |
| `history` | dict | `{"train_loss": [...], "val_loss": [...]}` |
| `timeframe` | str | e.g. "1h" |
| `window_size` | int | e.g. 72 |
| `model_cfg` | dict | Full architecture config (channels, pool_size, lstm_hidden, lstm_layers, dropout) |
| `n_features` | int | Number of input features |

Note: this model uses the key `model_cfg` — CNN1D uses `cnn_cfg`. Both contain equivalent architecture dicts.

---

## Evaluation

Same interface as CNN1D. Plots saved to `models/cnn_bilstm_am/results/{timeframe}/`.

---

## File Structure

```
models/cnn_bilstm_am/
  ├── CNN_BiLSTM_AM.py     # nn.Module: CNNBiLSTMAM
  ├── data_preparator.py   # Thin wrapper → models.cnn.data_preparator.prepare_data
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

## CNN1D vs CNN-BiLSTM-AM — When to Use Which

| Consideration | CNN1D | CNN-BiLSTM-AM |
|---|---|---|
| Training speed | Fast | ~2–3× slower (LSTM is sequential, not parallelizable) |
| Parameter count | Smaller | ~2× larger |
| Strength | Local pattern recognition (candle structures, short momentum) | Long-range sequence dependencies across the window |
| Overfitting risk | Lower | Higher (needs more data to generalize) |
| Interpretability | Low | Medium — attention weights `alpha` are inspectable |
| Minimum recommended data | Small datasets (< 5,000 samples) | Larger datasets (> 10,000 samples) |
| Best timeframe | 1d (30-bar windows with limited structure) | 1h / 4h (longer windows with richer sequences) |

For the 1d timeframe with 10 symbols and ~1,500 bars each (~15,000 training samples after windowing), CNN1D is often sufficient and trains faster. CNN-BiLSTM-AM shows more meaningful gains on 1h data where the 72-bar window contains richer sequential structure for the BiLSTM to exploit.

**Recommended workflow**: train CNN1D first as a baseline. If direction accuracy on validation plateaus below 55%, try CNN-BiLSTM-AM, especially on 1h.
