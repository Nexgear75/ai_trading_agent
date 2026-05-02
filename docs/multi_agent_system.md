# Multi-Agent System — Summary

This document summarises how the multi-agent (ensemble) trading system is wired
in this project: from the unified predictor interface, through the registry,
the ensemble aggregator, the four voting strategies, and the backtest
integration.

## 1. Goal

Run several heterogeneous trading models (CNN, BiLSTM, CNN-BiLSTM-AM,
Transformer, PatchTST, XGBoost, LSTM, RL) as independent "agents" on the same
raw market window, then aggregate their predictions into a single trading
signal (`buy` / `sell` / `hold`) using a configurable voting strategy.

Each model is trained independently and stored at:

```
models/<type>/checkpoints/<timeframe>/best_model.pth   (or .json for XGBoost)
models/<type>/checkpoints/<timeframe>/scalers.joblib
```

## 2. Unified predictor interface

File: `models/base_predictor.py`

Every model — supervised or RL — implements the abstract `BasePredictor`
class so the rest of the pipeline (backtest, ensemble, realtime) does not
need to know the model type.

Key contract:

```python
@dataclass
class Prediction:
    signal: str         # "buy" | "sell" | "hold"
    confidence: float   # 0.0 → 1.0
    raw_value: float    # raw model output (predicted return % or action id)

class BasePredictor(ABC):
    def load(self, checkpoint_path: str) -> None: ...
    def predict(self, market_data, portfolio_state=None) -> Prediction: ...
    @property name -> str
    @property timeframe -> str
    @property requires_portfolio_state -> bool
```

## 3. Supervised predictor base

File: `models/supervised_predictor.py`

`SupervisedPredictor` extends `BasePredictor` for all regression-style models.
It owns its own `feature_scaler`, `target_scaler` and `clip_bounds`, so the
ensemble can pass the **same raw window** to every model — each one clips,
scales, infers and inverse-transforms internally.

Public surface used by the ensemble:

- `predict(raw_window) → Prediction`
- `predict_batch(X_raw) → np.ndarray` (vectorised path)

This is the contract that makes "drop-in agents" possible.

## 4. Registry

File: `models/registry.py`

A name → `(module, class)` map with **lazy import**, so only the requested
model's heavy dependencies are loaded.

```python
AVAILABLE_MODELS = {
    "rl":            ("models.rl.predictor",            "RLPredictor"),
    "cnn":           ("models.cnn.predictor",           "CNNPredictor"),
    "lstm":          ("models.lstm.predictor",          "LSTMPredictor"),
    "bilstm":        ("models.bilstm.predictor",        "BiLSTMPredictor"),
    "cnn_bilstm_am": ("models.cnn_bilstm_am.predictor", "CnnBiLstmAmPredictor"),
    "transformer":   ("models.transformer.predictor",   "TransformerPredictor"),
    "patch_tst":     ("models.patch_tst.predictor",     "PatchTSTPredictor"),
    "xgboost":       ("models.xgboost.predictor",       "XGBoostPredictor"),
}

get_predictor(name) -> BasePredictor   # unloaded; call .load(path) next
list_models()       -> list[str]
```

## 5. The Ensemble aggregator

File: `models/ensemble/ensemble_predictor.py`

`EnsemblePredictor` is itself a `BasePredictor`, so an ensemble can be used
anywhere a single model is expected.

### Construction

```python
EnsemblePredictor(
    models:    list[BasePredictor],
    strategy:  "majority_vote" | "weighted_average"
             | "confidence_weighted" | "unanimous",
    weights:   list[float] | None,        # required only for weighted_average
    timeframe: str,                       # shared across all models
)
```

Validates that `strategy` is known and that `len(weights) == len(models)`.

### Loading constituent models

`load()` is a no-op. Use the dedicated:

```python
ensemble.load_models([
    "models/cnn/checkpoints/1d/best_model.pth",
    "models/bilstm/checkpoints/1d/best_model.pth",
    ...
])
```

One checkpoint per model, in the same order as `models`.

### Prediction APIs

| Method                                | Input              | Output                                                    |
|---------------------------------------|--------------------|-----------------------------------------------------------|
| `predict(raw_window)`                 | `(window, n_feat)` | Aggregated `Prediction`                                   |
| `predict_with_breakdown(raw_window)`  | `(window, n_feat)` | `(Prediction, [{model, signal, confidence, raw_value}])`  |
| `predict_batch(X_raw)`                | `(N, window, n)`   | `(N,)` aggregated returns                                 |
| `predict_batch_per_model(X_raw)`      | `(N, window, n)`   | `{model_name: (N,)}` raw return predictions               |
| `predict_batch_full(X_raw)`           | `(N, window, n)`   | `(ensemble (N,), per_model {name: (N,)})` in a single pass|

`predict_batch_full` is the hot path used by the backtester: each constituent
model runs **exactly once** over all windows, then the matrix
`(n_models, N)` is reduced according to the chosen strategy.

### Internal aggregation

- Single-window path: `_aggregate(predictions)` dispatches to the strategy
  function in `strategies.py`.
- Batched path: `_majority_vote_batch` and `_unanimous_batch` are vectorised
  over the `(n_models, N)` matrix; weighted/confidence variants use NumPy
  broadcasting directly.

## 6. Voting strategies

File: `models/ensemble/strategies.py`

All four strategies operate on the list of `Prediction` objects (one per
agent) plus the timeframe-specific signal threshold from
`config.SIGNAL_THRESHOLDS`.

### 6.1 `majority_vote`
- Counts `buy` / `sell` / `hold` votes.
- Tie or `hold` majority → `hold`.
- `raw_value` = mean of all agents' raw predictions.
- `confidence` = mean confidence among the winning side.

### 6.2 `weighted_average` *(default)*
- Normalises `weights` to sum to 1.
- `avg_pred = Σ wᵢ · raw_valueᵢ`.
- Signal: `buy` if `avg_pred > +threshold`, `sell` if `< -threshold`, else `hold`.
- `confidence = min(1, |avg_pred| / (2·threshold))`.

### 6.3 `confidence_weighted`
- Each model's contribution is weighted by its **own** reported confidence.
- Falls back to a simple mean when the total confidence is 0.
- Same threshold/confidence logic as weighted average.

### 6.4 `unanimous` *(most conservative)*
- Trade only when every model emits the same non-`hold` direction.
- Otherwise `hold`. Eliminates conflicting signals entirely.

## 7. Backtest integration

File: `testing/backtesting.py`

### Loading

```python
_build_ensemble(model_types, strategy, weights, timeframe)
```
Walks `model_types`, calls `get_predictor(mt)` for each, sets the timeframe,
loads the matching checkpoint (`best_model.pth` or `.json` for XGBoost) and
returns a ready-to-use `EnsemblePredictor`.

### Single-symbol run

```python
run_ensemble_backtest(
    model_types, symbol,
    strategy="weighted_average",
    weights=None,
    capital=10_000, threshold=0.0,
    allow_short=False, timeframe=DEFAULT_TIMEFRAME,
    entry_fee_pct=None, exit_fee_pct=None,
    _ensemble=None,            # optional pre-loaded ensemble for reuse
)
```

Pipeline:
1. `prepare_raw_windows(symbol, timeframe)` → `(X_raw, y, timestamps, df_prices)`.
2. `ensemble.predict_batch_full(X_raw)` → ensemble preds + per-model preds in one pass.
3. `simulate_trading(...)` for the ensemble, plus an oracle baseline.
4. Re-runs `simulate_trading` for **each** constituent model individually so the
   comparison chart can show per-agent equity curves.
5. Saves two plots in `models/ensemble/results/<timeframe>/`:
   - `ensemble_equity_comparison_<symbol>.png` — equity curves: per-model + ensemble + oracle, plus ensemble drawdown.
   - `ensemble_predictions_<symbol>.png` — predicted return per model, the aggregated ensemble, and the oracle target, with a signal heatmap.

### Multi-symbol run

```python
run_ensemble_backtest_all_symbols(model_types, strategy, weights, ...)
```
Builds the ensemble **once**, then iterates through `config.SYMBOLS`, passing
`_ensemble=ensemble` into `run_ensemble_backtest` so models are not reloaded.
Prints a global summary at the end.

### CLI

```bash
python -m testing.backtesting \
  --model ensemble \
  --ensemble-models cnn,bilstm,cnn_bilstm_am \
  --ensemble-strategy weighted_average \
  --ensemble-weights 0.4,0.3,0.3 \
  --symbol BTC                 # or --all-symbols
```

Flags:
- `--ensemble-models`   comma-separated keys from the registry (required).
- `--ensemble-strategy` one of the four strategies (default `weighted_average`).
- `--ensemble-weights`  comma-separated floats (only used by `weighted_average`).

## 8. End-to-end flow

```
raw window (N, 30, 20)
        │
        ▼
EnsemblePredictor.predict_batch_full
        │
        ├── CNNPredictor.predict_batch  ─┐
        ├── BiLSTMPredictor.predict_batch ┤  each scales/infers internally
        ├── XGBoostPredictor.predict_batch ┘
        │
        ▼
preds_matrix (n_models, N)
        │
        ▼
strategy reduction (majority / weighted / confidence / unanimous)
        │
        ▼
ensemble preds (N,) + per-model preds {name: (N,)}
        │
        ▼
simulate_trading → BacktestResult + plots
```

## 9. Adding a new agent

1. Implement a `BasePredictor` (extend `SupervisedPredictor` for regression
   models) under `models/<type>/predictor.py`.
2. Train it; checkpoint must land at
   `models/<type>/checkpoints/<timeframe>/best_model.pth` with
   `scalers.joblib` next to it.
3. Register it in `models/registry.py::AVAILABLE_MODELS`.
4. It is now usable in any ensemble via
   `--ensemble-models …,<type>,…`.

No changes to `EnsemblePredictor`, `strategies.py` or the backtester are
required.
