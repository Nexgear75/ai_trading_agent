# Tâche — Sécurité et performance du dashboard

Statut : DONE
Ordre : 089
Workstream : WS-D-6
Milestone : MD-4
Gate lié : N/A

## Contexte
Le dashboard doit respecter les contraintes de sécurité (lecture seule, validation des chemins) et de performance (cache Streamlit, chargement paresseux, pagination, seuil d'alerte) définies en §11.1 et §11.2 de la spécification. Ces contraintes s'appliquent transversalement à tous les modules du dashboard (`data_loader.py`, pages, `utils.py`).

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-6.2)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§11.1, §11.2)
- Code : `scripts/dashboard/data_loader.py`, `scripts/dashboard/pages/`, `scripts/dashboard/utils.py`

Dépendances :
- Tâche 074 — Data loader : découverte et validation des runs (DONE)
- Tâche 075 — Data loader : chargement des CSV (DONE)
- Tâche 078 — Point d'entrée et navigation Streamlit (DONE)

## Objectif
Auditer et compléter les modules du dashboard pour garantir la conformité aux exigences de sécurité (§11.1) et de performance (§11.2). Ajouter les décorateurs `@st.cache_data`, la validation des chemins, et les mécanismes de protection.

## Règles attendues
- **Sécurité** : aucune opération d'écriture dans le code dashboard. Tous les chemins validés via `Path.resolve()` pour éviter les directory traversals (§11.1). Pas d'accès réseau. Pas de `st.file_uploader()`.
- **Performance** : `@st.cache_data` sur toutes les fonctions de chargement (JSON, CSV, YAML). Chargement paresseux des CSV volumineux. Pagination des tableaux de trades à 50 lignes/page.
- **Strict code** : pas de fallback silencieux. Avertissement explicite si un run contient plus de 200 folds.

## Évolutions proposées
- Vérifier que `data_loader.py` applique `Path.resolve()` sur tous les chemins d'entrée avant lecture.
- Ajouter `@st.cache_data` sur les fonctions `load_run_metrics()`, `load_run_manifest()`, `load_config_snapshot()`, `load_equity_curve()`, `load_trades()`, `load_predictions()`, `load_fold_metrics()`.
- Implémenter un avertissement si un run contient plus de 200 folds (`st.warning()`).
- Vérifier l'absence de toute opération d'écriture (`open(..., 'w')`, `to_csv()`, `shutil.copy`, etc.) dans l'ensemble du code dashboard.
- Vérifier le chargement paresseux : les CSV ne sont chargés que lorsque la page correspondante est affichée (pas au démarrage global).

## Critères d'acceptation
- [x] Aucune opération d'écriture dans le code dashboard (audit complet).
- [x] Tous les chemins d'entrée validés via `Path.resolve()` dans `data_loader.py`.
- [x] `@st.cache_data` appliqué sur toutes les fonctions de chargement.
- [x] Avertissement affiché si un run contient > 200 folds.
- [x] Chargement paresseux des CSV : uniquement lorsque la page est affichée.
- [x] Pagination des tableaux de trades à 50 lignes/page (déjà implémenté, validation).
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/089-wsd6-security-performance` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/089-wsd6-security-performance` créée depuis `milestone/MD-4`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-D-6] #089 RED: tests sécurité et performance dashboard`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check scripts/dashboard/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-D-6] #089 GREEN: sécurité et performance dashboard`.
- [ ] **Pull Request ouverte** vers `Max6000i1` (via milestone PR).
