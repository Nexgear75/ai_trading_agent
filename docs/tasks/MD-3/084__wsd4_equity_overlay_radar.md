# Tâche — Page 3 : courbes d'équité superposées et radar chart

Statut : DONE
Ordre : 084
Workstream : WS-D-4
Milestone : MD-3
Gate lié : N/A

## Contexte
La seconde section de la page de comparaison affiche la superposition des courbes d'équité stitchées (normalisées à 1.0) et un radar chart 5 axes pour comparer visuellement les runs sélectionnés. Les fonctions graphiques `chart_equity_overlay()` et `chart_radar()` sont déjà implémentées dans `charts.py` (tâche #077). Le chargement des equity curves est implémenté dans `data_loader.py` (tâche #075).

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-4.2)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§7.3, §7.4)
- Code : `scripts/dashboard/pages/3_comparison.py`, `scripts/dashboard/charts.py`

Dépendances :
- Tâche 083 — Sélection et tableau comparatif (doit être DONE) — la sélection des runs est déjà implémentée
- Tâche 075 — Data loader CSV (DONE) — `load_equity_curve()`
- Tâche 077 — Charts library (DONE) — `chart_equity_overlay()`, `chart_radar()`

## Objectif
Compléter `pages/3_comparison.py` avec la superposition des courbes d'équité et le radar chart comparatif.

## Règles attendues
- **DRY** : réutiliser `chart_equity_overlay()` et `chart_radar()` de `charts.py`, `load_equity_curve()` de `data_loader.py`.
- **Strict code** : pas de fallback silencieux. Si une equity curve est absente pour un run, afficher un message informatif pour ce run sans bloquer les autres.
- **Performance** : chargement paresseux des equity curves (uniquement lorsque la section est affichée).
- **Lecture seule** : aucune écriture dans le répertoire de runs.

## Évolutions proposées
- Charger les equity curves stitchées de chaque run sélectionné via `load_equity_curve()`.
- Afficher via `chart_equity_overlay()` : une courbe par run, normalisées à 1.0, légende cliquable (§7.3).
- Afficher le radar chart via `chart_radar()` : 5 axes (Net PnL, Sharpe, 1−MDD, Win Rate, PF), normalisation min-max sur les runs sélectionnés (§7.4).
- Dégradation si equity curves absentes pour certains runs : message informatif listant les runs sans equity curve, radar chart toujours affiché (il ne dépend que de `metrics.json`).
- Dégradation si equity curves absentes pour tous les runs : message informatif à la place du graphique overlay.

## Critères d'acceptation
- [x] Courbes d'équité superposées normalisées à 1.0 avec légende interactive.
- [x] Radar chart 5 axes avec normalisation min-max correcte.
- [x] Dégradation gracieuse si equity curves partiellement absentes (message + radar toujours affiché).
- [x] Dégradation gracieuse si toutes les equity curves sont absentes.
- [x] Tests avec données synthétiques multi-runs : overlay avec 2+ runs, radar chart, cas de dégradation.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/084-wsd4-equity-overlay-radar` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/084-wsd4-equity-overlay-radar` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-D-4] #084 RED: tests overlay equity et radar chart`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/ scripts/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-D-4] #084 GREEN: page comparaison — overlay equity et radar`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-4] #084 — Page 3 : overlay equity et radar chart`.
