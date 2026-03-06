# Tâche — Page 2 : equity curve stitchée et métriques par fold

Statut : DONE
Ordre : 081
Workstream : WS-D-3
Milestone : MD-2
Gate lié : N/A

## Contexte
La deuxième section de la page de détail d'un run affiche la courbe d'équité stitchée (normalisée à 1.0, avec frontières de folds, drawdown, zones in-trade) et le tableau détaillé des métriques par fold avec bar chart du Net PnL. Les fonctions graphiques `chart_equity_curve()` et `chart_pnl_bar()` sont déjà implémentées dans `charts.py` (tâche #077).

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-3.2)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§6.3, §6.4, §9.3)
- Code : `scripts/dashboard/pages/2_run_detail.py`

Dépendances :
- Tâche 080 — En-tête du run et KPI cards (doit être DONE)
- Tâche 075 — Data loader CSV (DONE)
- Tâche 077 — Charts library (DONE)

## Objectif
Implémenter dans `pages/2_run_detail.py` la section equity curve et le tableau des métriques par fold.

## Règles attendues
- **Strict code** : si `equity[0] <= 0`, afficher un message d'erreur (pas de normalisation silencieuse incorrecte). Pas de fallback pour données manquantes.
- **Config-driven** : lecture du threshold object `{method, theta, selected_quantile}` depuis `metrics.json`. Pas de valeur par défaut pour θ.
- **DRY** : réutiliser `chart_equity_curve()`, `chart_pnl_bar()` de `charts.py`, `format_pct()`, `format_float()`, `format_sharpe_per_trade()` de `utils.py`, `load_equity_curve()` de `data_loader.py`.
- **Anti-fuite** : les données sont lues, jamais recalculées.

## Évolutions proposées
- Charger `equity_curve.csv` stitché via `load_equity_curve()`.
- Afficher via `chart_equity_curve()` avec `fold_boundaries=True`, `drawdown=True`, `in_trade_zones=True`.
- Construire le tableau métriques par fold (§6.4) avec colonnes : Fold, θ, Method, Quantile, Net PnL, Sharpe, MDD, Win Rate, N Trades, MAE, RMSE, DA, IC, Sharpe/Trade.
- Accéder à θ via `fold.threshold.theta` (pas directement comme float). Afficher `threshold.method` et `threshold.selected_quantile`. Pour `method="none"`, afficher θ comme `—`.
- Indicateur ⚠️ pour folds avec `n_trades ≤ 2` sur la colonne Sharpe/Trade (§6.4).
- Formatage via `format_sharpe_per_trade()` pour valeurs extrêmes (notation scientifique si `|value| > 1000`).
- Valeurs `null` affichées comme `—` (§6.4).
- Bar chart du Net PnL par fold via `chart_pnl_bar()`.
- Dégradation si `equity_curve.csv` absent : message informatif (§4.2).

## Critères d'acceptation
- [x] Equity curve normalisée à 1.0, frontières de folds visibles, drawdown et zones in-trade.
- [x] Tableau métriques par fold avec toutes les colonnes de §6.4.
- [x] θ accédé via `fold.threshold.theta` (objet, pas float direct).
- [x] `threshold.method` et `threshold.selected_quantile` affichés.
- [x] Pour `method="none"` : θ affiché comme `—`.
- [x] Indicateur ⚠️ pour folds avec `n_trades ≤ 2` sur Sharpe/Trade.
- [x] Valeurs `null` affichées comme `—`.
- [x] Bar chart PnL par fold fonctionnel.
- [x] Message informatif si equity curve absente.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/081-wsd3-equity-fold-metrics` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/081-wsd3-equity-fold-metrics` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-D-3] #081 RED: tests equity curve et métriques par fold`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-D-3] #081 GREEN: equity curve stitchée et métriques par fold`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-3] #081 — Page 2 : equity curve et métriques par fold`.
