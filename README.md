# AI Trading Pipeline

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Linter: ruff](https://img.shields.io/badge/linter-ruff-orange.svg)](https://github.com/astral-sh/ruff)
[![Tests: pytest](https://img.shields.io/badge/tests-pytest-blue.svg)](https://docs.pytest.org/)

> Pipeline rigoureux de comparaison de modèles ML/DL et baselines sur données OHLCV crypto (Binance), avec protocole walk-forward, backtest unifié et métriques standardisées.

---

## Table des matières

- [Objectif](#objectif)
- [Architecture](#architecture)
- [Modèles & Baselines](#modèles--baselines)
- [Features MVP](#features-mvp-9)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Docker](#docker)
- [Configuration](#configuration)
- [Walk-Forward Rolling](#walk-forward-rolling)
- [Métriques](#métriques)
- [Artefacts de sortie](#artefacts-de-sortie)
- [Tests](#tests)
- [Documentation](#documentation)
- [Principes de conception](#principes-de-conception)
- [Licence](#licence)

---

## Objectif

Comparer de manière **systématique et reproductible** des stratégies de trading ML/DL contre des baselines naïves sur un walk-forward rolling, avec métriques standardisées et coûts réalistes.

Le pipeline couvre l'intégralité du cycle :

```
Données OHLCV → QA → Features → Splits → Scaling → Entraînement → Calibration θ → Backtest → Métriques
```

---

## Architecture

```
ai_trading/                      ← package principal
├── config.py                    # Chargement + validation YAML (Pydantic v2)
├── data/
│   ├── ingestion.py             # Téléchargement OHLCV via ccxt (Binance)
│   ├── qa.py                    # Contrôles qualité (gaps, volumes, timestamps)
│   ├── missing.py               # Politique de traitement des bougies manquantes
│   ├── labels.py                # Construction de la cible y_t (log-return trade)
│   ├── dataset.py               # Sample builder (N, L, F) + adapter XGBoost
│   ├── splitter.py              # Walk-forward rolling (train/val/test)
│   ├── scaler.py                # Standard scaler, robust scaler (fit on train)
│   └── timeframes.py            # Résolution des timeframes
├── features/
│   ├── registry.py              # Registre pluggable de features
│   ├── pipeline.py              # Orchestration du calcul de features
│   ├── warmup.py                # Gestion du warmup (min_warmup bougies)
│   ├── log_returns.py           # logret_1, logret_2, logret_4
│   ├── volatility.py            # vol_24, vol_72
│   ├── volume.py                # logvol, dlogvol
│   ├── rsi.py                   # RSI Wilder (rsi_14)
│   └── ema.py                   # EMA ratio (ema_ratio_12_26)
├── models/
│   ├── base.py                  # Interface BaseModel (ABC)
│   └── dummy.py                 # Dummy model (tests & baseline interne)
├── training/
│   └── trainer.py               # Fold trainer (boucle d'entraînement)
├── calibration/
│   └── threshold.py             # Calibration du seuil θ (quantile grid)
├── backtest/
│   ├── engine.py                # Moteur de backtest mark-to-market
│   ├── costs.py                 # Modèle de coûts (fee + slippage)
│   └── journal.py               # Trade journal CSV
├── baselines/
│   ├── no_trade.py              # Baseline no-trade
│   ├── buy_hold.py              # Baseline buy & hold
│   └── sma_rule.py              # Baseline SMA crossover
├── metrics/
│   ├── prediction.py            # MSE, MAE, R², IC (Information Coefficient)
│   ├── trading.py               # Sharpe, MDD, Win Rate, P&L net, Profit Factor
│   └── aggregation.py           # Agrégation inter-fold (mean ± std)
├── artifacts/
│   ├── manifest.py              # Construction du manifest.json
│   └── run_dir.py               # Arborescence des runs
├── utils/
│   └── seed.py                  # Seed manager (numpy, random, torch)
└── pipeline/                    # Orchestrateur de run end-to-end
```

---

## Modèles & Baselines

### Stratégies ML/DL

| Modèle | Type | Description |
|---|---|---|
| **XGBoost** | Gradient boosting | Régression sur features tabulaires (adapter flat) |
| **CNN 1D** | Deep Learning | Convolutions temporelles sur séquences (N, L, F) |
| **GRU** | Deep Learning | Réseau récurrent à portes (Gated Recurrent Unit) |
| **LSTM** | Deep Learning | Réseau récurrent à mémoire longue |
| **PatchTST** | Transformer | Patch-based Time Series Transformer |
| **RL PPO** | Reinforcement Learning | Proximal Policy Optimization (Go/No-Go) |

### Baselines

| Baseline | Description |
|---|---|
| **No-Trade** | Aucun trade → equity constante |
| **Buy & Hold** | Achat au début, maintien jusqu'à la fin |
| **SMA Crossover** | Signal long quand SMA rapide > SMA lente |

Toutes les stratégies sont évaluées sur le **même protocole** (mêmes splits, mêmes coûts, mêmes métriques).

---

## Features MVP (9)

| Feature | Formule | Réf. spec |
|---|---|---|
| `logret_1` | $\log(C_t / C_{t-1})$ | §6.2 |
| `logret_2` | $\log(C_t / C_{t-2})$ | §6.2 |
| `logret_4` | $\log(C_t / C_{t-4})$ | §6.2 |
| `vol_24` | $\text{std}(\text{logret\_1},\ 24,\ \text{ddof}=0)$ | §6.5 |
| `vol_72` | $\text{std}(\text{logret\_1},\ 72,\ \text{ddof}=0)$ | §6.5 |
| `logvol` | $\log(V_t + \varepsilon)$ | §6.2 |
| `dlogvol` | $\text{logvol}(t) - \text{logvol}(t-1)$ | §6.2 |
| `rsi_14` | RSI Wilder ($n=14$) | §6.3 |
| `ema_ratio_12_26` | $\text{EMA}_{12} / \text{EMA}_{26} - 1$ | §6.4 |

Le registre de features est **pluggable** : ajouter une feature = implémenter une fonction + l'enregistrer dans le registre.

---

## Installation

### Prérequis

- Python ≥ 3.11
- pip ou un gestionnaire d'environnement virtuel

### Depuis les sources

```bash
git clone https://github.com/Nexgear75/ai_trading_agent.git
cd ai_trading_agent

# Environnement virtuel
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows

# Installation avec dépendances de développement
pip install -e ".[dev]"
```

### Dépendances principales

| Catégorie | Packages |
|---|---|
| Données | numpy, pandas, pyarrow, ccxt |
| Config | PyYAML, pydantic, jsonschema |
| ML/DL | xgboost, torch, scikit-learn |
| Stats | scipy |

---

## Utilisation

```bash
# Lancer un run complet
python -m ai_trading --config configs/default.yaml

# Override de paramètres via CLI (dot notation)
python -m ai_trading --config configs/default.yaml \
  --set costs.slippage_rate_per_side=0.0005 \
  --set splits.train_days=365

# Lancer avec une baseline
python -m ai_trading --config configs/default.yaml \
  --set strategy.strategy_type=baseline \
  --set strategy.name=buy_hold
```

---

## Docker

```bash
# Build
docker build -t ai-trading .

# Run
docker run --rm -v $(pwd)/data:/app/data -v $(pwd)/runs:/app/runs \
  ai-trading

# Run avec override
docker run --rm -v $(pwd)/data:/app/data -v $(pwd)/runs:/app/runs \
  ai-trading python -m ai_trading --config configs/default.yaml \
  --set strategy.name=sma_rule
```

---

## Configuration

La configuration centralisée est dans `configs/default.yaml`. Tous les paramètres sont documentés dans la [spécification](docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md) (Annexe E.1).

### Paramètres principaux

| Section | Paramètres clés | Valeurs par défaut |
|---|---|---|
| `dataset` | Symbole, timeframe, période | BTCUSDT, 1h, 2024–2026 |
| `label` | Horizon de prédiction | H = 4 bougies, log-return trade |
| `window` | Fenêtre d'entrée, warmup | L = 128 pas, warmup = 200 |
| `features` | Liste des 9 features MVP | logret, vol, rsi, ema, volume |
| `splits` | Walk-forward rolling | train 180j, test 30j, step 30j, val 20% |
| `scaling` | Normalisation | standard (fit on train) |
| `costs` | Frais de transaction | fee 0.05% + slippage 0.025% / side |
| `backtest` | Mode d'exécution | one_at_a_time, long_only |
| `thresholding` | Calibration θ | quantile_grid, MDD cap 25% |
| `reproducibility` | Seed globale | 42, deterministic_torch = true |

### Configuration des modèles

Chaque modèle possède ses hyperparamètres dédiés dans la section `models` :

```yaml
models:
  xgboost:
    max_depth: 5
    n_estimators: 500
    learning_rate: 0.05
  gru:
    hidden_size: 64
    num_layers: 1
    dropout: 0.2
  # ...
```

---

## Walk-Forward Rolling

Le pipeline évalue chaque stratégie sur des folds glissants :

```
Fold 0:  |---- train 180j ----|-- val --|--emb--|-- test 30j --|
Fold 1:       |---- train 180j ----|-- val --|--emb--|-- test 30j --|
Fold 2:            |---- train 180j ----|-- val --|--emb--|-- test 30j --|
...
```

- **Embargo** = H bougies entre val et test pour éviter toute fuite d'information
- **Scaler** fit sur train uniquement (anti-fuite)
- **θ** calibré sur validation uniquement (jamais sur test)
- **Splits** strictement séquentiels : train < val < test

---

## Métriques

### Métriques de prédiction

| Métrique | Description |
|---|---|
| MSE | Mean Squared Error |
| MAE | Mean Absolute Error |
| R² | Coefficient de détermination |
| IC | Information Coefficient (corrélation Spearman) |

### Métriques de trading

| Métrique | Description |
|---|---|
| Sharpe Ratio | Rendement ajusté au risque |
| Max Drawdown | Perte maximale depuis le pic |
| Win Rate | Proportion de trades gagnants |
| P&L Net | Profit & Loss après coûts |
| Profit Factor | Gains bruts / Pertes brutes |
| Nombre de trades | Total de trades exécutés |

### Agrégation inter-fold

Les métriques sont agrégées sur l'ensemble des folds walk-forward : **moyenne ± écart-type**.

---

## Artefacts de sortie

Chaque run produit dans `runs/<run_id>/` :

```
runs/<run_id>/
├── manifest.json            # Métadonnées du run (config, splits, hashes SHA-256)
├── metrics.json             # Métriques par fold + agrégées
├── config_snapshot.yaml     # Config figée du run
└── folds/
    ├── fold_00/
    │   ├── equity_curve.csv # Courbe d'equity mark-to-market
    │   ├── trades.csv       # Journal des trades
    │   ├── preds_val.csv    # Prédictions validation
    │   └── preds_test.csv   # Prédictions test
    ├── fold_01/
    │   └── ...
    └── ...
```

Les JSON sont validés contre les schémas de la spécification.

---

## Tests

```bash
# Lancer tous les tests
pytest

# Avec couverture
pytest --cov=ai_trading --cov-report=term-missing

# Linter
ruff check ai_trading/ tests/
```

Les tests sont structurés par module (`test_config.py`, `test_features.py`, etc.) et couvrent :

- Cas nominaux
- Cas d'erreur (validation stricte)
- Cas limites
- Données synthétiques (pas de réseau)
- Seeds fixées (tests déterministes)

---

## Documentation

| Document | Contenu |
|---|---|
| [Spécification v1.0](docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md) | Spec complète : features, labels, walk-forward, backtest, métriques |
| [Plan d'implémentation](docs/plan/implementation.md) | Découpage en 12 Work Streams et 5 Milestones |
| [Config par défaut](configs/default.yaml) | Tous les paramètres MVP documentés |
| [Tâches](docs/tasks/) | Fiches de tâches par milestone (M1–M5) |

---

## Principes de conception

| Principe | Description |
|---|---|
| **Strict code** | Pas de fallback silencieux, validation explicite + `raise` |
| **Anti-fuite** | Scaler fit-on-train, embargo ≥ H, splits séquentiels, features backward-looking |
| **Reproductibilité** | Seed globale fixée, hashes SHA-256, config versionnée |
| **Config-driven** | Tout paramètre lu depuis YAML, zéro hardcoding |
| **Plug-in** | Registres extensibles de features et de modèles |
| **TDD strict** | Tests d'acceptation avant implémentation (RED → GREEN) |

---

## Licence

MIT
