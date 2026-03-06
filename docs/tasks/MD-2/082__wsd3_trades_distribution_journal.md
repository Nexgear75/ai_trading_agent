# Tâche — Page 2 : distribution des trades et journal

Statut : DONE
Ordre : 082
Workstream : WS-D-3
Milestone : MD-2
Gate lié : N/A

## Contexte
La troisième section de la page de détail affiche la distribution des rendements (histogramme, box plot, statistiques) et le journal des trades paginé avec filtres. Les fonctions graphiques `chart_returns_histogram()` et `chart_returns_boxplot()` sont déjà implémentées dans `charts.py` (tâche #077). Le chargement des trades et de l'equity curve est implémenté dans `data_loader.py` (tâche #075).

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-3.3)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§6.5, §6.6, §9.3, §11.2)
- Code : `scripts/dashboard/pages/2_run_detail.py`

Dépendances :
- Tâche 080 — En-tête du run et KPI cards (doit être DONE)
- Tâche 075 — Data loader CSV (DONE)
- Tâche 077 — Charts library (DONE)

## Objectif
Implémenter dans `pages/2_run_detail.py` la section distribution des trades et le journal des trades paginé avec filtres.

## Règles attendues
- **Strict code** : pas de fallback silencieux pour données manquantes. Dégradation gracieuse documentée (message informatif, pas de crash).
- **DRY** : réutiliser `chart_returns_histogram()`, `chart_returns_boxplot()` de `charts.py`, `load_trades()`, `load_equity_curve()` de `data_loader.py`, fonctions de formatage de `utils.py`.
- **Performance** : pagination à 50 lignes/page (§11.2). Chargement paresseux des CSV.
- **Anti-fuite** : statistiques (mean, median, std, skewness) calculées avec `pandas`/`scipy` sur les données lues, jamais recalculées à partir de métriques agrégées.

## Évolutions proposées
- Charger les trades via `load_trades()` (concaténation de tous les folds avec colonne `fold`).
- Afficher l'histogramme des rendements nets via `chart_returns_histogram()` (§6.5).
- Afficher le box plot par fold via `chart_returns_boxplot()` (§6.5).
- Afficher les statistiques : mean, median, std, skewness, best trade, worst trade (§6.5).
- Implémenter le journal des trades paginé (§6.6) avec colonnes : Fold, Entry time, Exit time, Entry price, Exit price, Gross return, Costs (`fees_paid + slippage_paid`), Net return, Equity after.
- Colonne Equity after : jointure `pandas.merge_asof(direction='backward')` de `exit_time_utc` vers `equity_curve.csv → time_utc` du même fold (§6.6). Si aucune correspondance, afficher `—`.
- Pagination : 50 lignes par page (§11.2).
- Filtres : par fold (dropdown), par signe gagnant/perdant (radio), par période (date range) (§6.6).
- Dégradation si `trades.csv` absent : message informatif (§4.2, §12.2).
- Colonne Equity after omise si `equity_curve.csv` absent (§6.6).

## Critères d'acceptation
- [x] Histogramme des rendements nets fonctionnel.
- [x] Box plot par fold fonctionnel.
- [x] Statistiques affichées : mean, median, std, skewness, best trade, worst trade.
- [x] Journal paginé à 50 lignes/page.
- [x] Colonne Costs calculée correctement (`fees_paid + slippage_paid`).
- [x] Jointure `merge_asof` pour Equity after correcte (par fold).
- [x] Filtres fonctionnels : par fold, par signe, par période.
- [x] Dégradation gracieuse si trades ou equity curve absents (message informatif).
- [x] Colonne Equity after omise si equity curve absente.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/082-wsd3-trades-distribution-journal` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/082-wsd3-trades-distribution-journal` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-D-3] #082 RED: tests distribution trades et journal paginé`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-D-3] #082 GREEN: distribution des trades et journal paginé`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-3] #082 — Page 2 : distribution des trades et journal`.
