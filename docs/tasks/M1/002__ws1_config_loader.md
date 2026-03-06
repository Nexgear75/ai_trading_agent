# Tâche — Config loader (YAML → Pydantic v2 model)

Statut : DONE
Ordre : 002
Workstream : WS-1
Milestone : M1
Gate lié : M1

## Contexte
Le pipeline AI Trading est piloté par une configuration YAML unique (`configs/default.yaml`). Un config loader robuste est nécessaire pour charger, fusionner et typer cette configuration à travers un modèle Pydantic v2, garantissant l'accès par attribut et la validation automatique des types.

Références :
- Plan : `docs/plan/implementation.md` (WS-1.2)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (Annexe E.1, §17.5)
- Code : `ai_trading/` (module `config.py` à créer)
- Config : `configs/default.yaml`

Dépendances :
- Tâche 001 — Structure du projet et logging (doit être DONE)

## Objectif
Implémenter un module `ai_trading/config.py` qui :
1. Charge `configs/default.yaml` (ou un fichier YAML passé en argument).
2. Fusionne avec des overrides CLI en dot notation (`--set key.subkey=value`).
3. Retourne une instance Pydantic v2 (`BaseModel`) avec tous les champs accessibles par attribut.

## Règles attendues
- Config-driven : tous les paramètres de `configs/default.yaml` sont modélisés dans le schéma Pydantic.
- Strict code : erreur explicite si le fichier YAML n'existe pas, si le parsing échoue, ou si un chemin dot notation ne correspond à aucun champ du schéma.
- Pas de valeur par défaut implicite dans le code : tous les defaults sont dans le fichier YAML.
- Rejet des clés inconnues : `model_config = ConfigDict(extra="forbid")` sur tous les sous-modèles Pydantic.

## Évolutions proposées
- Créer `ai_trading/config.py` avec :
  - Des sous-modèles Pydantic v2 pour chaque section YAML : `LoggingConfig`, `DatasetConfig`, `LabelConfig`, `WindowConfig`, `FeaturesConfig`, `FeaturesParamsConfig`, `SplitsConfig`, `ScalingConfig`, `StrategyConfig`, `ThresholdingConfig`, `CostsConfig`, `BacktestConfig`, `BaselinesConfig`, `SmaConfig`, `TrainingConfig`, `ModelsConfig` (et sous-modèles par modèle), `MetricsConfig`, `ReproducibilityConfig`, `ArtifactsConfig`.
  - Un modèle racine `PipelineConfig` agrégeant toutes les sections.
  - Une fonction `load_config(yaml_path: str, overrides: list[str] | None = None) -> PipelineConfig`.
  - Le mécanisme d'override CLI applique la dot notation : parcourt la config imbriquée et remplace la valeur au chemin spécifié.
- Chaque sous-modèle utilise `ConfigDict(extra="forbid")`.

## Critères d'acceptation
- [x] `load_config("configs/default.yaml")` retourne une instance `PipelineConfig` valide
- [x] Tous les champs de `configs/default.yaml` sont accessibles par attribut (ex: `config.dataset.symbols`, `config.splits.embargo_bars`)
- [x] Override par fichier custom : un YAML partiel surcharge les valeurs du défaut
- [x] Override CLI dot notation : `--set splits.train_days=240` modifie la valeur correspondante
- [x] Erreur explicite si le chemin dot notation n'existe pas dans le schéma
- [x] Erreur explicite si le fichier YAML n'existe pas (`FileNotFoundError`)
- [x] Erreur explicite si une clé YAML inconnue est présente (`extra="forbid"`)
- [x] Types automatiquement validés par Pydantic (ex: `embargo_bars` reçoit un string → erreur)
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/002-config-loader` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/002-config-loader` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-1] #002 RED: tests config loader Pydantic v2`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-1] #002 GREEN: config loader Pydantic v2`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-1] #002 — Config loader Pydantic v2`.
