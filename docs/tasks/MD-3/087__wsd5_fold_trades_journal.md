# Tâche — Page 4 : journal des trades du fold

Statut : DONE
Ordre : 087
Workstream : WS-D-5
Milestone : MD-3
Gate lié : N/A

## Contexte
La troisième section de la page d'analyse par fold affiche le journal des trades filtré sur le fold sélectionné. Cette section réutilise la logique de pagination et de filtrage déjà implémentée en tâche #082 (Page 2 : distribution des trades et journal). Le chargement des trades par fold est implémenté dans `data_loader.py` via `load_fold_trades()`.

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-5.3)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§8.4, §6.6)
- Code : `scripts/dashboard/pages/4_fold_analysis.py`, `scripts/dashboard/pages/2_run_detail.py` (logique de journal à factoriser)

Dépendances :
- Tâche 085 — Navigation fold et equity curve (doit être DONE)
- Tâche 082 — Page 2 : distribution des trades et journal (DONE, logique à réutiliser)
- Tâche 075 — Data loader CSV (DONE)

## Objectif
Implémenter dans `pages/4_fold_analysis.py` le journal des trades du fold sélectionné, conforme à §8.4 (reprend §6.6 filtré sur un fold unique).

## Règles attendues
- **DRY** : la logique de pagination, formatage et affichage du journal existe dans `pages/2_run_detail.py` (tâche #082). Factoriser cette logique dans un helper partagé ou la réutiliser directement. Ne pas dupliquer le code de construction du tableau.
- **Strict code** : pas de fallback silencieux. Si `trades.csv` du fold est absent, afficher un message informatif.
- **Performance** : pagination à 50 lignes/page (§11.2).

## Évolutions proposées
- Charger `trades.csv` du fold sélectionné via `load_fold_trades()`.
- Factoriser la logique de journal partagée entre Page 2 (§6.6) et Page 4 (§8.4) : pagination 50 lignes/page, colonnes (Entry time, Exit time, Entry price, Exit price, Gross return, Costs, Net return, Equity after), formatage §9.3.
- Afficher le journal filtré sur le fold unique (pas de filtre par fold ici, puisque le fold est déjà sélectionné en amont).
- Conserver les filtres par signe (gagnant/perdant) et par période (§6.6).
- Colonne Equity after : jointure avec `equity_curve.csv` du fold si disponible, omise sinon.
- Dégradation si `trades.csv` du fold absent : message informatif.

## Critères d'acceptation
- [x] Journal des trades conforme à §6.6 et §8.4, filtré sur le fold sélectionné.
- [x] Logique de journal factorisée (DRY avec tâche #082) — pas de duplication du code de tableau.
- [x] Pagination à 50 lignes/page.
- [x] Filtres par signe et par période fonctionnels.
- [x] Colonne Equity after présente si equity curve disponible, omise sinon.
- [x] Dégradation gracieuse si trades du fold absents (message informatif).
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/087-wsd5-fold-trades-journal` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/087-wsd5-fold-trades-journal` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-D-5] #087 RED: tests journal trades du fold`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-D-5] #087 GREEN: journal trades du fold`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-5] #087 — Page 4 : journal des trades du fold`.
