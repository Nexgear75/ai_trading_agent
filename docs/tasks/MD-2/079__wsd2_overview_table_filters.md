# Tâche — Page 1 : tableau récapitulatif et filtres

Statut : DONE
Ordre : 079
Workstream : WS-D-2
Milestone : MD-2
Gate lié : N/A

## Contexte
La page 1 (vue d'ensemble) affiche un tableau récapitulatif de tous les runs avec métriques clés, filtres par type/stratégie, tri par colonne, et navigation vers la page de détail. Le fichier `pages/1_overview.py` est un stub vide (créé en MD-1).

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-2.2)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§5.2, §5.3, §9.3, §12.2)
- Code : `scripts/dashboard/pages/1_overview.py`

Dépendances :
- Tâche 078 — Point d'entrée et navigation (doit être DONE)
- Tâche 076 — Utils formatage (DONE)

## Objectif
Implémenter la page `1_overview.py` avec le tableau des runs, filtres par type et stratégie, tri par colonne, et navigation vers Page 2 au clic.

## Règles attendues
- **Strict code** : pas de fallback silencieux. Si `st.session_state` ne contient pas les runs, afficher un message d'erreur explicite (pas de tableau vide sans explication).
- **Config-driven** : les colonnes et leur formatage suivent §5.2 et §9.3 de la spec.
- **DRY** : réutiliser les fonctions de formatage de `utils.py` (tâche #076).
- **Sécurité** : lecture seule, pas de `st.file_uploader()`.

## Évolutions proposées
- Construire le DataFrame récapitulatif avec colonnes §5.2 : Run ID, Stratégie, Type, Folds, Net PnL moy, Sharpe moy, MDD moy, Win Rate moy, Trades moy.
- Tri par défaut : Run ID décroissant (le plus récent en premier).
- Implémenter filtre par type : dropdown `Tous / Modèles / Baselines` (spec §5.3).
- Implémenter filtre par stratégie : multiselect des noms présents (spec §5.3).
- Implémenter le tri par clic sur en-tête de colonne (spec §5.3).
- Rendre le tableau cliquable : clic → stockage du `run_id` dans `st.session_state` → navigation vers Page 2.
- Formatage : Net PnL et MDD en `:.2%`, Sharpe en `:.2f`, Win Rate en `:.1%`, Trades en entier (§9.3).
- Indicateur tooltip sur runs dont `aggregate.notes` contient des warnings (§4.3).
- Affichage optionnel de `comparison_type` comme filtre si présent.
- Message informatif si aucun run trouvé ou uniquement des runs dummy (§12.2).

## Critères d'acceptation
- [x] Tableau affiche toutes les colonnes de §5.2 avec formatage correct (§9.3).
- [x] Tri par défaut : Run ID décroissant.
- [x] Filtre par type (Tous / Modèles / Baselines) fonctionnel.
- [x] Filtre par stratégie (multiselect) fonctionnel.
- [x] Tri par colonne fonctionnel.
- [x] Clic sur une ligne stocke le `run_id` dans `st.session_state` et navigue vers Page 2.
- [x] Message informatif si répertoire vide ou uniquement runs dummy.
- [x] Indicateur sur les runs avec warnings dans `aggregate.notes`.
- [x] Tests avec fixture multi-runs, vérification des colonnes et du filtrage.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/079-wsd2-overview-table-filters` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/079-wsd2-overview-table-filters` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-D-2] #079 RED: tests page overview tableau et filtres`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-D-2] #079 GREEN: page overview tableau récapitulatif et filtres`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-2] #079 — Page 1 : tableau récapitulatif et filtres`.
