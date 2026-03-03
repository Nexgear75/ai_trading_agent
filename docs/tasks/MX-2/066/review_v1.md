# Revue PR — [WS-XGB-5] #066 — Sauvegarde JSON native XGBoost

Branche : `task/066-xgb-save-json`
Tâche : `docs/tasks/MX-2/066__ws_xgb5_save_json.md`
Date : 2026-03-03

## Verdict global : ✅ CLEAN

## Résumé

Implémentation propre de `save()` pour `XGBoostRegModel` : format JSON natif XGBoost, résolution de chemin directory/fichier via `_resolve_path` (pattern identique à `DummyModel`), guard `RuntimeError` si modèle non entraîné, création des répertoires parents. 9 nouveaux tests couvrent tous les critères d'acceptation. Aucun item identifié.

---

## Phase A — Compliance

### A1. Périmètre

Fichiers modifiés vs `Max6000i1` :

```
ai_trading/models/xgboost.py
docs/tasks/MX-2/066__ws_xgb5_save_json.md
tests/test_xgboost_model.py
```

- Source : 1 fichier (`ai_trading/models/xgboost.py`)
- Tests : 1 fichier (`tests/test_xgboost_model.py`)
- Docs : 1 fichier (tâche)

### A2. Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/066-xgb-save-json` | ✅ | `HEAD -> task/066-xgb-save-json` |
| Commit RED présent | ✅ | `bdd66cd` — `[WS-XGB-5] #066 RED: tests save XGBoostRegModel` |
| Commit RED = tests uniquement | ✅ | `git show --stat bdd66cd` → `tests/test_xgboost_model.py \| 105 +++---` (1 fichier, 99 ins, 6 del) |
| Commit GREEN présent | ✅ | `9b46a07` — `[WS-XGB-5] #066 GREEN: save JSON natif XGBoostRegModel` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 9b46a07` → `ai_trading/models/xgboost.py` + `docs/tasks/MX-2/066__ws_xgb5_save_json.md` (2 fichiers) |
| Pas de commits parasites | ✅ | `git log --oneline` : exactement 2 commits (RED puis GREEN) |

### A3. Tâche

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` en tête du fichier |
| Critères d'acceptation cochés | ✅ (9/9) | Tous `[x]` — voir mapping ci-dessous |
| Checklist cochée | ✅ (8/9) | Seule la PR non ouverte — attendu à ce stade |

**Mapping critères d'acceptation → preuves** :

| Critère | Code | Test |
|---|---|---|
| `save()` crée `xgboost_model.json` | `self._model.save_model(str(resolved))` L193 | `test_save_creates_file_in_directory` |
| Fichier JSON valide | XGBoost `save_model()` produit du JSON natif | `test_save_file_is_valid_json_directory`, `test_save_explicit_path_is_valid_json` |
| `RuntimeError` si non entraîné | `if self._model is None: raise RuntimeError(...)` L191 | `test_save_raises_runtime_error_if_not_fitted` |
| Résolution directory → append filename | `_resolve_path` : `if path.is_dir(): return path / _MODEL_FILENAME` L182 | `test_resolve_path_directory_appends_filename`, `test_save_creates_file_in_directory` |
| Résolution fichier → tel quel | `_resolve_path` : `return path` L183 | `test_resolve_path_file_returns_as_is`, `test_save_uses_explicit_file_path` |
| Répertoire parent créé | `resolved.parent.mkdir(parents=True, exist_ok=True)` L192 | `test_save_creates_parent_directories` |
| Tests nominaux + erreurs + bords | — | 9 tests : 1 erreur, 5 nominaux, 2 _resolve_path, 1 bord (overwrite) |
| Suite verte | — | 1739 passed, 0 failed |
| ruff clean | — | All checks passed |

### A4. Suite de validation

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1739 passed**, 12 deselected, 0 failed (22.13s) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

✅ Phase A validée — passage en Phase B.

---

## Phase B — Code Review

### B1. Scan automatisé (GREP)

Tous les scans exécutés sur `ai_trading/models/xgboost.py` et `tests/test_xgboost_model.py` :

| Pattern recherché | Règle | Résultat |
|---|---|---|
| Fallbacks silencieux (`or []`, `or {}`, etc.) | §R1 | 0 occurrences |
| `except:` / `except Exception:` trop large | §R1 | 0 occurrences |
| `print()` résiduel | §R7 | 0 occurrences |
| `.shift(-` (look-ahead) | §R3 | 0 occurrences |
| Legacy random API (`np.random.seed`, etc.) | §R4 | 0 occurrences |
| TODO/FIXME/HACK/XXX | §R7 | 0 occurrences |
| Chemins hardcodés `/tmp`, `C:\` (tests) | §R7 | 0 occurrences |
| Imports absolus `__init__.py` | §R7 | N/A (aucun `__init__.py` modifié) |
| Registration manuelle tests | §R7 | 1 match L59 : commentaire dans docstring `_reload_xgboost_module`, **faux positif** (pas un appel) |
| Mutable default arguments | §R6 | 0 occurrences |
| `open()` sans context manager | §R6 | 0 occurrences |
| Comparaison bool par identité (`is True/False`) | §R6 | 0 occurrences |
| Dict collision silencieuse en boucle | §R6 | 0 occurrences |
| Boucle Python sur array numpy | §R9 | 0 occurrences |
| `isfinite` validation | §R6 | 0 occurrences (N/A — pas de paramètre float en entrée publique dans le diff) |
| Appels numpy répétés vectorisables | §R9 | 0 occurrences |
| Fixtures dupliquées (`load_config.*configs/`) | §R7 | 0 occurrences |
| `noqa` suppressions | §R7 | 3 matches pré-existants : L35 `N803` (`X_train`), L37 `N803` (`X_val`), L145 `N803` (`X`) — noms imposés par l'ABC. 1 match test L157 `F811/F401` — reimport pour `_reload_xgboost_module`. **Aucun nouveau `noqa` dans cette PR.** |
| `per-file-ignores` pyproject.toml | §R7 | L52 pré-existant, **inchangé par cette PR** |

### B2. Annotations par fichier

#### `ai_trading/models/xgboost.py` (25 lignes modifiées)

**Diff lu intégralement** (1 constante, 1 méthode statique `_resolve_path`, 1 méthode `save`).

- **L20** `_MODEL_FILENAME = "xgboost_model.json"` : constante module-level, cohérente avec `dummy.py:19` (`_MODEL_FILENAME = "dummy_model.json"`). Valeur conforme à la spec §7.1 ("Nom de fichier : `xgboost_model.json`"). RAS.

- **L174–183** `_resolve_path(path: Path) -> Path` :
  - `@staticmethod` : cohérent avec `dummy.py:58`.
  - `path = Path(path)` : conversion défensive pour accepter `str` en plus de `Path`. OK.
  - `if path.is_dir()` → append `_MODEL_FILENAME` ; sinon retourne `path` tel quel. Cohérent avec le contrat ABC (`path` = "Directory or file path"). OK.
  - La spec §7.2 montre `self._resolve_path(path, "xgboost_model.json")` (2 args) ; l'implémentation utilise 1 arg + constante module-level. Choix identique à `DummyModel` et explicitement demandé par la tâche ("suivant le pattern de DummyModel"). **Fonctionnellement équivalent.** RAS.

- **L185–193** `save(self, path: Path) -> None` :
  1. **Type safety (B2-1)** : `path` est typé `Path` via l'ABC. `_resolve_path` applique `Path(path)`. OK.
  2. **Edge cases (B2-2)** : `self._model is None` → `RuntimeError`. Couvert. OK.
  3. **Domaine paramètres (B2-3)** : N/A (pas de paramètre numérique).
  4. **Path handling (B2-4)** : ✅ `resolved.parent.mkdir(parents=True, exist_ok=True)` avant `save_model()`. Parents créés. Conforme §R6.
  5. **Return contract (B2-5)** : `-> None`. `save_model()` retourne `None`. OK.
  6. **Resource cleanup (B2-6)** : `save_model()` gère l'I/O en interne (XGBoost C++ backend). Pas de fichier ouvert manuellement. OK.
  7. **Cohérence doc/code (B2-7)** : Docstring "Persist the trained XGBoost model to JSON format" → correspond au comportement. Task #066 référencée. OK.

RAS après lecture complète du diff (25 lignes).

#### `tests/test_xgboost_model.py` (99 insertions, 6 suppressions)

**Diff lu intégralement.**

- **Suppression L125–130** : ancien `test_save_raises_not_implemented` supprimé. Correct — le stub `NotImplementedError` n'existe plus ; les nouveaux tests le remplacent.

- **Classe `TestXGBoostRegModelSave`** (L979–1077) : 9 tests, docstrings `#066` présentes.

  | Test | Type | Critère couvert |
  |---|---|---|
  | `test_save_raises_runtime_error_if_not_fitted` | Erreur | `RuntimeError` si non entraîné |
  | `test_save_creates_file_in_directory` | Nominal | Directory → `xgboost_model.json` |
  | `test_save_file_is_valid_json_directory` | Nominal | JSON valide |
  | `test_save_uses_explicit_file_path` | Nominal | File path → tel quel |
  | `test_save_explicit_path_is_valid_json` | Nominal | JSON valide (file path) |
  | `test_save_creates_parent_directories` | Nominal | `mkdir(parents=True)` |
  | `test_resolve_path_directory_appends_filename` | Unitaire | `_resolve_path` directory |
  | `test_resolve_path_file_returns_as_is` | Unitaire | `_resolve_path` fichier |
  | `test_save_twice_overwrites` | Bord | Idempotence overwrite |

- Usage de `tmp_path` exclusif (portabilité). ✅
- `fitted_model` fixture réutilisée (définie L824, partagée avec predict tests). ✅
- `_make_xgb_model()` pour le test d'erreur (modèle non entraîné). ✅
- Pas de `@pytest.mark.skip` ni `xfail`. ✅
- Données synthétiques (pas de réseau). ✅
- Déterministe (seeds fixées dans `fitted_model` via `default_config`). ✅
- `import json` dans les tests JSON : import local dans le test, léger mais acceptable pour 2 usages. RAS.

### B3. Vérification des tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_xgboost_model.py`, `#066` dans docstrings |
| Chaque critère d'acceptation couvert | ✅ | Mapping A3 ci-dessus |
| Cas nominaux | ✅ | 5 tests (directory, file, JSON, parents, _resolve_path) |
| Cas erreur | ✅ | `test_save_raises_runtime_error_if_not_fitted` |
| Cas de bords | ✅ | `test_save_twice_overwrites` |
| Boundary fuzzing numérique | N/A | Pas de paramètre numérique dans `save()` |
| Boundary fuzzing taux/proportions | N/A | Pas de taux/proportion |
| Pas de skip/xfail | ✅ | Scan grep : 0 occurrences |
| Tests déterministes | ✅ | Seeds fixées via `default_config` |
| Données synthétiques | ✅ | Pas de réseau |
| Portabilité chemins | ✅ | `tmp_path` exclusif (scan B1 : 0 `/tmp`) |
| Tests registre réalistes | N/A | Pas de test de registre dans cette PR |
| Contrat ABC complet (directory + fichier) | ✅ | Tests couvrent les deux cas |

### B4. Audit du code — Règles non négociables

#### B4a. Strict code (§R1)
- ✅ Pas de fallback silencieux (scan B1 : 0 occurrences).
- ✅ Pas d'`except` trop large (scan B1 : 0 occurrences).
- ✅ `RuntimeError` explicite si `self._model is None`.

#### B4a-bis. Defensive indexing / slicing (§R10)
- N/A — pas d'indexation/slicing dans le diff.

#### B4b. Config-driven (§R2)
- N/A — `save()` ne lit pas de paramètre de configuration. Le nom de fichier `xgboost_model.json` est défini par la spec §7.1 (constante structurelle, pas un paramètre utilisateur). OK.

#### B4c. Anti-fuite (§R3)
- N/A — `save()` n'accède pas aux données temporelles. Scan B1 `.shift(-` : 0 occurrences.

#### B4d. Reproductibilité (§R4)
- ✅ Pas de legacy random API (scan B1 : 0 occurrences).
- Sérialisation JSON native = format portable et reproductible (conforme spec §7.1).

#### B4e. Float conventions (§R5)
- N/A — `save()` ne manipule pas de tenseurs/métriques.

#### B4f. Anti-patterns Python (§R6)
- ✅ Pas de mutable defaults (scan B1 : 0 occurrences).
- ✅ Pas d'`open()` sans context manager (`save_model()` gère l'I/O en interne).
- ✅ Path creation : `resolved.parent.mkdir(parents=True, exist_ok=True)` avant `save_model()`.
- ✅ Pas de comparaison bool par identité (scan B1 : 0 occurrences).

### B5. Qualité du code (§R7)

| Critère | Verdict | Preuve |
|---|---|---|
| snake_case | ✅ | `_resolve_path`, `_MODEL_FILENAME`, `save` |
| Pas de code mort / TODO | ✅ | Scan B1 : 0 occurrences TODO/FIXME |
| Pas de `print()` | ✅ | Scan B1 : 0 occurrences |
| Imports propres | ✅ | Aucun import ajouté dans le diff source |
| Variables mortes | ✅ | Aucune variable inutilisée |
| Pas de fichiers générés | ✅ | Seuls `.py` et `.md` dans le diff |
| DRY | ✅ | `_MODEL_FILENAME` = constante unique par module (dummy: `dummy_model.json`, xgboost: `xgboost_model.json`). `_resolve_path` dupliquée entre dummy et xgboost mais avec constante différente — pattern cohérent, extraction en base class possible en refactoring futur mais pas nécessaire à ce stade. |
| `noqa` minimal | ✅ | Aucun nouveau `noqa` dans cette PR |
| `__init__.py` à jour | N/A | Pas de nouveau module créé |

### B5-bis. Bonnes pratiques métier (§R9)

- N/A — `save()` est une opération d'I/O pure, pas de calcul financier.

### B6. Cohérence avec les specs

| Critère | Verdict | Preuve |
|---|---|---|
| Conforme spec §7.1 (format JSON, nom `xgboost_model.json`) | ✅ | `_MODEL_FILENAME = "xgboost_model.json"`, `save_model()` |
| Conforme spec §7.2 (procédure `save()`) | ✅ | `_resolve_path` → `mkdir` → `save_model(str(resolved))`. Signature `_resolve_path` adaptée (1 arg + constante vs 2 args dans le pseudocode) mais fonctionnellement identique et cohérent avec DummyModel. |
| Pickle interdit | ✅ | Seul `save_model()` utilisé (JSON natif XGBoost) |
| Pas d'exigence inventée | ✅ | Toutes les fonctionnalités tracées vers spec ou tâche |

### B7. Cohérence intermodule (§R8)

| Critère | Verdict | Preuve |
|---|---|---|
| Signature ABC respectée | ✅ | `save(self, path: Path) -> None` conforme à `BaseModel.save` (L251 de base.py) |
| Pattern `_resolve_path` cohérent avec DummyModel | ✅ | Même structure : `@staticmethod`, `Path(path)`, `is_dir()` → append, sinon retour direct |
| `_MODEL_FILENAME` convention | ✅ | dummy: `dummy_model.json`, xgboost: `xgboost_model.json` — pas de collision, convention respectée |
| Imports croisés | ✅ | Aucun nouvel import ajouté |

---

## Remarques

Aucune.

---

## Résumé

Implémentation minimale, focalisée et conforme à la spec §7.1/§7.2. Le pattern `_resolve_path` + `mkdir` + `save_model` est identique à celui de `DummyModel`, assurant la cohérence intermodule. Les 9 tests couvrent l'intégralité des critères d'acceptation (erreur, nominal directory/fichier, JSON valide, parent dirs, overwrite). Aucun item identifié.

---

```
RÉSULTAT PARTIE B :
- Verdict : CLEAN
- Bloquants : 0
- Warnings : 0
- Mineurs : 0
- Rapport : docs/tasks/MX-2/066/review_v1.md
```
