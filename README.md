# AI Trading Pipeline

Pipeline de trading algorithmique avec walk-forward cross-validation.
Exécute le cycle complet : données OHLCV → features → entraînement → backtest → métriques.

## Prérequis

- Python 3.11+
- Dépendances : `pip install -r requirements.txt`
- Dev/test : `pip install -r requirements-dev.txt`

## Structure du projet

```
pipeline.py                  # Orchestrateur principal (CLI + run_pipeline)
conftest.py                  # Fixtures pytest partagées
pipeline_test.py             # Tests E2E, reproductibilité, anti-leak, CLI
fullscale_btc_xgboost.yaml   # Config exemple : BTCUSDT / XGBoost
manifest.schema.json         # JSON Schema — manifest.json
metrics.schema.json          # JSON Schema — metrics.json
requirements.txt             # Dépendances runtime
requirements-dev.txt         # Dépendances dev/test

lib/                         # Modules extraits
├── config.py                # Modèles Pydantic, load_config()
├── timeframes.py            # TIMEFRAME_DELTA, parse_timeframe()
├── seed.py                  # set_global_seed()
├── qa.py                    # Contrôles qualité sur données brutes
├── features.py              # Registre de features + implémentations
├── data.py                  # Labels, valid_mask, sample builder
├── splitter.py              # Walk-forward splitter + purge/embargo
├── scaler.py                # StandardScaler, RobustScaler
├── models.py                # Registre modèles (Dummy, XGBoost)
├── trainer.py               # FoldTrainer
├── backtest.py              # Coûts, moteur de trades, equity curve
├── calibration.py           # Calibration du seuil θ
├── metrics.py               # Métriques prédiction/trading, agrégation
└── artifacts.py             # Manifest, metrics JSON, run directory
```

## Usage

### CLI

```bash
# Lancer le pipeline avec un fichier de config
python pipeline.py --config fullscale_btc_xgboost.yaml

# Overrider la stratégie
python pipeline.py --config fullscale_btc_xgboost.yaml --strategy dummy

# Overrider le dossier de sortie
python pipeline.py --config fullscale_btc_xgboost.yaml --output-dir /tmp/runs

# Aide
python pipeline.py --help
```

### Python

```python
from lib.config import load_config
from pipeline import run_pipeline

config = load_config("fullscale_btc_xgboost.yaml")
run_dir = run_pipeline(config)
print(f"Résultats dans : {run_dir}")
```

## Configuration

La config est un fichier YAML validé par Pydantic. Voir `fullscale_btc_xgboost.yaml` pour un exemple complet. Sections principales :

| Section | Description |
|---|---|
| `dataset` | Exchange, symbole, timeframe, période, chemin des données brutes |
| `qa` | Seuils de contrôle qualité |
| `label` | Horizon de prédiction, type de cible (`log_return_trade`) |
| `window` | Longueur de séquence `L`, warmup minimum |
| `features` | Liste de features et paramètres (RSI, EMA, volatilité…) |
| `splits` | Walk-forward rolling : `train_days`, `test_days`, `step_days`, embargo |
| `scaling` | Méthode de normalisation (`standard` / `robust`) |
| `strategy` | Nom du modèle (`dummy`, `xgboost_reg`, `cnn1d_reg`, `gru_reg`…) |
| `thresholding` | Calibration θ par grille de quantiles |
| `costs` | Frais et slippage par côté |
| `backtest` | Mode d'exécution, direction, equity initiale |
| `training` | Loss, optimizer, epochs, early stopping |
| `models` | Hyperparamètres par modèle (XGBoost, CNN1D, GRU, LSTM, PatchTST, RL-PPO) |
| `metrics` | Sharpe annualisé ou non, epsilon |
| `reproducibility` | Seed global, torch déterministe |
| `artifacts` | Dossier de sortie, sauvegardes (modèle, equity, trades, prédictions) |

## Données d'entrée

Le pipeline attend un fichier Parquet `{symbol}_{timeframe}.parquet` dans `dataset.raw_dir` avec les colonnes :

- `timestamp_utc` — datetime UTC
- `open`, `high`, `low`, `close` — prix OHLC
- `volume` — volume

## Artefacts de sortie

Chaque run crée un dossier `runs/{timestamp}_{strategy}/` contenant :

```
config_snapshot.yaml        # Copie de la config utilisée
manifest.json               # Métadonnées du run (validé par JSON Schema)
metrics.json                # Métriques agrégées + par fold (validé par JSON Schema)
equity_curve.csv            # Courbe d'equity stitchée (tous folds)
pipeline.log                # Log complet du run

folds/
  fold_00/
    metrics_fold.json       # Métriques du fold
    preds_val.csv           # Prédictions validation
    preds_test.csv          # Prédictions test
    equity_curve.csv        # Equity du fold
    trades.csv              # Journal de trades
    model_artifacts/        # Modèle sauvegardé
  fold_01/
    ...
```

## Stratégies disponibles

| Nom | Type | Framework |
|---|---|---|
| `dummy` | model | internal |
| `xgboost_reg` | model | xgboost |
| `cnn1d_reg` | model | pytorch |
| `gru_reg` | model | pytorch |
| `lstm_reg` | model | pytorch |
| `patchtst_reg` | model | pytorch |
| `rl_ppo` | model | pytorch |
| `no_trade` | baseline | — |
| `buy_hold` | baseline | — |
| `sma_rule` | baseline | — |

## Tests

```bash
# Lancer tous les tests
python -m pytest pipeline_test.py -v

# Un test spécifique
python -m pytest pipeline_test.py::TestPipelineE2E::test_run_completes_without_crash -v
```

Les tests couvrent :
- **E2E** — run complet avec XGBoost sur données synthétiques, validation des artefacts et schémas JSON
- **Reproductibilité** — deux runs identiques produisent les mêmes métriques et trades
- **Anti-leak** — perturbation future ne change pas le premier fold
- **CLI** — `--help`, `--config`, `--strategy`, `--output-dir`
