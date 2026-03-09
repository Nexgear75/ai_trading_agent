# Tâche — Tests d'intégration et smoke test du dashboard

Statut : DONE
Ordre : 091
Workstream : WS-D-6
Milestone : MD-4
Gate lié : N/A

## Contexte
La suite de tests existante couvre les modules individuels du dashboard (data_loader, utils, charts, pages). Il manque les tests d'intégration de bout en bout définis en §12.2 de la spécification : smoke test, exclusion dummy, comparaison multi-runs, edge cases (répertoire vide), dégradation gracieuse (fichiers manquants), et reconstruction du signal Go/No-Go. Ces tests nécessitent des fixtures de runs synthétiques complètes.

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-6.4)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§12.2, §8.3, §4.2)
- Code : `tests/`, `scripts/dashboard/`

Dépendances :
- Tâche 089 — Sécurité et performance dashboard (doit être DONE)
- Tâche 087 — Dernière tâche MD-3 (DONE, toutes les pages sont implémentées)

## Objectif
Implémenter la suite complète de tests d'intégration du dashboard conforme à §12.2 : smoke test, exclusion dummy, comparaison, edge cases, dégradation, et reconstruction Go/No-Go. Créer les fixtures de test dédiées dans `tests/fixtures/dashboard/`.

## Règles attendues
- **Pas de dépendance réseau** : fixtures synthétiques uniquement, pas de run réel nécessaire.
- **Tests déterministes** : seeds fixées pour les données synthétiques.
- **Strict code** : chaque scénario de dégradation testé individuellement. Pas de test « fourre-tout ».
- **Isolation** : les tests d'intégration n'écrivent aucun fichier permanent. Utiliser `tmp_path` pytest.

## Évolutions proposées
- Créer des fixtures de runs synthétiques dans `tests/fixtures/dashboard/` ou via `conftest.py` :
  - Un run valide complet (`manifest.json`, `metrics.json`, `config_snapshot.yaml`, `equity_curve.csv`, `folds/fold_00/` avec `trades.csv`, `preds_test.csv`, `equity_curve.csv`, `metrics_fold.json`).
  - Un run dummy (stratégie `dummy`).
  - Un run partiel (sans `equity_curve.csv`, sans `trades.csv`).
  - Un run avec `preds_test.csv` absent.
- Implémenter les tests d'intégration dans `tests/test_dashboard_integration.py` :
  1. **Smoke test** : chargement d'un run valide, vérification que `discover_runs()` le trouve, que les métriques et manifest sont chargeables.
  2. **Exclusion dummy** : répertoire avec uniquement un run dummy → `discover_runs()` retourne une liste vide.
  3. **Comparaison multi-runs** : 2 runs valides, vérification du chargement conjoint.
  4. **Edge case répertoire vide** : `discover_runs()` sur un dossier vide → liste vide, pas de crash.
  5. **Dégradation equity_curve absente** : `load_equity_curve()` retourne `None`.
  6. **Dégradation trades absents** : `load_trades()` retourne `None`.
  7. **Dégradation preds absentes** : `load_predictions()` retourne `None`.
- Implémenter les tests de reconstruction Go/No-Go :
  8. **θ positif** : `y_hat > theta` → signal Go correct.
  9. **θ négatif** : reconstruction correcte.
  10. **θ = 0** : edge case, tous les positifs sont Go.
  11. **method == "none"** (modèle signal) : message informatif, pas de scatter.

## Critères d'acceptation
- [x] Fixtures de runs synthétiques créées (run valide, dummy, partiel, sans prédictions).
- [x] Smoke test : run valide découvert et chargé sans erreur.
- [x] Exclusion dummy : run dummy filtré correctement.
- [x] Comparaison : 2+ runs chargés conjointement.
- [x] Edge case : répertoire vide → liste vide, pas de crash.
- [x] Dégradation `equity_curve.csv` absent → `None` retourné.
- [x] Dégradation `trades.csv` absent → `None` retourné.
- [x] Dégradation `preds_test.csv` absent → `None` retourné.
- [x] Go/No-Go θ positif : signal correct.
- [x] Go/No-Go θ négatif : signal correct.
- [x] Go/No-Go θ = 0 : edge case couvert.
- [x] Go/No-Go `method == "none"` : détection correcte.
- [x] Pas de dépendance réseau dans les tests.
- [x] Tests déterministes (seeds fixées).
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/091-wsd6-integration-tests` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/091-wsd6-integration-tests` créée depuis `milestone/MD-4`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-D-6] #091 RED: tests d'intégration dashboard`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check scripts/dashboard/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-D-6] #091 GREEN: tests d'intégration dashboard`.
- [ ] **Pull Request ouverte** vers `Max6000i1` (via milestone PR).
