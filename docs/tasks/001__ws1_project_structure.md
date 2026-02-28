# Tâche — Structure du projet, dépendances et logging

Statut : DONE
Ordre : 001
Workstream : WS-1
Milestone : M1
Gate lié : M1

## Contexte
Le pipeline AI Trading nécessite une structure de projet Python correctement initialisée avec toutes les dépendances, un versionnement cohérent et un système de logging configurable en deux phases.

L'arborescence `ai_trading/`, le `pyproject.toml`, `requirements.txt` et `requirements-dev.txt` existent déjà. Cette tâche se concentre sur la **complétion** : vérification de conformité de l'existant et implémentation du **logging en deux phases** qui est le livrable principal manquant.

Références :
- Plan : `docs/plan/implementation.md` (WS-1.1)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§1, §16, §17.1, §17.7)
- Code : `ai_trading/__init__.py`, `ai_trading/utils/`

Dépendances :
- Aucune

## Objectif
Compléter la structure du projet avec le module de logging configurable en deux phases :
1. **Phase 1 (démarrage)** : logging vers stdout uniquement (le `run_dir` n'existe pas encore).
2. **Phase 2 (post run_dir)** : ajout dynamique d'un `FileHandler` vers `run_dir/pipeline.log` si `config.logging.file` est spécifié (`"pipeline.log"` par défaut, `null` = stdout only).

## Règles attendues
- Config-driven : le niveau de log, le format (text/JSON) et le fichier de sortie sont lus depuis `config.logging` (level, format, file).
- Strict code : pas de fallback silencieux ; si le format est invalide → erreur explicite.
- Messages clés en INFO (§17.7) : début/fin de chaque étape, nombre de samples par split par fold, seuil θ retenu, chemin du `run_dir`.
- Le niveau DEBUG ajoute shapes des tenseurs, durée de chaque étape, loss par epoch.

## Évolutions proposées
- Créer `ai_trading/utils/logging.py` avec une fonction `setup_logging(level, fmt, file)` pour la phase 1 (stdout).
- Ajouter une fonction `add_file_handler(run_dir, filename)` pour la phase 2 (appelée par l'orchestrateur WS-12.2).
- Vérifier que `ai_trading.__version__` retourne `"1.0.0"`.
- Vérifier que `pip install -e .` fonctionne.
- Vérifier que `requirements.txt` contient toutes les dépendances runtime (pandas, numpy, PyYAML, pydantic>=2.0, jsonschema, xgboost, torch, scikit-learn, scipy, ccxt, pyarrow).
- Vérifier que `requirements-dev.txt` inclut pytest, ruff, mypy.

## Critères d'acceptation
- [x] `pip install -e .` réussit sans erreur
- [x] `import ai_trading` fonctionne et `ai_trading.__version__` retourne `"1.0.0"`
- [x] `ruff check ai_trading/ tests/` passe sans erreur
- [x] Module `ai_trading/utils/logging.py` implémenté avec `setup_logging()` et `add_file_handler()`
- [x] `setup_logging()` configure le logging vers stdout avec le niveau et le format spécifiés
- [x] `add_file_handler()` ajoute dynamiquement un handler fichier vers le chemin donné
- [x] Format text et JSON supportés ; format inconnu → erreur explicite (`ValueError`)
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/001-project-structure` depuis `main`.

## Checklist de fin de tâche
- [x] Branche `task/001-project-structure` créée depuis `main`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-1] #001 RED: tests logging setup deux phases`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-1] #001 GREEN: logging setup deux phases`.
- [x] **Pull Request ouverte** vers `main` : `[WS-1] #001 — Structure du projet et logging`.
