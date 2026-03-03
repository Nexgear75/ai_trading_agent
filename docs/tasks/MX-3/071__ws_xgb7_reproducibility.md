# Tâche — Tests de reproductibilité XGBoost

Statut : DONE
Ordre : 071
Workstream : WS-XGB-7
Milestone : MX-3
Gate lié : G-XGB-Integration

## Contexte

Le gate G-XGB-Ready (tâche #068) a validé la reproductibilité unitaire (deux `fit()` + `predict()` même seed → identiques). Cette tâche valide la reproductibilité au niveau **pipeline complet** : deux runs E2E avec la même seed et les mêmes données doivent produire des `metrics.json` et `trades.csv` identiques.

XGBoost avec `tree_method="hist"` et `random_state` fixé est déterministe sur une même plateforme CPU. La reproductibilité cross-plateforme n'est pas garantie.

Références :
- Plan : `docs/plan/models/implementation_xgboost.md` (WS-XGB-7.3)
- Spécification modèle : `docs/specifications/models/Specification_Modele_XGBoost_v1.0.md` (§9)
- Spécification pipeline : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§16)
- Code : `ai_trading/pipeline/runner.py`, `ai_trading/utils/seed.py`

Dépendances :
- Tâche 069 — Intégration E2E XGBoost (doit être DONE)

## Objectif

Ajouter des tests de reproductibilité dans `tests/test_xgboost_integration.py` (classe dédiée `TestXGBoostReproducibility`) qui vérifient que le pipeline XGBoost produit des résultats identiques sur deux runs indépendants avec la même seed.

## Règles attendues

- **Déterminisme local** : deux runs même seed, mêmes données → `metrics.json` identiques à `atol=1e-7`.
- **SHA-256** : les fichiers `trades.csv` des deux runs sont identiques byte-à-byte.
- **Sérialisation** : `save()` + `load()` + `predict()` → résultat identique (déjà vérifié unitairement, ici au niveau pipeline).
- **Seed manager** : `reproducibility.global_seed` est propagée à XGBoost via `random_state`.
- **Données synthétiques** : pas de réseau, fixtures CI.

## Évolutions proposées

- Ajouter une classe `TestXGBoostReproducibility` dans `tests/test_xgboost_integration.py`.
- **Test 1 — Déterminisme métriques** : exécuter deux runs complets avec la même seed et les mêmes données synthétiques → comparer les `metrics.json` field-by-field : métriques identiques à `atol=1e-7` pour les float.
- **Test 2 — Déterminisme trades** : les fichiers `trades.csv` des deux runs sont identiques bit-exact (comparaison SHA-256 des contenus).
- **Test 3 — Sérialisation modèle** : vérifier que `save()` → `load()` → `predict()` sur des tenseurs synthétiques reproduit les prédictions originales (round-trip modèle). Le déterminisme pipeline (même seed → mêmes résultats) est couvert par les tests 1 et 2. L'artefact sauvegardé est `model_artifacts/model`.

## Critères d'acceptation

- [x] Classe `TestXGBoostReproducibility` ajoutée dans `tests/test_xgboost_integration.py`.
- [x] Deux runs même seed → `metrics.json` identiques (`atol=1e-7`).
- [x] Deux runs même seed → `trades.csv` identiques (SHA-256).
- [x] Sérialisation round-trip au niveau modèle : `save()` → `load()` → `predict()` sur tenseurs synthétiques = prédictions originales. Le déterminisme pipeline est validé par les tests métriques et trades.
- [x] Seed fixée, tests déterministes.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.

## Pré-condition de démarrage

- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/071-xgb-reproducibility` depuis `Max6000i1`.

## Checklist de fin de tâche

- [x] Branche `task/071-xgb-reproducibility` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-XGB-7] #071 RED: tests reproductibilité XGBoost` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-XGB-7] #071 GREEN: reproductibilité XGBoost validée`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-XGB-7] #071 — Reproductibilité XGBoost` (PR #85).
