# Tâche — Bibliothèque de graphiques Plotly (charts.py)

Statut : DONE
Ordre : 077
Workstream : WS-D-1
Milestone : MD-1
Gate lié : N/A

## Contexte
Le module `charts.py` centralise toutes les fonctions de génération de graphiques Plotly réutilisables par les 4 pages du dashboard. Chaque fonction retourne un `go.Figure` prêt à être affiché via `st.plotly_chart()`. Les graphiques utilisent la palette de couleurs définie dans `utils.py`.

Références :
- Plan : `docs/plan/streamlit/implementation.md` (WS-D-1.5)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§6.3, §6.4, §6.5, §7.3, §7.4, §8.2, §8.3, §9.2)
- Code : `scripts/dashboard/charts.py` (à implémenter)

Dépendances :
- Tâche 076 — Utilitaires formatage et couleurs (doit être DONE, pour les constantes palette)
- Tâche 075 — Data loader CSV (doit être DONE, pour les formats DataFrame attendus)

## Objectif
Implémenter dans `charts.py` les 8 fonctions de graphiques Plotly réutilisables : equity curve stitchée, PnL bar chart par fold, histogramme des rendements, box plot par fold, overlay multi-runs, radar chart, scatter prédictions, et equity curve fold avec marqueurs de trades.

## Règles attendues
- Chaque fonction retourne un `go.Figure` Plotly valide, jamais `None`.
- Couleurs conformes à §9.2, importées depuis `utils.py`.
- Tous les graphiques utilisent `use_container_width=True` côté Streamlit.
- Normalisation equity à 1.0 (diviser par `equity[0]`) dans les graphiques concernés (§6.3, §7.3).
- Détection du type signal via `threshold_method == "none"` pour le scatter plot (§8.3).
- Fold boundaries détectées par changement de la colonne `fold` (§6.3).

## Évolutions proposées
- Implémenter `chart_equity_curve(df, fold_boundaries=True, drawdown=True, in_trade_zones=True) -> go.Figure` : line chart avec frontières de folds (lignes verticales pointillées grises), zone de drawdown ombrée, zones de position colorées (§6.3).
- Implémenter `chart_pnl_bar(fold_metrics: list[dict]) -> go.Figure` : bar chart Net PnL par fold, coloré vert/rouge (§6.4).
- Implémenter `chart_returns_histogram(trades_df: pd.DataFrame) -> go.Figure` : histogramme rendements nets par trade (§6.5).
- Implémenter `chart_returns_boxplot(trades_df: pd.DataFrame) -> go.Figure` : box plot rendements par fold (§6.5).
- Implémenter `chart_equity_overlay(curves: dict[str, pd.DataFrame]) -> go.Figure` : superposition equity multi-runs, normalisées départ=1.0 (§7.3).
- Implémenter `chart_radar(runs_data: list[dict]) -> go.Figure` : radar 5 axes (Net PnL, Sharpe, 1−MDD, Win Rate, PF), normalisation min-max (§7.4).
- Implémenter `chart_scatter_predictions(preds_df, theta, threshold_method) -> go.Figure` : scatter y_hat vs y_true avec coloration Go/No-Go (§8.3). Si `threshold_method == "none"`, retourner un Figure avec annotation informatif.
- Implémenter `chart_fold_equity(df, trades_df) -> go.Figure` : equity curve fold avec points d'entrée ▲ vert et sortie ▼ rouge (§8.2).

## Critères d'acceptation
- [x] Chaque fonction génère un `go.Figure` Plotly valide (pas de `None`).
- [x] Couleurs conformes à §9.2 (palette centralisée).
- [x] `chart_equity_curve()` : fold boundaries détectées par changement colonne `fold`, drawdown ombré, zones in_trade.
- [x] `chart_equity_overlay()` : normalisation equity à 1.0, légende cliquable.
- [x] `chart_radar()` : 5 axes, normalisation min-max sur les runs fournis.
- [x] `chart_scatter_predictions()` : coloration Go/No-Go, message informatif si `method == "none"`.
- [x] `chart_fold_equity()` : marqueurs ▲ vert (entrée) et ▼ rouge (sortie).
- [x] Tests unitaires avec données synthétiques (pas de test visuel) : vérification du type `go.Figure`, nombre de traces, axes, annotations.
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/077-wsd1-charts-library` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/077-wsd1-charts-library` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-D-1] #077 RED: tests bibliothèque graphiques Plotly` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-D-1] #077 GREEN: bibliothèque graphiques Plotly`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-1] #077 — Bibliothèque graphiques Plotly`.
