# Tâche — Validation du gate G-Backtest

Statut : DONE
Ordre : 036
Workstream : WS-8
Milestone : M4
Gate lié : G-Backtest

## Contexte
Le gate intra-milestone G-Backtest est bloquant pour WS-9 (baselines) et WS-10 (métriques). Il vérifie que le moteur de backtest complet (exécution, coûts, equity, journal) est déterministe, correct et conforme avant de construire les couches supérieures.

Références :
- Plan : `docs/plan/implementation.md` (Gate G-Backtest, après WS-8.4)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§12)
- Code : `ai_trading/backtest/`

Dépendances :
- Tâche 035 — Journal de trades (doit être DONE)

## Objectif
Écrire les tests de validation des 6 critères du gate G-Backtest et s'assurer qu'ils passent tous.

## Règles attendues
- **Déterminisme** : 2 runs identiques (même seed, DummyModel, données synthétiques) → `trades.csv` identiques (SHA-256), equity curves identiques (`atol=1e-10`).
- **Cohérence equity-trades** : `E_final == E_0 * Π(1 + w * r_net_i)` à `atol=1e-8`.
- **Mode one_at_a_time** : aucun trade chevauché (test sur séquence de signaux Go consécutifs).
- **Modèle de coûts** : résultat identique au calcul à la main sur `>= 3` cas.
- **trades.csv parseable** : colonnes conformes à §12.6.
- **Anti-fuite backtest** : signaux à t indépendants des prix `t' > t` (test de perturbation).
- **Données synthétiques** : pas de réseau, tests déterministes avec seeds fixées.

## Évolutions proposées
- Ajouter un fichier de tests dédié `tests/test_gate_backtest.py` couvrant les 6 critères.
- Chaque critère est un test distinct et identifiable.
- Les tests utilisent le DummyModel et des données OHLCV synthétiques.

## Critères d'acceptation
- [x] Critère 1 — Déterminisme : 2 runs → `trades.csv` byte-identiques (SHA-256), equity `atol=1e-10`.
- [x] Critère 2 — Cohérence equity-trades : `E_final == E_0 * Π(1 + w * r_net_i)` à `atol=1e-8`.
- [x] Critère 3 — One-at-a-time : aucun chevauchement sur signaux denses.
- [x] Critère 4 — Coûts : résultat identique au calcul à la main sur >= 3 cas.
- [x] Critère 5 — trades.csv parseable avec colonnes conformes.
- [x] Critère 6 — Anti-fuite : perturbation des prix futurs ne change pas les signaux passés.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/036-gate-backtest` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/036-gate-backtest` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-8] #036 RED: <résumé>` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-8] #036 GREEN: <résumé>`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-8] #036 — Validation du gate G-Backtest`.
