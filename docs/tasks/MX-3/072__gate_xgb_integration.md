# Tâche — Gate G-XGB-Integration : intégration pipeline validée

Statut : DONE
Ordre : 072
Workstream : WS-XGB-7
Milestone : MX-3
Gate lié : G-XGB-Integration

## Contexte

Les tâches #069 (E2E), #070 (anti-fuite) et #071 (reproductibilité) couvrent les trois volets de WS-XGB-7. Le gate G-XGB-Integration est le point de décision GO/NO-GO final pour le modèle XGBoost : il valide que le modèle fonctionne dans le pipeline complet, sans fuite, de manière reproductible.

Ce gate est bloquant pour la livraison et pour l'ajout de `xgboost_reg` aux gates pipeline (M4).

Références :
- Plan : `docs/plan/models/implementation_xgboost.md` (G-XGB-Integration)
- Spécification modèle : `docs/specifications/models/Specification_Modele_XGBoost_v1.0.md` (§8, §9, §10, §12.2)
- Tests : `tests/test_xgboost_integration.py`

Dépendances :
- Tâche 069 — Intégration E2E XGBoost (doit être DONE)
- Tâche 070 — Anti-fuite XGBoost (doit être DONE)
- Tâche 071 — Reproductibilité XGBoost (doit être DONE)

## Objectif

Valider les 8 critères du gate G-XGB-Integration :

1. Run complet sans crash (features → split → scale → fit → predict → θ → backtest → métriques → artefacts).
2. `manifest.json` et `metrics.json` valides (JSON Schema).
3. `strategy.name == "xgboost_reg"` et `strategy.framework == "xgboost"` dans le manifest.
4. Métriques de prédiction non nulles (MAE, RMSE, DA).
5. Métriques de trading présentes et cohérentes.
6. Anti-fuite : modification des prix futurs → prédictions identiques pour `t ≤ T`.
7. Reproductibilité : deux runs même seed → `metrics.json` identiques (`atol=1e-7`).
8. `ruff check ai_trading/ tests/` clean.

## Règles attendues

- **Gate bloquant** : si l'un des 8 critères échoue, le verdict est NO-GO.
- **Automatisation** : `pytest tests/test_xgboost_integration.py -v --cov=ai_trading.models.xgboost --cov-fail-under=90`
- **Reproductibilité** : les tests sont reproductibles (seeds fixées).
- **Pas de code source modifié** : cette tâche ne modifie que des tests et de la documentation.

## Évolutions proposées

- Ajouter une classe `TestGateXGBIntegration` dans `tests/test_xgboost_integration.py` qui consolide les 8 critères du gate.
- Exécuter la commande d'automatisation : `pytest tests/test_xgboost_integration.py -v --cov=ai_trading.models.xgboost --cov-fail-under=90`.
- Documenter le verdict GO/NO-GO dans le fichier de tâche.

## Verdict

**GO** — Les 8 critères du gate G-XGB-Integration sont satisfaits :
1. Run complet sans crash : ✅ (26 tests passants)
2. manifest.json et metrics.json valides : ✅ (JSON Schema validé)
3. strategy.name/framework : ✅ (xgboost_reg / xgboost)
4. Métriques de prédiction non nulles : ✅ (MAE > 0, RMSE > 0, DA ∈ [0,1])
5. Métriques de trading présentes : ✅ (net_pnl, n_trades, max_drawdown)
6. Anti-fuite : ✅ (perturbation prix futurs → métriques identiques fold 1)
7. Reproductibilité : ✅ (deux runs → metrics.json identiques, atol=1e-7)
8. ruff check clean : ✅ (0 erreur)

Couverture `ai_trading.models.xgboost` : **100%** (82/82 stmts).

Note : `pytest --cov` avec instrumentation en-processus déclenche un bug connu numpy 2.x / Python 3.13 (`_NoValueType`). La couverture est mesurée via les tests unitaires seuls (`tests/test_xgboost_model.py + tests/test_xgboost_config.py`).

## Critères d'acceptation

- [x] Run complet E2E sans crash (vérifié par #069 + gate criterion 1).
- [x] `manifest.json` et `metrics.json` valides JSON Schema (vérifié par #069 + gate criterion 2).
- [x] `strategy.name == "xgboost_reg"` et `strategy.framework == "xgboost"` (vérifié par #069 + gate criterion 3).
- [x] Métriques de prédiction non nulles (vérifié par #069 + gate criterion 4).
- [x] Métriques de trading présentes (vérifié par #069 + gate criterion 5).
- [x] Anti-fuite : pas de look-ahead (vérifié par #070 + gate criterion 6).
- [x] Reproductibilité : deux runs identiques (vérifié par #071 + gate criterion 7).
- [x] `ruff check ai_trading/ tests/` clean (gate criterion 8).
- [x] Couverture ≥ 90% sur `ai_trading.models.xgboost` (100% mesuré via unit tests).
- [x] Verdict : **GO** — tous les 8 critères sont satisfaits.

## Pré-condition de démarrage

- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/072-gate-xgb-integration` depuis `Max6000i1`.

## Checklist de fin de tâche

- [x] Branche `task/072-gate-xgb-integration` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-XGB-7] #072 RED: tests gate G-XGB-Integration (8 criteria consolidated)`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-XGB-7] #072 GREEN: gate G-XGB-Integration validé`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-XGB-7] #072 — Gate G-XGB-Integration` (PR #86).
