# Tâche — Metrics builder

Statut : TODO
Ordre : 046
Workstream : WS-11
Milestone : M5
Gate lié : M5

## Contexte
Le fichier `metrics.json` contient les métriques par fold et les agrégats inter-fold. Il doit permettre de reconstruire les tableaux de comparaison sans relancer le backtest. En outre, un fichier `metrics_fold.json` est produit dans chaque `folds/fold_XX/` avec les métriques du fold individuel plus les champs `n_samples_train`, `n_samples_val`, `n_samples_test`.

Références :
- Plan : `docs/plan/implementation.md` (WS-11.3)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§15.3, §8.4, Annexe B, Annexe C.2)
- Schéma : `docs/specifications/metrics.schema.json`
- Exemple : `docs/specifications/example_metrics.json`
- Code : `ai_trading/artifacts/metrics_builder.py`

Dépendances :
- Tâche 042 — Agrégation inter-fold (doit être DONE)
- Tâche 031 — Theta optimization (doit être DONE, pour theta par fold)
- Tâche 044 — Arborescence run_dir (doit être DONE)

## Objectif
Implémenter le module `ai_trading/artifacts/metrics_builder.py` qui :
1. Construit le `metrics.json` global avec : `run_id`, `strategy`, `folds` (par fold : `fold_id`, `period_test`, `threshold`, `prediction`, `n_samples_train`, `n_samples_val`, `n_samples_test`, `trading`), `aggregate` (mean/std).
2. Produit un fichier `metrics_fold.json` dans chaque `folds/fold_XX/` contenant les métriques du fold individuel (même structure que l'objet fold dans `metrics.json`).

## Règles attendues
- Strict code : toutes les données d'entrée (métriques par fold, agrégats, threshold info) sont requises.
- Float64 pour toutes les métriques (convention du projet).
- Chaque `metrics_fold.json` doit être cohérent avec l'entrée correspondante dans le `metrics.json` global.
- Le JSON produit doit être valide contre `metrics.schema.json` (Draft 2020-12).

## Évolutions proposées
- Fonction `build_metrics(run_id, strategy_info, folds_data, aggregate_data) -> dict`.
- Fonction `write_metrics(metrics_data, run_dir)` pour écrire le `metrics.json` global.
- Fonction `write_fold_metrics(fold_data, fold_dir)` pour écrire `metrics_fold.json` par fold.

## Critères d'acceptation
- [ ] Le module `ai_trading/artifacts/metrics_builder.py` existe et est importable.
- [ ] Le JSON global `metrics.json` est valide contre `metrics.schema.json` (test via `jsonschema.validate()`).
- [ ] Chaque `folds/fold_XX/metrics_fold.json` est généré et cohérent avec l'entrée correspondante dans `metrics.json`.
- [ ] Les champs `n_samples_train`, `n_samples_val`, `n_samples_test` sont présents par fold.
- [ ] Les métriques sont en float64.
- [ ] Test d'intégration : construction complète avec données synthétiques → JSON valide.
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords (0 trades, 1 fold, multi-folds).
- [ ] Suite de tests verte après implémentation.
- [ ] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/046-metrics-builder` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/046-metrics-builder` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-11] #046 RED: tests metrics builder`.
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-11] #046 GREEN: metrics builder`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-11] #046 — Metrics builder`.
