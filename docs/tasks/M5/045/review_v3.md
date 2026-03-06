# Revue PR — [WS-11] #045 — Manifest builder

Branche : `task/045-manifest-builder`
Tâche : `docs/tasks/M5/045__ws11_manifest_builder.md`
Date : 2026-03-03
Itération : v3

## Verdict global : ✅ CLEAN

## Résumé

Itération v3 après correction du MINEUR v2 (imports absolus dans `__init__.py`). Le commit `9413848` remplace les 2 imports absolus (`from ai_trading.artifacts.manifest`) par des imports relatifs (`from .manifest`). Tous les scans GREP sont propres, pytest 1284 passed / 0 failed, ruff clean. 0 item résiduel.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/045-manifest-builder` | ✅ | `git branch --show-current` → `task/045-manifest-builder` |
| Commit RED `[WS-11] #045 RED: tests manifest builder` | ✅ | `e8f1a7f` — 1 fichier (`tests/test_manifest_builder.py`, +556) |
| Commit RED contient uniquement des tests | ✅ | `git show --stat e8f1a7f` : 1 seul fichier `tests/test_manifest_builder.py` |
| Commit GREEN `[WS-11] #045 GREEN: manifest builder` | ✅ | `d8622ac` — 3 fichiers (`manifest.py` +197, tâche +36/-22, tests +6/-6) |
| Commit GREEN contient implémentation + tâche | ✅ | `ai_trading/artifacts/manifest.py`, `docs/tasks/M5/045__ws11_manifest_builder.md`, `tests/test_manifest_builder.py` |
| Pas de commits parasites entre RED et GREEN | ✅ | `git log --oneline` : RED → GREEN → 2 FIX post-GREEN (corrections review) |

Commits FIX post-GREEN :
- `f3b142e` : `[WS-11] #045 FIX: re-export manifest symbols in artifacts __init__ + checklist update` — correction MINEURs v1.
- `9413848` : `[WS-11] #045 FIX: use relative imports in artifacts __init__` — correction MINEUR v2.

### Tâche

| Critère | Verdict | Détail |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` en en-tête |
| Critères d'acceptation cochés | ✅ (10/10) | Tous `[x]` (L51-L60) |
| Checklist cochée | ✅ (8/9) | Seul `[ ] PR ouverte` reste (L75) — attendu (PR pas encore créée) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1284 passed**, 0 failed (8.12s) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

> Phase A : PASS.

---

## Phase B — Code Review

### Suivi des items v1 et v2

| # | Sévérité | Description | Introduit en | Statut v3 | Preuve |
|---|---|---|---|---|---|
| v1-1 | MINEUR | Checklist commit GREEN non coché | v1 | ✅ Corrigé | FIX `f3b142e` : tâche modifiée, L74 `[x] **Commit GREEN**` |
| v1-2 | MINEUR | `__init__.py` ne réexporte pas les symboles | v1 | ✅ Corrigé | FIX `f3b142e` : `__init__.py` +22 lignes, 7 symboles exportés |
| v2-1 | MINEUR | Imports absolus auto-référençants dans `__init__.py` | v2 | ✅ Corrigé | FIX `9413848` : `from ai_trading.artifacts.manifest` → `from .manifest`, `from ai_trading.artifacts.run_dir` → `from .run_dir` (diff vérifié) |

### B1. Résultats du scan automatisé (GREP)

Fichiers scannés :
- `ai_trading/artifacts/__init__.py` (modifié — FIX v3)
- `ai_trading/artifacts/manifest.py` (inchangé depuis v1)
- `tests/test_manifest_builder.py` (inchangé depuis v1)

| §Rule | Pattern recherché | Résultat |
|---|---|---|
| §R1 | Fallbacks silencieux (`or []`, `or {}`, `or ""`, `if..else`) | 0 occurrences (grep exécuté) |
| §R1 | Except trop large (`except:$`, `except Exception:`) | 0 occurrences (grep exécuté) |
| §R7 | Suppressions lint (`noqa`) | 0 occurrences (grep exécuté, src + tests) |
| §R7 | Print résiduel (`print(`) | 0 occurrences (grep exécuté) |
| §R3 | Shift négatif (`.shift(-`) | 0 occurrences (grep exécuté) |
| §R4 | Legacy random API (`np.random.seed`, etc.) | 0 occurrences (grep exécuté) |
| §R7 | TODO/FIXME/HACK/XXX | 0 occurrences (grep exécuté, src + tests) |
| §R7 | Chemins hardcodés OS-spécifiques (`/tmp`, `C:\\`) | 0 occurrences (grep exécuté sur tests) |
| §R7 | Imports absolus `__init__.py` (`from ai_trading.`) | **0 occurrences** (grep exécuté — corrigé v3) |
| §R7 | Registration manuelle tests (`register_model`, `register_feature`) | 0 occurrences (grep exécuté) |
| §R6 | Mutable default arguments (`def..=[]`, `def..={}`) | 0 occurrences (grep exécuté) |
| §R6 | `open()` sans context manager | 0 occurrences (grep exécuté — `Path.write_text()` utilisé) |
| §R6 | Comparaison booléenne par identité (`is True`, `is False`, `is np.bool_`) | 0 occurrences (grep exécuté) |
| §R6 | Dict collision silencieuse | 0 occurrences (faux positifs analysés en v1) |
| §R9 | Boucle Python sur array numpy (`for..in range`) | 0 occurrences (match L124 `run_dir.py` hors PR) |
| §R6 | `isfinite` check | 0 occurrences (N/A — pas de paramètres numériques bornés) |
| §R9 | Appels numpy dans compréhension | 0 occurrences (grep exécuté) |
| §R7 | Fixtures dupliquées (`load_config.*configs/`) | 0 occurrences (grep exécuté) |
| §R7 | `per-file-ignores` dans `pyproject.toml` | Existant (L51), aucun ajout lié à cette PR |

### B2. Annotations par fichier

#### `ai_trading/artifacts/__init__.py` (23 lignes — 2 lignes modifiées par FIX v3)

- **L3** `from .manifest import (` : ✅ import relatif conforme §R7.
- **L9** `from .run_dir import (` : ✅ import relatif conforme §R7.
- **L15-23** `__all__` : 7 symboles triés alphabétiquement. ✅

> RAS après lecture complète du diff (23 lignes).

#### `ai_trading/artifacts/manifest.py` (197 lignes — inchangé depuis v1)

Inchangé depuis v1. Lecture complète confirmée en v1/v2. Points clés :

- **L24-35** `STRATEGY_FRAMEWORK_MAP` : mapping interne couvrant 10 stratégies MVP. ✅
- **L38-70** `get_git_commit` : `subprocess.run` avec liste args (pas `shell=True`), except ciblé (`CalledProcessError`, `FileNotFoundError`), warning loggé. Exception documentée au strict-no-fallback. ✅
- **L77-87** `build_manifest` : 14 kwargs keyword-only obligatoires, aucun default. ✅
- **L133-144** Validations explicites (`not run_id`, `not git_commit`, `not pipeline_version`, `strategy_name not in STRATEGY_FRAMEWORK_MAP`) + `raise ValueError`. ✅
- **L152-160** Construction strategy section : conditionnels `if "key" in dict` pour champs optionnels du schéma (`hyperparams`, `thresholding`). ✅
- **L163** `datetime.now(UTC)` pour `created_at_utc`. ✅
- **L179-189** `write_manifest` : `mkdir(parents=True, exist_ok=True)` avant écriture + `write_text(encoding="utf-8")`. ✅

> RAS après lecture du diff complet (197 lignes).

#### `tests/test_manifest_builder.py` (562 lignes — inchangé depuis v1)

Inchangé depuis v1. Lecture complète confirmée en v1/v2. Points clés :

- **L27-30** `SCHEMA_PATH` portable via `Path(__file__).resolve()`. ✅
- **L184-202** `_build_minimal_manifest(**overrides)` helper réutilisable. ✅
- **L213-228** `TestModuleImportable` → AC-1 (module importable). ✅
- **L234-267** `TestSchemaValidation` → AC-2 (nominal, pipeline_log, multi-fold). ✅
- **L273-280** `TestTrainExcludesVal` → AC-3 (train.end_utc < val.start_utc). ✅
- **L286-326** `TestGitCommit` → AC-4 (hex valide, "unknown", caplog WARNING). ✅
- **L332-345** `TestPipelineVersion` → AC-5 (`__version__`). ✅
- **L351-366** `TestPipelineLogConditional` → AC-6 (pipeline_log conditionnel). ✅
- **L372-414** `TestStrategyFrameworkMap` → AC-7 (parametrize 10 stratégies + unknown). ✅
- **L420-462** `TestBuildManifestStructure` → nominaux. ✅
- **L468-501** `TestWriteManifest` → I/O avec `tmp_path`. ✅
- **L507-549** `TestBuildManifestErrors` → erreurs (TypeError, ValueError). ✅

> RAS après lecture du diff complet (562 lignes).

#### `docs/tasks/M5/045__ws11_manifest_builder.md`

- Statut DONE. ✅
- 10/10 critères d'acceptation cochés. ✅
- 8/9 checklist cochés (seul `[ ] PR ouverte` — attendu). ✅

### B3. Vérification des tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_manifest_builder.py` |
| Docstrings avec `#045` | ✅ | Module docstring L1-L3 |
| Couverture AC-1 à AC-10 | ✅ | Chaque AC couvert par classe dédiée |
| Cas nominaux | ✅ | `TestBuildManifestStructure`, `TestSchemaValidation` |
| Cas d'erreur | ✅ | `TestBuildManifestErrors` (TypeError, ValueError) |
| Cas de bords | ✅ | git absent, pipeline_log conditionnel, multi-fold, unknown strategy |
| skip/xfail | ✅ | 0 occurrences |
| Déterministe | ✅ | Pas d'aléatoire |
| Données synthétiques | ✅ | Tout construit en mémoire |
| Portabilité chemins | ✅ | `tmp_path` partout, 0 chemin hardcodé (scan B1) |
| Tests registre réalistes | N/A | Pas de registre |
| Contrat ABC complet | N/A | Pas d'ABC |

### B4. Audit du code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallbacks, 0 except trop large. 14 kwargs obligatoires. Validations explicites + `raise ValueError`. Exception `"unknown"` documentée + loggée. |
| §R10 Defensive indexing | ✅ | N/A — pas d'indexation array/slice |
| §R2 Config-driven | ✅ | N/A — reçoit config en entrée, ne lit pas YAML. `STRATEGY_FRAMEWORK_MAP` interne. |
| §R3 Anti-fuite | ✅ | N/A — module sérialisation, pas de traitement temporel. Scan B1 : 0 `.shift(-` |
| §R4 Reproductibilité | ✅ | N/A — pas d'aléatoire. Scan B1 : 0 legacy random |
| §R5 Float conventions | ✅ | N/A — pas de tenseurs ni métriques |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 `open()` nu, 0 bool identité. `Path.write_text()` utilisé. `mkdir(parents=True, exist_ok=True)` avant écriture. |

### B5. Qualité du code (§R7)

| Critère | Verdict | Preuve |
|---|---|---|
| snake_case cohérent | ✅ | Lecture diff |
| Pas de code mort / TODO | ✅ | Scan B1 : 0 TODO/FIXME/HACK/XXX |
| Pas de `print()` | ✅ | Scan B1 : 0 occurrences |
| Imports propres | ✅ | `manifest.py` : stdlib → third-party (absent) → local (absent). Ordre correct. |
| Pas de `noqa` | ✅ | Scan B1 : 0 occurrences |
| `__init__.py` à jour | ✅ | Re-exports 7 symboles, imports relatifs (vérifié v3) |
| Imports relatifs dans `__init__.py` | ✅ | Scan B1 : 0 `from ai_trading.` dans `__init__.py` |
| Fichiers générés exclus | ✅ | Aucun artefact dans le diff |

### B5-bis. Bonnes pratiques métier (§R9)

| Critère | Verdict | Commentaire |
|---|---|---|
| N/A | ✅ | Module de sérialisation, pas de calcul financier |

### B6. Cohérence avec les specs

| Critère | Verdict | Preuve |
|---|---|---|
| Conforme à la spec (§15.2, Annexe A, E.2.1) | ✅ | Structure manifest conforme au schéma `manifest.schema.json` (validé via `jsonschema.validate()` dans tests) |
| Conforme au plan (WS-11.2) | ✅ | 4 symboles publics implémentés (`STRATEGY_FRAMEWORK_MAP`, `build_manifest`, `get_git_commit`, `write_manifest`) |
| Pas d'exigence inventée | ✅ | Toutes les validations correspondent à des exigences de la tâche |
| Formules doc vs code | ✅ | N/A — pas de formule mathématique |
| Train exclut val (E.2.1) | ✅ | Test `train.end_utc < val.start_utc` dans `TestTrainExcludesVal` |

### B7. Cohérence intermodule (§R8)

| Critère | Verdict | Preuve |
|---|---|---|
| Signatures compatibles | ✅ | `build_manifest` utilise des dicts génériques — compatible avec tout appelant |
| Imports croisés | ✅ | Aucun import d'autres modules `ai_trading.*` hors package `artifacts` |
| `__version__` accessible | ✅ | `ai_trading.__init__.py` exporte `__version__ = "1.0.0"` |
| Re-exports `__init__.py` | ✅ | `__all__` avec 7 symboles dans `__init__.py` |
| Noms de colonnes DataFrame | N/A | Pas de DataFrame |
| Clés de configuration | N/A | Ne lit pas directement le YAML |
| Registres partagés | N/A | Pas de registre |
| Structures de données partagées | N/A | Dicts génériques |
| Conventions numériques | N/A | Pas de calcul numérique |

---

## Remarques

Aucune.

---

## Résumé

Le MINEUR v2 (imports absolus dans `__init__.py`) est corrigé par le commit `9413848`. Les imports sont désormais relatifs (`from .manifest`, `from .run_dir`) conformément à §R7. L'ensemble du code (`manifest.py`, tests, `__init__.py`) est propre : tous les scans GREP à 0 occurrence, pytest 1284/0, ruff clean. Aucun item résiduel.

---

```
RÉSULTAT PARTIE B :
- Verdict : CLEAN
- Bloquants : 0
- Warnings : 0
- Mineurs : 0
- Rapport : docs/tasks/M5/045/review_v3.md
```
