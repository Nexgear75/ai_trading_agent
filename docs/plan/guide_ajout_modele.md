# Guide — Comment implémenter un modèle supplémentaire

**Référence** : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md`, `docs/plan/implementation.md` (WS-6.1)

Ce guide décrit, étape par étape, comment ajouter un nouveau modèle (ML, DL ou RL) au pipeline AI Trading. L'architecture plug-in repose sur le pattern `BaseModel` + `MODEL_REGISTRY` (WS-6.1) : **aucune modification du pipeline, du trainer, du calibrateur ou du backtest n'est nécessaire**.

---

## Table des matières

1. [Vue d'ensemble du pattern plug-in](#1--vue-densemble-du-pattern-plug-in)
2. [Étape 1 — Créer le fichier du modèle](#2--étape-1--créer-le-fichier-du-modèle)
3. [Étape 2 — Implémenter `BaseModel`](#3--étape-2--implémenter-basemodel)
4. [Étape 3 — Enregistrer le modèle dans `__init__.py`](#4--étape-3--enregistrer-le-modèle-dans-__init__py)
5. [Étape 4 — Ajouter la configuration YAML](#5--étape-4--ajouter-la-configuration-yaml)
6. [Étape 5 — Valider la configuration (Pydantic)](#6--étape-5--valider-la-configuration-pydantic)
7. [Étape 6 — Écrire les tests](#7--étape-6--écrire-les-tests)
8. [Étape 7 — Exécuter un run](#8--étape-7--exécuter-un-run)
9. [Checklist récapitulative](#9--checklist-récapitulative)
10. [Exemples de référence](#10--exemples-de-référence)

---

## 1 — Vue d'ensemble du pattern plug-in

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│ Orchestrateur│────▶│  MODEL_REGISTRY  │────▶│ MonModèle    │
│  (WS-12.2)   │     │  {name → class}  │     │ (BaseModel)  │
└──────────────┘     └──────────────────┘     └──────────────┘
       │                                             │
       │  model = MODEL_REGISTRY[config.strategy.name]()
       │                                             │
       ▼                                             ▼
  FoldTrainer.train_fold()                    model.fit() / predict()
       │                                             │
       ▼                                             ▼
  Calibration θ (si output_type == "regression")
       │
       ▼
  Backtest engine (utilise execution_mode)
```

**Principes clés :**

- Le pipeline ne contient **aucune logique spécifique** à un modèle concret. Il interagit uniquement avec `BaseModel`.
- `output_type` détermine si la calibration θ est appliquée (`"regression"`) ou bypassée (`"signal"`).
- `execution_mode` détermine le comportement du backtest (`"standard"` = multi-trades, `"single_trade"` = un seul trade).
- Le trainer passe systématiquement `meta_train`, `meta_val` et `ohlcv` ; les modèles supervisés les ignorent.

---

## 2 — Étape 1 — Créer le fichier du modèle

Créer un fichier dans `ai_trading/models/`, par exemple :

```
ai_trading/models/mon_modele.py
```

Pour une baseline, le placer dans `ai_trading/models/baselines/`.

---

## 3 — Étape 2 — Implémenter `BaseModel`

### Contrat d'interface

Chaque modèle doit hériter de `BaseModel` et implémenter :

| Méthode / Attribut | Description |
|---|---|
| `output_type` | `"regression"` (float → calibration θ) ou `"signal"` (binaire 0/1 → bypass θ) |
| `execution_mode` | `"standard"` (défaut) ou `"single_trade"` |
| `fit(X_train, y_train, X_val, y_val, config, run_dir, meta_train, meta_val, ohlcv)` | Entraînement. Retourne un dict d'artefacts (ou `{}`) |
| `predict(X, meta, ohlcv)` | Prédictions. Retourne `np.ndarray` de shape `(N,)` |
| `save(path)` | Sérialisation sur disque |
| `load(path)` | Désérialisation depuis le disque |

### Squelette générique

```python
"""Mon modèle — description courte."""

import numpy as np
from pathlib import Path

from ai_trading.models.base import BaseModel
from ai_trading.models.registry import register_model


@register_model("mon_modele_reg")
class MonModele(BaseModel):
    """Description du modèle."""

    output_type = "regression"   # ou "signal"
    execution_mode = "standard"  # ou "single_trade"

    def __init__(self):
        self.model = None

    def fit(self, X_train, y_train, X_val, y_val, config, run_dir,
            meta_train=None, meta_val=None, ohlcv=None):
        # X_train : np.ndarray (N_train, L, F) — déjà scalé par le trainer
        # y_train : np.ndarray (N_train,)
        # X_val   : np.ndarray (N_val, L, F) — déjà scalé
        # y_val   : np.ndarray (N_val,)

        # --- Adapter les données si nécessaire ---
        # Ex: flatten pour tabulaire : X_flat = X_train.reshape(X_train.shape[0], -1)
        # Ex: garder (N, L, F) pour DL séquentiel

        # --- Construire et entraîner le modèle ---
        # L'early stopping est de VOTRE responsabilité.
        # Pour DL, utiliser le helper training/dl_train_loop.py
        # Pour tree-based, utiliser l'API native (early_stopping_rounds)

        # --- Retourner les artefacts d'entraînement ---
        return {"best_epoch": ..., "train_loss": ..., "val_loss": ...}

    def predict(self, X, meta=None, ohlcv=None):
        # Retourner un vecteur (N,) :
        #   - float si output_type == "regression"
        #   - int 0/1 si output_type == "signal"
        X_input = ...  # adapter si nécessaire
        return self.model.predict(X_input)

    def save(self, path):
        # Sauvegarder dans le répertoire `path`
        ...

    def load(self, path):
        # Charger depuis le répertoire `path`
        ...
```

### Cas particuliers selon `output_type`

#### Modèle supervisé (`output_type = "regression"`)

- `fit()` : entraîner sur `(X_train, y_train)`, utiliser `(X_val, y_val)` pour l'early stopping.
- `predict()` : retourner des **floats** (log-returns prédits).
- `meta_train`, `meta_val`, `ohlcv` : **ignorés** (ne pas les utiliser).
- La calibration θ est appliquée automatiquement par l'orchestrateur.

#### Modèle signal / RL (`output_type = "signal"`)

- `predict()` : retourner des **entiers 0/1** (Go / No-Go).
- La calibration θ est **bypassée** automatiquement.
- Si le modèle nécessite `meta` ou `ohlcv`, valider leur présence au début de `fit()` :

```python
def fit(self, X_train, y_train, X_val, y_val, config, run_dir,
        meta_train=None, meta_val=None, ohlcv=None):
    if meta_train is None:
        raise ValueError("meta_train is required for MonModeleRL")
    ...
```

### Helper DL partagé

Pour les modèles Deep Learning (PyTorch), utiliser le helper commun pour éviter la duplication de la boucle d'entraînement :

```python
from ai_trading.training.dl_train_loop import run_dl_training

def fit(self, X_train, y_train, X_val, y_val, config, run_dir, **kwargs):
    # Construire les DataLoaders, loss_fn, optimizer...
    
    result = run_dl_training(
        model=self.net,
        train_loader=train_loader,
        val_loader=val_loader,
        loss_fn=loss_fn,
        optimizer=optimizer,
        patience=config.training.early_stopping_patience,
        max_epochs=config.training.max_epochs,
    )
    return {"best_epoch": result.best_epoch, ...}
```

---

## 4 — Étape 3 — Enregistrer le modèle dans `__init__.py`

Ajouter l'import dans `ai_trading/models/__init__.py` pour peupler le `MODEL_REGISTRY` au chargement du package :

```python
# ai_trading/models/__init__.py

from ai_trading.models.mon_modele import MonModele  # <-- ajouter cette ligne
```

Sans cet import, le décorateur `@register_model` n'est jamais exécuté et le modèle reste invisible pour le pipeline.

---

## 5 — Étape 4 — Ajouter la configuration YAML

Ajouter les hyperparamètres du modèle dans `configs/default.yaml` sous la clé `models` :

```yaml
models:
  # ... modèles existants ...

  mon_modele:
    hidden_size: 128
    num_layers: 2
    dropout: 0.3
    mon_param_specifique: 42
```

Ces paramètres sont accessibles dans `fit()` via `config.models.mon_modele.*`.

Pour utiliser le modèle, modifier la section `strategy` :

```yaml
strategy:
  strategy_type: model
  name: mon_modele_reg    # doit correspondre au nom dans @register_model
```

---

## 6 — Étape 5 — Valider la configuration (Pydantic)

Ajouter un sous-modèle Pydantic pour les hyperparamètres du modèle dans le module de configuration (`ai_trading/config.py` ou équivalent) :

```python
class MonModeleConfig(BaseModel):
    hidden_size: int = Field(64, ge=1)
    num_layers: int = Field(1, ge=1)
    dropout: float = Field(0.2, ge=0.0, lt=1.0)
    mon_param_specifique: int = Field(42, ge=1)
```

Et l'ajouter dans le modèle `ModelsConfig` parent :

```python
class ModelsConfig(BaseModel):
    # ... existants ...
    mon_modele: MonModeleConfig = MonModeleConfig()
```

Ceci garantit :
- Validation des types et bornes à la charge de la config.
- Rejet des clés inconnues (`extra="forbid"`).
- Valeurs par défaut documentées.

---

## 7 — Étape 6 — Écrire les tests

### Tests unitaires minimaux

Créer `tests/test_mon_modele.py` :

```python
import numpy as np
import pytest

from ai_trading.models.registry import MODEL_REGISTRY


def test_model_registered():
    """Le modèle est présent dans le registre."""
    assert "mon_modele_reg" in MODEL_REGISTRY


def test_fit_predict_shapes(dummy_config, tmp_path):
    """fit() et predict() respectent le contrat BaseModel."""
    model_cls = MODEL_REGISTRY["mon_modele_reg"]
    model = model_cls()

    N_train, N_val, L, F = 200, 50, 128, 9
    X_train = np.random.randn(N_train, L, F).astype(np.float32)
    y_train = np.random.randn(N_train).astype(np.float32)
    X_val = np.random.randn(N_val, L, F).astype(np.float32)
    y_val = np.random.randn(N_val).astype(np.float32)

    model.fit(X_train, y_train, X_val, y_val, config=dummy_config, run_dir=tmp_path)

    y_hat = model.predict(X_val)
    assert y_hat.shape == (N_val,)
    # Pour un modèle "regression" :
    assert y_hat.dtype in (np.float32, np.float64)
    # Pour un modèle "signal" :
    # assert set(np.unique(y_hat)).issubset({0, 1})


def test_save_load(dummy_config, tmp_path):
    """Le cycle save/load produit les mêmes prédictions."""
    model_cls = MODEL_REGISTRY["mon_modele_reg"]
    model = model_cls()

    X = np.random.randn(50, 128, 9).astype(np.float32)
    y = np.random.randn(50).astype(np.float32)

    model.fit(X, y, X, y, config=dummy_config, run_dir=tmp_path)
    y_hat_before = model.predict(X)

    save_dir = tmp_path / "model_save"
    save_dir.mkdir()
    model.save(str(save_dir))

    model2 = model_cls()
    model2.load(str(save_dir))
    y_hat_after = model2.predict(X)

    np.testing.assert_array_almost_equal(y_hat_before, y_hat_after)


def test_output_type():
    """output_type est correctement déclaré."""
    model_cls = MODEL_REGISTRY["mon_modele_reg"]
    assert model_cls.output_type in ("regression", "signal")


def test_execution_mode():
    """execution_mode a une valeur valide."""
    model_cls = MODEL_REGISTRY["mon_modele_reg"]
    assert model_cls.execution_mode in ("standard", "single_trade")
```

### Tests de reproductibilité

```python
def test_determinism(dummy_config, tmp_path):
    """Deux entraînements avec la même seed produisent le même résultat."""
    X = np.random.randn(100, 128, 9).astype(np.float32)
    y = np.random.randn(100).astype(np.float32)

    model1 = MODEL_REGISTRY["mon_modele_reg"]()
    model1.fit(X, y, X, y, config=dummy_config, run_dir=tmp_path)
    y1 = model1.predict(X)

    model2 = MODEL_REGISTRY["mon_modele_reg"]()
    model2.fit(X, y, X, y, config=dummy_config, run_dir=tmp_path)
    y2 = model2.predict(X)

    np.testing.assert_array_equal(y1, y2)
```

---

## 8 — Étape 7 — Exécuter un run

```bash
# Run avec le nouveau modèle
python -m ai_trading --config configs/default.yaml --set strategy.name=mon_modele_reg

# Ou avec un fichier config dédié
python -m ai_trading --config configs/mon_modele.yaml
```

Le pipeline exécute automatiquement :
1. Chargement et validation de la config
2. Walk-forward splitting
3. Pour chaque fold : scaling → `fit()` → `predict()` → calibration θ (si regression) → backtest
4. Agrégation inter-fold
5. Génération des artefacts (`manifest.json`, `metrics.json`, `equity_curve.csv`, etc.)

---

## 9 — Checklist récapitulative

| # | Action | Fichier(s) |
|---|---|---|
| 1 | Créer le fichier du modèle | `ai_trading/models/mon_modele.py` |
| 2 | Hériter de `BaseModel`, implémenter `fit/predict/save/load` | idem |
| 3 | Décorer avec `@register_model("mon_modele_reg")` | idem |
| 4 | Déclarer `output_type` et `execution_mode` | idem |
| 5 | Ajouter l'import dans `__init__.py` | `ai_trading/models/__init__.py` |
| 6 | Ajouter les hyperparamètres dans le YAML | `configs/default.yaml` |
| 7 | Ajouter le sous-modèle Pydantic de validation | `ai_trading/config.py` |
| 8 | Écrire les tests unitaires | `tests/test_mon_modele.py` |
| 9 | Vérifier le run bout en bout | CLI |

**Aucune modification nécessaire dans :**
- `ai_trading/training/trainer.py` (FoldTrainer)
- `ai_trading/calibration/` (calibrateur θ)
- `ai_trading/backtest/` (moteur de backtest)
- `ai_trading/pipeline/` (orchestrateur)
- `ai_trading/metrics/` (métriques)
- `ai_trading/artifacts/` (artefacts)

---

## 10 — Exemples de référence

| Type | Modèle | Fichier | `output_type` | `execution_mode` |
|---|---|---|---|---|
| Supervisé (tabulaire) | XGBoost | `models/xgboost.py` | `regression` | `standard` |
| DL séquentiel | CNN1D | `models/cnn1d.py` | `regression` | `standard` |
| DL séquentiel | GRU | `models/gru.py` | `regression` | `standard` |
| DL séquentiel | LSTM | `models/lstm.py` | `regression` | `standard` |
| DL Transformer | PatchTST | `models/patchtst.py` | `regression` | `standard` |
| RL | PPO | `models/rl_ppo.py` | `signal` | `standard` |
| Baseline | No-Trade | `models/baselines/no_trade.py` | `signal` | `standard` |
| Baseline | Buy & Hold | `models/baselines/buy_hold.py` | `signal` | `single_trade` |
| Baseline | SMA Rule | `models/baselines/sma_rule.py` | `signal` | `standard` |

Pour un premier modèle, s'inspirer de `XGBoostModel` (supervisé simple) ou de `NoTradeBaseline` (contrat minimal).
