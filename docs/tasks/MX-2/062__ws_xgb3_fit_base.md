# Tâche — Instanciation du régresseur XGBoost et fit de base

Statut : TODO
Ordre : 062
Workstream : WS-XGB-3
Milestone : MX-2
Gate lié : G-XGB-Ready

## Contexte

La classe `XGBoostRegModel` est créée (tâche #060) avec des stubs `NotImplementedError`. La config Pydantic `XGBoostModelConfig` est validée (tâche #061). L'adapter tabulaire `flatten_seq_to_tab()` est fonctionnel (tâche #059). Cette tâche implémente le cœur de la méthode `fit()` : validation stricte des entrées, aplatissement via l'adapter, instanciation du `XGBRegressor` avec les hyperparamètres de la config, et appel à `fit()` avec `eval_set`.

Références :
- Plan : `docs/plan/models/implementation_xgboost.md` (WS-XGB-3.1)
- Spécification modèle : `docs/specifications/models/Specification_Modele_XGBoost_v1.0.md` (§5.1, §4.1, §4.2, §4.3)
- Code : `ai_trading/models/xgboost.py` (`XGBoostRegModel.fit`)
- Code : `ai_trading/data/dataset.py` (`flatten_seq_to_tab`)
- Code : `ai_trading/config.py` (`XGBoostModelConfig`)

Dépendances :
- Tâche 059 — WS-XGB-1 adapter validation (doit être DONE) ✅
- Tâche 060 — WS-XGB-2 classe modèle et registre (doit être DONE) ✅
- Tâche 061 — WS-XGB-6 config Pydantic validation (doit être DONE) ✅

## Objectif

Implémenter la méthode `fit()` de `XGBoostRegModel` avec :
1. Validation stricte des entrées (shape 3D, shapes compatibles, dtype float32)
2. Aplatissement `X_train` et `X_val` via `flatten_seq_to_tab()`
3. Instanciation de `xgboost.XGBRegressor` avec les 7 hyperparamètres de `config.models.xgboost`
4. Paramètres imposés (non configurables) : `objective="reg:squarederror"`, `tree_method="hist"`, `booster="gbtree"`, `verbosity=0`
5. `random_state = config.reproducibility.global_seed`
6. Appel à `self._model.fit(X_tab_train, y_train, eval_set=[(X_tab_val, y_val)], verbose=False)`

## Règles attendues

- **Strict code** : validation explicite des entrées avec `raise ValueError` / `raise TypeError`. Pas de fallback silencieux.
- **Config-driven** : les 7 hyperparamètres sont lus depuis `config.models.xgboost`. Aucun n'est hardcodé.
- **Anti-fuite** : `eval_set` ne contient que des données de validation, jamais de test.
- **Float32** : les entrées `X_train`, `X_val` doivent être en float32. `y_train`, `y_val` en float32.

## Évolutions proposées

- Remplacer le stub `NotImplementedError` de `fit()` dans `ai_trading/models/xgboost.py` par l'implémentation réelle
- Ajouter `import xgboost as xgb` et `from ai_trading.data.dataset import flatten_seq_to_tab`
- Validation stricte avant l'aplatissement :
  - `X_train.ndim != 3` → `ValueError`
  - `X_val.ndim != 3` → `ValueError`
  - `X_train.shape[0] != y_train.shape[0]` → `ValueError`
  - `X_val.shape[0] != y_val.shape[0]` → `ValueError`
  - `X_train.dtype != np.float32` → `TypeError`
  - `X_val.dtype != np.float32` → `TypeError`
- Instanciation de `XGBRegressor` avec tous les paramètres spec §5.1
- Appel à `fit()` avec `eval_set`
- Retourner `{}` provisoirement (les artefacts seront ajoutés en tâche #064)
- Créer/enrichir `tests/test_xgboost_model.py` avec les tests de `fit()`

## Critères d'acceptation

- [ ] `fit()` s'exécute sans erreur sur données synthétiques (N=100, L=10, F=5)
- [ ] `self._model` est un `XGBRegressor` entraîné après `fit()`
- [ ] `ValueError` si `X_train.ndim != 3`
- [ ] `ValueError` si `X_val.ndim != 3`
- [ ] `ValueError` si `X_train.shape[0] != y_train.shape[0]`
- [ ] `ValueError` si `X_val.shape[0] != y_val.shape[0]`
- [ ] `TypeError` si `X_train.dtype != float32`
- [ ] `TypeError` si `X_val.dtype != float32`
- [ ] Les 7 hyperparamètres sont lus depuis `config.models.xgboost`, aucun hardcodé
- [ ] `random_state` est fixé à `config.reproducibility.global_seed`
- [ ] Paramètres imposés : `objective="reg:squarederror"`, `tree_method="hist"`, `booster="gbtree"`, `verbosity=0`
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords
- [ ] Suite de tests verte après implémentation
- [ ] `ruff check` passe sans erreur

## Pré-condition de démarrage

- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/062-xgb-fit-base` depuis `Max6000i1`.

## Checklist de fin de tâche

- [ ] Branche `task/062-xgb-fit-base` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-XGB-3] #062 RED: tests fit base XGBoostRegModel` (fichiers de tests uniquement).
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-XGB-3] #062 GREEN: implémentation fit base XGBoostRegModel`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-XGB-3] #062 — Instanciation régresseur et fit de base`.
