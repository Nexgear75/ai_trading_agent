# Tâche — Agrégation inter-fold et stitched equity

Statut : DONE
Ordre : 042
Workstream : WS-10
Milestone : M4
Gate lié : M4

## Contexte
Après le calcul des métriques par fold (WS-10.1, WS-10.2), l'agrégation inter-fold produit les statistiques globales (mean, std) et la courbe d'équité stitchée. Ce module est le dernier livrable technique avant la validation du gate M4.

Références :
- Plan : `docs/plan/implementation.md` (WS-10.3)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§14.3, §14.4, §13.4)
- Code : `ai_trading/metrics/aggregation.py` (à créer)

Dépendances :
- Tâche 040 — Métriques de prédiction (doit être DONE)
- Tâche 041 — Métriques de trading (doit être DONE)

## Objectif
Implémenter le module `metrics/aggregation.py` calculant les métriques agrégées inter-fold (mean/std), la courbe d'équité stitchée avec continuation, les avertissements §14.4 et le champ `comparison_type`.

## Règles attendues
- **Agrégation** : pour chaque métrique m, calculer `mean(m)` et `std(m, ddof=1)` sur tous les folds test.
- **Métriques agrégées (exhaustif I-04)** :
  - Trading : `net_pnl, net_return, max_drawdown, sharpe, profit_factor, hit_rate, n_trades, avg_trade_return, median_trade_return, exposure_time_frac`.
  - Prédiction (si applicable) : `mae, rmse, directional_accuracy, spearman_ic`.
  - **Exclues** de l'agrégation : `sharpe_per_trade`, `n_samples_train`, `n_samples_val`, `n_samples_test`.
- **Gestion des null** : les métriques `None` (null) sont exclues du calcul mean/std (ex : si un fold a `sharpe = null`, il est omis).
- **Equity stitchée** : `E_start[k+1] = E_end[k]` (continuation). Export en `equity_curve.csv` à la racine du run_dir.
- **Gaps inter-fold** : si `step_days > test_days`, warning émis et equity constante pendant le gap. Même traitement pour les micro-gaps (cf. Note A-10).
- **Avertissements §14.4** : warning si `net_pnl_mean <= 0`, `profit_factor_mean <= 1.0`, ou `max_drawdown_mean >= mdd_cap`. Enregistrés dans les logs et dans `aggregate.notes`.
- **comparison_type** : dérivé de `strategy.name` → `"contextual"` pour `buy_hold`, `"go_nogo"` pour tout le reste. Stocké dans `aggregate.comparison_type`.
- **Float conventions** : `ddof=1` pour std, float64 pour les métriques.
- **Strict code** : pas de fallback.

## Évolutions proposées
- Créer `ai_trading/metrics/aggregation.py` avec les fonctions : `aggregate_fold_metrics(fold_metrics_list)`, `stitch_equity_curves(fold_equities)`, `check_acceptance_criteria(aggregate, config)`, `derive_comparison_type(strategy_name)`.
- Mettre à jour `ai_trading/metrics/__init__.py`.
- Créer `tests/test_aggregation.py`.

## Critères d'acceptation
- [x] Test avec 3 folds synthétiques → mean et std (ddof=1) corrects pour chaque métrique.
- [x] Métriques exclues (`sharpe_per_trade`, `n_samples_*`) absentes de l'agrégat.
- [x] Gestion des null : folds avec métriques null omis du calcul mean/std.
- [x] Stitched equity : `E_start[k+1] == E_end[k]` pour tout k.
- [x] Stitched equity exportée en CSV (`time_utc, equity, in_trade, fold`).
- [x] Gaps inter-fold : equity constante, warning émis si gap détecté.
- [x] Avertissement émis si `net_pnl_mean <= 0`.
- [x] Avertissement émis si `profit_factor_mean <= 1.0`.
- [x] Avertissement émis si `max_drawdown_mean >= mdd_cap`.
- [x] `comparison_type` = `"contextual"` pour `buy_hold`, `"go_nogo"` pour les autres.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/042-aggregation` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/042-aggregation` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-10] #042 RED: <résumé>` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-10] #042 GREEN: <résumé>`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-10] #042 — Agrégation inter-fold`.
