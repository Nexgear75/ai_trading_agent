# Revue PR — [WS-11] #045 — Manifest builder

Branche : `task/045-manifest-builder`
Tâche : `docs/tasks/M5/045__ws11_manifest_builder.md`
Date : 2026-03-03
Itération : v1

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Implémentation propre et bien testée du module `manifest.py` qui construit et sérialise le `manifest.json`. Le code est conforme au schéma JSON, les GREP scans sont tous clean, et les 1284 tests passent. Deux items mineurs identifiés : checklist de tâche incomplète et absence de mise à jour du `__init__.py` du package `artifacts`.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/045-manifest-builder` | ✅ | `git branch --show-current` → `task/045-manifest-builder` |
| Commit RED `[WS-11] #045 RED: tests manifest builder` | ✅ | `e8f1a7f` — `git show --stat` : 1 fichier (tests/test_manifest_builder.py, +556) |
| Commit RED contient uniquement des tests | ✅ | `git show --stat e8f1a7f` : 1 seul fichier `tests/test_manifest_builder.py` |
| Commit GREEN `[WS-11] #045 GREEN: manifest builder` | ✅ | `d8622ac` — `git show --stat` : 3 fichiers (manifest.py +197, tâche +36/-22, tests +6/-6) |
| Commit GREEN contient implémentation + tâche | ✅ | `ai_trading/artifacts/manifest.py`, `docs/tasks/M5/045__ws11_manifest_builder.md`, `tests/test_manifest_builder.py` |
| Pas de commits parasites entre RED et GREEN | ✅ | `git log --oneline Max6000i1...HEAD` : exactement 2 commits (RED puis GREEN) |

### Tâche

| Critère | Verdict | Détail |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` en en-tête |
| Critères d'acceptation cochés | ✅ (10/10) | Tous `[x]` |
| Checklist cochée | ❌ (7/9) | 2 items restants `[ ]` : « Commit GREEN » et « Pull Request ouverte » |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1284 passed**, 0 failed (7.36s) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

> Phase A : PASS (CI OK, structure TDD conforme). Item MINEUR identifié sur la checklist.

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

| §Rule | Pattern recherché | Fichiers scannés | Résultat |
|---|---|---|---|
| §R1 | Fallbacks silencieux (`or []`, `or {}`, `or ""`, `if..else`) | `manifest.py` | 0 occurrences |
| §R1 | Except trop large (`except:$`, `except Exception:`) | `manifest.py` | 0 occurrences |
| §R7 | Suppressions lint (`noqa`) | `manifest.py`, `test_manifest_builder.py` | 0 occurrences |
| §R7 | Print résiduel | `manifest.py` | 0 occurrences |
| §R3 | Shift négatif (`.shift(-`) | `manifest.py` | 0 occurrences |
| §R4 | Legacy random API | `manifest.py`, `test_manifest_builder.py` | 0 occurrences |
| §R7 | TODO/FIXME/HACK/XXX | `manifest.py`, `test_manifest_builder.py` | 0 occurrences |
| §R7 | Chemins hardcodés (`/tmp`, `C:\\`) | `test_manifest_builder.py` | 0 occurrences |
| §R7 | Imports absolus `__init__.py` | `ai_trading/artifacts/__init__.py` | 0 occurrences |
| §R7 | Registration manuelle tests | `test_manifest_builder.py` | 0 occurrences |
| §R6 | Mutable default arguments | `manifest.py`, `test_manifest_builder.py` | 0 occurrences |
| §R6 | `open()` sans context manager | `manifest.py` | 0 occurrences (utilise `Path.write_text()`) |
| §R6 | Comparaison booléenne par identité | `manifest.py`, `test_manifest_builder.py` | 0 occurrences |
| §R6 | Dict collision silencieuse | `manifest.py` | 0 occurrences |
| §R9 | Boucle Python sur array numpy | `manifest.py` | 0 occurrences |
| §R6 | `isfinite` check | `manifest.py` | 0 occurrences (N/A — pas de paramètres numériques à borner) |
| §R9 | Appels numpy dans compréhension | `manifest.py` | 0 occurrences |
| §R7 | Fixtures dupliquées (`load_config`) | `test_manifest_builder.py` | 0 occurrences |
| §R7 | `per-file-ignores` ajoutés | `pyproject.toml` | Aucun ajout lié à cette PR |

> Tous les scans GREP sont **clean**. Aucun faux positif à analyser.

### B2. Annotations par fichier

#### `ai_trading/artifacts/manifest.py` (197 lignes ajoutées)

- **L25-35** `STRATEGY_FRAMEWORK_MAP` : mapping interne conforme à la tâche. Couvre les 10 stratégies MVP (dummy, xgboost_reg, cnn1d_reg, gru_reg, lstm_reg, patchtst_reg, rl_ppo, no_trade, buy_hold, sma_rule). Non lu depuis config YAML. ✅

- **L38** `get_git_commit(working_dir: Path | None = None)` : le paramètre `working_dir=None` est un default utilitaire documenté (= cwd), pas un fallback silencieux. La fonction est appelée par l'orchestrateur futur qui fournira le chemin. ✅

- **L56-67** `subprocess.run(["git", "rev-parse", "HEAD"], ...)` : utilise une liste (pas `shell=True`) → pas de risque d'injection. `check=True` + except ciblé (`CalledProcessError`, `FileNotFoundError`). Le cas `"unknown"` est documenté dans la tâche et loggé au WARNING. ✅

- **L77-87** `build_manifest(*, ...)` : tous les paramètres sont keyword-only, aucun default. Les 14 paramètres sont obligatoires. Conformité §R1 strict-no-fallback. ✅

- **L133-137** Validation explicite `run_id`, `git_commit`, `pipeline_version` : `if not run_id: raise ValueError(...)`. Pas de fallback silencieux. ✅

- **L139-144** Validation `strategy_name` dans `STRATEGY_FRAMEWORK_MAP` : message d'erreur explicite avec la liste des stratégies connues. ✅

- **L150-160** Construction `strategy_section` : `hyperparams` et `thresholding` sont conditionnellement inclus (`if key in dict`). Ce n'est PAS un fallback — le schéma JSON déclare ces propriétés comme optionnelles (`additionalProperties: false` sans les lister dans `required`). Le code reflète correctement le schéma. ✅

- **L163** `datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")` : format ISO 8601 avec suffixe `Z` littéral. Conforme au `"format": "date-time"` du schéma. Non-déterministe (timestamp courant) — acceptable pour un champ metadata de run. ✅

- **L179-189** `write_manifest` : `run_dir.mkdir(parents=True, exist_ok=True)` avant écriture → conforme §R6 path creation. `Path.write_text()` avec `encoding="utf-8"` OK. JSON indenté avec newline finale. ✅

> RAS. Lecture complète du diff (197 lignes). Aucune anomalie détectée dans le code source.

#### `tests/test_manifest_builder.py` (556 lignes RED + 6 lignes modifiées GREEN)

- **L27-30** `SCHEMA_PATH` : chemin construit avec `Path(__file__).resolve().parent.parent / "docs" / ...`. Chemin relatif au fichier de test, portable. ✅

- **L184-202** `_build_minimal_manifest(**overrides)` : helper bien structuré. Les overrides permettent de tester chaque variante sans dupliquer le setup. ✅

- **L213-228** `TestModuleImportable` : vérifie AC-1 (importabilité des 4 symboles publics). ✅

- **L234-267** `TestSchemaValidation` : vérifie AC-2 via `jsonschema.validate()`. Cas nominal, avec pipeline_log, multi-fold. ✅

- **L273-280** `TestTrainExcludesVal` : vérifie AC-3 (train.end_utc < val.start_utc). Assertion avec message d'erreur explicite. ✅

- **L286-326** `TestGitCommit` : vérifie AC-4 (hex hash + unknown). `test_get_git_commit_returns_unknown_outside_repo` utilise `tmp_path` et vérifie le WARNING dans caplog. ✅

- **L332-345** `TestPipelineVersion` : vérifie AC-5. ✅

- **L351-366** `TestPipelineLogConditional` : vérifie AC-6 (absent si non fourni, présent si fourni). ✅

- **L372-414** `TestStrategyFrameworkMap` : vérifie AC-7. Parametrize sur les 10 stratégies MVP. `test_unknown_strategy_raises` couvre le cas d'erreur. ✅

- **L420-462** `TestBuildManifestStructure` : cas nominaux — clés requises, passthrough des sections. ✅

- **L468-501** `TestWriteManifest` : I/O tests avec `tmp_path`. Vérifie écriture, validation schema du fichier écrit, création du répertoire parent, et indentation. ✅

- **L507-549** `TestBuildManifestErrors` : cas d'erreur — missing required param (TypeError), empty values (ValueError). ✅

- **L526** `build_manifest(  # type: ignore[call-arg]` : justifié — teste volontairement l'appel avec paramètre manquant. ✅

> RAS après lecture complète du diff tests (562 lignes). Tests solides et complets.

#### `docs/tasks/M5/045__ws11_manifest_builder.md`

- Statut DONE, 10 critères d'acceptation cochés. ✅
- Checklist : 7/9 cochés. Les 2 items restants (`Commit GREEN`, `Pull Request ouverte`) sont des actions post-commit qui ne peuvent structurellement pas être cochées au moment du GREEN commit. Néanmoins, le commit GREEN est maintenant fait et devrait être marqué `[x]`. Sévérité : MINEUR.

### B3. Vérification des tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage (`test_manifest_builder.py`) | ✅ | Fichier unique, bien nommé |
| Docstrings avec `#045` | ✅ | Module docstring + classes docstrings |
| Couverture des critères d'acceptation (AC-1 à AC-10) | ✅ | Chaque AC couvert par une classe de tests dédiée |
| Cas nominaux | ✅ | `TestBuildManifestStructure`, `TestSchemaValidation` |
| Cas d'erreur | ✅ | `TestBuildManifestErrors` (missing param, empty values, unknown strategy) |
| Cas de bords | ✅ | git absent, pipeline_log conditionnel, multi-fold |
| Pas de `@pytest.mark.skip` / `xfail` | ✅ | grep : 0 occurrences |
| Tests déterministes | ✅ | Pas d'aléatoire |
| Données synthétiques (pas réseau) | ✅ | Toutes les données sont construites en mémoire |
| Portabilité des chemins (`tmp_path`) | ✅ | Grep : 0 chemins hardcodés |

### B4. Audit du code — Règles non négociables

#### B4a. Strict code (§R1)
- ✅ Aucun fallback silencieux (grep : 0 occurrences).
- ✅ Except ciblé (`CalledProcessError`, `FileNotFoundError`) — exception documentée dans la tâche.
- ✅ Tous les paramètres de `build_manifest` sont keyword-only sans defaults.
- ✅ Validation explicite + `raise ValueError` pour `run_id`, `git_commit`, `pipeline_version`, `strategy_name`.

#### B4a-bis. Defensive indexing (§R10)
- ✅ N/A — pas d'indexation array/slice dans ce module.

#### B4b. Config-driven (§R2)
- ✅ N/A — ce module reçoit la config en entrée (passthrough), ne lit pas le YAML directement.
- ✅ `STRATEGY_FRAMEWORK_MAP` est un mapping interne dérivé automatiquement, pas un paramètre config — conforme à la tâche.

#### B4c. Anti-fuite (§R3)
- ✅ N/A — pas de traitement de données temporelles.

#### B4d. Reproductibilité (§R4)
- ✅ N/A — pas d'aléatoire. `datetime.now(UTC)` est un timestamp metadata acceptable.

#### B4e. Float conventions (§R5)
- ✅ N/A — pas de tenseurs ni métriques.

#### B4f. Anti-patterns Python (§R6)
- ✅ Pas de mutable defaults (grep : 0).
- ✅ `Path.write_text()` sans `open()` explicite.
- ✅ Path creation avec `mkdir(parents=True, exist_ok=True)` avant I/O.
- ✅ Pas de comparaison booléenne par identité.
- ✅ Pas de dict collision silencieuse.

### B5. Qualité du code (§R7)

| Critère | Verdict | Preuve |
|---|---|---|
| snake_case cohérent | ✅ | Lecture diff |
| Pas de code mort / TODO | ✅ | grep : 0 occurrences |
| Pas de `print()` | ✅ | grep : 0 occurrences |
| Imports propres | ✅ | Lecture diff : stdlib → third-party → local |
| Pas de `noqa` ajouté | ✅ | grep : 0 occurrences |
| `__init__.py` à jour | ❌ | `ai_trading/artifacts/__init__.py` ne contient qu'un docstring, n'importe pas `manifest` |
| Fichiers générés/temporaires exclus | ✅ | Aucun artefact dans le diff |

### B5-bis. Bonnes pratiques métier (§R9)
- ✅ N/A — module de sérialisation, pas de calcul financier.

### B6. Cohérence avec les specs

| Critère | Verdict | Preuve |
|---|---|---|
| Conforme à la spec (§15.2, Annexe A, E.2.1) | ✅ | Manifest structure correspond au schéma `manifest.schema.json` |
| Conforme au plan (WS-11.2) | ✅ | Fonctions `build_manifest`, `write_manifest`, `get_git_commit`, `STRATEGY_FRAMEWORK_MAP` présentes |
| Pas d'exigence inventée | ✅ | Toutes les validations correspondent à des exigences de la tâche |
| Validation schema Draft 2020-12 | ✅ | Tests utilisent `jsonschema.validate()` contre le schéma officiel |
| Train exclut val (E.2.1) | ✅ | Le builder passe les splits tels quels ; le test vérifie `train.end_utc < val.start_utc` |

### B7. Cohérence intermodule (§R8)

| Critère | Verdict | Preuve |
|---|---|---|
| Signatures compatibles | ✅ | `build_manifest` utilise des dicts génériques — pas de couplage avec des dataclasses d'autres modules |
| Imports croisés | ✅ | Aucun import d'autres modules `ai_trading.*` — module autonome |
| `__version__` accessible | ✅ | `ai_trading.__init__.py` exporte `__version__ = "1.0.0"` |

---

## Remarques

1. **[MINEUR]** Checklist de tâche incomplète — item « Commit GREEN » non coché `[x]`
   - Fichier : `docs/tasks/M5/045__ws11_manifest_builder.md`
   - Ligne(s) : checklist de fin de tâche, avant-dernier item
   - Détail : le commit GREEN `d8622ac` existe mais l'item correspondant est `[ ]`. L'item « Pull Request ouverte » est `[ ]` ce qui est attendu (PR pas encore créée).
   - Suggestion : cocher `[x]` l'item commit GREEN dans un commit d'amendement.

2. **[MINEUR]** `__init__.py` du package `artifacts` ne réexporte pas les symboles de `manifest`
   - Fichier : `ai_trading/artifacts/__init__.py`
   - Ligne(s) : 1 (fichier ne contient qu'un docstring)
   - Détail : le fichier ne contient que `"""Artifacts — run directory, manifest, metrics builder, schema validation."""`. Bien que l'import direct `from ai_trading.artifacts.manifest import build_manifest` fonctionne, la convention §R7 recommande la mise à jour du `__init__.py` si un nouveau module est créé. Les modules `run_dir.py` et `manifest.py` du package ne sont pas importés.
   - Suggestion : ajouter `from . import manifest` (et `from . import run_dir` si ce n'est pas déjà fait) pour cohérence. Alternativement, si l'import via `__init__.py` n'est pas nécessaire (pas de side-effect d'enregistrement), documenter ce choix.

---

## Résumé

Le module `manifest.py` est une implémentation propre, stricte et bien testée. Les 14 paramètres keyword-only sans defaults respectent le strict-no-fallback. La validation schema JSON fonctionne. Les scans GREP sont tous clean (0 occurrences sur tous les patterns). Deux items mineurs identifiés : checklist incomplète et `__init__.py` non mis à jour. Aucun bloquant ni warning.

---

```
RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 0
- Mineurs : 2
- Rapport : docs/tasks/M5/045/review_v1.md
```
