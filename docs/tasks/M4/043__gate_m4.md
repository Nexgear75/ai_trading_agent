# Tâche — Validation du gate M4

Statut : DONE
Ordre : 043
Workstream : WS-10
Milestone : M4
Gate lié : M4

## Contexte
Le gate M4 valide que l'ensemble du milestone « Evaluation Engine » est complet et conforme avant de passer à M5 (Production Readiness). Il vérifie le déterminisme, la robustesse du pipeline, la cohérence des métriques, la couverture des tests et la complétude des registres.

Références :
- Plan : `docs/plan/implementation.md` (Gate M4 — Evaluation trading robuste)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§12, §13, §14)
- Code : `ai_trading/backtest/`, `ai_trading/baselines/`, `ai_trading/metrics/`

Dépendances :
- Tâche 042 — Agrégation inter-fold (doit être DONE)
- Tâches 037, 038, 039 — Les 3 baselines (doivent être DONE)

## Objectif
Écrire les tests de validation des 5 critères M4-framework et s'assurer qu'ils passent tous. Produire le rapport de gate.

## Règles attendues
- **(a) Déterminisme backtest** : delta Sharpe (non-annualisé) absolu `<= 0.02` et delta MDD absolu `<= 0.5` point de pourcentage entre 2 runs même seed (DummyModel + données synthétiques).
- **(b) Pipeline complet sans crash** : DummyModel + 3 baselines (no_trade, buy_hold, sma_rule) exécutent le pipeline complet (predict → backtest → métriques) sans erreur.
- **(c) Métriques cohérentes** :
  - `no_trade` → `net_pnl = 0`, `n_trades = 0`, `MDD = 0`.
  - `buy_hold` → `n_trades = 1`.
  - `sma_rule` → `n_trades >= 0`.
- **(d) Couverture tests** : `>= 95%` couverture sur WS-8.4/WS-9/WS-10 (mesurée via `pytest --cov`).
- **(e) Complétude registres MVP** : `set(MODEL_REGISTRY) == {"dummy", "no_trade", "buy_hold", "sma_rule"}`.
- **Données synthétiques** : pas de réseau, tests déterministes avec seeds fixées.

## Évolutions proposées
- Créer `tests/test_gate_m4.py` avec un test par critère (a-e).
- Le critère (d) peut être vérifié via un test qui exécute `pytest --cov` programmatiquement ou via un commentaire de documentation.
- Le critère (e) vérifie l'égalité exacte de l'ensemble des clés du registre.

## Critères d'acceptation
- [x] Critère (a) — Déterminisme : delta Sharpe `<= 0.02`, delta MDD `<= 0.5 pp` entre 2 runs identiques.
- [x] Critère (b) — Pipeline sans crash pour DummyModel + 3 baselines.
- [x] Critère (c) — Cohérence métriques : no_trade (pnl=0, trades=0, mdd=0), buy_hold (trades=1), sma_rule (trades>=0).
- [x] Critère (d) — Couverture `>= 95%` sur WS-8.4/WS-9/WS-10.
- [x] Critère (e) — `set(MODEL_REGISTRY.keys()) == {"dummy", "no_trade", "buy_hold", "sma_rule"}`.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/043-gate-m4` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/043-gate-m4` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-10] #043 RED: <résumé>` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-10] #043 GREEN: <résumé>`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-10] #043 — Validation du gate M4`.
