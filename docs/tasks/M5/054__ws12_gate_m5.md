# Tâche — Gate M5 (Production Readiness)

Statut : DONE
Ordre : 054
Workstream : WS-12
Milestone : M5
Gate lié : M5

## Contexte
Le gate M5 est le point de décision GO/NO-GO final du projet. Il vérifie la reproductibilité end-to-end, la conformité des artefacts JSON et le bon fonctionnement du pipeline de bout en bout (CI verte, `make run-all`).

Références :
- Plan : `docs/plan/implementation.md` (Gate M5)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§15, §16)
- Code : `tests/test_gate_m5.py`

Dépendances :
- Tâche 049 — Orchestrateur runner (doit être DONE)
- Tâche 050 — CLI entry point (doit être DONE)
- Tâche 051 — Dockerfile et CI (doit être DONE)
- Tâche 053 — Makefile (doit être DONE)
- Tâche 043 — Gate M4 (doit être DONE)

## Objectif
Implémenter les tests de validation du gate M5 dans `tests/test_gate_m5.py` vérifiant les 3 critères du plan :

### Critère 1 — Reproductibilité E2E
- `>= 95%` des champs numériques clés de `metrics.json` dans une tolérance relative `<= 1%` (même seed, cross-plateforme).
- Champs numériques clés : dans `aggregate` — `trading.mean.*` et `trading.std.*` (net_pnl, net_return, max_drawdown, sharpe, profit_factor, hit_rate, n_trades, avg_trade_return, median_trade_return, exposure_time_frac), `prediction.mean.*` et `prediction.std.*` (mae, rmse, directional_accuracy, spearman_ic — si applicable) ; par fold — `theta`, `n_trades`, `net_pnl`, `sharpe`, `max_drawdown`.
- Protocole : 2 runs complets avec DummyModel, même seed, même config → comparer les `metrics.json`.

### Critère 2 — Conformité artefacts
- `100%` de validation JSON Schema (manifest + metrics).
- Arborescence §15.1 complète.

### Critère 3 — Exécution
- `make run-all` fonctionne (ou pipeline complet via CLI).
- Pipeline CI en succès (`0` job rouge) — vérifié manuellement ou via le workflow.

## Règles attendues
- Les tests doivent fonctionner sur données synthétiques (fixture CI, pas d'accès réseau).
- La tolérance float32 `atol=1e-7` est utilisée pour la comparaison same-platform ; la tolérance relative `<= 1%` pour cross-platform.
- Le rapport `gate_report_M5.json` est produit (mêmes conventions que les autres gates).

## Évolutions proposées
- Test `test_reproducibility_e2e` : 2 runs → comparaison metrics.json.
- Test `test_artefacts_conformity` : validation JSON Schema + arborescence.
- Test `test_pipeline_execution` : pipeline complet sans crash.
- Fonction auxiliaire pour la comparaison de `metrics.json`.

## Critères d'acceptation
- [x] Le fichier `tests/test_gate_m5.py` existe et est exécutable.
- [x] Test de reproductibilité : 2 runs avec même seed → `>= 95%` des champs numériques clés dans tolérance `<= 1%`.
- [x] Test de conformité : `manifest.json` et `metrics.json` valident contre les schémas JSON.
- [x] Test de conformité : l'arborescence §15.1 est complète (tous les fichiers attendus présents).
- [x] Test d'exécution : pipeline complet (DummyModel) sans crash.
- [x] Test d'exécution : pipeline complet (no_trade baseline) sans crash, bypass θ vérifié.
- [x] Les tests fonctionnent sur données synthétiques uniquement.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/054-gate-m5` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/054-gate-m5` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-12] #054 RED: tests gate M5`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-12] #054 GREEN: gate M5`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-12] #054 — Gate M5 (Production Readiness)`.
