# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
pip install -r requirements.txt

# Step 1: Fetch data from Binance and build feature dataset
python -m data.main

# Step 2: Train a model (example: CNN)
python -m models.cnn.training
python -m models.cnn.training --symbol BTC --epochs 100 --batch-size 32 --lr 1e-3 --patience 10

# Step 3: Evaluate a model (example: CNN)
python -m models.cnn.evaluation
python -m models.cnn.evaluation --symbol BTC --model-path models/cnn/checkpoints/best_model.pth

# Step 4: Backtesting on historical data
python -m testing.backtesting --model cnn --symbol BTC --capital 10000 --threshold 0.01

# Step 5: Realtime testing with live Binance data
python -m testing.realtime_testing --symbol BTC/USDT --model cnn --capital 10000 --rrr 2.0
python -m testing.realtime_testing --config testing/config.json

# Step 6: Backtest mode (simulate realtime on historical data)
python -m testing.realtime_testing --backtest --symbol BTC --model cnn --rrr 2.0
python -m testing.realtime_testing --backtest --symbol BTC --start-date 2024-01-01 --end-date 2024-12-31 --speed 0.01
```

All scripts must be run from the repo root so that relative imports (e.g. `from config import ...`) resolve correctly.

## Architecture

Crypto price-direction ML pipeline: **data → features → model**.

### Data flow

```
Binance API (ccxt)
  └─ data/fetcher.py           → data/raw/<SYMBOL>.csv
        └─ data/features/pipeline.py  (build_features)
              ├─ candle_features.py
              ├─ momentum_features.py
              ├─ trend_features.py
              ├─ oscillator_features.py
              └─ volume_features.py
        └─ data/labeling/labeler.py   (add_labels)
        └─ data/main.py               → output/<SYMBOL>.csv + output/full_dataset.csv
```

### Model pipeline

```
utils/dataset_loader.py              (load_symbol / load_all)
  └─ data/preprocessing/builder.py   (build_windows → X shape: [n, 30, 20])
        └─ models/<type>/data_preparator.py  (prepare_data → DataLoaders + scalers)
              └─ models/<type>/training.py    → models/<type>/checkpoints/best_model.pth + scalers.joblib
              └─ models/<type>/evaluation.py  → models/<type>/results/*.png
                    └─ utils/evaluation.py    (generic: metrics, plots, run_evaluation)
              └─ testing.backtesting          (simulate trading on historical data)
              └─ testing.realtime_testing     (paper trading with live Binance data)
```

### Convention pour nouveaux modèles

Chaque type de modèle (cnn, lstm, gru, etc.) suit la même structure :
```
models/<type>/
  ├─ <Model>.py          # Architecture (nn.Module)
  ├─ data_preparator.py  # Préparation des données spécifique
  ├─ training.py         # Boucle d'entraînement
  ├─ evaluation.py       # Thin wrapper → appelle utils.evaluation.run_evaluation()
  ├─ checkpoints/        # best_model.pth + scalers.joblib (gitignored)
  └─ results/            # Graphiques d'évaluation (*.png)
```

L'évaluation est centralisée dans `utils/evaluation.py` : métriques (MSE, RMSE, MAE, R², Direction Accuracy) et graphiques (training curves, predictions vs actual, scatter, residuals, rolling direction accuracy). Chaque modèle fournit un `load_model()` spécifique et un `evaluate()` wrapper.

### Key design decisions

- **20 features** per daily candle (4 candle structure + 5 momentum returns + 4 EMA ratios + 4 oscillators + 3 volume/volatility). All normalized as ratios/percentages — no absolute prices.
- **Window size = 30 days** (`WINDOW_SIZE` in `config.py`), producing tensors of shape `(batch, 30, 20)`.
- **Regression target**: 3-day forward return (continuous `%`), not the discrete `-1/0/1` label from `labeler.py`.
- **Per-symbol windowing**: forward returns and sliding windows are computed per symbol via `groupby("symbol")` to avoid cross-symbol contamination at DataFrame boundaries.
- **Outlier clipping**: features and targets are winsorized at 1st/99th percentile (fitted on train only) before scaling.
- **Scalers**: `RobustScaler` (median/IQR) for features, `StandardScaler` for targets. Both fitted on train only and saved alongside the model checkpoint via `joblib`.
- **Loss**: `HuberLoss(delta=1.0)` — linear for large errors, prevents outlier-driven gradient domination.
- **CNN1D architecture**: 3 conv blocks (20→32→64→128 channels), `AdaptiveAvgPool1d(5)` (preserves 5 temporal points), MLP head (640→64→32→1).
- **Device**: uses `mps` (Apple Silicon) when available, falls back to `cpu`.
- **Temporal split**: 80/20 chronological split, no shuffle; only the train `DataLoader` shuffles.
- **Early stopping** with `patience=10`. LR scheduler: `ReduceLROnPlateau(factor=0.5, patience=10)`.

### Configuration (`config.py`)

All global constants: `SYMBOLS`, `TIMEFRAME`, `START_DATE`, `LABEL_THRESHOLD`, `PREDICTION_HORIZON`, `WINDOW_SIZE`, `RAW_DATA_PATH`, `OUTPUT_PATH`.

### Code conventions

- Comments and docstrings may be in French or English — follow the surrounding file's convention.
- Section separators use `# ----- Section Name -----`.
- Type hints required on all public functions.
- Imports ordered: stdlib → third-party → local, with blank lines between groups.
