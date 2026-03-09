# Tâche — Page 3 : sélection des runs et tableau comparatif

Statut : DONE
Ordre : 083
Workstream : WS-D-4
Milestone : MD-3
Gate lié : N/A

## Contexte
La page 3 (comparaison multi-runs) permet de sélectionner 2 à 10 runs et d'afficher un tableau comparatif avec mise en surbrillance du meilleur/pire par colonne et vérification du critère §14.4 du pipeline. Le fichier `pages/3_comparison.py` existe (stub créé en MD-1). Les fonctions de chargement (`data_loader.py`) et de formatage (`utils.py`) sont déjà implémentées.

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-4.1)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§7.1, §7.2, §9.3)
- Code : `scripts/dashboard/pages/3_comparison.py`

Dépendances :
- Tâche 079 — Page 1 : tableau récapitulatif et filtres (doit être DONE)
- Tâche 074 — Data loader discovery (DONE)
- Tâche 075 — Data loader CSV (DONE)
- Tâche 076 — Utils formatting (DONE)

## Objectif
Implémenter dans `pages/3_comparison.py` le multiselect de runs et le tableau comparatif avec mise en surbrillance et vérification des critères §14.4.

## Règles attendues
- **Config-driven** : le seuil MDD est lu depuis `config_snapshot.yaml` de chaque run (`thresholding.mdd_cap`), jamais hardcodé dans le dashboard.
- **Strict code** : pas de fallback silencieux. Si `config_snapshot.yaml` est absent pour un run, signaler explicitement l'absence du seuil MDD.
- **DRY** : réutiliser `discover_runs()`, `load_run_metrics()`, `load_config_snapshot()` de `data_loader.py` et les fonctions de formatage de `utils.py`.

## Évolutions proposées
- Implémenter le multiselect en sidebar : 2 à 10 runs, avec nom de stratégie (`strategy.name`) à côté du run ID (§7.1).
- Construire le tableau comparatif avec les colonnes de §5.2 : Run ID, Stratégie, Type (`strategy_type`), Folds, Net PnL moy, Sharpe moy, MDD moy, Win Rate moy, Trades moy, restreint aux runs sélectionnés.
- Mise en surbrillance : meilleure valeur par colonne en gras vert, pire en italique rouge (§7.2).
- Vérification du critère §14.4 : icône ✅/❌ par run. Seuils : P&L net > 0, profit factor > 1.0 (hardcodés pipeline), MDD < `thresholding.mdd_cap` (lu depuis `config_snapshot.yaml` de chaque run).
- Lecture et affichage du champ `aggregate.notes` de `metrics.json` pour afficher les warnings éventuels (§7.2).
- Gestion du cas < 2 runs sélectionnés : message informatif.

## Critères d'acceptation
- [x] Multiselect 2-10 runs avec identification par stratégie (nom + run ID).
- [x] Tableau comparatif avec colonnes conformes à §5.2 et formatage §9.3.
- [x] Surbrillance meilleur (gras vert) / pire (italique rouge) par colonne.
- [x] Icône ✅/❌ basée sur critères §14.4 avec seuil MDD lu depuis `config_snapshot.yaml`.
- [x] Notes/warnings du pipeline affichés si `aggregate.notes` présent.
- [x] Message informatif si moins de 2 runs sélectionnés.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/083-wsd4-comparison-table` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/083-wsd4-comparison-table` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-D-4] #083 RED: tests sélection runs et tableau comparatif`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-D-4] #083 GREEN: sélection runs et tableau comparatif`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-4] #083 — Page 3 : sélection des runs et tableau comparatif`.
