# Revue PR — [WS-XGB-5] #068 — Gate G-XGB-Ready

Branche : `task/068-gate-xgb-ready`
Tâche : `docs/tasks/MX-2/068__gate_xgb_ready.md`
Date : 2026-03-03

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

La branche ajoute 8 tests de gate dans `TestGateXGBReady` couvrant les 7 critères fonctionnels du gate G-XGB-Ready. Les tests passent (1756 passed), ruff est clean. Deux points nécessitent correction : (1) le critère de couverture AC7 est marqué `[x]` avec "100% atteint" alors que la commande d'automatisation du plan échoue (58.43% combiné), et (2) le test AC5 utilise une registration manuelle au lieu de `_reload_xgboost_module()`.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/068-gate-xgb-ready` | ✅ | `git branch --show-current` → `task/068-gate-xgb-ready` |
| Commit RED présent | ✅ | `077e1f7 [WS-XGB-5] #068 RED: tests gate G-XGB-Ready` |
| Commit GREEN présent | ✅ | `79294ba [WS-XGB-5] #068 GREEN: gate G-XGB-Ready validé` |
| RED contient uniquement des tests | ✅ | `git show --stat 077e1f7` → `tests/test_xgboost_model.py | 155 insertions(+)` (1 fichier) |
| GREEN contient implémentation + tâche | ✅ | `git show --stat 79294ba` → `docs/tasks/MX-2/068__gate_xgb_ready.md` + `tests/test_xgboost_model.py` (2 fichiers) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → 2 commits exactement |

### Tâche

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | Diff : `TODO` → `DONE` |
| Critères d'acceptation cochés | ⚠️ 9/9 cochés (voir WARNING #1) | Diff : tous `[ ]` → `[x]` |
| Checklist cochée | ✅ 7/9 | 7 cochés, 2 non cochés attendus (commit GREEN + PR = chicken-and-egg) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1756 passed**, 12 deselected, 0 failed ✅ |
| `ruff check ai_trading/ tests/` | **All checks passed** ✅ |

**Phase A : PASS** — continuation vers Phase B.

---

## Phase B — Code Review

### Fichiers modifiés

```
tests/test_xgboost_model.py     (161 lignes ajoutées/modifiées)
docs/tasks/MX-2/068__gate_xgb_ready.md  (doc uniquement)
```

Aucun fichier source (`ai_trading/`) modifié — cohérent avec une tâche de gate.

### Résultats du scan automatisé (B1)

| Pattern recherché | Résultat |
|---|---|
| §R1 Fallbacks (`or []`, `or {}`, `or ""`) | 0 occurrences (grep exécuté) |
| §R1 Except trop large (`except:`, `except Exception:`) | 0 occurrences (grep exécuté) |
| §R7 Suppressions lint (`noqa`) | 1 match L142 — **pré-existant**, hors diff (`import ai_trading.models  # noqa: F811, F401`) |
| §R7 Print résiduel | 0 occurrences (grep exécuté) |
| §R3 Shift négatif (`.shift(-`) | 0 occurrences (grep exécuté) |
| §R4 Legacy random API | 0 occurrences (grep exécuté) |
| §R7 TODO/FIXME/HACK/XXX | 0 occurrences (grep exécuté) |
| §R7 Chemins hardcodés (`/tmp`, `C:\`) | 0 occurrences (grep exécuté) |
| §R7 Imports absolus `__init__` | N/A (aucun `__init__.py` modifié) |
| §R7 Registration manuelle (`register_model`) | 1 match L59 docstring — faux positif. Mais voir **MINEUR #2** (AC5, L1309) |
| §R6 Mutable defaults (`def ...=[]`) | 0 occurrences (grep exécuté) |
| §R6 `open()` sans context manager | 0 occurrences (grep exécuté) |
| §R6 Comparaison booléenne identité (`is True`) | 0 occurrences (grep exécuté) |
| §R6 Dict collision silencieuse | L1309 `MODEL_REGISTRY["xgboost_reg"] = XGBoostRegModel` — voir MINEUR #2, intentionnel dans le test |
| §R9 Boucle Python sur array | 0 occurrences (grep exécuté) |
| §R6 isfinite | 0 occurrences (grep exécuté) — N/A (pas de code source modifié) |
| §R9 Appels numpy répétés | 0 occurrences (grep exécuté) |
| §R7 Fixtures dupliquées | 0 occurrences (grep exécuté) |
| `pyproject.toml` per-file-ignores | Pré-existant, non modifié par cette branche |

### Annotations par fichier (B2)

#### `tests/test_xgboost_model.py` (diff : 161 lignes)

Lecture complète du diff `git diff Max6000i1...HEAD -- tests/test_xgboost_model.py`.

- **L1195-1201** `_RNG_GATE = np.random.default_rng(68)` — Données synthétiques avec seed déterministe dédiée (68), séparée du RNG global (seed 60). Seeds utilisées pour float32.
  Sévérité : RAS

- **L1220-1231** `_fit_model()` helper — Mutate `config.models.xgboost.n_estimators = 10` sur l'objet config reçu. Acceptable car `default_config` est une fixture instanciée par test, mais le pattern est fragile si la fixture devenait scope=session.
  Sévérité : RAS (fixture scope=function)

- **L1235-1237** `test_ac1_early_stopping_converges` — Assertion `result["best_iteration"] < n_est` après mutation `n_estimators = 10`. Correct : vérifie le critère gate 1.
  Sévérité : RAS

- **L1241-1244** `test_ac2_predict_shape_and_dtype` — Vérifie shape `(N,)` et dtype `float32`. Correct : critère gate 2.
  Sévérité : RAS

- **L1249-1265** `test_ac3_save_load_round_trip_bit_exact` — Round-trip save→load→predict avec `np.testing.assert_array_equal`. L1262 : `new_model._feature_names = model._feature_names` (accès attribut privé). Pattern pré-existant dans le fichier (L1112, L1123, L1133, L1148, L1161). Cohérent avec le contrat actuel de `load()`.
  Sévérité : RAS (pattern pré-existant)

- **L1269-1300** `test_ac4_determinism_two_fits_same_seed` — Deux cycles complets `fit()+predict()` avec `copy.deepcopy(default_config)`, `run_dir` séparés (`run1`/`run2`). Assertion bit-exact via `assert_array_equal`. Correct : critère gate 4.
  Sévérité : RAS

- **L1304-1314** `test_ac5_registry_entry` — ⚠️ Voir **MINEUR #2** ci-dessous.

- **L1318-1349** `test_ac6_*` (3 tests) — Couvrent `ValueError` (shape 2D), `TypeError` (float64), `RuntimeError` (predict sans fit). Correct : critère gate 6.
  Sévérité : RAS

#### `docs/tasks/MX-2/068__gate_xgb_ready.md`

Passage de `TODO` à `DONE`, cochage des AC et de la checklist. RAS sauf le **WARNING #1** sur l'AC7 (couverture).

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | Tests dans `test_xgboost_model.py`, `#068` dans docstrings |
| Couverture des critères | ✅ | AC1→`test_ac1`, AC2→`test_ac2`, AC3→`test_ac3`, AC4→`test_ac4`, AC5→`test_ac5`, AC6→3 tests, AC7→externe |
| Cas nominaux + erreurs + bords | ✅ | Nominal (AC1-AC4), erreurs (AC6 × 3), bords (early stopping convergence) |
| Boundary fuzzing | ✅ | N/A — gate tests valident des propriétés, pas des paramètres numériques arbitraires |
| Déterministes | ✅ | `_RNG_GATE = np.random.default_rng(68)` — seed fixée |
| Données synthétiques | ✅ | `_X_TRAIN_GATE`, `_Y_TRAIN_GATE` etc. — pas de réseau |
| Portabilité chemins | ✅ | Scan B1 : 0 match `/tmp`. Utilise `tmp_path` partout |
| Tests registre réalistes | ⚠️ | Voir MINEUR #2 — AC5 utilise registration manuelle au lieu de `_reload_xgboost_module()` |
| Contrat ABC complet | N/A | Pas de nouvelle méthode abstraite |
| Tests désactivés (`skip`/`xfail`) | ✅ | `grep -n 'skip\|xfail' tests/test_xgboost_model.py` dans le diff → 0 occurrence |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 match. Pas de code source modifié |
| §R10 Defensive indexing | N/A | Pas de code source modifié |
| §R2 Config-driven | ✅ | `_fit_model` lit config ; `n_estimators` overridé pour performance (acceptable dans un test) |
| §R3 Anti-fuite | N/A | Pas de code source modifié |
| §R4 Reproductibilité | ✅ | `np.random.default_rng(68)` — API moderne, seed fixée |
| §R5 Float conventions | ✅ | Données `.astype(np.float32)`, assertions dtype float32 |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable default, 0 `open()`, 0 `is True` |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage et style | ✅ | snake_case cohérent |
| Pas de code mort/debug | ✅ | Scan B1 : 0 `print()`, 0 TODO |
| Imports propres / relatifs | ✅ | Imports standard en haut du fichier, import local dans AC5 |
| DRY | ✅ | Helper `_fit_model` factorise le code de fit |
| Fixtures partagées | ✅ | Utilise `default_config` et `tmp_path` de conftest, pas de duplication |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts | N/A | Tests de validation gate, pas de logique financière |
| Nommage métier | ✅ | `early_stopping`, `predict`, `save`, `load` — cohérent |
| Séparation des responsabilités | ✅ | Tests organisés par critère AC |
| Invariants de domaine | N/A | Pas de code source |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Preuve |
|---|---|---|
| Plan d'implémentation | ✅ | 7 critères du plan G-XGB-Ready (`docs/plan/models/implementation_xgboost.md` L93-109) fidèlement reproduits dans les tests |
| Formules doc vs code | N/A | Gate : pas de formule |
| Pas d'exigence inventée | ✅ | Tous les AC tracent vers le plan |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `fit()`, `predict()`, `save()`, `load()` appelés avec les mêmes signatures que les tests existants |
| Registres et conventions | ✅ | `MODEL_REGISTRY["xgboost_reg"]`, `output_type == "regression"` — cohérent avec `base.py` |
| Imports croisés | ✅ | Importe `MODEL_REGISTRY` de `base.py`, `XGBoostRegModel` de `xgboost.py` — symboles existants sur `Max6000i1` |
| Conventions numériques | ✅ | float32 pour données, `assert_array_equal` pour bit-exactness |

### Couverture gate (vérification spécifique)

```
$ pytest tests/test_adapter_xgboost.py tests/test_xgboost_model.py -v \
    --cov=ai_trading.models.xgboost --cov=ai_trading.data.dataset \
    --cov-fail-under=90 --cov-report=term-missing

Name                           Stmts   Miss  Cover   Missing
------------------------------------------------------------
ai_trading/data/dataset.py        84     69    18%   63-159, 262-320
ai_trading/models/xgboost.py      82      0   100%
------------------------------------------------------------
TOTAL                            166     69    58%
FAIL Required test coverage of 90% not reached. Total coverage: 58.43%
```

La commande d'automatisation du plan **échoue**. `xgboost.py` est à 100%, mais `dataset.py` à 18% depuis ces 2 fichiers de test.

---

## Remarques

### 1. [WARNING] AC7 — Critère de couverture marqué `[x]` mais commande d'automatisation en échec

- **Fichier** : `docs/tasks/MX-2/068__gate_xgb_ready.md`
- **Ligne(s)** : AC7 (critère de couverture)
- **Description** : Le critère d'acceptation est coché `[x]` avec la mention "**100%** atteint", mais la commande d'automatisation définie dans le plan (`pytest tests/test_adapter_xgboost.py tests/test_xgboost_model.py -v --cov=ai_trading.models.xgboost --cov=ai_trading.data.dataset --cov-fail-under=90`) échoue à 58.43% (xgboost.py: 100%, dataset.py: 18%). Même en ajoutant `test_sample_builder.py`, le total n'atteint que 83.13%.
- **Impact** : Le verdict GO repose sur 7 critères dont un n'est pas factuellement validé par la commande spécifiée. La mention "100%" est trompeuse (ne s'applique qu'à xgboost.py).
- **Suggestion** :
  - Option A : corriger la commande d'automatisation dans la tâche pour ne mesurer que `--cov=ai_trading.models.xgboost` (la couverture pertinente pour le gate XGBoost) — le 100% est alors atteint.
  - Option B : inclure les fichiers de test supplémentaires nécessaires pour atteindre 90% sur dataset.py (ajouter `test_sample_builder.py` et `test_label_target.py` à la commande).
  - Dans les deux cas, corriger l'annotation "100% atteint" pour qu'elle corresponde à la réalité mesurée.

### 2. [MINEUR] AC5 — Registration manuelle au lieu de `_reload_xgboost_module()`

- **Fichier** : `tests/test_xgboost_model.py`
- **Ligne(s)** : 1309
- **Description** : Le test AC5 utilise `MODEL_REGISTRY["xgboost_reg"] = XGBoostRegModel` (registration manuelle) au lieu du helper existant `_reload_xgboost_module()` qui teste le vrai side-effect du décorateur `@register_model`. Le commit RED (077e1f7) utilisait correctement `_reload_xgboost_module()`, mais le commit GREEN l'a remplacé par l'assignation directe. Le commentaire "Re-register since autouse fixture clears the registry" reconnaît le problème mais utilise un contournement plutôt que le mécanisme validé.
- **Impact** : Le test valide les propriétés (clé, classe, output_type) mais ne teste pas le side-effect réel du décorateur. Les tests existants dans `TestXGBoostRegModelRegistry` (L73-82) utilisent `_reload_xgboost_module()` avec succès malgré la même fixture autouse.
- **Suggestion** : Remplacer par :
  ```python
  def test_ac5_registry_entry(self):
      """#068 AC5 — 'xgboost_reg' in MODEL_REGISTRY with output_type 'regression'."""
      mod = _reload_xgboost_module()
      assert "xgboost_reg" in MODEL_REGISTRY
      cls = MODEL_REGISTRY["xgboost_reg"]
      assert cls is mod.XGBoostRegModel
      assert cls.output_type == "regression"
  ```

### 3. [MINEUR] Commit RED pas réellement RED

- **Fichier** : N/A (processus TDD)
- **Description** : Le commit RED (077e1f7) contient 8 tests qui passent tous immédiatement (`8 passed, 0 failed` vérifié par exécution). Aucun test n'était en échec au moment du commit RED. Le commit GREEN ne fait que modifier le test AC5 (regression du reload) et mettre à jour la doc.
- **Impact** : Pour une tâche de gate (validation de code existant), l'absence de phase RED est structurellement attendue — les tests vérifient du code déjà implémenté. Cependant, la checklist affirme "Tests RED écrits avant implémentation" `[x]` alors qu'il n'y a pas d'implémentation à écrire et que les tests étaient GREEN dès le départ.
- **Suggestion** : Ajuster le wording de la checklist pour les tâches de type gate (ex : "Tests de gate écrits et exécutés" au lieu de "Tests RED écrits avant implémentation").

---

## Résumé

| Sévérité | Nombre |
|---|---|
| BLOQUANT | 0 |
| WARNING | 1 |
| MINEUR | 2 |

Les 8 tests de gate couvrent fidèlement les 7 critères fonctionnels du plan G-XGB-Ready. Le code est propre, déterministe, et sans violation des règles non négociables. Le WARNING sur la couverture nécessite une correction factuelle (annotation ou périmètre de la commande) avant merge.

---

```
RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 1
- Mineurs : 2
- Rapport : docs/tasks/MX-2/068/review_v1.md
```
