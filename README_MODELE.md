# Guide — Ajouter un nouveau modèle au pipeline

Ce document décrit pas à pas comment intégrer un nouveau modèle dans le pipeline AI Trading.

---

## Table des matières

1. [Architecture générale](#1-architecture-générale)
   - [Modèles prévus](#modèles-prévus)
2. [Interface `BaseModel` (ABC)](#2-interface-basemodel-abc)
3. [Étapes d'intégration](#3-étapes-dintégration)
   - [3.1 Créer la classe du modèle](#31-créer-la-classe-du-modèle)
   - [3.2 Ajouter la config Pydantic](#32-ajouter-la-config-pydantic)
   - [3.3 Ajouter les valeurs YAML](#33-ajouter-les-valeurs-yaml)
   - [3.4 Déclarer la stratégie](#34-déclarer-la-stratégie)
   - [3.5 Enregistrer le module](#35-enregistrer-le-module)
4. [Contrats d'entrée / sortie](#4-contrats-dentrée--sortie)
5. [Adapter Pattern (modèles tabulaires)](#5-adapter-pattern-modèles-tabulaires)
6. [Flux d'exécution dans le pipeline](#6-flux-dexécution-dans-le-pipeline)
7. [Exemple complet : modèle Transformer personnalisé](#7-exemple-complet--modèle-transformer-personnalisé)
8. [Checklist finale](#8-checklist-finale)

---

## 1. Architecture générale

```
ai_trading/models/
├── __init__.py          # Imports des modules modèles (déclenche l'enregistrement)
├── base.py              # BaseModel ABC + MODEL_REGISTRY + @register_model
├── dummy.py             # DummyModel (modèle de test)
└── xgboost.py           # XGBoostRegModel (modèle tabulaire de référence)
```

Le pipeline utilise un **registre global** (`MODEL_REGISTRY`) alimenté par des décorateurs `@register_model("nom")`. Le runner résout le nom de la stratégie en classe, l'instancie et l'injecte dans le `FoldTrainer`.

### Modèles prévus

Le pipeline prévoit les stratégies suivantes. Seuls `dummy` et `xgboost_reg` sont implémentés ; les autres sont **déclarés dans la config** (`VALID_STRATEGIES`, `ModelsConfig`, `configs/default.yaml`) et prêts à recevoir leur implémentation.

| Stratégie | Type | Fichier modèle | Config Pydantic | Statut |
|---|---|---|---|---|
| `dummy` | model | `models/dummy.py` | — | **Implémenté** |
| `xgboost_reg` | model | `models/xgboost.py` | `XGBoostModelConfig` | **Implémenté** |
| `cnn1d_reg` | model | — | `CNN1DModelConfig` | En attente |
| `gru_reg` | model | — | `GRUModelConfig` | En attente |
| `lstm_reg` | model | — | `LSTMModelConfig` | En attente |
| `patchtst_reg` | model | — | `PatchTSTModelConfig` | En attente |
| `rl_ppo` | model | — | `RLPPOModelConfig` | En attente |
| `no_trade` | baseline | `baselines/` | — | **Implémenté** |
| `buy_hold` | baseline | `baselines/` | — | **Implémenté** |
| `sma_rule` | baseline | `baselines/` | — | **Implémenté** |

Pour chaque modèle en attente, l'infrastructure est déjà en place :
- **Config Pydantic** : la classe `XxxModelConfig` existe dans `ai_trading/config.py` avec validation des hyperparamètres
- **YAML** : les valeurs par défaut sont définies dans `configs/default.yaml` sous `models.<nom>`
- **`VALID_STRATEGIES`** : le nom est déjà enregistré comme stratégie valide

Il ne reste qu'à créer le fichier `ai_trading/models/<nom>.py` avec la classe décorée `@register_model("...")` et l'importer dans `ai_trading/models/__init__.py` (voir les étapes détaillées dans la [section 3](#3-étapes-dintégration)).

---

## 2. Interface `BaseModel` (ABC)

Tout modèle **doit** hériter de `BaseModel` (défini dans `ai_trading/models/base.py`) et satisfaire les contraintes suivantes :

### Attributs de classe obligatoires

| Attribut | Type | Valeurs | Description |
|---|---|---|---|
| `output_type` | `Literal["regression", "signal"]` | **Obligatoire** en variable de classe | `"regression"` → prédictions continues, calibrées par seuil θ. `"signal"` → prédictions binaires 0/1, θ court-circuité. |
| `execution_mode` | `Literal["standard", "single_trade"]` | Optionnel (défaut `"standard"`) | `"single_trade"` réservé à `BuyHoldBaseline`. |

> **Attention** : `output_type` doit être déclaré **dans le corps de la classe** (pas seulement en annotation). Le mécanisme `__init_subclass__` vérifie sa présence dans `cls.__dict__` et lève `TypeError` sinon.

### Méthodes abstraites

#### `fit(X_train, y_train, X_val, y_val, config, run_dir, meta_train=None, meta_val=None, ohlcv=None) → dict`

Entraîne le modèle. Le scaler est déjà appliqué en amont par le `FoldTrainer` — les données arrivent pré-normalisées.

| Paramètre | Shape / Type | Description |
|---|---|---|
| `X_train` | `(N, L, F)` float32 | Features d'entraînement (séquentielles, normalisées) |
| `y_train` | `(N,)` float32 | Labels d'entraînement (log-returns) |
| `X_val` | `(N_val, L, F)` float32 | Features de validation (pour early stopping uniquement) |
| `y_val` | `(N_val,)` float32 | Labels de validation |
| `config` | `PipelineConfig` | Configuration complète — accès aux hyperparamètres via `config.models.<nom>` |
| `run_dir` | `Path` | Répertoire pour checkpoints et logs |
| `meta_train` | `Any` (optionnel) | Métadonnées (ex : `decision_time`) |
| `meta_val` | `Any` (optionnel) | Métadonnées validation |
| `ohlcv` | `Any` (optionnel) | Données OHLCV brutes (pour RL / baselines) |
| **Retour** | `dict` | Artefacts d'entraînement (meilleure epoch, loss finale, etc.) |

**Règle anti-fuite** : `X_val` / `y_val` servent uniquement à l'early stopping ou aux métriques de validation. Ne jamais les utiliser pour le fit du modèle lui-même.

#### `predict(X, meta=None, ohlcv=None) → np.ndarray`

Génère des prédictions.

| Paramètre | Shape / Type | Description |
|---|---|---|
| `X` | `(N, L, F)` float32 | Features pré-normalisées |
| `meta` | `Any` (optionnel) | Métadonnées |
| `ohlcv` | `Any` (optionnel) | Données OHLCV brutes |
| **Retour** | `(N,)` float32 | Prédictions continues (`regression`) ou binaires (`signal`) |

#### `save(path: Path) → None`

Persiste l'état du modèle sur disque.

#### `load(path: Path) → None`

Restaure l'état du modèle depuis le disque.

---

## 3. Étapes d'intégration

### 3.1 Créer la classe du modèle

Créer un fichier `ai_trading/models/mon_modele.py` :

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ai_trading.models.base import BaseModel, register_model


@register_model("mon_modele_reg")
class MonModeleModel(BaseModel):
    """Mon modèle de régression personnalisé."""

    output_type = "regression"  # Variable de classe, pas une annotation

    def __init__(self) -> None:
        self._model = None

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        config: Any,
        run_dir: Path,
        meta_train: Any = None,
        meta_val: Any = None,
        ohlcv: Any = None,
    ) -> dict:
        # Validation stricte des entrées
        if X_train.ndim != 3:
            raise ValueError(f"X_train must be 3D, got {X_train.ndim}D")
        if X_train.dtype != np.float32:
            raise TypeError(f"X_train must be float32, got {X_train.dtype}")

        # Accès aux hyperparamètres via la config
        model_cfg = config.models.mon_modele
        seed = config.reproducibility.global_seed

        # ... logique d'entraînement ...

        return {"best_epoch": 42, "final_loss": 0.01}

    def predict(
        self,
        X: np.ndarray,
        meta: Any = None,
        ohlcv: Any = None,
    ) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Model not fitted. Call fit() before predict().")
        if X.ndim != 3:
            raise ValueError(f"X must be 3D, got {X.ndim}D")
        if X.dtype != np.float32:
            raise TypeError(f"X must be float32, got {X.dtype}")

        y_hat = self._model.predict(X)
        return y_hat.astype(np.float32)

    def save(self, path: Path) -> None:
        if self._model is None:
            raise RuntimeError("Model not fitted. Call fit() before save().")
        resolved = path if path.suffix else path / "model.bin"
        resolved.parent.mkdir(parents=True, exist_ok=True)
        # ... sérialisation (pickle, torch.save, json, etc.) ...

    def load(self, path: Path) -> None:
        resolved = path if path.suffix else path / "model.bin"
        if not resolved.exists():
            raise FileNotFoundError(f"Model file not found: {resolved}")
        # ... désérialisation ...
```

**Règles impératives (strict code)** :
- Aucun fallback silencieux (`or default`, `value if value else default`)
- Validation explicite + `raise` pour les entrées invalides
- Pas de `except` trop large

### 3.2 Ajouter la config Pydantic

Dans `ai_trading/config.py`, ajouter une classe de config pour les hyperparamètres :

```python
class MonModeleModelConfig(_StrictBase):
    """Hyperparamètres de MonModele."""
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    hidden_dim: int = Field(gt=0)
    num_layers: int = Field(ge=1)
    dropout: float = Field(ge=0, lt=1)
    # ... autres hyperparamètres ...
```

Puis l'ajouter dans `ModelsConfig` :

```python
class ModelsConfig(_StrictBase):
    xgboost: XGBoostModelConfig
    cnn1d: CNN1DModelConfig
    gru: GRUModelConfig
    lstm: LSTMModelConfig
    patchtst: PatchTSTModelConfig
    rl_ppo: RLPPOModelConfig
    mon_modele: MonModeleModelConfig      # ← Ajouter ici
```

### 3.3 Ajouter les valeurs YAML

Dans `configs/default.yaml`, sous la section `models:` :

```yaml
models:
  # ... modèles existants ...

  mon_modele:
    hidden_dim: 128
    num_layers: 3
    dropout: 0.1
```

> **Config-driven** : tout hyperparamètre doit être dans le YAML. Aucune valeur ne doit être hardcodée dans le code Python.

### 3.4 Déclarer la stratégie

Dans `ai_trading/config.py`, ajouter l'entrée dans `VALID_STRATEGIES` :

```python
VALID_STRATEGIES: dict[str, str] = {
    "dummy": "model",
    "xgboost_reg": "model",
    "cnn1d_reg": "model",
    "gru_reg": "model",
    "lstm_reg": "model",
    "patchtst_reg": "model",
    "rl_ppo": "model",
    "mon_modele_reg": "model",          # ← Ajouter ici
    "no_trade": "baseline",
    "buy_hold": "baseline",
    "sma_rule": "baseline",
}
```

### 3.5 Enregistrer le module

Dans `ai_trading/models/__init__.py`, importer le nouveau module pour déclencher l'enregistrement :

```python
from . import (
    dummy,          # noqa: F401
    xgboost,        # noqa: F401
    mon_modele,     # noqa: F401    ← Ajouter ici
)
```

---

## 4. Contrats d'entrée / sortie

### Shapes et dtypes

| Donnée | Shape | Dtype | Notes |
|---|---|---|---|
| `X_train`, `X_val`, `X` (predict) | `(N, L, F)` | `float32` | L = `window.seq_len`, F = nombre de features |
| `y_train`, `y_val` | `(N,)` | `float32` | Log-returns futurs (label) |
| `y_hat` (retour predict) | `(N,)` | `float32` | Prédictions |

### Conventions float

- **float32** pour les tenseurs (`X_seq`, `y`, `y_hat`)
- **float64** pour les métriques de performance

### output_type et flux post-prédiction

```
output_type = "regression"
    predict() → y_hat continu → calibration θ (quantile grid) → signaux Go/No-Go → backtest

output_type = "signal"
    predict() → y_hat ∈ {0, 1} → PAS de calibration θ → signaux directs → backtest
```

---

## 5. Adapter Pattern (modèles tabulaires)

Les modèles séquentiels (CNN, GRU, LSTM, PatchTST) travaillent directement sur les données 3D `(N, L, F)`.

Les modèles tabulaires (ex : XGBoost) doivent aplatir les données en 2D. Le pipeline fournit un utilitaire dans `ai_trading/data/dataset.py` :

```python
from ai_trading.data.dataset import flatten_seq_to_tab

# (N, L, F) → (N, L×F)
x_tab, column_names = flatten_seq_to_tab(X_train, feature_names)
```

L'aplatissement se fait en C-order : pour chaque lag t, toutes les features sont concaténées :
```
[f0_t0, f1_t0, ..., fF-1_t0, f0_t1, f1_t1, ..., fF-1_tL-1]
```

L'adapter doit être appelé **dans `fit()` et `predict()`** du modèle tabulaire, pas dans le pipeline.

---

## 6. Flux d'exécution dans le pipeline

Le `FoldTrainer` (`ai_trading/training/trainer.py`) orchestre l'exécution par fold walk-forward :

```
Pour chaque fold :
  1. Scaler.fit(X_train)              ← Fit sur train UNIQUEMENT (anti-fuite)
  2. X_train_s = Scaler.transform(X_train)
     X_val_s   = Scaler.transform(X_val)
     X_test_s  = Scaler.transform(X_test)
  3. model.fit(X_train_s, y_train, X_val_s, y_val, config, run_dir)
  4. y_hat_val  = model.predict(X_val_s)
     y_hat_test = model.predict(X_test_s)
  5. model.save(run_dir / "model")
```

Le runner (`ai_trading/pipeline/runner.py`) instancie le modèle :

```python
model_cls = get_model_class(strategy_name)    # Résolution depuis le registre
model = model_cls()                           # Constructeur sans argument (sauf DummyModel)
```

> **Constructeur** : le runner appelle `model_cls()` sans argument pour tous les modèles (sauf `dummy` qui reçoit `seed`). Votre modèle doit avoir un `__init__(self)` sans paramètre obligatoire.

---

## 7. Exemple complet : modèle Transformer personnalisé

### 7.1 — `ai_trading/models/my_transformer.py`

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from ai_trading.models.base import BaseModel, register_model


class _TransformerNet(nn.Module):
    """Réseau Transformer interne."""

    def __init__(self, n_features: int, seq_len: int, d_model: int,
                 n_heads: int, n_layers: int, dropout: float) -> None:
        super().__init__()
        self.input_proj = nn.Linear(n_features, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dropout=dropout, batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.head = nn.Linear(d_model, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.input_proj(x)            # (B, L, d_model)
        h = self.encoder(h)               # (B, L, d_model)
        h = h[:, -1, :]                   # (B, d_model) — dernier pas
        return self.head(h).squeeze(-1)   # (B,)


@register_model("my_transformer_reg")
class MyTransformerModel(BaseModel):
    """Transformer encoder pour régression de log-returns."""

    output_type = "regression"

    def __init__(self) -> None:
        self._net: _TransformerNet | None = None
        self._device = torch.device("cpu")

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        config: Any,
        run_dir: Path,
        meta_train: Any = None,
        meta_val: Any = None,
        ohlcv: Any = None,
    ) -> dict:
        if X_train.ndim != 3:
            raise ValueError(f"X_train must be 3D, got {X_train.ndim}D")
        if X_train.dtype != np.float32:
            raise TypeError(f"X_train must be float32, got {X_train.dtype}")

        _, seq_len, n_features = X_train.shape
        cfg = config.models.my_transformer
        seed = config.reproducibility.global_seed

        torch.manual_seed(seed)
        self._net = _TransformerNet(
            n_features=n_features,
            seq_len=seq_len,
            d_model=cfg.d_model,
            n_heads=cfg.n_heads,
            n_layers=cfg.n_layers,
            dropout=cfg.dropout,
        ).to(self._device)

        optimizer = torch.optim.Adam(self._net.parameters(), lr=config.training.learning_rate)
        loss_fn = nn.MSELoss()

        x_t = torch.from_numpy(X_train).to(self._device)
        y_t = torch.from_numpy(y_train).to(self._device)
        x_v = torch.from_numpy(X_val).to(self._device)
        y_v = torch.from_numpy(y_val).to(self._device)

        best_val_loss = float("inf")
        patience_counter = 0
        best_epoch = 0

        for epoch in range(config.training.max_epochs):
            self._net.train()
            optimizer.zero_grad()
            pred = self._net(x_t)
            loss = loss_fn(pred, y_t)
            loss.backward()
            optimizer.step()

            self._net.eval()
            with torch.no_grad():
                val_pred = self._net(x_v)
                val_loss = loss_fn(val_pred, y_v).item()

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                best_epoch = epoch
            else:
                patience_counter += 1
                if patience_counter >= config.training.early_stopping_patience:
                    break

        return {"best_epoch": best_epoch, "best_val_loss": best_val_loss}

    def predict(
        self,
        X: np.ndarray,
        meta: Any = None,
        ohlcv: Any = None,
    ) -> np.ndarray:
        if self._net is None:
            raise RuntimeError("Model not fitted. Call fit() before predict().")
        if X.ndim != 3:
            raise ValueError(f"X must be 3D, got {X.ndim}D")
        if X.dtype != np.float32:
            raise TypeError(f"X must be float32, got {X.dtype}")

        self._net.eval()
        with torch.no_grad():
            x_t = torch.from_numpy(X).to(self._device)
            y_hat = self._net(x_t).cpu().numpy()
        return y_hat.astype(np.float32)

    def save(self, path: Path) -> None:
        if self._net is None:
            raise RuntimeError("Model not fitted. Call fit() before save().")
        resolved = path if path.suffix else path / "model.pt"
        resolved.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self._net.state_dict(), resolved)

    def load(self, path: Path) -> None:
        resolved = path if path.suffix else path / "model.pt"
        if not resolved.exists():
            raise FileNotFoundError(f"Model file not found: {resolved}")
        state = torch.load(resolved, map_location=self._device, weights_only=True)
        # Note : _net doit être reconstruit avec les mêmes paramètres avant load
        if self._net is None:
            raise RuntimeError("Network architecture must be initialized before load().")
        self._net.load_state_dict(state)
```

### 7.2 — Config Pydantic (`ai_trading/config.py`)

```python
class MyTransformerModelConfig(_StrictBase):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    d_model: int = Field(ge=1)
    n_heads: int = Field(ge=1)
    n_layers: int = Field(ge=1)
    dropout: float = Field(ge=0, lt=1)

    @model_validator(mode="after")
    def _validate(self) -> MyTransformerModelConfig:
        if self.d_model % self.n_heads != 0:
            raise ValueError(
                f"n_heads ({self.n_heads}) must divide d_model ({self.d_model})"
            )
        return self
```

Ajouter dans `ModelsConfig` :

```python
class ModelsConfig(_StrictBase):
    # ... existants ...
    my_transformer: MyTransformerModelConfig
```

### 7.3 — YAML (`configs/default.yaml`)

```yaml
models:
  # ... existants ...

  my_transformer:
    d_model: 64
    n_heads: 4
    n_layers: 2
    dropout: 0.1
```

### 7.4 — Déclaration stratégie et import

Dans `ai_trading/config.py` :
```python
VALID_STRATEGIES: dict[str, str] = {
    # ... existants ...
    "my_transformer_reg": "model",
}
```

Dans `ai_trading/models/__init__.py` :
```python
from . import (
    dummy,            # noqa: F401
    xgboost,          # noqa: F401
    my_transformer,   # noqa: F401
)
```

---

## 8. Checklist finale

Avant de soumettre une PR, vérifier :

- [ ] **Héritage** : la classe hérite de `BaseModel`
- [ ] **`output_type`** : déclaré comme variable de classe (`= "regression"` ou `= "signal"`)
- [ ] **4 méthodes abstraites** : `fit()`, `predict()`, `save()`, `load()` implémentées
- [ ] **`@register_model("nom")`** : décorateur appliqué avec un nom unique
- [ ] **Constructeur sans argument** : `__init__(self)` sans paramètre obligatoire
- [ ] **Validation stricte** : `raise ValueError` / `TypeError` pour entrées invalides — aucun fallback
- [ ] **Shapes** : `X` en `(N, L, F)` float32, `y_hat` retourné en `(N,)` float32
- [ ] **Config Pydantic** : classe `XxxModelConfig(_StrictBase)` avec `extra="forbid"`
- [ ] **YAML** : hyperparamètres dans `configs/default.yaml` sous `models.<nom>`
- [ ] **`VALID_STRATEGIES`** : nom du modèle ajouté dans le dictionnaire
- [ ] **Import** : module importé dans `ai_trading/models/__init__.py`
- [ ] **Anti-fuite** : `fit()` n'utilise `X_val` / `y_val` que pour early stopping
- [ ] **Config-driven** : aucun hyperparamètre hardcodé dans le code
- [ ] **Reproductibilité** : seed lue depuis `config.reproducibility.global_seed`
- [ ] **Tests TDD** : tests écrits avant l'implémentation, couvrant cas nominaux, erreurs et bords
- [ ] **Ruff** : `ruff check ai_trading/ tests/` clean
