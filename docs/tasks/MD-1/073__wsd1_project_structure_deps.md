# Tâche — Structure du projet et dépendances dashboard Streamlit

Statut : DONE
Ordre : 073
Workstream : WS-D-1
Milestone : MD-1
Gate lié : N/A

## Contexte
Le dashboard Streamlit est un composant de visualisation post-exécution, en lecture seule, exploitant les artefacts produits par le pipeline AI Trading (M1–M5). Cette tâche fondatrice crée l'arborescence du code, le fichier de dépendances et la configuration Streamlit.

Références :
- Plan : `docs/plan/streamlit/implementation.md` (WS-D-1.1)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§10.2, §10.4, Annexe C)
- Code : `scripts/dashboard/` (à créer)

Dépendances :
- Pipeline principal M5 terminé (artefacts disponibles dans `runs/`)

## Objectif
Créer l'arborescence `scripts/dashboard/` avec tous les fichiers du projet, le fichier `requirements-dashboard.txt` avec les dépendances conformes à l'Annexe C de la spec, et le fichier `.streamlit/config.toml`.

## Règles attendues
- Les versions dans `requirements-dashboard.txt` ne doivent pas entrer en conflit avec `requirements.txt` existant (pandas, numpy, PyYAML déjà présents).
- Arborescence conforme à §10.2 de la spec : `app.py`, `pages/`, `data_loader.py`, `charts.py`, `utils.py`.
- Configuration Streamlit conforme à §10.4.

## Évolutions proposées
- Créer `requirements-dashboard.txt` avec : `streamlit>=1.30`, `plotly>=5.18`, `pandas>=2.0`, `numpy>=1.24`, `PyYAML>=6.0`.
- Créer l'arborescence `scripts/dashboard/` : `app.py`, `pages/1_overview.py`, `pages/2_run_detail.py`, `pages/3_comparison.py`, `pages/4_fold_analysis.py`, `data_loader.py`, `charts.py`, `utils.py`.
- Créer `.streamlit/config.toml` conforme à §10.4.
- Vérifier l'absence de conflits de versions avec `requirements.txt`.

## Critères d'acceptation
- [x] `requirements-dashboard.txt` existe avec versions conformes à Annexe C.
- [x] Arborescence `scripts/dashboard/` créée avec tous les fichiers (cf. §10.2).
- [x] `scripts/dashboard/pages/` contient les 4 fichiers de pages.
- [x] `.streamlit/config.toml` conforme à §10.4.
- [x] `pip install -r requirements-dashboard.txt` passe sans conflit avec les dépendances existantes.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/073-wsd1-project-structure-deps` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/073-wsd1-project-structure-deps` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-D-1] #073 RED: tests structure projet et dépendances dashboard` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-D-1] #073 GREEN: structure projet et dépendances dashboard`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-1] #073 — Structure projet et dépendances dashboard`.
