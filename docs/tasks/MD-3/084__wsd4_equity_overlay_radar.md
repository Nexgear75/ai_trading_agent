# Tâche — Page 3 : courbes d'équité superposées et radar chart

Statut : TODO
Ordre : 084
Workstream : WS-D-4
Milestone : MD-3
Gate lié : N/A

## Contexte
La seconde section de la page de comparaison affiche les courbes d'équité stitchées superposées (normalisées à 1.0) et un radar chart comparatif sur 5 axes. Les fonctions graphiques `chart_equity_overlay()` et `chart_radar()` sont déjà implémentées dans `charts.py` (tâche #077). Le chargement des equity curves est implémenté dans `data_loader.py` (tâche #075).

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-4.2)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§7.3, §7.4, §9.2)
- Code : `scripts/dashboard/pages/3_comparison.py`, `scripts/dashboard/charts.py`

Dépendances :
- Tâche 083 — Sélection runs et tableau comparatif (doit être DONE)
- Tâche 077 — Charts library (DONE)
- Tâche 075 — Data loader CSV (DONE)

## Objectif
Implémenter dans `pages/3_comparison.py` la superposition des courbes d'équité et le radar chart comparatif, en aval du tableau comparatif.

## Règles attendues
- **DRY** : réutiliser `chart_equity_overlay()` et `chart_radar()` de `charts.py`, `load_equity_curve()` de `data_loader.py`.
- **Strict code** : dégradation gracieuse documentée si equity curves partiellement absentes (message informatif). Le radar chart est toujours affiché (il dépend de `metrics.json` uniquement).
- **Performance** : chargement paresseux des equity curves (uniquement quand la page est affichée).

## Évolutions proposées
- Charger les equity curves stitchées de chaque run sélectionné via `load_equity_curve()`.
- Afficher via `chart_equity_overlay()` : une courbe par run, normalisées à 1.0, légende cliquable (§7.3).
- Afficher le radar chart via `chart_radar()` : 5 axes (Net PnL, Sharpe, 1−MDD, Win Rate, PF), normalisation min-max sur les runs sélectionnés (§7.4).
- Dégradation si equity curves absentes pour certains runs : message informatif listant les runs sans equity curve, les runs ayant une equity curve sont toujours superposés.
- Le radar chart est toujours affiché tant que `metrics.json` est disponible.

## Critères d'acceptation
- [ ] Courbes d'équité superposées normalisées à 1.0 avec légende interactive.
- [ ] Radar chart 5 axes avec normalisation min-max correcte.
- [ ] Dégradation gracieuse si equity curves partiellement absentes (message + courbes restantes).
- [ ] Radar chart affiché indépendamment de la disponibilité des equity curves.
- [ ] Tests avec données synthétiques multi-runs (2+ runs).
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords.
- [ ] Suite de tests verte après implémentation.
- [ ] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/084-wsd4-equity-overlay-radar` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/084-wsd4-equity-overlay-radar` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-D-4] #084 RED: tests courbes superposées et radar chart`.
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-D-4] #084 GREEN: courbes superposées et radar chart`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-4] #084 — Page 3 : courbes d'équité superposées et radar chart`.
