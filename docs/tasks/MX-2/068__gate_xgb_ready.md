# Tâche — Gate G-XGB-Ready : modèle unitairement fonctionnel

Statut : TODO
Ordre : 068
Workstream : WS-XGB-5
Milestone : MX-2
Gate lié : G-XGB-Ready

## Contexte

Les work streams WS-XGB-3 (fit), WS-XGB-4 (predict) et WS-XGB-5 (save/load) sont complétés (tâches #062–#067). Le gate G-XGB-Ready est le point de décision GO/NO-GO avant de passer à l'intégration E2E (MX-3, WS-XGB-7). Il valide que le modèle XGBoost fonctionne en isolation : fit, predict, save, load, déterminisme, et couverture de tests ≥ 90%.

Références :
- Plan : `docs/plan/models/implementation_xgboost.md` (G-XGB-Ready)
- Spécification modèle : `docs/specifications/models/Specification_Modele_XGBoost_v1.0.md` (§5, §6, §7, §8.1, §9)
- Code : `ai_trading/models/xgboost.py`
- Tests : `tests/test_xgboost_model.py`, `tests/test_adapter_xgboost.py`

Dépendances :
- Tâche 065 — WS-XGB-4.1 predict (doit être DONE)
- Tâche 067 — WS-XGB-5.2 load JSON (doit être DONE)

## Objectif

Valider les 7 critères du gate G-XGB-Ready :
1. `fit()` converge avec early stopping (`best_iteration < n_estimators`) sur données synthétiques
2. `predict()` retourne shape $(N,)$ dtype `float32`
3. `save()` + `load()` → prédictions identiques (bit-exact)
4. Déterminisme : deux `fit()` + `predict()` même seed → sorties identiques
5. Enregistrement : `"xgboost_reg"` dans `MODEL_REGISTRY`, `output_type == "regression"`
6. Validation stricte : shape invalide → `ValueError`, dtype invalide → `TypeError`, `predict()` sans `fit()` → `RuntimeError`
7. Couverture ≥ 90% sur `ai_trading.models.xgboost` et `ai_trading.data.dataset`

## Règles attendues

- **Gate bloquant** : si l'un des 7 critères échoue, le verdict est NO-GO.
- **Automatisation** : `pytest tests/test_adapter_xgboost.py tests/test_xgboost_model.py -v --cov=ai_trading.models.xgboost --cov=ai_trading.data.dataset --cov-fail-under=90`
- **Reproductibilité** : les tests de déterminisme doivent être reproductibles (seeds fixées).

## Évolutions proposées

- Ajouter un test de déterminisme dans `tests/test_xgboost_model.py` : deux `fit()` + `predict()` avec même seed → sorties identiques
- Ajouter un test de round-trip complet : `fit()` → `predict()` → `save()` → nouvelle instance → `load()` → `predict()` → résultats identiques
- Vérifier la couverture avec `--cov-fail-under=90`
- Documenter le verdict GO/NO-GO dans le fichier de tâche

## Critères d'acceptation

- [ ] `fit()` converge avec early stopping (`best_iteration < n_estimators`) sur données synthétiques
- [ ] `predict()` retourne shape $(N,)$ dtype `float32`
- [ ] `save()` + `load()` → prédictions identiques (bit-exact)
- [ ] Déterminisme : deux `fit()` + `predict()` même seed → sorties identiques
- [ ] `"xgboost_reg"` dans `MODEL_REGISTRY`, `output_type == "regression"`
- [ ] Validation stricte : `ValueError` (shape), `TypeError` (dtype), `RuntimeError` (pas de fit)
- [ ] Couverture ≥ 90% (`pytest --cov=ai_trading.models.xgboost --cov=ai_trading.data.dataset --cov-fail-under=90`)
- [ ] `ruff check ai_trading/ tests/` clean
- [ ] Verdict : GO ou NO-GO documenté

## Pré-condition de démarrage

- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/068-gate-xgb-ready` depuis `Max6000i1`.

## Checklist de fin de tâche

- [ ] Branche `task/068-gate-xgb-ready` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-XGB-5] #068 RED: tests gate G-XGB-Ready` (fichiers de tests uniquement).
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-XGB-5] #068 GREEN: gate G-XGB-Ready validé`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-XGB-5] #068 — Gate G-XGB-Ready`.
