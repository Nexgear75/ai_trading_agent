# Tâche — Page 3 : sélection des runs et tableau comparatif

Statut : DONE
Ordre : 083
Workstream : WS-D-4
Milestone : MD-3
Gate lié : N/A

## Contexte
La page 3 (Comparaison multi-runs) permet de comparer côte à côte les métriques agrégées de 2 à 10 runs sélectionnés. Elle affiche un multiselect en sidebar, un tableau comparatif avec surbrillance meilleur/pire, et les icônes ✅/❌ basées sur les critères §14.4 du pipeline (P&L net > 0, profit factor > 1.0, MDD < `thresholding.mdd_cap`). Le fichier `pages/3_comparison.py` existe en tant que stub vide.

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-4.1)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§7.1, §7.2)
- Code : `scripts/dashboard/pages/3_comparison.py` (stub existant)

Dépendances :
- Tâche 078 — App entry et navigation (doit être DONE) — pour `st.session_state` et navigation
- Tâche 079 — Page 1 overview table (doit être DONE) — même format de colonnes §5.2
- Tâche 074 — Data loader discovery (DONE) — `discover_runs()`, `load_run_metrics()`
- Tâche 075 — Data loader CSV (DONE) — `load_config_snapshot()`
- Tâche 076 — Utils formatting (DONE) — fonctions de formatage

## Objectif
Implémenter dans `pages/3_comparison.py` le multiselect de runs et le tableau comparatif avec surbrillance et indicateur de conformité pipeline.

## Règles attendues
- **Config-driven** : le seuil MDD est lu depuis `config_snapshot.yaml` de chaque run (`thresholding.mdd_cap`), jamais hardcodé dans le dashboard.
- **Strict code** : pas de fallback silencieux. Si `config_snapshot.yaml` est absent, le critère MDD affiche `—` (pas de valeur par défaut).
- **DRY** : réutiliser les colonnes et le formatage de la Page 1 (§5.2). Factoriser la logique de construction du tableau si possible.
- **Lecture seule** : aucune écriture dans le répertoire de runs.

## Évolutions proposées
- Implémenter le multiselect en sidebar : 2 à 10 runs, avec nom de stratégie à côté du run ID (§7.1).
- Construire le tableau comparatif avec les colonnes de §5.2 : Run ID, Stratégie, Type, Folds, Net PnL moy, Sharpe moy, MDD moy, Win Rate moy, Trades moy, restreint aux runs sélectionnés (§7.2).
- Mise en surbrillance : meilleure valeur en gras vert, pire en italique rouge, par colonne (§7.2).
- Vérification du critère §14.4 pipeline : icône ✅/❌ par run. Seuils : P&L net > 0, profit factor > 1.0, MDD < `thresholding.mdd_cap` lu depuis `config_snapshot.yaml` (§7.2).
- Lecture du champ `aggregate.notes` de `metrics.json` pour afficher les warnings éventuels (§7.2).
- Gestion du cas où moins de 2 runs sont sélectionnés : message informatif invitant à sélectionner au moins 2 runs.

## Critères d'acceptation
- [x] Multiselect 2-10 runs avec identification par stratégie.
- [x] Tableau comparatif avec colonnes conformes à §5.2 et formatage §9.3.
- [x] Surbrillance meilleur (gras vert) / pire (italique rouge) par colonne.
- [x] Icône ✅/❌ basée sur critères §14.4 avec seuil MDD lu depuis `config_snapshot.yaml`.
- [x] Notes/warnings du pipeline affichés si présents dans `aggregate.notes`.
- [x] Message informatif si < 2 runs sélectionnés.
- [x] Tests avec 2+ runs synthétiques couvrant : sélection, surbrillance, critères ✅/❌.
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
- [x] `ruff check ai_trading/ tests/ scripts/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-D-4] #083 GREEN: page comparaison — sélection et tableau`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-4] #083 — Page 3 : sélection et tableau comparatif`.
