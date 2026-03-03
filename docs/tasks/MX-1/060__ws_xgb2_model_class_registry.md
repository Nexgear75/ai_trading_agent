# Tâche — Classe XGBoostRegModel et enregistrement dans MODEL_REGISTRY

Statut : DONE
Ordre : 060
Workstream : WS-XGB-2
Milestone : MX-1
Gate lié : G-XGB-Ready

## Contexte

Le pipeline commun fournit l'interface abstraite `BaseModel` et le mécanisme de registre `MODEL_REGISTRY` via le décorateur `@register_model()` (WS-6.1). La stratégie `"xgboost_reg"` est déjà déclarée dans `VALID_STRATEGIES` de `ai_trading/config.py`. Il faut créer la classe concrète `XGBoostRegModel` héritant de `BaseModel`, l'enregistrer dans le registre, et l'importer automatiquement dans `ai_trading/models/__init__.py`.

Références :
- Plan : `docs/plan/models/implementation_xgboost.md` (WS-XGB-2.1)
- Spécification modèle : `docs/specifications/models/Specification_Modele_XGBoost_v1.0.md` (§2.1, §2.3, §8.1)
- Code : `ai_trading/models/base.py` (`BaseModel`, `MODEL_REGISTRY`, `@register_model`)
- Code : `ai_trading/models/__init__.py` (import à ajouter)
- Guide : `docs/plan/guide_ajout_modele.md`

Dépendances :
- Tâche 024 — WS-6 BaseModel + MODEL_REGISTRY (doit être DONE) ✅

## Objectif

Créer le fichier `ai_trading/models/xgboost.py` avec la classe `XGBoostRegModel` :
1. Héritage de `BaseModel`
2. Attributs de classe : `output_type = "regression"`, `execution_mode = "standard"` (hérité)
3. Décorateur `@register_model("xgboost_reg")`
4. Constructeur : `self._model = None`
5. Méthodes abstraites implémentées en stubs levant `NotImplementedError` pour `fit`, `predict`, `save`, `load` (en attendant WS-XGB-3/4/5)
6. Import automatique dans `ai_trading/models/__init__.py`

## Règles attendues

- **Interface conforme** : signature des méthodes identique à `BaseModel` (spec pipeline §10.1).
- **Strict code** : pas de fallback silencieux. Les stubs lèvent `NotImplementedError` explicitement.
- **Aucun import conditionnel** : `xgboost` n'est pas importé à ce stade (le module xgboost n'est utilisé que dans `fit`/`predict`/`save`/`load`, implémentés plus tard).
- **Pas de code mort** : seul le strict nécessaire pour l'enregistrement et les stubs.

## Évolutions proposées

- Créer `ai_trading/models/xgboost.py` avec :
  - Import de `BaseModel`, `register_model` depuis `ai_trading.models.base`
  - Classe `XGBoostRegModel(BaseModel)` décorée `@register_model("xgboost_reg")`
  - `output_type = "regression"`
  - `__init__()` initialisant `self._model = None`
  - Stubs `fit()`, `predict()`, `save()`, `load()` levant `NotImplementedError`
- Modifier `ai_trading/models/__init__.py` : ajouter `from . import xgboost  # noqa: F401`
- Créer `tests/test_xgboost_model.py` avec les tests d'enregistrement et de stubs

## Critères d'acceptation

- [x] `"xgboost_reg"` présent dans `MODEL_REGISTRY` après import du module
- [x] `MODEL_REGISTRY["xgboost_reg"]` retourne `XGBoostRegModel`
- [x] `XGBoostRegModel.output_type == "regression"`
- [x] `XGBoostRegModel.execution_mode == "standard"`
- [x] La classe hérite de `BaseModel`
- [x] `fit()` lève `NotImplementedError` (stub temporaire)
- [x] `predict()` lève `NotImplementedError` (stub temporaire)
- [x] `save()` lève `NotImplementedError` (stub temporaire)
- [x] `load()` lève `NotImplementedError` (stub temporaire)
- [x] Import dans `ai_trading/models/__init__.py` fonctionne sans erreur
- [x] Tests couvrent les scénarios nominaux + erreurs
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage

- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/060-xgb-model-class-registry` depuis `Max6000i1`.

## Checklist de fin de tâche

- [x] Branche `task/060-xgb-model-class-registry` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-XGB-2] #060 RED: tests classe XGBoostRegModel et registre` (fichiers de tests uniquement).
- [x] **Commit GREEN** : `[WS-XGB-2] #060 GREEN: classe XGBoostRegModel et enregistrement registre`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-XGB-2] #060 — Classe XGBoostRegModel et enregistrement registre`.
