# Revue PR — [WS-XGB-5] #067 — Chargement JSON native XGBoost

Branche : `task/067-xgb-load-json`
Tâche : `docs/tasks/MX-2/067__ws_xgb5_load_json.md`
Date : 2026-03-03

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Implémentation minimale et correcte de `load()` (8 lignes de code), conforme à la spec §7.3. 9 tests couvrent tous les critères d'acceptation (erreur, nominal, round-trip bit-exact, sécurité JSON). Un seul item mineur identifié : classe de test vide résiduelle (`TestXGBoostRegModelStubs` avec `pass`).

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/067-xgb-load-json` | ✅ | `git branch --show-current` → `task/067-xgb-load-json` |
| Commit RED présent | ✅ | `5fe804d [WS-XGB-5] #067 RED: tests load XGBoostRegModel` |
| Commit RED = tests uniquement | ✅ | `git show --stat 5fe804d` → `tests/test_xgboost_model.py` seul (133 ins, 6 del) |
| Commit GREEN présent | ✅ | `040ecc4 [WS-XGB-5] #067 GREEN: load JSON natif XGBoostRegModel` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 040ecc4` → `ai_trading/models/xgboost.py`, `docs/tasks/MX-2/067__*.md`, `tests/test_xgboost_model.py` |
| Pas de commits parasites entre RED et GREEN | ✅ | `git log --oneline Max6000i1...HEAD` → exactement 2 commits |

### Tâche

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | Diff tâche montre `Statut : TODO` → `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (9/9) | Tous `- [ ]` → `- [x]` dans le diff |
| Checklist cochée | ✅ (8/9) | 8 cochés, 1 non coché (PR ouverte — attendu) |

**Mapping critères d'acceptation → preuves :**

| Critère | Test ou code preuve |
|---|---|
| `load()` restaure modèle fonctionnel | `test_load_from_directory_path`, `test_load_from_explicit_file_path` |
| Round-trip bit-exact | `test_round_trip_bit_exact_directory`, `test_round_trip_bit_exact_explicit_path` |
| `FileNotFoundError` si fichier absent | `test_load_raises_file_not_found_nonexistent_file`, `test_load_raises_file_not_found_nonexistent_dir` |
| Résolution chemin directory | `test_load_from_directory_path` + `_resolve_path` L173-178 |
| Résolution chemin fichier | `test_load_from_explicit_file_path` + `_resolve_path` L178 |
| `predict()` après `load()` | `test_predict_works_after_load` |
| Tests nominaux + erreurs + bords | 9 tests : 2 erreur, 4 nominal, 1 boundary, 1 round-trip, 1 sécurité |
| Suite tests verte | pytest : 1747 passed, 0 failed |
| ruff clean | `ruff check ai_trading/ tests/` → All checks passed |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1747 passed**, 12 deselected, 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** |

---

## Phase B — Code Review

### B1 — Résultats du scan automatisé (GREP)

| Pattern recherché | Règle | Résultat |
|---|---|---|
| Fallbacks silencieux (`or []`, `or {}`, `or ""`, `or 0`, `if...else`) | §R1 | 0 occurrences (grep exécuté) |
| Except trop large (`except:`, `except Exception:`) | §R1 | 0 occurrences (grep exécuté) |
| Suppressions lint (`noqa`) | §R7 | 3 matches : L35, L37, L145 — tous `# noqa: N803` sur paramètres ABC (`X_train`, `X_val`, `X`), pré-existants, non modifiés dans ce diff. Justifiés (noms imposés par spec). |
| `per-file-ignores` dans `pyproject.toml` | §R7 | Non modifié dans ce diff |
| Print résiduel | §R7 | 0 occurrences (grep exécuté) |
| Shift négatif (`.shift(-`) | §R3 | 0 occurrences (grep exécuté) |
| Legacy random API | §R4 | 0 occurrences dans SRC et TEST (grep exécuté) |
| TODO/FIXME/HACK/XXX | §R7 | 0 occurrences (grep exécuté) |
| Chemins hardcodés `/tmp`, `C:\` | §R7 | 0 occurrences dans tests (grep exécuté) |
| Imports absolus `__init__.py` | §R7 | N/A — aucun `__init__.py` modifié |
| Registration manuelle tests | §R7 | 0 occurrences (seule mention dans docstring de helper) |
| Mutable default arguments | §R6 | 0 occurrences (grep exécuté) |
| `open()` / `.read_text()` dans SRC | §R6 | 0 occurrences (grep exécuté) |
| Comparaison booléenne identité | §R6 | 0 occurrences (grep exécuté) |
| `isfinite` checks | §R6 | 0 occurrences — N/A, `load()` ne valide pas de bornes numériques |
| Appels numpy compréhension | §R9 | 0 occurrences (grep exécuté) |
| Fixtures dupliquées | §R7 | 0 occurrences (grep exécuté) |

### B2 — Annotations par fichier (lecture diff)

#### `ai_trading/models/xgboost.py` (8 lignes ajoutées)

Diff total : 2 lignes supprimées (stub `NotImplementedError`), 9 lignes ajoutées.

- **L196-L205** — Implémentation de `load()` :
  ```python
  def load(self, path: Path) -> None:
      resolved = self._resolve_path(path)
      if not resolved.exists():
          raise FileNotFoundError(f"Model file not found: {resolved}")
      self._model = xgb.XGBRegressor()
      self._model.load_model(str(resolved))
  ```
  1. **Type safety** : `path` typé `Path`, `_resolve_path` appelle `Path(path)` pour garantir le type. ✅
  2. **Edge cases** : `path=None` → `Path(None)` → `TypeError` (propagée). `path=""` → résout vers CWD, `exists()` teste la présence → `FileNotFoundError` si absent. ✅
  3. **Fichier corrompu** : l'erreur XGBoost (`XGBoostError`) remonte sans fallback silencieux, conforme à la tâche et à la spec. ✅
  4. **Return contract** : `None`, mutation de `self._model`. Signature conforme à `BaseModel.load(path: Path) -> None`. ✅
  5. **Resource cleanup** : aucun fichier ouvert explicitement, XGBoost gère l'I/O en interne. ✅
  6. **Path creation** : `load()` ne crée pas de répertoires (lecture seule) → N/A. ✅
  7. **Cohérence doc/code** : docstring « Restore a trained XGBoost model from JSON format » → correct. ✅
  8. **Conformité spec §7.3** : la spec montre `_resolve_path(path, "xgboost_model.json")` avec deux arguments, l'implémentation utilise `_resolve_path(path)` avec le nom de fichier dans la constante module `_MODEL_FILENAME`. Déviation introduite en #066 (save), pas dans ce diff. Comportement fonctionnellement identique. ✅

  RAS après lecture complète du diff (8 lignes d'implémentation).

#### `tests/test_xgboost_model.py` (133 lignes ajoutées RED + 13 modifiées GREEN)

- **L122-L125** — Classe `TestXGBoostRegModelStubs` vidée :
  ```python
  class TestXGBoostRegModelStubs:
      """#060 — Remaining stub methods (none currently)."""
      pass
  ```
  Sévérité : **MINEUR**
  Observation : classe de test vide avec `pass`. Le test `test_load_raises_not_implemented` a été supprimé (attendu — le stub est remplacé), mais la classe résiduelle est du code mort. §R7 : « Pas de code mort ».
  Suggestion : supprimer la classe `TestXGBoostRegModelStubs` entièrement, ou la laisser avec uniquement le docstring (sans `pass`).

- **L1070-L1190** — Classe `TestXGBoostRegModelLoad` (9 tests) :
  - `test_load_raises_file_not_found_nonexistent_file` : fichier inexistant → `FileNotFoundError`. ✅
  - `test_load_raises_file_not_found_nonexistent_dir` : répertoire vide → `FileNotFoundError` (default file absent). ✅
  - `test_load_from_directory_path` : `save(dir)` → `load(dir)` → `_model is not None`. ✅
  - `test_load_from_explicit_file_path` : chemin fichier explicite. ✅
  - `test_predict_works_after_load` : vérifie ndarray, shape, dtype float32 après load. ✅
  - `test_round_trip_bit_exact_directory` : `assert_array_equal` avant/après round-trip via directory. ✅
  - `test_round_trip_bit_exact_explicit_path` : idem via chemin fichier explicite. ✅
  - `test_load_overwrites_existing_model` : charge sur un modèle fresh → predictions identiques. ✅
  - `test_load_uses_json_format` : vérifie que le fichier est du JSON parseable (sécurité anti-pickle). ✅

  Note : les tests qui appellent `predict()` après `load()` configurent `new_model._feature_names = fitted_model._feature_names` manuellement. C'est nécessaire car `load()` ne restaure pas `_feature_names` (non défini dans la spec §7.3). Le design est cohérent : dans le pipeline, le trainer/orchestrateur gère le contexte.

  RAS après lecture complète du diff (124 lignes de tests).

#### `docs/tasks/MX-2/067__ws_xgb5_load_json.md`

- Passage `TODO` → `DONE`, critères et checklist cochés. Conforme. ✅

### B3 — Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères | ✅ | 9/9 critères mappés (voir tableau Phase A) |
| Cas nominaux + erreurs + bords | ✅ | 2 erreur, 4 nominal, 1 boundary (overwrite), 2 round-trip bit-exact |
| Boundary fuzzing | ✅ | `path` : fichier inexistant, dir vide, dir avec fichier, fichier explicite — couvert. Pas de paramètres numériques. |
| Déterministes | ✅ | Seeds fixées `_RNG_PRED = np.random.default_rng(65)` |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé, tous `tmp_path` |
| Tests registre réalistes | ✅ | `importlib.reload` utilisé dans `_reload_xgboost_module()` |
| Contrat ABC complet | ✅ | `load()` documenté pour directory OU fichier → les deux variantes testées |
| Pas de skip/xfail | ✅ | Aucun `@pytest.mark.skip` ni `xfail` dans le diff |
| Données synthétiques | ✅ | Données RNG + fitted_model fixture |

### B4 — Code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback. `FileNotFoundError` explicite. Pas de fallback corrompu. |
| §R10 Defensive indexing | ✅ | N/A — pas d'indexation dans `load()` |
| §R2 Config-driven | ✅ | N/A — `load()` ne lit aucun paramètre config (méthode I/O pure) |
| §R3 Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. N/A — `load()` ne manipule pas de données temporelles |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random. N/A — `load()` est déterministe |
| §R5 Float conventions | ✅ | N/A — `load()` ne crée pas de tenseurs |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 open(), 0 bool identity. `load_model(str(resolved))` — conversion Path→str pour API XGBoost. |

### B5 — Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage et style | ✅ | `snake_case` cohérent, nommage clair |
| Pas de code mort/debug | ⚠️ | `TestXGBoostRegModelStubs` vide avec `pass` (MINEUR) |
| Imports propres / relatifs | ✅ | Suppression `from pathlib import Path` inutilisé (nettoyage correct) |
| DRY | ✅ | `_resolve_path` réutilisé de `save()`, pas de duplication |
| `.gitignore` | ✅ | Pas de fichiers temporaires/générés dans la PR |

### B5-bis — Bonnes pratiques métier

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts | ✅ | Sérialisation JSON XGBoost standard |
| Nommage métier | ✅ | `load`, `save`, `xgboost_model.json` — clair |
| Séparation responsabilités | ✅ | `load()` fait uniquement de l'I/O modèle |
| Invariants de domaine | ✅ | N/A pour la sérialisation |
| Cohérence unités/échelles | ✅ | N/A |
| Patterns calcul financier | ✅ | N/A |

### B6 — Conformité spec v1.0

| Critère | Verdict | Preuve |
|---|---|---|
| Spec §7.3 load() | ✅ | Implémentation conforme : `XGBRegressor()` + `load_model(str(resolved))` + `FileNotFoundError` |
| Plan d'implémentation | ✅ | WS-XGB-5.2 `load()` |
| Formules doc vs code | ✅ | Pas de formule mathématique dans `load()` |
| Pas d'exigence inventée | ✅ | Uniquement ce que la spec et la tâche exigent |

### B7 — Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `load(self, path: Path) -> None` conforme à `BaseModel.load` (L261 base.py) |
| Registres et conventions | ✅ | Même pattern que `save()` dans la même classe |
| Imports croisés | ✅ | `xgb`, `Path`, `BaseModel` — tous existants dans Max6000i1 |
| Forwarding kwargs | ✅ | N/A — `load()` ne délègue pas de kwargs |
| Cohérence des defaults | ✅ | N/A |

---

## Remarques

1. [MINEUR] Classe de test vide `TestXGBoostRegModelStubs`
   - Fichier : `tests/test_xgboost_model.py`
   - Ligne(s) : L122-L125
   - Code : `class TestXGBoostRegModelStubs: ... pass`
   - Observation : le test `test_load_raises_not_implemented` a été supprimé (attendu), mais la classe résiduelle avec `pass` est du code mort (§R7).
   - Suggestion : supprimer la classe entièrement, ou laisser uniquement le docstring sans `pass`.

---

## Résumé

L'implémentation de `load()` est minimale (8 lignes), correcte, et conforme à la spec §7.3. Les 9 tests couvrent exhaustivement tous les critères d'acceptation (erreur, nominal, round-trip bit-exact, sécurité JSON). Le processus TDD est respecté (2 commits RED/GREEN sans parasite). Un seul item mineur : la classe de test vidée `TestXGBoostRegModelStubs` avec `pass` constitue du code mort résiduel.

---

RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 0
- Mineurs : 1
- Rapport : `docs/tasks/MX-2/067/review_v1.md`
