# Tâche — CLI entry point

Statut : DONE
Ordre : 050
Workstream : WS-12
Milestone : M5
Gate lié : M5

## Contexte
Le point d'entrée CLI permet de lancer le pipeline via `python -m ai_trading`. Il expose les sous-commandes `run` (pipeline complet), `fetch` (ingestion OHLCV seulement) et `qa` (contrôles qualité). Les arguments incluent `--config`, `--strategy`, `--output-dir` et les overrides `--set key=value`.

Références :
- Plan : `docs/plan/implementation.md` (WS-12.3)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§16.2, §17.5)
- Code : `ai_trading/__main__.py`

Dépendances :
- Tâche 049 — Orchestrateur runner (doit être DONE)

## Objectif
Implémenter le CLI dans `ai_trading/__main__.py` avec :

1. **Sous-commande `run`** (par défaut) : lance le pipeline complet via `run_pipeline()`.
2. **Sous-commande `fetch`** : lance l'ingestion OHLCV uniquement.
3. **Sous-commande `qa`** : lance les contrôles qualité sur les données brutes.
4. **Arguments communs** :
   - `--config` : chemin vers le fichier de configuration YAML (défaut : `configs/default.yaml`).
   - `--strategy` : surcharge de `strategy.name`.
   - `--output-dir` : surcharge de `artifacts.output_dir`.
   - `--set key=value` : overrides arbitraires (multi-valués).
5. **Logging** : niveau INFO par défaut, setup phase 1 au démarrage.
6. **Help** : `--help` affiche une aide lisible pour chaque sous-commande.

## Règles attendues
- Config-driven : les overrides CLI surchargent les valeurs de la config (priorité CLI > YAML).
- Strict code : erreur explicite si le fichier de config n'existe pas, si une clé `--set` est invalide.
- Le `__main__.py` existant est un placeholder — le remplacer par l'implémentation complète.

## Évolutions proposées
- Utiliser `argparse` pour le parsing CLI (sous-commandes, arguments, `--set`).
- Fonction `main()` comme point d'entrée unique.
- Intégration avec `setup_logging()` (phase 1) au démarrage.

## Critères d'acceptation
- [x] `python -m ai_trading --help` affiche l'aide générale avec les sous-commandes.
- [x] `python -m ai_trading run --config configs/default.yaml` lance le pipeline complet (via l'orchestrateur).
- [x] `python -m ai_trading fetch --config configs/default.yaml` lance l'ingestion uniquement.
- [x] `python -m ai_trading qa --config configs/default.yaml` lance le QA uniquement.
- [x] `--set strategy.name=dummy` surcharge correctement la config.
- [x] `--strategy dummy` est un raccourci pour `--set strategy.name=dummy`.
- [x] Erreur explicite si `--config` pointe vers un fichier inexistant.
- [x] Le logging phase 1 est configuré au démarrage (INFO par défaut).
- [x] Tests couvrent les scénarios nominaux + erreurs + bords (fichier absent, sous-commande invalide).
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/050-cli-entry-point` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/050-cli-entry-point` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-12] #050 RED: tests CLI entry point`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-12] #050 GREEN: CLI entry point`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-12] #050 — CLI entry point`.
