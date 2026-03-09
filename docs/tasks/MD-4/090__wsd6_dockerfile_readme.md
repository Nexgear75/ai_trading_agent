# Tâche — Dockerfile dashboard et documentation README

Statut : DONE
Ordre : 090
Workstream : WS-D-6
Milestone : MD-4
Gate lié : N/A

## Contexte
Le dashboard nécessite un Dockerfile dédié (optionnel, basse priorité) et une mise à jour du README pour documenter les instructions de lancement, les variables d'environnement et les commandes Makefile. La spec §10.5 fournit un template de Dockerfile et la documentation doit couvrir les modes de lancement (Makefile, CLI directe, Docker).

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-6.3)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§10.3, §10.5)
- Code : `Dockerfile` (existant, pipeline), `README.md`, `scripts/dashboard/`

Dépendances :
- Tâche 088 — Cibles Makefile dashboard (doit être DONE)
- Tâche 078 — Point d'entrée et navigation Streamlit (DONE)

## Objectif
Créer un Dockerfile pour le dashboard (basé sur §10.5) et mettre à jour le `README.md` avec une section dédiée au dashboard : installation, lancement, variables d'environnement (`AI_TRADING_RUNS_DIR`).

## Règles attendues
- **Sécurité** : le Dockerfile expose uniquement le port 8501, lance en mode headless, pas d'exécution en root si possible.
- **Cohérence** : le Dockerfile dashboard est distinct du Dockerfile pipeline existant. Nommer `Dockerfile.dashboard` pour éviter le conflit.
- **Documentation complète** : le README doit couvrir les 3 modes de lancement (Makefile, CLI direct, Docker).

## Évolutions proposées
- Créer `Dockerfile.dashboard` conforme à §10.5 : base `python:3.11-slim`, copie des requirements, installation des dépendances, exposition du port 8501, commande de lancement headless.
- Ajouter une section `## Dashboard` dans `README.md` avec :
  - Prérequis : `make install-dashboard` ou `pip install -r requirements-dashboard.txt`.
  - Lancement : `make dashboard`, `make dashboard RUNS_DIR=...`, commande Streamlit directe.
  - Variable d'environnement `AI_TRADING_RUNS_DIR`.
  - Docker : `docker build -f Dockerfile.dashboard -t ai-trading-dashboard .` et `docker run -p 8501:8501 -v $(pwd)/runs:/app/runs ai-trading-dashboard`.
- Ajouter la cible `make docker-dashboard` dans le Makefile (build + run).

## Critères d'acceptation
- [x] `Dockerfile.dashboard` existe et est conforme à §10.5.
- [x] `docker build -f Dockerfile.dashboard .` passe sans erreur.
- [x] `README.md` contient une section dashboard avec instructions complètes.
- [x] Variable `AI_TRADING_RUNS_DIR` documentée.
- [x] Les 3 modes de lancement sont documentés (Makefile, CLI, Docker).
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/090-wsd6-dockerfile-readme` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/090-wsd6-dockerfile-readme` créée depuis `milestone/MD-4`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-D-6] #090 RED: tests Dockerfile et documentation dashboard`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check scripts/dashboard/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-D-6] #090 GREEN: Dockerfile et documentation dashboard`.
- [ ] **Pull Request ouverte** vers `Max6000i1` (via milestone PR).
