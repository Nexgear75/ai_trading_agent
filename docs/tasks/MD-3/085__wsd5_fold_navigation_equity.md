# Tâche — Page 4 : navigation fold et equity curve du fold

Statut : DONE
Ordre : 085
Workstream : WS-D-5
Milestone : MD-3
Gate lié : N/A

## Contexte
La page 4 (Analyse par fold) permet une analyse détaillée fold par fold. Cette première tâche couvre la sélection du run et du fold (dropdown + slider), ainsi que l'affichage de l'equity curve du fold avec les marqueurs d'entrée/sortie des trades. Les fonctions graphiques `chart_fold_equity()` sont déjà implémentées dans `charts.py` (tâche #077). Le chargement des données par fold est implémenté dans `data_loader.py` (tâches #074, #075).

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-5.1)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§8.1, §8.2)
- Code : `scripts/dashboard/pages/4_fold_analysis.py` (stub existant)

Dépendances :
- Tâche 078 — App entry et navigation (doit être DONE) — pour `st.session_state` et navigation
- Tâche 074 — Data loader discovery (DONE) — `discover_runs()`, `load_run_metrics()`
- Tâche 075 — Data loader CSV (DONE) — `load_fold_equity_curve()`, `load_fold_trades()`
- Tâche 077 — Charts library (DONE) — `chart_fold_equity()`

## Objectif
Implémenter dans `pages/4_fold_analysis.py` la navigation run/fold et l'affichage de l'equity curve du fold avec marqueurs de trades.

## Règles attendues
- **Strict code** : pas de fallback silencieux. Si le fold sélectionné n'a pas d'equity curve, afficher un message informatif explicite.
- **DRY** : réutiliser `chart_fold_equity()` de `charts.py`, `load_fold_equity_curve()` et `load_fold_trades()` de `data_loader.py`.
- **Lecture seule** : aucune écriture dans le répertoire de runs.
- **Performance** : chargement paresseux des données du fold sélectionné uniquement.

## Évolutions proposées
- Implémenter le dropdown de sélection du run (liste des runs disponibles avec stratégie) (§8.1).
- Implémenter le dropdown de sélection du fold (dynamique selon le run sélectionné) (§8.1).
- Implémenter le slider alternatif pour navigation rapide entre folds (§8.1).
- Charger les données du fold sélectionné : equity curve via `load_fold_equity_curve()` et trades via `load_fold_trades()`.
- Afficher via `chart_fold_equity()` : equity curve du fold avec points d'entrée (▲ vert) et sortie (▼ rouge) des trades, zone de drawdown ombrée (§8.2).
- Dégradation si `equity_curve.csv` du fold absent : message informatif.
- Dégradation si `trades.csv` du fold absent : equity curve sans marqueurs de trades.

## Critères d'acceptation
- [x] Dropdown run + fold fonctionnels, mis à jour dynamiquement.
- [x] Slider alternatif pour navigation entre folds fonctionnel.
- [x] Equity curve du fold affichée avec zone de drawdown ombrée.
- [x] Marqueurs d'entrée (▲ vert) et de sortie (▼ rouge) des trades superposés.
- [x] Dégradation gracieuse si equity curve absente (message informatif).
- [x] Dégradation gracieuse si trades absents (equity curve sans marqueurs).
- [x] Tests couvrant : sélection run/fold, affichage equity curve, cas de dégradation.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/085-wsd5-fold-navigation-equity` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/085-wsd5-fold-navigation-equity` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-D-5] #085 RED: tests navigation fold et equity curve`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/ scripts/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-D-5] #085 GREEN: page analyse fold — navigation et equity`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-5] #085 — Page 4 : navigation fold et equity curve`.
