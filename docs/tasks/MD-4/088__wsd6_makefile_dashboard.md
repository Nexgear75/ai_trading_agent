# Tâche — Cibles Makefile pour le dashboard

Statut : DONE
Ordre : 088
Workstream : WS-D-6
Milestone : MD-4
Gate lié : N/A

## Contexte
Le dashboard Streamlit est fonctionnel (MD-1 à MD-3 terminés) mais ne dispose pas encore de cibles Makefile pour le lancement et l'installation des dépendances. Le Makefile existant du projet ne contient aucune référence au dashboard. Les commandes de lancement sont spécifiées en §10.3 de la spec.

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-6.1)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§10.3)
- Code : `Makefile`, `scripts/dashboard/app.py`, `requirements-dashboard.txt`

Dépendances :
- Tâche 073 — Structure projet et dépendances (DONE, `requirements-dashboard.txt` existe)
- Tâche 078 — Point d'entrée et navigation Streamlit (DONE, `app.py` existe)

## Objectif
Ajouter au `Makefile` existant les cibles `dashboard`, `install-dashboard` et documenter ces cibles dans `make help`.

## Règles attendues
- **Config-driven** : le répertoire de runs est paramétrable via `RUNS_DIR` en variable Make (§10.3).
- **Cohérence** : les cibles suivent le style et les conventions du `Makefile` existant.
- **Pas de hardcoding** : le chemin vers `app.py` est `scripts/dashboard/app.py`, le répertoire de runs par défaut est `runs/`.

## Évolutions proposées
- Ajouter la cible `make dashboard` qui lance `streamlit run scripts/dashboard/app.py -- --runs-dir $(RUNS_DIR)`.
- Ajouter la variable `RUNS_DIR ?= runs/` en tête de Makefile.
- Ajouter la cible `make install-dashboard` qui exécute `pip install -r requirements-dashboard.txt`.
- Documenter les deux cibles dans la section `help` du Makefile.

## Critères d'acceptation
- [x] `make dashboard` lance le dashboard Streamlit.
- [x] `make dashboard RUNS_DIR=/path/to/runs` passe le paramètre `--runs-dir` correctement.
- [x] `make install-dashboard` installe les dépendances depuis `requirements-dashboard.txt`.
- [x] `make help` affiche les cibles `dashboard` et `install-dashboard`.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/088-wsd6-makefile-dashboard` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/088-wsd6-makefile-dashboard` créée depuis `milestone/MD-4`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-D-6] #088 RED: tests cibles Makefile dashboard` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-D-6] #088 GREEN: cibles Makefile dashboard`.
- [ ] **Pull Request ouverte** vers `Max6000i1` (via milestone PR).
