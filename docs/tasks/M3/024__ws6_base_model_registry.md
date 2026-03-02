# Tâche — Interface abstraite BaseModel et registre MODEL_REGISTRY

Statut : DONE
Ordre : 024
Workstream : WS-6
Milestone : M3
Gate lié : G-Doc

## Contexte
Le pipeline nécessite un contrat d'interface plug-in que tout modèle (XGBoost, CNN, GRU, LSTM, PatchTST, RL-PPO) et toute baseline (no-trade, buy & hold, SMA) doit respecter. Ce contrat découple le pipeline de la logique interne des modèles : le trainer, le calibrateur, le backtest et l'orchestrateur interagissent uniquement avec `BaseModel`. WS-6.1 est la fondation du pattern plug-in pour tout M3 et M4.

Références :
- Plan : `docs/plan/implementation.md` (WS-6.1)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§10.1, §10.2, §10.4)
- Code : `ai_trading/models/base.py` (à créer)

Dépendances :
- Tâche 002 — WS-1 config loader (doit être DONE)

## Objectif
Implémenter la classe abstraite `BaseModel(ABC)` dans `ai_trading/models/base.py` avec les méthodes abstraites, les attributs de classe, et le registre `MODEL_REGISTRY` avec décorateur `@register_model`.

## Règles attendues
- **Strict code** : un modèle qui n'implémente pas les méthodes abstraites lève `NotImplementedError`. Un nom de stratégie inconnu dans le registre lève `ValueError`.
- **Config-driven** : `config.strategy.name` résout dynamiquement vers la classe modèle via le registre.
- **Pattern plug-in** : aucune logique spécifique à un modèle dans le pipeline — tout passe par `BaseModel`.

## Évolutions proposées

### 1. Classe abstraite `BaseModel(ABC)` dans `ai_trading/models/base.py`
- Méthodes abstraites :
  - `fit(X_train, y_train, X_val, y_val, config, run_dir, meta_train=None, meta_val=None, ohlcv=None) → artifacts`
  - `predict(X, meta=None, ohlcv=None) → y_hat`
  - `save(path)`
  - `load(path)`
- Attribut de classe obligatoire `output_type: Literal["regression", "signal"]`
  - `"regression"` pour modèles supervisés (prédiction float → seuil θ)
  - `"signal"` pour RL et baselines (signaux binaires 0/1 → bypass θ)
- Attribut de classe `execution_mode: Literal["standard", "single_trade"]` avec défaut `"standard"`
  - Seul `BuyHoldBaseline` déclarera `"single_trade"` (en M4)
- Conventions d'entrée/sortie documentées : `X_seq (N, L, F)`, `y (N,)`, `y_hat (N,)` en float
- Docstring exhaustive du contrat (shapes, types, contraintes anti-fuite)

### 2. Registre `MODEL_REGISTRY` et décorateur `@register_model`
- Dictionnaire `MODEL_REGISTRY: dict[str, type[BaseModel]]`
- Décorateur `@register_model("name")` pour enregistrer une sous-classe
- Fonction de résolution `get_model_class(name: str) → type[BaseModel]` levant `ValueError` si nom inconnu
- Pattern symétrique au `FEATURE_REGISTRY` (WS-3.6)

### 3. Module `ai_trading/models/__init__.py`
- Auto-import de `dummy.py` (dès cette tâche WS-6.2, ou après)
- Note : les imports des baselines (`no_trade.py`, `buy_hold.py`, `sma_rule.py`) ne sont ajoutés qu'à M4

## Critères d'acceptation
- [x] Classe abstraite `BaseModel(ABC)` importable depuis `ai_trading.models.base`
- [x] Un modèle qui n'implémente pas les méthodes abstraites lève `TypeError` à l'instanciation
- [x] `output_type` est un attribut de classe obligatoire, vérifié à l'instanciation ou par convention ABC
- [x] `execution_mode` a la valeur par défaut `"standard"` dans `BaseModel`
- [x] `MODEL_REGISTRY` résout un nom enregistré vers la classe modèle correspondante
- [x] Un nom inconnu dans le registre lève `ValueError`
- [x] `@register_model("name")` enregistre correctement une sous-classe
- [x] Signature `fit()` accepte `meta_train`, `meta_val` et `ohlcv` optionnels
- [x] Docstring du contrat exhaustive (shapes, types, anti-fuite)
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/024-base-model-registry` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/024-base-model-registry` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-6] #024 RED: tests BaseModel ABC et MODEL_REGISTRY` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-6] #024 GREEN: BaseModel ABC et MODEL_REGISTRY`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-6] #024 — Interface abstraite BaseModel et registre MODEL_REGISTRY`.
