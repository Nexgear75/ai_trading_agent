# Guide — Ajouter une feature supplémentaire au pipeline

**Référence** : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` §6.2, `docs/plan/implementation.md` WS-3.6
**Date** : 2026-02-28

> Ce guide explique pas à pas comment implémenter et intégrer une nouvelle feature dans le pipeline AI Trading, en respectant l'architecture pluggable du registre.

---

## Prérequis

- Le WS-3.6 (registre pluggable) est implémenté.
- L'architecture repose sur :
  - `ai_trading/features/registry.py` — `FEATURE_REGISTRY`, `BaseFeature`, `@register_feature`
  - `ai_trading/features/pipeline.py` — `compute_features()`
  - `ai_trading/features/__init__.py` — auto-imports

---

## Exemple concret : ajouter `atr_14` (Average True Range)

L'ATR mesure la volatilité à partir des prix High, Low et Close. Formule :

$$
\text{TR}(t) = \max\bigl(H_t - L_t,\; |H_t - C_{t-1}|,\; |L_t - C_{t-1}|\bigr)
$$

$$
\text{ATR}_n(t) = \text{EMA}_{\text{Wilder}}(\text{TR}, n) \quad \text{avec } \alpha = 1/n
$$

---

## Étapes d'implémentation

### 1. Créer le module feature

Créer `ai_trading/features/atr.py` :

```python
"""ATR (Average True Range) feature."""

import numpy as np
import pandas as pd

from ai_trading.features.registry import BaseFeature, register_feature


@register_feature("atr_14")
class ATR14Feature(BaseFeature):
    """Average True Range sur 14 périodes (lissage de Wilder)."""

    required_params: list[str] = ["atr_period"]

    @property
    def min_periods(self) -> int:
        return 14  # Ou lire depuis params si paramétrable

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        period = params["atr_period"]
        high = ohlcv["high"]
        low = ohlcv["low"]
        close = ohlcv["close"]

        prev_close = close.shift(1)
        tr = pd.concat(
            [
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        # Lissage de Wilder : EMA avec alpha = 1/n
        atr = tr.ewm(alpha=1.0 / period, adjust=False).mean()
        atr.name = "atr_14"
        return atr
```

**Contraintes à respecter** :
- La feature est **strictement causale** : elle ne dépend que de données à $t' \leq t$.
- La méthode `compute()` reçoit le DataFrame OHLCV complet et le dict `params`.
- Elle retourne une `pd.Series` indexée par timestamp.
- `required_params` liste les clés nécessaires dans `config.features.params`.
- `min_periods` déclare le nombre minimum de bougies avant la première valeur valide.

---

### 2. Enregistrer le module dans `features/__init__.py`

Ajouter l'import pour peupler automatiquement `FEATURE_REGISTRY` :

```python
"""Feature engineering — pluggable registry and pipeline."""

from ai_trading.features import log_returns, volatility, rsi, ema, volume
from ai_trading.features import atr  # ← AJOUTER
```

Sans cet import, la feature ne sera pas dans le registre et `compute_features()` lèvera une `ValueError`.

---

### 3. Ajouter les paramètres dans `configs/default.yaml`

```yaml
features:
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
    - atr_14              # ← AJOUTER

  params:
    # ... params existants ...
    atr_period: 14        # ← AJOUTER
```

**Important** : si `atr_period` n'est pas présent dans `params`, le pipeline lèvera une erreur explicite grâce à la validation de `required_params` dans `compute_features()`.

---

### 4. Vérifier la contrainte warmup

Si la nouvelle feature introduit un `min_periods` supérieur au `min_warmup` actuel, mettre à jour la config :

```yaml
window:
  min_warmup: 200  # Doit être >= max(min_periods de toutes les features)
```

La validation de config (WS-1.3) vérifie :

```
min_warmup >= max(rsi_period, ema_slow, max(vol_windows), atr_period, ...)
```

Pour `atr_14` avec `period=14`, le `min_warmup=200` actuel est largement suffisant.

---

### 5. Incrémenter `feature_version`

La spec (§6.2) impose que tout changement du jeu de features soit tracé :

```yaml
features:
  feature_version: mvp_v2   # ← était mvp_v1
```

Ceci garantit la comparabilité : les runs avec `mvp_v1` (9 features) et `mvp_v2` (10 features) sont distincts et non comparables directement.

---

### 6. Écrire les tests

Créer `tests/features/test_atr.py` :

```python
"""Tests pour la feature ATR."""

import numpy as np
import pandas as pd
import pytest


class TestATR14:
    """Tests unitaires pour atr_14."""

    def test_atr_shape(self, sample_ohlcv: pd.DataFrame):
        """Le résultat a la même longueur que l'input."""
        from ai_trading.features.registry import FEATURE_REGISTRY

        feature_cls = FEATURE_REGISTRY["atr_14"]
        result = feature_cls().compute(sample_ohlcv, {"atr_period": 14})
        assert len(result) == len(sample_ohlcv)

    def test_atr_non_negative(self, sample_ohlcv: pd.DataFrame):
        """L'ATR est toujours >= 0."""
        from ai_trading.features.registry import FEATURE_REGISTRY

        feature_cls = FEATURE_REGISTRY["atr_14"]
        result = feature_cls().compute(sample_ohlcv, {"atr_period": 14})
        valid = result.dropna()
        assert (valid >= 0).all()

    def test_atr_causality(self, sample_ohlcv: pd.DataFrame):
        """Modifier les données futures ne change pas la valeur à t."""
        from ai_trading.features.registry import FEATURE_REGISTRY

        feature_cls = FEATURE_REGISTRY["atr_14"]
        params = {"atr_period": 14}

        result_full = feature_cls().compute(sample_ohlcv, params)

        # Modifier les 10 dernières bougies
        modified = sample_ohlcv.copy()
        modified.iloc[-10:, modified.columns.get_loc("close")] *= 2.0
        result_modified = feature_cls().compute(modified, params)

        # Les valeurs avant la modification doivent être identiques
        t = len(sample_ohlcv) - 11
        np.testing.assert_array_equal(
            result_full.iloc[:t].values,
            result_modified.iloc[:t].values,
        )

    def test_atr_known_value(self):
        """Vérification sur données synthétiques à valeur connue."""
        # Bougies constantes → TR = 0 → ATR = 0
        n = 50
        ohlcv = pd.DataFrame(
            {
                "open": np.full(n, 100.0),
                "high": np.full(n, 100.0),
                "low": np.full(n, 100.0),
                "close": np.full(n, 100.0),
                "volume": np.full(n, 1000.0),
            }
        )
        from ai_trading.features.registry import FEATURE_REGISTRY

        feature_cls = FEATURE_REGISTRY["atr_14"]
        result = feature_cls().compute(ohlcv, {"atr_period": 14})
        # Après warmup, ATR doit être ~0 pour des prix constants
        assert result.iloc[-1] == pytest.approx(0.0, abs=1e-10)

    def test_registry_contains_atr(self):
        """La feature est bien enregistrée."""
        from ai_trading.features.registry import FEATURE_REGISTRY

        assert "atr_14" in FEATURE_REGISTRY

    def test_missing_param_raises(self, sample_ohlcv: pd.DataFrame):
        """Un param manquant lève une erreur."""
        from ai_trading.features.registry import FEATURE_REGISTRY

        feature_cls = FEATURE_REGISTRY["atr_14"]
        with pytest.raises(KeyError):
            feature_cls().compute(sample_ohlcv, {})
```

**Tests essentiels** pour toute nouvelle feature :
1. **Shape** — même longueur que l'input
2. **Non-régression sur valeurs connues** — formule vérifiable analytiquement
3. **Causalité** — modifier le futur ne change pas le passé
4. **Enregistrement** — la feature est dans `FEATURE_REGISTRY`
5. **Paramètre manquant** — erreur explicite

---

### 7. Mettre à jour le tenseur

Le changement de `F=9` à `F=10` est automatique : le sample builder (WS-4.2) lit `feature_list` et dimensionne le tenseur `X_seq ∈ ℝ^{N × L × F}` dynamiquement. L'adapter XGBoost (WS-4.3) produit `(N, L*F)` = `(N, 1280)` au lieu de `(N, 1152)`.

Aucune modification du code de WS-4 n'est nécessaire.

---

## Checklist récapitulative

| # | Action | Fichier(s) concerné(s) |
|---|--------|----------------------|
| 1 | Créer la classe feature avec `@register_feature` | `ai_trading/features/<nom>.py` |
| 2 | Ajouter l'import dans `__init__.py` | `ai_trading/features/__init__.py` |
| 3 | Ajouter le nom dans `feature_list` + les params | `configs/default.yaml` |
| 4 | Vérifier `min_warmup >= max(min_periods)` | `configs/default.yaml` |
| 5 | Incrémenter `feature_version` | `configs/default.yaml` |
| 6 | Écrire les tests (shape, causalité, valeur connue) | `tests/features/test_<nom>.py` |
| 7 | Valider que le pipeline complet passe | `make test` |

---

## Erreurs courantes à éviter

| Erreur | Conséquence | Prévention |
|--------|------------|------------|
| Oublier l'import dans `__init__.py` | `ValueError: unknown feature` | Auto-check : `assert "nom" in FEATURE_REGISTRY` |
| Utiliser des données futures ($t' > t$) | Fuite d'information (look-ahead bias) | Test de causalité obligatoire |
| Oublier `required_params` | Crash silencieux ou `KeyError` | Le pipeline valide les params avant `compute()` |
| Ne pas incrémenter `feature_version` | Runs non comparables mélangés | Convention d'équipe |
| `min_periods` trop faible | NaN dans la zone "valide" | Le warmup mask (WS-3.7) attrape les NaN résiduels |

---

## Features candidates post-MVP

Pour référence, voici des candidates pertinentes pour de futurs ajouts :

| Feature | Description | `min_periods` estimé |
|---------|-------------|---------------------|
| `atr_14` | Average True Range (volatilité H/L/C) | 14 |
| `macd_hist` | MACD histogramme (EMA 12 − EMA 26 − signal 9) | 35 |
| `bbw_20` | Largeur des bandes de Bollinger (20 périodes) | 20 |
| `obv` | On-Balance Volume (volume cumulé directionnel) | 1 |
| `stoch_k_14` | Stochastique %K (position dans le range H/L) | 14 |
| `vwap_ratio` | Prix / VWAP rolling (24h) | 24 |
| `logret_24` | Log-return à 24 pas (momentum journalier) | 24 |
