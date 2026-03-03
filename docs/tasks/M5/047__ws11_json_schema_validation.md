# Tâche — Validation des schémas JSON

Statut : DONE
Ordre : 047
Workstream : WS-11
Milestone : M5
Gate lié : M5

## Contexte
Les fichiers `manifest.json` et `metrics.json` doivent être validés contre leurs JSON Schemas respectifs (Draft 2020-12) à chaque fin de run. Ce module fournit les fonctions de validation et est appelé systématiquement par l'orchestrateur.

Références :
- Plan : `docs/plan/implementation.md` (WS-11.4)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§15.4)
- Schémas : `docs/specifications/manifest.schema.json`, `docs/specifications/metrics.schema.json`
- Exemples : `docs/specifications/example_manifest.json`, `docs/specifications/example_metrics.json`
- Code : `ai_trading/artifacts/validation.py`

Dépendances :
- Tâche 045 — Manifest builder (doit être DONE)
- Tâche 046 — Metrics builder (doit être DONE)

## Objectif
Implémenter le module `ai_trading/artifacts/validation.py` avec :
1. `validate_manifest(data: dict) -> None` : valide un dictionnaire contre `manifest.schema.json`. Lève une erreur explicite si invalide.
2. `validate_metrics(data: dict) -> None` : valide un dictionnaire contre `metrics.schema.json`. Lève une erreur explicite si invalide.

Les schémas JSON sont chargés depuis `docs/specifications/manifest.schema.json` et `docs/specifications/metrics.schema.json`.

## Règles attendues
- Strict code : erreur explicite (`raise`) si la validation échoue — pas de passage silencieux.
- Utiliser `jsonschema` avec Draft 2020-12.
- Le chemin vers les fichiers de schéma doit être résolu de manière robuste (relatif à la racine du projet, pas hardcodé en absolu).
- Appelé systématiquement par l'orchestrateur en fin de run.

## Évolutions proposées
- Fonction `validate_manifest(data: dict) -> None`.
- Fonction `validate_metrics(data: dict) -> None`.
- Fonction utilitaire `_load_schema(schema_name: str) -> dict` pour charger les schémas JSON.

## Critères d'acceptation
- [x] Le module `ai_trading/artifacts/validation.py` existe et est importable.
- [x] Les exemples fournis (`example_manifest.json`, `example_metrics.json`) passent la validation sans erreur.
- [x] Tests de violation : un champ requis manquant → erreur explicite avec message clair.
- [x] Tests de violation : un type incorrect → erreur explicite.
- [x] Tests de violation : une valeur hors enum → erreur explicite.
- [x] La validation utilise Draft 2020-12 de JSON Schema.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/047-json-schema-validation` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/047-json-schema-validation` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-11] #047 RED: tests validation schémas JSON`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-11] #047 GREEN: validation schémas JSON`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-11] #047 — Validation des schémas JSON`.
