# XGBoost Model

Gradient-boosted tree ensemble for cryptocurrency forward-return regression. Uses the same windowing and preprocessing pipeline as neural models (sliding windows, clipping, scaling) but flattens 3D tensors into 2D feature vectors for tabular learning.

## Quick Start

```bash
# Train on all symbols (1d timeframe)
python -m models.xgboost.training

# Train on all symbols (1h timeframe)
python -m models.xgboost.training --timeframe 1h

# Train on a single symbol
python -m models.xgboost.training --symbol BTC --timeframe 1d --seed 42

# Evaluate (uses auto-detected checkpoint path)
python -m models.xgboost.evaluation --timeframe 1d
python -m models.xgboost.evaluation --symbol BTC --timeframe 1h

# Evaluate from a specific checkpoint
python -m models.xgboost.evaluation --timeframe 1d --model-path models/xgboost/checkpoints/1d/best_model.json
```

---

## Architecture

XGBoost operates on flat feature vectors, not sequences. The temporal structure captured by sliding windows is preserved implicitly through feature ordering.

```
Input (batch, window_size, n_features)
  └── Flatten           →  (batch, window_size × n_features)
  └── XGBRegressor      →  (batch, 1)    predicted forward return
```

| Timeframe | window_size | n_features | Flat dimension |
|---|---|---|---|
| 1d | 30 | 16 | 480 |
| 1h | 72 | 24 | 1728 |

### Hyperparameters (from `config.py`)

| Parameter | 1d | 1h |
|---|---|---|
| n_estimators | 1000 | 1500 |
| max_depth | 6 | 8 |
| learning_rate | 0.05 | 0.03 |
| early_stopping_rounds | 50 | 80 |
| objective | reg:squarederror | reg:squarederror |
| tree_method | hist | hist |

Early stopping monitors val loss and halts training when no improvement is observed for `early_stopping_rounds` boosting rounds.

---

## Training

### CLI arguments

| Argument | Default | Description |
|---|---|---|
| `--symbol` | None (all) | Single symbol to train on (e.g. BTC) |
| `--timeframe` | 1d | Timeframe |
| `--seed` | 42 | Random seed for reproducibility |

### Data preprocessing pipeline (`data_preparator.py`)

1. Load processed CSVs via `utils.dataset_loader`
2. Compute N-bar forward return labels per symbol: `close[t+N] / close[t] - 1` (grouped by symbol to prevent cross-asset contamination)
3. Drop rows with no future price available
4. Build sliding windows per symbol (`build_windows`)
5. Chronological 80/20 train/val split per symbol (symbols with insufficient history are skipped)
6. **Flatten** 3D windows `(n, window_size, n_features)` → 2D vectors `(n, window_size × n_features)`
7. Winsorize targets to 1st/99th percentile (train stats only)
8. Winsorize features to 1st/99th percentile (train stats only)
9. `RobustScaler` on features (median/IQR normalization)
10. `StandardScaler` on targets (centers returns around 0)
11. Scalers + clip bounds saved alongside checkpoint in `scalers.joblib`

### Checkpoint format

`best_model.json` — native XGBoost JSON format.

`scalers.joblib` — dict with keys:

| Key | Type | Content |
|---|---|---|
| `feature_scaler` | RobustScaler | Fitted on flattened train features |
| `target_scaler` | StandardScaler | Fitted on train targets |
| `clip_bounds` | ndarray | Per-feature (lo, hi) from train 1st/99th percentile |
| `target_clip_bounds` | ndarray | Target (lo, hi) from train 1st/99th percentile |
| `timeframe` | str | e.g. "1d" |
| `window_size` | int | e.g. 30 |
| `train_ratio` | float | 0.8 |
| `prediction_horizon` | int | e.g. 3 |
| `n_features` | int | Number of input features per timestep |
| `feature_columns` | list[str] | Ordered feature names |
| `xgb_cfg` | dict | Full XGBoost hyperparameters |
| `seed` | int | Random seed used |

---

## Evaluation

`evaluation.py` loads the checkpoint and scalers, rebuilds validation windows via `build_val_from_checkpoint()`, then runs inference and generates metrics/plots.

Unlike neural models, XGBoost evaluation does **not** use `run_evaluation()` (which is coupled to PyTorch). Instead, it directly calls the individual metric and plot functions from `utils.evaluation`.

**Metrics** (printed and returned as dict):

| Metric | Description |
|---|---|
| MSE | Mean Squared Error on returns |
| RMSE | Root MSE |
| MAE | Mean Absolute Error |
| R² | Coefficient of determination |
| Direction Accuracy | % of samples where `sign(pred) == sign(actual)` |

**Plots** saved to `models/xgboost/results/{timeframe}/`:

| File | Description |
|---|---|
| `predictions_vs_actual.png` | Predicted and actual returns over time |
| `scatter.png` | Predicted vs actual scatter with 45° ideal line |
| `residuals.png` | Residual histogram + temporal residual plot |
| `direction_accuracy.png` | Rolling 50-sample direction accuracy vs 50% baseline |
| `price_vs_predicted.png` | Price reconstructed from predicted returns vs actual price |

Note: no `training_curves.png` — XGBoost does not produce per-epoch loss curves in the same format as neural models.

---

## File Structure

```
models/xgboost/
  ├── __init__.py
  ├── data_preparator.py   # prepare_data() → (X_train, X_val, y_train, y_val, scalers, ...)
  ├── training.py          # train() function + argparse __main__
  ├── evaluation.py        # evaluate() → metrics dict + plots
  ├── checkpoints/
  │   └── {timeframe}/
  │       ├── best_model.json
  │       └── scalers.joblib
  └── results/
      └── {timeframe}/
          └── *.png
```

---

## Design Notes

**Why XGBoost alongside neural models?**
Gradient-boosted trees offer complementary strengths: faster training, no GPU dependency, natural feature importance, and strong performance on tabular data. XGBoost serves as a non-neural baseline and potentially as an ensemble candidate.

**Why flatten instead of using native 3D handling?**
XGBoost operates on flat feature vectors. Flattening preserves the temporal ordering (features from timestep 0 come first, then timestep 1, etc.), allowing the tree splits to implicitly learn temporal patterns like "feature X at the beginning of the window vs. the end."

**Why `reg:squarederror` instead of HuberLoss?**
XGBoost's built-in `reg:squarederror` combined with feature/target winsorization at the 1st/99th percentile achieves a similar effect to HuberLoss — outliers are clipped before reaching the model, making the quadratic loss well-behaved on the remaining distribution.
