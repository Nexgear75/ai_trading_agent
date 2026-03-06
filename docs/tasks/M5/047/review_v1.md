# Revue PR — [WS-11] #047 — Validation des schémas JSON

Branche : `task/047-json-schema-validation`
Tâche : `docs/tasks/M5/047__ws11_json_schema_validation.md`
Date : 2026-03-03

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Implémentation propre et minimaliste du module `ai_trading/artifacts/validation.py` pour la validation JSON Schema Draft 2020-12 de `manifest.json` et `metrics.json`. Le code est bien structuré, les 31 tests couvrent tous les critères d'acceptation (nominaux, erreurs de type, champs manquants, enums invalides, bords). Deux items mineurs identifiés : checklist de tâche incomplète et absence d'encodage explicite UTF-8 sur les `open()`.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/047-json-schema-validation` | ✅ | `git branch` : `task/047-json-schema-validation` |
| Commit RED présent | ✅ | `04ff849 [WS-11] #047 RED: tests validation schémas JSON` — `git show --stat` : 1 fichier `tests/test_json_schema_validation.py` (280 insertions) |
| Commit GREEN présent | ✅ | `e2c5496 [WS-11] #047 GREEN: validation schémas JSON manifest/metrics (Draft 2020-12)` — 4 fichiers (impl + init + tâche + tests ajustés) |
| Commit RED contient uniquement des tests | ✅ | `git show --stat 04ff849` : seul `tests/test_json_schema_validation.py` |
| Commit GREEN contient implémentation + tâche | ✅ | `git show --stat e2c5496` : `validation.py`, `__init__.py`, tâche .md, tests .py |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1..HEAD` : 2 commits uniquement (RED + GREEN) |

### Tâche

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | Diff : `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (9/9) | Diff : toutes les 9 lignes `- [x]` |
| Checklist cochée | ⚠️ (7/9) | 2 items non cochés : « Commit GREEN » et « PR ouverte » — voir remarque #1 |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1364 passed**, 0 failed |
| `pytest tests/test_json_schema_validation.py -v` | **31 passed**, 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** |

Phase A : **PASS** — on continue en Phase B.

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux | `grep 'or []\|or {}\|or ""\|if.*else'` | 0 occurrences (grep exécuté) |
| §R1 Except trop large | `grep 'except:$\|except Exception:'` | 0 occurrences (grep exécuté) |
| §R7 noqa | `grep 'noqa'` | 0 occurrences (grep exécuté) |
| §R7 per-file-ignores | `grep 'per-file-ignores' pyproject.toml` | 1 match ligne 51 — existant, non lié à cette PR |
| §R7 Print résiduel | `grep 'print('` | 0 occurrences (grep exécuté) |
| §R3 Shift négatif | `grep '.shift(-'` | 0 occurrences (grep exécuté) |
| §R4 Legacy random API | `grep 'np.random.seed\|RandomState\|random.seed'` | 0 occurrences (grep exécuté) |
| §R7 TODO/FIXME orphelins | `grep 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences (grep exécuté) |
| §R7 Chemins hardcodés (tests) | `grep '/tmp\|C:\\'` | 0 occurrences (grep exécuté) |
| §R7 Imports absolus __init__ | `grep 'from ai_trading\.'` dans `__init__.py` | 0 occurrences — imports relatifs utilisés (`from .validation`) |
| §R7 Registration manuelle tests | `grep 'register_model\|register_feature'` | 0 occurrences (N/A pour ce module) |
| §R6 Mutable defaults | `grep 'def.*=[]\|def.*={}'` | 0 occurrences (grep exécuté) |
| §R6 open() sans context manager | `grep 'open('` | 3 matches — tous dans `with` blocks ✅ |
| §R6 Bool identity | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences (grep exécuté) |
| §R9 for range (vectorisation) | `grep 'for.*in range(.*):' ` | 0 occurrences (grep exécuté) |
| §R6 isfinite | `grep 'isfinite'` | 0 occurrences (N/A — pas de validation de bornes numériques dans ce module) |
| §R9 np comprehension | `grep 'np\.[a-z]*(.*for.*in'` | 0 occurrences (grep exécuté) |
| §R7 Fixture dupliquée | `grep 'load_config.*configs/'` | 0 occurrences (grep exécuté) |
| §R6 Dict collision | `grep '\[.*\] = .*'` | 0 occurrences (grep exécuté) |

### Annotations par fichier (B2)

#### `ai_trading/artifacts/validation.py` (77 lignes — diff entier lu)

- **L13** `_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent` : Résolution robuste du root projet en remontant 3 niveaux (`ai_trading/artifacts/validation.py`). Cohérent avec d'autres modules du projet.
  Sévérité : RAS

- **L14** `_SCHEMAS_DIR = _PROJECT_ROOT / "docs" / "specifications"` : Chemin relatif à la racine du projet, conforme à la tâche (« résolu de manière robuste »).
  Sévérité : RAS

- **L36-41** `_load_schema` : Validation `schema_path.is_file()` avant lecture + `FileNotFoundError` explicite. Conforme §R1 strict code.
  Sévérité : RAS

- **L40** `with open(schema_path) as f:` : Pas d'encodage explicite. `json.load()` sur un fichier texte ouvert sans `encoding="utf-8"` pourrait poser un problème de portabilité sur des systèmes avec locale non-UTF-8. Même observation sur les fixtures de test L33 et L41.
  Sévérité : MINEUR
  Suggestion : `with open(schema_path, encoding="utf-8") as f:`

- **L45-57** `_validate()` : Création du `Draft202012Validator` à chaque appel (pas de cache). Acceptable car la validation n'est appelée qu'une fois par run. L'exception `ValidationError` de jsonschema est propagée directement — conforme strict code.
  Sévérité : RAS

- **L60-77** `validate_manifest()` / `validate_metrics()` : Wrappers minimalistes. Pas de fallback, pas de catch silencieux. Conforme.
  Sévérité : RAS

#### `ai_trading/artifacts/__init__.py` (diff : +6 lignes)

- **L19-22** `from .validation import (validate_manifest, validate_metrics)` : Import relatif ✅. Ajout dans `__all__` en ordre alphabétique ✅.
  Sévérité : RAS après lecture complète du diff (6 lignes).

#### `tests/test_json_schema_validation.py` (281 lignes — diff entier lu)

- **L1-6** Docstring avec `#047` (WS-11) : Conforme convention d'ID de tâche dans docstring.
  Sévérité : RAS

- **L21** `PROJECT_ROOT = Path(__file__).resolve().parent.parent` : Même pattern que le source. Cohérent.
  Sévérité : RAS

- **L31-42** Fixtures `example_manifest` / `example_metrics` : Chargent des fichiers réels depuis `docs/specifications/`. Pas de dépendance réseau. `with open()` utilisé correctement.
  Sévérité : RAS (même remarque MINEUR sur encoding UTF-8 que ci-dessus)

- **L51-68** `TestModuleImportable` : 3 tests `callable()` pour les 3 fonctions publiques.
  Sévérité : RAS

- **L75-89** `TestLoadSchema` : Teste chargement manifest, metrics, et fichier inexistant. Vérifie `$schema` Draft 2020-12 + `properties`.
  Sévérité : RAS

- **L96-103** `TestNominalValidation` : Valide exemples sans erreur.
  Sévérité : RAS

- **L110-121** `TestDraft202012` : Vérifie la propriété `$schema` dans les fichiers de schéma. Redondant avec `TestLoadSchema` mais acceptable.
  Sévérité : RAS

- **L128-157** `TestMissingRequiredField` : 5 tests (manifest run_id, dataset, metrics run_id, folds, nested exchange). Vérifie `match="<field>"`. Bonne couverture incluant champs imbriqués.
  Sévérité : RAS

- **L164-185** `TestIncorrectType` : 4 tests (string→int, array→string, int→string, int→float).
  Sévérité : RAS

- **L192-224** `TestEnumViolation` : 5 tests (exchange, strategy_type×2, cost_model, threshold method).
  Sévérité : RAS

- **L231-281** `TestEdgeCases` : 7 tests — empty dict, additional properties, empty arrays, negative horizon. Bonne couverture des bords.
  Sévérité : RAS

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_json_schema_validation.py` — cohérent avec le plan |
| ID tâche #047 dans docstrings | ✅ | `"""Tests for JSON schema validation — Task #047 (WS-11)."""` + docstrings de classes |
| Couverture des critères d'acceptation | ✅ | Mapping : AC1→`TestModuleImportable`, AC2→`TestNominalValidation`, AC3→`TestMissingRequiredField`, AC4→`TestIncorrectType`, AC5→`TestEnumViolation`, AC6→`TestDraft202012`, AC7→`TestEdgeCases` (nominaux+erreurs+bords), AC8→1364 passed, AC9→ruff clean |
| Cas nominaux + erreurs + bords | ✅ | Nominaux: 2, Erreurs: 14 (missing field, type, enum), Bords: 7 |
| Boundary fuzzing numérique | ✅ (limité) | `horizon_H_bars = 0` testé. Pas de paramètre numérique dans le code source, la validation est entièrement déléguée au schéma JSON |
| Tests déterministes | ✅ | Pas d'aléatoire — tests purement déterministes |
| Données synthétiques | ✅ | Fichiers locaux `docs/specifications/example_*.json` — pas de réseau |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé |
| Tests registre réalistes | N/A | Pas de registre dans ce module |
| Contrat ABC complet | N/A | Pas d'ABC dans ce module |
| Tests désactivés (skip/xfail) | ✅ | 0 test désactivé |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback. `FileNotFoundError` explicite L38-40. `ValidationError` propagée sans catch |
| §R10 Defensive indexing | N/A | Pas d'indexation/slicing numérique dans ce module |
| §R2 Config-driven | N/A | Module de validation — pas de paramètres configurables (les schémas sont des artefacts de spécification, pas de la config runtime) |
| §R3 Anti-fuite | N/A | Pas de données temporelles dans ce module |
| §R4 Reproductibilité | N/A | Pas d'aléatoire dans ce module. Scan B1 : 0 legacy random |
| §R5 Float conventions | N/A | Pas de calculs numériques dans ce module |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable default, 0 bool identity, 3 `open()` tous dans `with`. Pas de `json.loads()` suivi d'accès non validé — les données sont validées par le schéma JSON lui-même. |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `_load_schema`, `_validate`, `validate_manifest`, `validate_metrics` |
| Pas de code mort/debug | ✅ | Scan B1 : 0 `print()`, 0 `TODO`/`FIXME` |
| Imports propres / relatifs | ✅ | `__init__.py` : imports relatifs (`from .validation`). Scan B1 : 0 `from ai_trading.` dans `__init__.py`. Pas d'imports `*` |
| DRY | ✅ | `_validate()` factorise la logique commune. `_load_schema()` factorise le chargement |
| `__init__.py` à jour | ✅ | `validate_manifest`, `validate_metrics` ajoutés dans `__init__.py` + `__all__` |
| Variables mortes | ✅ | Aucune variable assignée non utilisée |
| Fichiers générés | ✅ | Aucun fichier généré/temporaire dans la PR |
| Suppressions lint | ✅ | Scan B1 : 0 `noqa` |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Preuve |
|---|---|---|
| Spécification (§15.4) | ✅ | Module `validation.py` valide manifest et metrics contre leurs schémas JSON Draft 2020-12, conforme au plan WS-11.4 |
| Plan d'implémentation | ✅ | WS-11.4 : « Validation JSON Schema des artefacts manifest/metrics » — implémenté |
| Formules doc vs code | N/A | Pas de formules mathématiques dans cette tâche |
| Exigences inventées | ✅ | Aucune exigence ajoutée hors spec/plan |

### Cohérence intermodule (B7)

| Critère | Verdict | Preuve |
|---|---|---|
| Signatures et types de retour | ✅ | `validate_manifest(data: dict) -> None`, `validate_metrics(data: dict) -> None` — conformes à la tâche. Lèvent `ValidationError` documenté |
| Clés de configuration | N/A | Pas de config lue |
| Registres et conventions partagées | N/A | |
| Structures partagées | ✅ | Les schémas validés correspondent aux structures produites par `build_manifest()` et `build_metrics()` (tâches 045, 046) |
| Imports croisés | ✅ | Seul import local : `from jsonschema import Draft202012Validator`. `jsonschema>=4.17` est dans `requirements.txt` et `pyproject.toml` |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts | N/A | Module utilitaire de validation, pas de calcul métier |
| Nommage métier cohérent | ✅ | `validate_manifest`, `validate_metrics` — clairs |
| Séparation des responsabilités | ✅ | Validation séparée de la construction (manifest.py, metrics_builder.py) |
| Invariants de domaine | N/A | |
| Cohérence des unités/échelles | N/A | |
| Patterns de calcul financier | N/A | |

---

## Remarques

1. **[MINEUR]** Checklist de tâche incomplète : les items « Commit GREEN » et « PR ouverte » sont non cochés (`[ ]`) alors que le commit GREEN `e2c5496` existe bien.
   - Fichier : `docs/tasks/M5/047__ws11_json_schema_validation.md`
   - Ligne(s) : dernières lignes de la checklist
   - Suggestion : cocher `[x]` pour « Commit GREEN » (le commit existe). L'item « PR ouverte » peut rester `[ ]` si la PR n'est pas encore créée.

2. **[MINEUR]** `open()` sans encodage explicite UTF-8 : les appels `open(schema_path)` dans `validation.py` L40 et dans les fixtures de test L33/L41 n'utilisent pas `encoding="utf-8"`. Sur un système avec locale non-UTF-8, cela pourrait causer des problèmes de lecture de fichiers JSON.
   - Fichier : `ai_trading/artifacts/validation.py` L40, `tests/test_json_schema_validation.py` L33, L41
   - Suggestion : `with open(path, encoding="utf-8") as f:`

---

## Résumé

Le code est propre, minimaliste et bien testé (31 tests, 100% des critères d'acceptation couverts). Aucun problème bloquant ni warning identifié. Deux items mineurs empêchent le verdict CLEAN : checklist de tâche incomplète et absence d'encodage UTF-8 explicite sur les `open()`.
