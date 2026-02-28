# AI Trading Pipeline

> Pipeline rigoureux de comparaison de modèles ML/DL et baselines sur données OHLCV crypto (Binance).

## Objectif

Comparer de manière systématique et reproductible des stratégies de trading (XGBoost, CNN 1D, GRU, LSTM, PatchTST, RL-PPO) contre des baselines (no-trade, buy & hold, SMA crossover) sur un walk-forward rolling, avec métriques standardisées et coûts réalistes.

## Architecture

```
ai_trading/                  ← package principal
├── config.py                # Chargement + validation YAML (Pydantic v2)
├── data/                    # Ingestion, QA, dataset, splitter, scaler
├── features/                # Feature pipeline pluggable (registre)
├── models/                  # Interface BaseModel + registre
├── training/                # Fold trainer
├── calibration/             # Seuil θ (quantile grid)
├── backtest/                # Moteur de backtest mark-to-market
├── baselines/               # no_trade, buy_hold, sma_rule
├── metrics/                 # Prédiction + trading + agrégation
├── artifacts/               # Manifest, metrics JSON, schémas
├── utils/                   # Seed manager
└── pipeline/                # Orchestrateur de run
```

## Features MVP (9)

| Feature | Formule | Réf. spec |
|---|---|---|
| `logret_1` | `log(C_t / C_{t-1})` | §6.2 |
| `logret_2` | `log(C_t / C_{t-2})` | §6.2 |
| `logret_4` | `log(C_t / C_{t-4})` | §6.2 |
| `vol_24` | `std(logret_1, 24 pas, ddof=0)` | §6.5 |
| `vol_72` | `std(logret_1, 72 pas, ddof=0)` | §6.5 |
| `logvol` | `log(V_t + ε)` | §6.2 |
| `dlogvol` | `logvol(t) - logvol(t-1)` | §6.2 |
| `rsi_14` | RSI Wilder (n=14) | §6.3 |
| `ema_ratio_12_26` | `EMA_12 / EMA_26 - 1` | §6.4 |

## Prérequis

- Python ≥ 3.11
- Dépendances : voir `requirements.txt`

## Installation

```bash
# Clone
git clone https://github.com/Nexgear75/ai_trading_agent.git
cd ai_trading_agent

# Environnement virtuel
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows

# Dépendances
pip install -e ".[dev]"
```

## Utilisation

```bash
# Lancer un run complet
python -m ai_trading --config configs/default.yaml

# Override CLI (dot notation)
python -m ai_trading --config configs/default.yaml --set costs.slippage_rate_per_side=0.0005

# Tests
pytest
```

## Configuration

La configuration centralisée est dans `configs/default.yaml`. Tous les paramètres sont documentés dans la [spécification](docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md) (Annexe E.1).

Paramètres principaux :

| Section | Paramètres clés |
|---|---|
| `dataset` | symbole, timeframe 1h, période 2024-2026 |
| `label` | horizon H=4 bougies, log-return trade |
| `window` | L=128 pas, warmup=200 |
| `splits` | train 180j, test 30j, step 30j, val 20%, embargo=H |
| `costs` | fee 0.05% + slippage 0.025% per side |
| `backtest` | one_at_a_time, long_only |

## Walk-Forward Rolling

Le pipeline évalue chaque stratégie sur des folds glissants :

```
Fold 0:  |--- train 180j ---|-- val --|--emb--|-- test 30j --|
Fold 1:       |--- train 180j ---|-- val --|--emb--|-- test 30j --|
Fold 2:            |--- train 180j ---|-- val --|--emb--|-- test 30j --|
...
```

Embargo = H bougies entre val et test pour éviter toute fuite d'information.

## Artefacts de sortie

Chaque run produit dans `runs/<run_id>/` :

- `manifest.json` — métadonnées du run (config, splits, hashes)
- `metrics.json` — métriques par fold + agrégées
- `config_snapshot.yaml` — config figée
- `folds/fold_XX/` — equity curve, trades, prédictions par fold

Les JSON sont validés contre les schémas (`docs/specifications/manifest.schema.json`, `metrics.schema.json`).

## Documentation

| Document | Contenu |
|---|---|
| [Spécification v1.0](docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md) | Spec complète (features, labels, walk-forward, backtest, métriques) |
| [Plan d'implémentation](docs/plan/implementation.md) | Découpage en Work Streams et Milestones |
| [Config par défaut](configs/default.yaml) | Tous les paramètres MVP |

## Principes

- **Strict code** : pas de fallback silencieux, `raise` explicite
- **Anti-fuite** : scaler fit-on-train, embargo, purge
- **Reproductibilité** : seed fixée, SHA-256, config versionnée
- **Plug-in** : registres de features et de modèles
- **TDD** : tests d'acceptation avant implémentation

## Licence

MIT
