# Revue PR — [WS-11] #045 — Manifest builder

Branche : `task/045-manifest-builder`
Tâche : `docs/tasks/M5/045__ws11_manifest_builder.md`
Date : 2026-03-03
Itération : v2

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Itération v2 après correction des 2 MINEURs de v1 (checklist commit GREEN + re-exports `__init__.py`). Les deux items v1 sont résolus. Cependant, le FIX commit introduit des imports absolus dans `__init__.py` au lieu d'imports relatifs (§R7). Un item MINEUR identifié.

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
| Pas de commits parasites entre RED et GREEN | ✅ | `git log --oneline` : RED → GREEN → FIX (post-GREEN fix acceptable) |

Commit FIX `f3b142e` : `[WS-11] #045 FIX: re-export manifest symbols in artifacts __init__ + checklist update` — corrige les 2 MINEURs v1 (ajout re-exports dans `__init__.py`, cochage checklist). Commit post-GREEN conforme.

### Tâche

| Critère | Verdict | Détail |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` en en-tête |
| Critères d'acceptation cochés | ✅ (10/10) | Tous `[x]` |
| Checklist cochée | ✅ (8/9) | Seul `[ ] PR ouverte` reste — attendu (PR pas encore créée) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1284 passed**, 0 failed (7.99s) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

> Phase A : PASS.

---

## Phase B — Code Review

### Suivi des items v1

| # | Sévérité | Description v1 | Statut v2 | Preuve |
|---|---|---|---|---|
| 1 | MINEUR | Checklist commit GREEN non coché | ✅ Corrigé | `git show --stat f3b142e` : `docs/tasks/M5/045__ws11_manifest_builder.md` modifié. Ligne 78 : `[x] **Commit GREEN**` |
| 2 | MINEUR | `__init__.py` ne réexporte pas les symboles | ✅ Corrigé | `git show --stat f3b142e` : `ai_trading/artifacts/__init__.py` modifié (+22 lignes). Re-exports de `STRATEGY_FRAMEWORK_MAP`, `build_manifest`, `get_git_commit`, `write_manifest`, `create_run_dir`, `generate_run_id`, `save_config_snapshot` |

### B1. Résultats du scan automatisé (GREP)

Fichiers scannés :
- `ai_trading/artifacts/__init__.py` (nouveau contenu FIX)
- `ai_trading/artifacts/manifest.py` (inchangé depuis v1)
- `tests/test_manifest_builder.py` (inchangé depuis v1)

| §Rule | Pattern recherché | Résultat |
|---|---|---|
| §R1 | Fallbacks silencieux (`or []`, `or {}`, `or ""`, `if..else`) | 0 occurrences |
| §R1 | Except trop large (`except:$`, `except Exception:`) | 0 occurrences |
| §R7 | Suppressions lint (`noqa`) | 0 occurrences |
| §R7 | Print résiduel | 0 occurrences |
| §R3 | Shift négatif (`.shift(-`) | 0 occurrences |
| §R4 | Legacy random API | 0 occurrences |
| §R7 | TODO/FIXME/HACK/XXX | 0 occurrences |
| §R7 | Chemins hardcodés (`/tmp`, `C:\\`) | 0 occurrences |
| §R7 | **Imports absolus `__init__.py`** | **2 occurrences** (voir ci-dessous) |
| §R7 | Registration manuelle tests | 0 occurrences |
| §R6 | Mutable default arguments | 0 occurrences |
| §R6 | `open()` sans context manager | 0 occurrences (`Path.write_text()` utilisé) |
| §R6 | Comparaison booléenne par identité | 0 occurrences |
| §R6 | Dict collision silencieuse | 0 occurrences (faux positifs L24, L158, L160 analysés — assignations uniques) |
| §R9 | Boucle Python sur array numpy | 0 occurrences |
| §R6 | `isfinite` check | 0 occurrences (N/A — pas de paramètres numériques bornés) |
| §R9 | Appels numpy dans compréhension | 0 occurrences |
| §R7 | Fixtures dupliquées (`load_config`) | 0 occurrences |
| §R7 | `per-file-ignores` | Aucun ajout lié à cette PR |

**Détail scan imports absolus `__init__.py` :**
```
ai_trading/artifacts/__init__.py:3:from ai_trading.artifacts.manifest import (
ai_trading/artifacts/__init__.py:9:from ai_trading.artifacts.run_dir import (
```

### B2. Annotations par fichier

#### `ai_trading/artifacts/__init__.py` (22 lignes ajoutées — FIX commit)

- **L3** `from ai_trading.artifacts.manifest import (` : import absolu auto-référençant. §R7 exige des imports relatifs dans `__init__.py` : devrait être `from .manifest import (`.
  Sévérité : **MINEUR**
  Suggestion : remplacer par `from .manifest import (` et `from .run_dir import (`.

- **L9** `from ai_trading.artifacts.run_dir import (` : même problème.
  Sévérité : MINEUR (même item que L3).

- **L14-22** `__all__` : liste correcte des 7 symboles exportés, tri alphabétique. ✅

> Note : le même pattern d'import absolu existe dans `ai_trading/features/__init__.py` et `ai_trading/models/__init__.py` (pré-existant). L'item reste MINEUR car la règle §R7 est explicite sur l'usage d'imports relatifs dans `__init__.py`.

#### `ai_trading/artifacts/manifest.py` (197 lignes — inchangé depuis v1)

Inchangé depuis v1. Lecture complète confirmée en v1 — aucune anomalie. Points clés rappelés :

- **L24-35** `STRATEGY_FRAMEWORK_MAP` couvre les 10 stratégies MVP. ✅
- **L38-70** `get_git_commit` : `subprocess.run` avec liste args (pas `shell=True`), except ciblé, warning loggé. ✅
- **L77-87** `build_manifest` : 14 kwargs obligatoires, aucun default. ✅
- **L133-144** Validations explicites + `raise ValueError`. ✅
- **L152-160** Construction strategy section : conditionnels `if "key" in dict` pour champs optionnels du schéma. ✅
- **L163** `datetime.now(UTC)` pour `created_at_utc`. ✅
- **L179-189** `write_manifest` : `mkdir(parents=True, exist_ok=True)` + `write_text(encoding="utf-8")`. ✅

> RAS après lecture du diff complet (197 lignes).

#### `tests/test_manifest_builder.py` (562 lignes — inchangé depuis v1)

Inchangé depuis v1. Lecture complète confirmée en v1. Points clés :

- **L27-30** `SCHEMA_PATH` portable via `Path(__file__).resolve()`. ✅
- **L184-202** `_build_minimal_manifest(**overrides)` helper réutilisable. ✅
- **L213-228** `TestModuleImportable` → AC-1. ✅
- **L234-267** `TestSchemaValidation` → AC-2 (nominal, pipeline_log, multi-fold). ✅
- **L273-280** `TestTrainExcludesVal` → AC-3. ✅
- **L286-326** `TestGitCommit` → AC-4 (hex, unknown, caplog WARNING). ✅
- **L332-345** `TestPipelineVersion` → AC-5. ✅
- **L351-366** `TestPipelineLogConditional` → AC-6. ✅
- **L372-414** `TestStrategyFrameworkMap` → AC-7 (parametrize 10 stratégies + unknown). ✅
- **L420-462** `TestBuildManifestStructure` → nominaux. ✅
- **L468-501** `TestWriteManifest` → I/O avec `tmp_path`. ✅
- **L507-549** `TestBuildManifestErrors` → erreurs (TypeError, ValueError). ✅

> RAS après lecture du diff complet (562 lignes).

#### `docs/tasks/M5/045__ws11_manifest_builder.md`

- Statut DONE. ✅
- 10/10 critères d'acceptation cochés. ✅
- 8/9 checklist cochés (seul `[ ] PR ouverte` reste — attendu). ✅

### B3. Vérification des tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_manifest_builder.py` |
| Docstrings avec `#045` | ✅ | Module docstring + classes |
| Couverture AC-1 à AC-10 | ✅ | Chaque AC couvert par classe dédiée |
| Cas nominaux | ✅ | `TestBuildManifestStructure`, `TestSchemaValidation` |
| Cas d'erreur | ✅ | `TestBuildManifestErrors` |
| Cas de bords | ✅ | git absent, pipeline_log conditionnel, multi-fold |
| skip/xfail | ✅ | 0 occurrences |
| Déterministe | ✅ | Pas d'aléatoire |
| Données synthétiques | ✅ | Tout construit en mémoire |
| Portabilité chemins | ✅ | `tmp_path` partout, 0 chemin hardcodé |

### B4. Audit du code — Règles non négociables

#### B4a. Strict code (§R1)
- ✅ Aucun fallback silencieux (grep : 0 occurrences).
- ✅ Except ciblé (`CalledProcessError`, `FileNotFoundError`) — exception documentée.
- ✅ 14 paramètres keyword-only sans defaults dans `build_manifest`.
- ✅ Validation explicite + `raise ValueError`.

#### B4a-bis. Defensive indexing (§R10)
- ✅ N/A — pas d'indexation array/slice.

#### B4b. Config-driven (§R2)
- ✅ N/A — reçoit la config en entrée, ne lit pas YAML.
- ✅ `STRATEGY_FRAMEWORK_MAP` est un mapping interne, pas un paramètre config.

#### B4c. Anti-fuite (§R3)
- ✅ N/A — pas de traitement de données temporelles.

#### B4d. Reproductibilité (§R4)
- ✅ N/A — pas d'aléatoire.

#### B4e. Float conventions (§R5)
- ✅ N/A — pas de tenseurs ni métriques.

#### B4f. Anti-patterns Python (§R6)
- ✅ Pas de mutable defaults (grep : 0).
- ✅ `Path.write_text()` sans `open()` explicite.
- ✅ Path creation avec `mkdir(parents=True, exist_ok=True)`.
- ✅ Pas de comparaison booléenne par identité.
- ✅ Pas de dict collision silencieuse.

### B5. Qualité du code (§R7)

| Critère | Verdict | Preuve |
|---|---|---|
| snake_case cohérent | ✅ | Lecture diff |
| Pas de code mort / TODO | ✅ | grep : 0 occurrences |
| Pas de `print()` | ✅ | grep : 0 occurrences |
| Imports propres | ✅ | manifest.py : stdlib → third-party → local |
| Pas de `noqa` ajouté | ✅ | grep : 0 occurrences |
| `__init__.py` à jour | ✅ | Re-exports ajoutés (FIX commit) |
| **Imports relatifs dans `__init__.py`** | ❌ | Imports absolus `from ai_trading.artifacts.manifest` au lieu de `from .manifest` |
| Fichiers générés exclus | ✅ | Aucun artefact dans le diff |

### B5-bis. Bonnes pratiques métier (§R9)
- ✅ N/A — module de sérialisation, pas de calcul financier.

### B6. Cohérence avec les specs

| Critère | Verdict | Preuve |
|---|---|---|
| Conforme à la spec (§15.2, Annexe A, E.2.1) | ✅ | Structure manifest conforme au schéma `manifest.schema.json` |
| Conforme au plan (WS-11.2) | ✅ | 4 symboles publics implémentés |
| Pas d'exigence inventée | ✅ | Toutes les validations correspondent à des exigences de la tâche |
| Validation schema Draft 2020-12 | ✅ | Tests : `jsonschema.validate()` |
| Train exclut val (E.2.1) | ✅ | Test `train.end_utc < val.start_utc` |

### B7. Cohérence intermodule (§R8)

| Critère | Verdict | Preuve |
|---|---|---|
| Signatures compatibles | ✅ | `build_manifest` utilise des dicts génériques |
| Imports croisés | ✅ | Aucun import d'autres modules `ai_trading.*` hors package |
| `__version__` accessible | ✅ | `ai_trading.__init__.py` exporte `__version__ = "1.0.0"` |
| Re-exports `__init__.py` | ✅ | `__all__` avec 7 symboles (FIX commit) |

---

## Remarques

1. **[MINEUR]** Imports absolus auto-référençants dans `__init__.py`
   - Fichier : `ai_trading/artifacts/__init__.py`
   - Ligne(s) : 3, 9
   - Détail : `from ai_trading.artifacts.manifest import (...)` et `from ai_trading.artifacts.run_dir import (...)` utilisent des imports absolus. La règle §R7 exige des imports relatifs dans `__init__.py` : `from .manifest import (...)` et `from .run_dir import (...)`.
   - Note : le même pattern existe dans `ai_trading/features/__init__.py` et `ai_trading/models/__init__.py` (pré-existant, hors scope de cette PR).
   - Suggestion : remplacer les 2 lignes d'import par leurs équivalents relatifs.

---

## Résumé

Les 2 MINEURs v1 ont été corrigés dans le commit FIX `f3b142e`. Cependant, la correction du `__init__.py` a introduit des imports absolus au lieu de relatifs (§R7). Le code `manifest.py` et les tests sont inchangés et restent solides. 1 item MINEUR résiduel.

---

```
RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 0
- Mineurs : 1
- Rapport : docs/tasks/M5/045/review_v2.md
```
