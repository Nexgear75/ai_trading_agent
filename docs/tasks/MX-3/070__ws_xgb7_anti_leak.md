# Tâche — Tests anti-fuite (look-ahead) XGBoost

Statut : DONE
Ordre : 070
Workstream : WS-XGB-7
Milestone : MX-3
Gate lié : G-XGB-Integration

## Contexte

Le test E2E (tâche #069) valide le bon fonctionnement du pipeline avec XGBoost. Cette tâche complète la validation en vérifiant l'absence de fuite temporelle (look-ahead) spécifiquement pour le chemin XGBoost dans le pipeline.

La spec modèle §10 et la spec pipeline §8.2 définissent les règles anti-fuite. Les vérifications spécifiques à XGBoost incluent : causalité des prédictions, isolation fit/test, indépendance du scaler, indépendance de θ par rapport au test, et conservation de l'ordre C par l'adapter.

Références :
- Plan : `docs/plan/models/implementation_xgboost.md` (WS-XGB-7.2)
- Spécification modèle : `docs/specifications/models/Specification_Modele_XGBoost_v1.0.md` (§10)
- Spécification pipeline : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§8.2, G-Leak)
- Code : `ai_trading/pipeline/runner.py`, `ai_trading/models/xgboost.py`, `ai_trading/data/dataset.py`

Dépendances :
- Tâche 069 — Intégration E2E XGBoost (doit être DONE)

## Objectif

Ajouter des tests anti-fuite dans `tests/test_xgboost_integration.py` (classe dédiée `TestXGBoostAntiLeak`) qui démontrent l'absence de look-ahead dans le pipeline XGBoost.

## Règles attendues

- **Causalité stricte** : modifier les données futures ne doit pas impacter les prédictions passées.
- **Isolation train/val/test** : `eval_set` dans `fit()` ne contient que la validation, jamais le test.
- **θ indépendant du test** : modifier `y_hat_test` ne doit pas changer θ (calibré sur val uniquement).
- **Adapter sans réordonnement** : l'adapter tabulaire préserve l'ordre C des données.
- **Données synthétiques** : pas de réseau, fixtures CI.

## Évolutions proposées

- Ajouter une classe `TestXGBoostAntiLeak` dans `tests/test_xgboost_integration.py`.
- **Test 1 — Causalité prédictions** : exécuter un run complet, puis modifier les prix OHLCV pour `t > T` (par exemple, multiplier par 2 les close après le point T), ré-exécuter et vérifier que les prédictions pour `t ≤ T` restent identiques (bit-exact).
- **Test 2 — Isolation scaler** : vérifier que les indices utilisés pour `scaler.fit()` sont strictement dans l'intervalle train, disjoints de val et test.
- **Test 3 — θ indépendant du test** : exécuter la calibration θ sur un fold, modifier arbitrairement `y_hat_test`, et vérifier que θ est identique.
- **Test 4 — Adapter C-order** : vérifier que `flatten_seq_to_tab()` produit les mêmes valeurs qu'un `reshape()` en C-order explicite, sans réordonnement.

## Critères d'acceptation

- [x] Classe `TestXGBoostAntiLeak` ajoutée dans `tests/test_xgboost_integration.py`.
- [x] Test causalité : modification des données futures → prédictions passées identiques.
- [x] Test scaler : indices fit strictement dans train.
- [x] Test θ : θ identique quand seul `y_hat_test` change.
- [x] Test adapter C-order : `flatten_seq_to_tab` == `reshape` C-order.
- [x] Tous les tests de perturbation démontrent l'absence de fuite.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.

## Pré-condition de démarrage

- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/070-xgb-anti-leak` depuis `Max6000i1`.

## Checklist de fin de tâche

- [x] Branche `task/070-xgb-anti-leak` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-XGB-7] #070 RED: tests anti-fuite XGBoost` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-XGB-7] #070 GREEN: anti-fuite XGBoost validée`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-XGB-7] #070 — Anti-fuite XGBoost` (PR #84).
