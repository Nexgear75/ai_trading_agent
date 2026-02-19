# 📊 Crypto Dataset – Documentation des Features

> Dataset généré à partir des données Binance (OHLCV, daily) sur 10 cryptomonnaies.  
> Ce fichier documente chaque feature ajoutée, sa formule, et sa justification.

---

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Features de structure de bougie](#1-features-de-structure-de-bougie-candle_featurespy)
3. [Features de momentum](#2-features-de-momentum-momentum_featurespy)
4. [Features de tendance](#3-features-de-tendance-trend_featurespy)
5. [Features d'oscillateur](#4-features-doscillateur-oscillator_featurespy)
6. [Features de volume et volatilité](#5-features-de-volume-et-volatilité-volume_featurespy)
7. [Label](#6-label--la-cible-à-prédire)
8. [Pourquoi tout normaliser ?](#pourquoi-tout-normaliser-)

---

## Vue d'ensemble

Le dataset contient **20 features** par bougie journalière, construites à partir des 5 colonnes brutes Binance : `open`, `high`, `low`, `close`, `volume`.

| Catégorie | Nombre de features | Fichier |
|---|---|---|
| Structure de bougie | 4 | `candle_features.py` |
| Momentum (returns) | 5 | `momentum_features.py` |
| Tendance (EMAs) | 4 | `trend_features.py` |
| Oscillateurs | 4 | `oscillator_features.py` |
| Volume & Volatilité | 3 | `volume_features.py` |
| **Total** | **20** | |

Chaque exemple dans le dataset est une **fenêtre de 30 jours consécutifs**, ce qui donne un array de forme `(30, 20)` par sample — l'input idéal pour un CNN 1D, un LSTM ou un GRU.

---

## 1. Features de structure de bougie (`candle_features.py`)

Ces features décrivent la **forme géométrique** de chaque bougie japonaise. Ce sont les informations les plus directement lisibles par un trader humain, et donc les premières que le CNN doit apprendre à reconnaître.

> **Principe clé :** Toutes ces features sont divisées par `open` pour être exprimées en pourcentage relatif. Ainsi, une bougie BTC à 60 000$ et une bougie BTC à 10 000$ peuvent être comparées directement.

---

### `body` — Corps de la bougie

```
body = (close - open) / open
```

**Ce que ça mesure :** La direction et l'intensité du mouvement pendant la journée.

- Valeur positive → journée haussière (les acheteurs ont dominé)
- Valeur négative → journée baissière (les vendeurs ont dominé)
- Proche de 0 → indécision du marché (Doji)

**Pourquoi c'est pertinent :** C'est la feature la plus fondamentale de l'analyse en chandeliers japonais. Un CNN qui enchaîne plusieurs valeurs de `body` peut détecter des séquences comme "3 grosses bougies vertes consécutives" (momentum haussier) ou "une longue bougie rouge après une série de hausses" (retournement potentiel).

---

### `upper_wick` — Mèche supérieure

```
upper_wick = (high - max(open, close)) / open
```

**Ce que ça mesure :** L'amplitude du rejet à la hausse pendant la journée. Le prix est monté jusqu'à `high`, mais les vendeurs ont ramené le cours vers le corps de la bougie.

**Pourquoi c'est pertinent :** Une longue mèche supérieure est un signal de **rejet haussier** — le marché a essayé de monter mais les vendeurs étaient présents à ces niveaux. C'est un indicateur classique de résistance. Combinée avec d'autres features, elle aide le modèle à identifier des zones de retournement.

---

### `lower_wick` — Mèche inférieure

```
lower_wick = (min(open, close) - low) / open
```

**Ce que ça mesure :** L'amplitude du rejet à la baisse. Symétrique de la mèche supérieure.

**Pourquoi c'est pertinent :** Une longue mèche inférieure signale un **rejet baissier** — les vendeurs ont poussé le prix vers le bas mais les acheteurs ont repris le contrôle. C'est typiquement le signe d'un support fort, potentiellement le début d'un rebond. Le pattern "Hammer" ou "Pin Bar" (corps petit + longue mèche inférieure) est l'un des plus fiables en trading.

---

### `range` — Amplitude totale de la bougie

```
range = (high - low) / open
```

**Ce que ça mesure :** La volatilité intra-journalière. Plus le `range` est grand, plus la journée a été volatile.

**Pourquoi c'est pertinent :** Un `range` anormalement élevé accompagné d'un fort volume signale souvent un **événement de marché majeur** (cassure d'un niveau, liquidation massive, news). Ces journées ont souvent un impact fort sur les jours suivants. Le CNN peut apprendre à les repérer dans une fenêtre.

---

## 2. Features de momentum (`momentum_features.py`)

Ces features mesurent la **vitesse et la direction** du mouvement de prix sur différents horizons temporels passés.

```
return_Nd = (close_aujourd'hui - close_il_y_a_N_jours) / close_il_y_a_N_jours
```

| Feature | Fenêtre | Ce que ça capture |
|---|---|---|
| `return_1d` | 1 jour | Momentum immédiat |
| `return_3d` | 3 jours | Tendance très court terme |
| `return_7d` | 7 jours | Tendance hebdomadaire |
| `return_14d` | 14 jours | Tendance bi-mensuelle |
| `return_21d` | 21 jours | Tendance mensuelle |

**Pourquoi plusieurs horizons ?**

Un marché peut être haussier sur 21 jours mais en train de corriger sur 3 jours. Donner ces deux informations simultanément au modèle lui permet de distinguer une **correction temporelle dans une tendance haussière** (potentiellement une opportunité d'achat) d'un **vrai retournement de tendance** (signal de vente).

C'est le principe du **multi-timeframe analysis** utilisé par les traders professionnels, ici encodé directement dans les features.

---

## 3. Features de tendance (`trend_features.py`)

Les moyennes mobiles exponentielles (EMA) lissent le prix pour révéler la tendance sous-jacente, en donnant plus de poids aux données récentes.

```
emaX_ratio = EMA(close, X périodes) / close
```

| Feature | Période | Rôle classique |
|---|---|---|
| `ema9_ratio` | 9 jours | Tendance très court terme |
| `ema21_ratio` | 21 jours | Tendance court terme |
| `ema50_ratio` | 50 jours | Tendance moyen terme |
| `ema100_ratio` | 100 jours | Tendance long terme |

**Pourquoi diviser par `close` ?**

Un ratio autour de `1.0` signifie que le prix est proche de son EMA. Un ratio de `1.05` signifie que le prix est 5% au-dessus de son EMA → le marché est potentiellement suracheté et une correction est probable. Un ratio de `0.95` → le marché est 5% sous son EMA → potentiellement survendu.

Cette normalisation rend les valeurs **comparables entre BTC, ETH, et toutes les autres cryptos**, quelle que soit leur échelle de prix absolue.

**Pourquoi plusieurs EMAs ?**

Le **croisement d'EMAs** est l'un des signaux les plus utilisés en trading algorithmique. Quand `ema9_ratio < ema50_ratio`, l'EMA courte passe sous l'EMA longue — c'est un signal baissier classique ("death cross"). Le CNN peut apprendre ces configurations sans qu'on les lui code explicitement.

---

## 4. Features d'oscillateurs (`oscillator_features.py`)

Les oscillateurs mesurent si un actif est en situation de **surachat ou survente**, indépendamment de la direction de la tendance.

---

### `rsi` — Relative Strength Index

```
RSI = 100 - (100 / (1 + moyenne_gains_14j / moyenne_pertes_14j))
Feature : rsi = RSI / 100  → normalisé entre 0 et 1
```

**Ce que ça mesure :** La force relative des mouvements haussiers vs baissiers sur 14 jours.

- `rsi > 0.70` → surachat (le marché a monté trop vite, correction probable)
- `rsi < 0.30` → survente (le marché a chuté trop vite, rebond probable)
- `rsi ≈ 0.50` → marché équilibré

**Pourquoi c'est pertinent :** Le RSI est l'indicateur le plus utilisé au monde en trading. Il capture des informations que les returns seuls ne voient pas — un actif peut avoir un `return_14d` positif mais un RSI en divergence baissière (les nouveaux hauts sont faits avec moins de force), ce qui signale un essoufflement.

---

### `macd`, `macd_signal`, `macd_hist` — MACD

```
MACD      = EMA(12) - EMA(26)
Signal    = EMA(MACD, 9)
Histogramme = MACD - Signal

Features normalisées par close pour comparaison inter-crypto
```

**Ce que ça mesure :** La convergence/divergence de deux moyennes mobiles. C'est essentiellement un indicateur de momentum qui détecte les changements de tendance.

**Pourquoi 3 features et pas une seule ?**

- `macd` seul indique la direction du momentum
- `macd_signal` est le lissage du MACD — son croisement avec `macd` génère les signaux buy/sell
- `macd_hist` (la différence entre les deux) montre **l'accélération ou le ralentissement** du momentum — c'est souvent le premier signe d'un retournement, avant même que le croisement se produise

Un CNN qui voit l'évolution de ces 3 valeurs sur 30 jours peut apprendre à reconnaître des patterns de divergence MACD-prix, ce que très peu de modèles simples capturent.

---

## 5. Features de volume et volatilité (`volume_features.py`)

Le volume est souvent appelé "le carburant du marché". Un mouvement de prix sans volume est suspect ; avec volume, il est confirmé.

---

### `volume_ratio` — Volume relatif

```
volume_ratio = volume_aujourd'hui / moyenne_mobile_volume(20 jours)
```

**Ce que ça mesure :** Si le volume du jour est anormalement élevé ou faible par rapport aux 20 derniers jours.

- `volume_ratio > 2.0` → volume 2x supérieur à la normale → événement significatif
- `volume_ratio < 0.5` → marché apathique, mouvement peu fiable

**Pourquoi c'est pertinent :** En analyse technique, le principe est : *"le volume confirme le prix"*. Une cassure à la hausse avec un `volume_ratio` élevé est beaucoup plus fiable qu'une cassure avec un volume faible. Cette feature permet au modèle de pondérer la fiabilité des mouvements de prix.

---

### `volume_return` — Variation du volume

```
volume_return = (volume_aujourd'hui - volume_hier) / volume_hier
```

**Ce que ça mesure :** L'accélération ou la décélération du volume, jour après jour.

**Pourquoi c'est pertinent :** Un volume qui augmente progressivement pendant une hausse signale une accumulation institutionnelle. Un volume qui s'effondre pendant une hausse signale un essoufflement. Cette feature capture cette dynamique temporelle que `volume_ratio` seul ne voit pas.

---

### `volatility` — Volatilité réalisée

```
volatility = écart-type des return_1d sur les 14 derniers jours
```

**Ce que ça mesure :** Le niveau de risque et d'incertitude actuel du marché.

**Pourquoi c'est pertinent :** Les marchés alternent entre phases de **basse volatilité** (consolidation, accumulation silencieuse) et phases de **haute volatilité** (tendances fortes, paniques). Ces régimes de marché ont des comportements très différents. Un CNN entraîné sans cette feature confondrait des patterns identiques dans des contextes de volatilité radicalement différents — avec des conséquences opposées.

---

## 6. Label — La cible à prédire

```
future_return = close(J+3) / close(J) - 1

label =  1  si future_return > +2%   → signal HAUSSE
label =  0  si -2% ≤ future_return ≤ +2%  → NEUTRE (pas de trade)
label = -1  si future_return < -2%   → signal BAISSE
```

**Pourquoi J+3 et pas J+1 ?**

Prédire le lendemain exact est trop sensible au bruit quotidien. Sur 3 jours, les mouvements aléatoires se lissent et les vrais signaux directionnels ressortent mieux.

**Pourquoi un seuil de ±2% ?**

Les mouvements inférieurs à 2% sur les cryptos sont souvent du bruit de marché. En filtrant ces cas neutres, on force le modèle à n'émettre des signaux que quand un vrai mouvement est attendu — ce qui correspond à une stratégie de trading réaliste où l'on ne prend position que sur des opportunités claires.

---

## Pourquoi tout normaliser ?

Un réseau de neurones est fondamentalement une machine qui fait des multiplications et des additions. Si une feature vaut 60 000 (prix BTC) et une autre vaut 0.65 (RSI), le gradient de la première va écraser celui de la seconde pendant l'entraînement — le modèle ignorera le RSI.

En exprimant tout en **ratios, pourcentages et scores entre 0 et 1**, toutes les features contribuent de manière équilibrée à l'apprentissage, et le modèle peut être entraîné indifféremment sur BTC, DOGE ou n'importe quelle autre crypto sans jamais voir de valeur absolue.

---

*Dataset généré via `main.py` — voir `config.py` pour modifier les paramètres.*
