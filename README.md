# ai_trading_agent

Stack de trading crypto organisée autour du pipeline `données → features → modèle → backtest / live`.
Huit familles de modèles partagent le même dataset de features et les mêmes harnais de backtest / live.

Toutes les commandes se lancent **depuis la racine du repo** (pour que les imports
`from config import ...` fonctionnent).

---

## Table des matières

1. [Installation](#1-installation)
2. [Télécharger les données et construire les features](#2-télécharger-les-données-et-construire-les-features)
3. [Modèles disponibles](#3-modèles-disponibles)
4. [Entraîner un modèle](#4-entraîner-un-modèle)
5. [Évaluer un modèle](#5-évaluer-un-modèle)
6. [Backtest sur données historiques](#6-backtest-sur-données-historiques)
7. [Comparer tous les modèles sur un seul graphe](#7-comparer-tous-les-modèles-sur-un-seul-graphe)
8. [Test temps réel / live](#8-test-temps-réel--live)
9. [Référence des features](#9-référence-des-features)

---

## 1. Installation

```bash
pip install -r requirements.txt
```

Tous les scripts se lancent en mode module avec `python -m <chemin>` — ne jamais
exécuter les fichiers directement, les imports `from config import ...` casseraient.

Le device est choisi automatiquement : CUDA → Apple MPS → CPU.

---

## 2. Télécharger les données et construire les features

Récupère les OHLCV depuis Binance via `ccxt`, construit les features, écrit un CSV
par symbole ainsi qu'un `full_dataset.csv` combiné, le tout sous `output/<timeframe>/`.

```bash
# Par défaut (1d, tous les SYMBOLS de config.py)
python -m data.main

# Autres timeframes — 1h / 4h / 6h etc. supportés
python -m data.main --timeframe 6h
python -m data.main --timeframe 1h
```

Pipeline :

```
API Binance (ccxt)
  └─ data/fetcher.py           → data/raw/<tf>/<SYMBOL>.csv
        └─ data/features/pipeline.py  (build_features)
              ├─ candle / momentum / trend
              ├─ oscillator (RSI, MACD)
              ├─ volume (+ OBV, volume_directional)
              ├─ volatility (Bollinger, ATR)
              └─ temporal (hour/dow sin/cos, uniquement 1h)
        └─ data/labeling/labeler.py   (add_labels)
        └─ data/main.py               → output/<tf>/<SYMBOL>.csv + full_dataset.csv
```

Le pipeline 1d produit 22 features ; le pipeline 1h en produit 30 (horizons
momentum supplémentaires + features temporelles intraday). L'agent RL utilise
son propre sous-ensemble figé de 16 features (`models/rl/features.py`) et
tourne en **6h**.

La configuration est dans `config.py` — `SYMBOLS`, `BACKTEST_SYMBOLS`,
`TEST_START_DATE`, `WINDOW_SIZES`, `PREDICTION_HORIZONS`, presets d'architecture
par modèle, frais, slippage, seuils de signal, risque par trade.

---

## 3. Modèles disponibles

| Clé             | Famille                             | Timeframe natif |
|-----------------|-------------------------------------|-----------------|
| `cnn`           | CNN 1-D                             | tout            |
| `lstm`          | LSTM                                | tout            |
| `bilstm`        | LSTM bidirectionnel                 | tout            |
| `cnn_bilstm_am` | CNN + BiLSTM + Attention            | tout            |
| `transformer`   | Transformer encodeur                | tout            |
| `patch_tst`     | PatchTST                            | tout            |
| `xgboost`       | Gradient boosting                   | tout            |
| `rl`            | Politique PPO (7 actions discrètes) | **6h uniquement** |
| `ensemble`      | Agrégation des modèles supervisés   | tout            |
| `compare-all`   | Mode benchmark (pas un modèle)      | tout            |

Chaque dossier modèle suit la même structure :

```
models/<type>/
  ├─ <Model>.py          # Architecture nn.Module
  ├─ data_preparator.py  # Windowing + scaling
  ├─ training.py
  ├─ evaluation.py       # Wrapper fin sur utils/evaluation.py
  ├─ predictor.py        # Adapter BasePredictor utilisé par backtest / live
  ├─ checkpoints/<tf>/   # best_model.pth + scalers.joblib (gitignored)
  └─ results/            # Plots d'évaluation
```

---

## 4. Entraîner un modèle

**Modèles supervisés** — même CLI pour toutes les familles, `--symbol` est
optionnel (omettre pour entraîner sur le dataset multi-symbole combiné) :

```bash
python -m models.cnn.training
python -m models.cnn.training --symbol BTC --epochs 100 --batch-size 32 --lr 1e-3 --patience 10
python -m models.lstm.training         --timeframe 1h
python -m models.bilstm.training       --timeframe 1h
python -m models.cnn_bilstm_am.training
python -m models.transformer.training  --symbol BTC
python -m models.patch_tst.training
python -m models.xgboost.training
```

**Agent RL (PPO)** — forcé en 6h en interne, il faut donc construire le dataset
6h au préalable :

```bash
python -m data.main --timeframe 6h
python -m models.rl.training                  # multi-symbole
python -m models.rl.training --symbol BTC
```

Les checkpoints atterrissent dans `models/<type>/checkpoints/[<tf>/]best_model.*`
(RL utilise `models/rl/checkpoints/best_agent.pth`).

---

## 5. Évaluer un modèle

Produit les métriques (MSE/RMSE/MAE/R², direction accuracy) et les plots (courbes
d'entraînement, prédictions vs réel, résidus, direction accuracy roulante) sous
`models/<type>/results/`.

```bash
python -m models.cnn.evaluation --symbol BTC
python -m models.cnn.evaluation --symbol BTC --model-path models/cnn/checkpoints/best_model.pth
python -m models.lstm.evaluation      --symbol ETH
python -m models.transformer.evaluation --symbol BTC --timeframe 1h
python -m models.xgboost.evaluation   --symbol BTC

# RL : par symbole ou sur toute la liste
python -m models.rl.evaluation --symbol BTC
python -m models.rl.evaluation --all
```

---

## 6. Backtest sur données historiques

`testing/backtesting.py` rejoue la stratégie sur une tranche figée d'historique,
applique la même logique de risque et de frais que la boucle live, et écrit un
résumé + un PNG de courbe d'équité sous `testing/results/`.

```bash
# Un modèle sur un symbole
python -m testing.backtesting --model cnn --symbol BTC --capital 10000 --threshold 0.01

# Frais + risk management ATR (SL/TP/trailing) + cutoff out-of-sample
python -m testing.backtesting --model cnn --symbol BTC \
    --capital 10000 --threshold 0.01 \
    --entry-fee 0.001 --exit-fee 0.001 \
    --atr-risk --test-start-date 2025-01-01

# Balayer tous les SYMBOLS
python -m testing.backtesting --model transformer --all-symbols --capital 1000

# Politique RL (6h natif)
python -m testing.backtesting --model rl --symbol BTC --capital 10000

# Ensemble supervisé
python -m testing.backtesting --model ensemble \
    --ensemble-models cnn,bilstm,cnn_bilstm_am,transformer \
    --ensemble-strategy confidence_weighted \
    --symbol BTC --capital 10000
```

Flags utiles : `--timeframe` (défaut `1d`), `--threshold`, `--allow-short`,
`--atr-risk`, `--entry-fee`, `--exit-fee`, `--test-start-date`,
`--ensemble-strategy` (`majority_vote | weighted_average | confidence_weighted | unanimous`),
`--ensemble-weights`, `--all-symbols`.

---

## 7. Comparer tous les modèles sur un seul graphe

`--model compare-all` benchmarke côte-à-côte l'agent RL, l'ensemble supervisé, et
chaque modèle supervisé individuel, sur le même symbole et la même plage de
dates. Les checkpoints manquants sont sautés avec un warning (soft-skip).

```bash
# Tous les contestants sur BTC (supervisés sur timeframe par défaut, RL sur son 6h natif)
python -m testing.backtesting --model compare-all --symbol BTC --capital 10000

# Forcer un timeframe spécifique côté supervisé
python -m testing.backtesting --model compare-all --symbol BTC --timeframe 1h --capital 10000

# Exclure des modèles pas encore entraînés
python -m testing.backtesting --model compare-all --symbol BTC --exclude patch_tst,transformer

# Fenêtre out-of-sample personnalisée
python -m testing.backtesting --model compare-all --symbol BTC \
    --test-start-date 2024-01-01 --capital 10000
```

Sorties sous `testing/results/compare_all/` :

- `<symbol>_<start>_<end>.csv` — une ligne par contestant, trié par Sharpe.
- `<symbol>_<start>_<end>.png` — toutes les courbes d'équité (rééchantillonnées
  en journalier) + buy-and-hold + oracle (perfect foresight), avec un sous-plot
  de drawdowns.

Note timeframes en compare-all : chaque contestant tourne à sa cadence native
(RL toujours en 6h, supervisés sur `--timeframe`). Les courbes d'équité sont
rééchantillonnées en journalier avant d'être superposées ; les métriques restent
calculées à la fréquence native de chaque contestant.

---

## 8. Test temps réel / live

`testing/realtime_testing.py` expose deux modes sur le même code :

- **Live** — interroge Binance toutes les `--interval` secondes et paper-trade.
- **Backtest** — rejoue les CSV historiques à vitesse configurable.

L'état (positions, ordres ouverts, equity) est checkpointé, on peut reprendre
ou repartir à zéro avec `--fresh`.

### 8.1 Paper trading live

```bash
# Minimal
python -m testing.realtime_testing --symbol BTC/USDT --model cnn --capital 10000 --rrr 2.0

# Config complète depuis JSON
python -m testing.realtime_testing --config testing/config.json

# Risque resserré
python -m testing.realtime_testing --symbol BTC/USDT --model bilstm \
    --capital 10000 --rrr 2.0 --risk 0.01 \
    --max-drawdown 0.15 --max-daily-trades 5 --cooldown 3600 \
    --sizing-mode fixed
```

### 8.2 Rejeu backtest

```bash
# Historique complet de BTC avec le modèle CNN
python -m testing.realtime_testing --backtest --symbol BTC --model cnn --rrr 2.0

# Fenêtre restreinte, assez lente pour suivre les décisions
python -m testing.realtime_testing --backtest --symbol BTC --model cnn \
    --start-date 2024-01-01 --end-date 2024-12-31 --speed 0.01
```

Flags utiles : `--interval`, `--threshold`, `--allow-short`, `--sizing-mode`,
`--max-drawdown`, `--max-daily-trades`, `--cooldown`, `--fresh`, et en mode
backtest `--start-date`, `--end-date`, `--speed`.

---

## 9. Référence des features

Voir `data/features/` pour les implémentations. Tour sémantique rapide :

| Catégorie              | Features                                                      | Pourquoi |
|------------------------|---------------------------------------------------------------|----------|
| Structure de bougie    | `body`, `upper_wick`, `lower_wick`, `range`, `green_ratio`    | Géométrie en chandeliers japonais, tout divisé par open pour comparabilité inter-crypto. |
| Momentum               | `return_1d`, `return_3d`, `return_6d`, `return_12d`, `return_24d` (tf 1h) / `return_{1,3,7,14,21}d` (tf 1d) | Momentum multi-horizon — un marché peut être haussier sur 3 semaines et en correction sur 3 jours. |
| Tendance (EMAs)        | `ema9_ratio`, `ema21_ratio`, `ema50_ratio`, `ema100_ratio`, `price_vs_ma50` | Normalisées autour de 1.0, les écarts montrent l'étirement / compression vs tendance. |
| Oscillateurs           | `rsi`, `macd`, `macd_signal`, `macd_hist`, `bollinger_position` | Surachat / survente + shifts de momentum + position dans la bande de Bollinger. |
| Volume & volatilité    | `volume_ratio`, `volume_return`, `volatility`, `obv_normalized`, `volume_directional`, `atr_normalized` | Le volume confirme le prix ; ATR et volatilité réalisée capturent le régime. |
| Temporel (1h uniquement) | `hour_sin`, `hour_cos`, `dow_sin`, `dow_cos`                | Encode l'heure du jour / jour de la semaine comme features continues. |

**Tout est normalisé** — ratios, pourcentages, scores dans [0, 1] — pour que le
même modèle généralise à BTC à 60 k$ comme à DOGE à 0,07 $ sans jamais voir de
prix absolu. La winsorisation au 1ᵉʳ / 99ᵉ percentile et le `RobustScaler`
(médiane/IQR) sont fittés **uniquement sur le split train**, sauvegardés avec
le checkpoint via `joblib`, puis réutilisés à l'inférence.

Label (modèles supervisés) :

```
future_return = close(J+H) / close(J) - 1           # H = PREDICTION_HORIZON[tf]
```

Les modèles supervisés régressent le `future_return` brut (loss Huber) ; le
label discret `-1 / 0 / 1` est conservé uniquement pour rapporter la direction
accuracy.

---

### Convention pour ajouter un nouveau modèle

1. Créer `models/<type>/` avec les quatre fichiers : `<Model>.py`,
   `data_preparator.py`, `training.py`, `evaluation.py`.
2. Ajouter un `predictor.py` qui hérite de `models.base_predictor.BasePredictor`.
3. L'enregistrer dans `models/registry.py`.

Il est ensuite automatiquement pris en compte par `--model <type>`,
`--model ensemble` (comme constituant) et `--model compare-all`.
