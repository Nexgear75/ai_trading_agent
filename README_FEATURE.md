# Guide — Ajouter une nouvelle feature au pipeline

Ce document décrit pas à pas comment intégrer une nouvelle feature dans le pipeline AI Trading.

---

## Table des matières

1. [Architecture générale](#1-architecture-générale)
2. [Interface `BaseFeature` (ABC)](#2-interface-basefeature-abc)
3. [Étapes d'intégration](#3-étapes-dintégration)
   - [3.1 Créer la classe de la feature](#31-créer-la-classe-de-la-feature)
   - [3.2 Ajouter les paramètres config (si nécessaire)](#32-ajouter-les-paramètres-config-si-nécessaire)
   - [3.3 Mettre à jour le YAML](#33-mettre-à-jour-le-yaml)
   - [3.4 Enregistrer le module](#34-enregistrer-le-module)
4. [Contrat `min_periods` / warmup](#4-contrat-min_periods--warmup)
5. [Features existantes (MVP)](#5-features-existantes-mvp)
6. [Flux d'exécution dans le pipeline](#6-flux-dexécution-dans-le-pipeline)
7. [Exemple complet : feature Momentum](#7-exemple-complet--feature-momentum)
8. [Checklist finale](#8-checklist-finale)

---

## 1. Architecture générale

```
ai_trading/features/
├── __init__.py          # Imports des modules features (déclenche l'enregistrement)
├── registry.py          # BaseFeature ABC + FEATURE_REGISTRY + @register_feature
├── pipeline.py          # resolve_features() + compute_features()
├── warmup.py            # apply_warmup() — validation warmup et NaN
├── ema.py               # ema_ratio_12_26
├── log_returns.py       # logret_1, logret_2, logret_4
├── rsi.py               # rsi_14
├── volatility.py        # vol_24, vol_72
└── volume.py            # logvol, dlogvol
```

Le pipeline utilise un **registre global** (`FEATURE_REGISTRY`) alimenté par des décorateurs `@register_feature("nom")`. Le pipeline résout les noms depuis `config.features.feature_list`, instancie les classes et appelle `compute()` sur chaque feature.

---

## 2. Interface `BaseFeature` (ABC)

Toute feature **doit** hériter de `BaseFeature` (défini dans `ai_trading/features/registry.py`) et satisfaire les contraintes suivantes :

### Attribut de classe obligatoire

| Attribut | Type | Description |
|---|---|---|
| `required_params` | `list[str]` | Liste des clés lues dans `config.features.params`. Doit être déclarée explicitement (même si vide `[]`). `__init_subclass__` vérifie sa présence dans `cls.__dict__` et lève `TypeError` sinon. |

### Méthodes abstraites

#### `min_periods(params: dict) → int`

Retourne le nombre de NaN en tête produits par `compute()`. Autrement dit, l'index 0-based de la première valeur non-NaN.

| Paramètre | Type | Description |
|---|---|---|
| `params` | `dict` | Dictionnaire complet `config.features.params` — la feature lit seulement ses clés |
| **Retour** | `int` | Nombre de NaN en tête (ex : `logret_1` → 1, `vol_24` → 24, `rsi_14` → 14) |

Ce nombre sert au calcul du warmup : le pipeline vérifie que `min_warmup >= max(min_periods)` pour toutes les features actives.

#### `compute(ohlcv: pd.DataFrame, params: dict) → pd.Series`

Calcule la feature à partir des données OHLCV.

| Paramètre | Type | Description |
|---|---|---|
| `ohlcv` | `pd.DataFrame` | Colonnes `open`, `high`, `low`, `close`, `volume`, indexé par timestamp |
| `params` | `dict` | Dictionnaire complet `config.features.params` |
| **Retour** | `pd.Series` | Même longueur que `ohlcv`, indexé par les mêmes timestamps |

### Contrat de causalité stricte

> **Règle fondamentale** : la valeur à l'index $t$ ne doit dépendre que des données OHLCV aux indices $\leq t$. Aucune donnée future ne peut être utilisée (anti look-ahead).

$$\text{feature}(t) = f\bigl(\text{OHLCV}[0], \text{OHLCV}[1], \ldots, \text{OHLCV}[t]\bigr)$$

---

## 3. Étapes d'intégration

### 3.1 Créer la classe de la feature

Créer un fichier `ai_trading/features/ma_feature.py` :

```python
from __future__ import annotations

import numpy as np
import pandas as pd

from ai_trading.features.registry import BaseFeature, register_feature


@register_feature("ma_feature_10")
class MaFeature10(BaseFeature):
    """Description de la feature."""

    required_params: list[str] = ["ma_feature_period"]  # Déclaration explicite

    def min_periods(self, params: dict) -> int:
        return params["ma_feature_period"]  # Ex : 10 → 10 NaN en tête

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        period = params["ma_feature_period"]
        close = ohlcv["close"]
        # Calcul strictement causal — valeur à t ne dépend que de données <= t
        result = close.rolling(window=period, min_periods=period).mean()
        return result
```

**Règles impératives** :
- `required_params` **doit** être déclaré dans le corps de la classe, même si vide (`[]`)
- Pas de fallback silencieux : si un paramètre est absent, laisser le `KeyError` remonter
- Le `pd.Series` retourné doit avoir **exactement** la même longueur que `ohlcv`
- Les NaN en tête doivent correspondre **exactement** à `min_periods()`

### 3.2 Ajouter les paramètres config (si nécessaire)

Si la feature a des paramètres configurables (`required_params` non vide), les ajouter dans `FeaturesParamsConfig` dans `ai_trading/config.py` :

```python
class FeaturesParamsConfig(_StrictBase):
    rsi_period: int
    rsi_epsilon: float
    ema_fast: int
    ema_slow: int
    vol_windows: list[int] = Field(min_length=1)
    logvol_epsilon: float
    volatility_ddof: int
    ma_feature_period: int          # ← Ajouter ici
```

> **Config-driven** : tout paramètre doit être dans le YAML et la config Pydantic. Aucune valeur hardcodée dans le code de calcul.

### 3.3 Mettre à jour le YAML

Dans `configs/default.yaml`, ajouter la feature dans `feature_list` et ses paramètres dans `params` :

```yaml
features:
  feature_version: mvp_v2          # ← Incrémenter la version si ajout de feature
  feature_list:
    - logret_1
    - logret_2
    - logret_4
    - vol_24
    - vol_72
    - logvol
    - dlogvol
    - rsi_14
    - ema_ratio_12_26
    - ma_feature_10                # ← Ajouter ici

  params:
    rsi_period: 14
    rsi_epsilon: 1.0e-12
    ema_fast: 12
    ema_slow: 26
    vol_windows:
      - 24
      - 72
    logvol_epsilon: 1.0e-8
    volatility_ddof: 0
    ma_feature_period: 10          # ← Ajouter ici
```

**Important** : vérifier que `window.min_warmup >= max(min_periods)` pour toutes les features. Si la nouvelle feature a un `min_periods` supérieur au `min_warmup` actuel (200), augmenter `min_warmup`.

### 3.4 Enregistrer le module

Dans `ai_trading/features/__init__.py`, importer le nouveau module pour déclencher l'enregistrement :

```python
from ai_trading.features import ema as _ema  # noqa: F401
from ai_trading.features import log_returns as _log_returns  # noqa: F401
from ai_trading.features import rsi as _rsi  # noqa: F401
from ai_trading.features import volatility as _volatility  # noqa: F401
from ai_trading.features import volume as _volume  # noqa: F401
from ai_trading.features import ma_feature as _ma_feature  # noqa: F401  ← Ajouter ici
```

---

## 4. Contrat `min_periods` / warmup

Le système de warmup garantit qu'aucun NaN ne subsiste dans la zone valide. Il repose sur un contrat strict entre chaque feature et le pipeline :

### Invariant

```
min_periods(params) == nombre exact de NaN en tête produits par compute()
```

Ce contrat est vérifié par les tests : on calcule la feature sur des données synthétiques et on compare le nombre de NaN en tête avec `min_periods()`.

### Validation du warmup

`apply_warmup()` (dans `ai_trading/features/warmup.py`) applique la logique suivante :

```
1. Calculer max_min_periods = max(feature.min_periods(params) for feature in features)
2. Vérifier : min_warmup >= max_min_periods
   → Sinon : raise ValueError("Warmup zone insufficient")
3. Construire warmup_mask : False pour [0..min_warmup-1], True à partir de min_warmup
4. Combiner avec valid_mask (détection de gaps) : final_mask = warmup_mask AND valid_mask
5. Vérifier : aucun NaN dans features_df[final_mask]
   → Sinon : raise ValueError("NaN in valid zone → bug feature ou warmup insuffisant")
```

### Exemple

```
feature     | min_periods
------------|------------
logret_1    | 1
logret_4    | 4
vol_72      | 72
ema_ratio   | 25  (ema_slow - 1)

max_min_periods = 72
min_warmup (config) = 200 ≥ 72 ✅
→ Les 200 premières barres sont exclues (warmup zone)
→ À partir de la barre 200, toutes les features sont garanties non-NaN
```

---

## 5. Features existantes (MVP)

Le pipeline MVP définit 9 features (F=9) :

| Feature | Formule | `min_periods` | `required_params` |
|---|---|---|---|
| `logret_1` | $\log(C_t / C_{t-1})$ | 1 | `[]` |
| `logret_2` | $\log(C_t / C_{t-2})$ | 2 | `[]` |
| `logret_4` | $\log(C_t / C_{t-4})$ | 4 | `[]` |
| `vol_24` | $\text{std}(\text{logret}_1[t\text{-}23:t],\ \text{ddof}{=}0)$ | 24 | `["volatility_ddof"]` |
| `vol_72` | $\text{std}(\text{logret}_1[t\text{-}71:t],\ \text{ddof}{=}0)$ | 72 | `["volatility_ddof"]` |
| `logvol` | $\log(V_t + \varepsilon)$ | 0 | `["logvol_epsilon"]` |
| `dlogvol` | $\text{logvol}(t) - \text{logvol}(t\text{-}1)$ | 1 | `["logvol_epsilon"]` |
| `rsi_14` | Wilder smoothing, $RSI = 100 - \frac{100}{1+RS}$ | 14 | `["rsi_period", "rsi_epsilon"]` |
| `ema_ratio_12_26` | $\frac{\text{EMA}_{12}(t)}{\text{EMA}_{26}(t)} - 1$ | 25 | `["ema_fast", "ema_slow"]` |

### Patterns d'implémentation observés

**Factory pattern** (log_returns) : une seule classe `LogReturnK` paramétrée par `k`, enregistrée 3 fois :
```python
def _make_logret_class(k: int) -> type:
    @register_feature(f"logret_{k}")
    class LogReturnK(BaseFeature):
        required_params: list[str] = []
        def min_periods(self, params): return k
        def compute(self, ohlcv, params):
            close = ohlcv["close"]
            return np.log(close / close.shift(k))
    return LogReturnK
```

**Wilder smoothing** (RSI) : initialisation SMA sur les $n$ premières valeurs, puis lissage exponentiel :
```python
ag_t = ((n-1) * ag_{t-1} + gain_t) / n
```

**EMA avec SMA init** : $\text{EMA}_n(n{-}1) = \text{SMA}(C[0..n{-}1])$, puis $\text{EMA}_n(t) = \alpha \cdot C_t + (1{-}\alpha) \cdot \text{EMA}_n(t{-}1)$

---

## 6. Flux d'exécution dans le pipeline

Le calcul des features est orchestré par `ai_trading/features/pipeline.py` :

```
config.features.feature_list         # ["logret_1", ..., "ema_ratio_12_26"]
         ↓
resolve_features(config)
  ├── Valide feature_list : non vide, pas de doublons
  ├── Pour chaque nom : lookup dans FEATURE_REGISTRY → instancie la classe
  ├── Valide required_params présents dans config.features.params
  └── Retourne : list[BaseFeature]
         ↓
compute_features(ohlcv, config)
  ├── Appelle resolve_features()
  ├── Pour chaque (nom, instance) :
  │     series = instance.compute(ohlcv, params_dict)
  │     assert len(series) == len(ohlcv)
  └── Retourne : pd.DataFrame (N × F), colonnes dans l'ordre de feature_list
         ↓
apply_warmup(features_df, valid_mask, min_warmup, instances, params)
  ├── Vérifie min_warmup >= max(min_periods)
  ├── Combine warmup_mask & valid_mask
  ├── Vérifie aucun NaN dans la zone valide
  └── Retourne : final_mask (np.ndarray[bool]) de taille N
```

Le résultat (`features_df` + `final_mask`) est ensuite passé au sample builder qui construit les tenseurs `(N, L, F)` pour l'entraînement des modèles.

---

## 7. Exemple complet : feature Momentum

### 7.1 — `ai_trading/features/momentum.py`

```python
"""Momentum feature — Close-to-close difference over k bars.

Formula: momentum_k(t) = C_t - C_{t-k}
Strictly causal: value at t depends only on data at t and t-k.
"""

from __future__ import annotations

import pandas as pd

from ai_trading.features.registry import BaseFeature, register_feature


@register_feature("momentum_10")
class Momentum10(BaseFeature):
    """Price momentum over 10 bars."""

    required_params: list[str] = ["momentum_period"]

    def min_periods(self, params: dict) -> int:
        return params["momentum_period"]

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        period = params["momentum_period"]
        close = ohlcv["close"]
        return close - close.shift(period)
```

### 7.2 — Config Pydantic (`ai_trading/config.py`)

Ajouter le champ dans `FeaturesParamsConfig` :

```python
class FeaturesParamsConfig(_StrictBase):
    rsi_period: int
    rsi_epsilon: float
    ema_fast: int
    ema_slow: int
    vol_windows: list[int] = Field(min_length=1)
    logvol_epsilon: float
    volatility_ddof: int
    momentum_period: int = Field(gt=0)    # ← Ajouter ici
```

### 7.3 — YAML (`configs/default.yaml`)

```yaml
features:
  feature_version: mvp_v2
  feature_list:
    - logret_1
    - logret_2
    - logret_4
    - vol_24
    - vol_72
    - logvol
    - dlogvol
    - rsi_14
    - ema_ratio_12_26
    - momentum_10

  params:
    rsi_period: 14
    rsi_epsilon: 1.0e-12
    ema_fast: 12
    ema_slow: 26
    vol_windows:
      - 24
      - 72
    logvol_epsilon: 1.0e-8
    volatility_ddof: 0
    momentum_period: 10
```

### 7.4 — Import (`ai_trading/features/__init__.py`)

```python
from ai_trading.features import momentum as _momentum  # noqa: F401
```

### 7.5 — Tests (`tests/test_momentum.py`)

Les tests doivent couvrir :

```python
def test_momentum_registered():
    """momentum_10 est présent dans FEATURE_REGISTRY."""
    assert "momentum_10" in FEATURE_REGISTRY

def test_momentum_min_periods():
    """min_periods == momentum_period."""
    instance = FEATURE_REGISTRY["momentum_10"]()
    assert instance.min_periods({"momentum_period": 10}) == 10

def test_momentum_compute_shape():
    """compute() retourne une Series de même longueur que l'input."""
    # ... données synthétiques ...
    assert len(result) == len(ohlcv)

def test_momentum_leading_nans():
    """Nombre de NaN en tête == min_periods."""
    # ... vérifier que les 10 premières valeurs sont NaN ...

def test_momentum_numerical_correctness():
    """Vérifier C_t - C_{t-10} sur un cas connu."""
    # ... calcul manuel vs résultat compute() ...

def test_momentum_causality():
    """Modifier des données futures ne change pas les valeurs passées."""
    # ... modifier ohlcv[t+1:] et vérifier que result[:t+1] est inchangé ...
```

---

## 8. Checklist finale

Avant de soumettre une PR, vérifier :

- [ ] **Héritage** : la classe hérite de `BaseFeature`
- [ ] **`required_params`** : déclaré explicitement dans le corps de la classe (même si `[]`)
- [ ] **2 méthodes abstraites** : `min_periods()` et `compute()` implémentées
- [ ] **`@register_feature("nom")`** : décorateur appliqué avec un nom unique
- [ ] **Causalité stricte** : valeur à $t$ ne dépend que de données $\leq t$
- [ ] **Contrat `min_periods`** : nombre de NaN en tête == valeur retournée par `min_periods()`
- [ ] **Longueur conservée** : `len(compute(ohlcv, params)) == len(ohlcv)`
- [ ] **Config Pydantic** : paramètres ajoutés dans `FeaturesParamsConfig` si `required_params` non vide
- [ ] **YAML** : feature ajoutée dans `feature_list` et paramètres dans `params`
- [ ] **Import** : module importé dans `ai_trading/features/__init__.py`
- [ ] **`feature_version`** : incrémentée si la liste de features change
- [ ] **Warmup** : vérifier que `window.min_warmup >= max(min_periods)` avec la nouvelle feature
- [ ] **Pas de hardcoding** : aucun paramètre en dur dans le code de calcul
- [ ] **Pas de fallback** : pas de `or default`, pas de `except` trop large — laisser les erreurs remonter
- [ ] **Tests TDD** : enregistrement, `min_periods`, shape, NaN en tête, exactitude numérique, causalité
- [ ] **Ruff** : `ruff check ai_trading/ tests/` clean
