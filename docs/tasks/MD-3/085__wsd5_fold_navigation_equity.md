# Tâche — Page 4 : navigation par fold et equity curve du fold

Statut : TODO
Ordre : 085
Workstream : WS-D-5
Milestone : MD-3
Gate lié : N/A

## Contexte
La page 4 (analyse par fold) permet de sélectionner un run puis un fold et d'afficher l'equity curve du fold avec les marqueurs d'entrée/sortie des trades. Le fichier `pages/4_fold_analysis.py` existe (stub créé en MD-1). Les fonctions `load_fold_equity_curve()`, `load_fold_trades()` de `data_loader.py` et `chart_fold_equity()` de `charts.py` sont déjà implémentées.

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-5.1)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§8.1, §8.2)
- Code : `scripts/dashboard/pages/4_fold_analysis.py`, `scripts/dashboard/charts.py`, `scripts/dashboard/data_loader.py`

Dépendances :
- Tâche 080 — Page 2 : en-tête et KPI cards (DONE, fournit le pattern de sélection de run)
- Tâche 075 — Data loader CSV (DONE)
- Tâche 077 — Charts library (DONE)

## Objectif
Implémenter dans `pages/4_fold_analysis.py` la sélection de run/fold et l'affichage de l'equity curve du fold avec marqueurs de trades.

## Règles attendues
- **Strict code** : pas de fallback silencieux. Si un fold sélectionné n'a pas d'equity curve, afficher un message informatif explicite.
- **DRY** : réutiliser `load_fold_equity_curve()`, `load_fold_trades()` de `data_loader.py` et `chart_fold_equity()` de `charts.py`.
- **Performance** : chargement des données par fold uniquement quand le fold est sélectionné.

## Évolutions proposées
- Implémenter le dropdown de sélection du run (liste des runs découverts avec nom de stratégie), puis dropdown du fold (§8.1).
- Implémenter le slider alternatif pour navigation entre folds (§8.1).
- Charger l'equity curve du fold via `load_fold_equity_curve()`.
- Charger les trades du fold via `load_fold_trades()` pour les marqueurs d'entrée/sortie.
- Afficher via `chart_fold_equity()` : courbe d'équité avec points d'entrée ▲ vert et sortie ▼ rouge, zone de drawdown ombrée (§8.2).
- Dégradation si `equity_curve.csv` du fold absent : message informatif.

## Critères d'acceptation
- [ ] Dropdown run + fold fonctionnels avec identification par stratégie.
- [ ] Slider alternatif pour navigation entre folds fonctionnel.
- [ ] Equity curve du fold affichée avec marqueurs d'entrée (▲ vert) et sortie (▼ rouge) des trades.
- [ ] Zone de drawdown ombrée visible.
- [ ] Dégradation gracieuse si equity curve du fold absente (message informatif).
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords.
- [ ] Suite de tests verte après implémentation.
- [ ] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/085-wsd5-fold-navigation-equity` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/085-wsd5-fold-navigation-equity` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-D-5] #085 RED: tests navigation fold et equity curve`.
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-D-5] #085 GREEN: navigation fold et equity curve`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-5] #085 — Page 4 : navigation par fold et equity curve`.
