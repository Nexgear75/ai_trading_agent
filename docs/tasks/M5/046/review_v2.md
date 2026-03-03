# Revue PR — [WS-11] #046 — Metrics builder

**Branche** : `task/046-metrics-builder`
**Tâche** : `docs/tasks/M5/046__ws11_metrics_builder.md`
**Date** : 2026-03-03
**Itération** : v2

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Les 3 warnings et 1 mineur technique identifiés en review v1 ont été corrigés par le commit FIX `fce74f7` : `allow_nan=False` sur les deux appels `json.dumps`, validation des sous-clés required dans `_normalize_prediction`/`_normalize_trading`, normalisation appliquée dans `write_fold_metrics`, et 7 tests ajoutés (49 total, tous green). Un seul item MINEUR persiste : le commit `bed7d31 maj README pipeline` hors périmètre TDD toujours présent sur la branche.

---

## Phase A — Compliance

### A1. Périmètre

Fichiers modifiés vs `Max6000i1` :

| Catégorie | Fichiers |
|---|---|
| Source (`ai_trading/`) | `ai_trading/artifacts/__init__.py`, `ai_trading/artifacts/metrics_builder.py` |
| Tests (`tests/`) | `tests/test_metrics_builder.py` |
| Docs | `docs/tasks/M5/046__ws11_metrics_builder.md` |
| Autres | `README.md` |

### A2. Structure branche & commits

```
fce74f7 (HEAD -> task/046-metrics-builder) [WS-11] #046 FIX: allow_nan=False, validate required sub-keys, normalize in write_fold_metrics
0ec7e67 [WS-11] #046 GREEN: metrics builder
11e6476 [WS-11] #046 RED: tests metrics builder
bed7d31 maj README pipeline
```

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/046-metrics-builder` | ✅ | `git branch --show-current` → `task/046-metrics-builder` |
| Commit RED présent | ✅ | `11e6476` — `[WS-11] #046 RED: tests metrics builder` |
| Commit GREEN présent | ✅ | `0ec7e67` — `[WS-11] #046 GREEN: metrics builder` |
| Commit RED = tests uniquement | ✅ | `git show --stat 11e6476` → `tests/test_metrics_builder.py` (775 insertions) |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 0ec7e67` → `__init__.py`, `metrics_builder.py`, tâche `.md` |
| Pas de commits parasites entre RED et GREEN | ✅ | Aucun commit entre `11e6476` (RED) et `0ec7e67` (GREEN) |
| Commit FIX post-review | ✅ | `fce74f7` — `[WS-11] #046 FIX: ...` : corrige les 3 warnings v1, contient src + tests (légitime pour un fix post-review) |
| Commit hors TDD sur la branche | ⚠️ | `bed7d31 maj README pipeline` — commit avant RED, `README.md` uniquement (voir remarque 1) |

### A3. Tâche associée

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (9/9) |
| Checklist cochée | ✅ (8/9 — seul « PR ouverte » non coché, attendu) |

**Vérification des critères d'acceptation :**

| AC | Description | Preuve code/test |
|---|---|---|
| AC-1 | Module importable | `TestImportable` (3 tests). `__init__.py` exporte `build_metrics`, `write_metrics`, `write_fold_metrics` via imports relatifs. |
| AC-2 | JSON valide contre schéma | `TestSchemaValidation` (7 tests) — `jsonschema.validate()` sur single fold, multi-fold, baseline, threshold none, zero trades, notes, comparison_type. |
| AC-3 | `metrics_fold.json` cohérent | `TestFoldMetricsCoherence` (3 tests) — `fold_loaded == fold_entry`. `write_fold_metrics` applique `_normalize_fold` (fix v1). |
| AC-4 | `n_samples_*` présents | `TestNSamplesFields` (3 tests) — presence, values, type `int`. Vérifiés dans `_REQUIRED_FOLD_KEYS`. |
| AC-5 | Métriques float64 | `TestFloat64Metrics` (5 tests) — `isinstance(val, float)` pour prediction, trading, aggregate mean, aggregate std. `_ensure_float()` convertit en Python float. |
| AC-6 | Test intégration | `TestIntegration` (2 tests) — build → write → reload → schema validate. Single et multi-fold (3). |
| AC-7 | Erreurs + bords | `TestStrictValidation` (12 tests) — empty run_id, empty folds, missing keys top-level et sous-clés, duplicates. `TestSchemaValidation.test_zero_trades_validates`, `test_threshold_none_validates`. |
| AC-8 | Suite verte | ✅ 49 passed, 0 failed |
| AC-9 | ruff clean | ✅ All checks passed |

### A4. CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1333 passed**, 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed!** |
| `pytest tests/test_metrics_builder.py -v` | **49 passed**, 0 failed |

✅ Phase A passée.

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux | `grep -n ' or \[\]\| or {}\| or ""\| or 0\b\| if .* else '` | 0 occurrences (grep exécuté) |
| §R1 Except trop large | `grep -n 'except:$\|except Exception:'` | 0 occurrences (grep exécuté) |
| §R7 Suppressions lint (noqa) | `grep -n 'noqa'` | 0 occurrences (grep exécuté) |
| §R7 per-file-ignores | `grep -n 'per-file-ignores' pyproject.toml` | L51 — non modifié par cette PR |
| §R7 Print résiduel | `grep -n 'print('` | 0 occurrences (grep exécuté) |
| §R3 Shift négatif | `grep -n '\.shift(-'` | 0 occurrences (grep exécuté) |
| §R4 Legacy random API | `grep -n 'np\.random\.seed\|...'` | 0 occurrences (grep exécuté) |
| §R7 TODO/FIXME | `grep -n 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences (grep exécuté) |
| §R7 Chemins hardcodés OS (tests) | `grep -n '/tmp\|/var/tmp\|C:\\'` | 0 occurrences (grep exécuté) |
| §R7 Imports absolus `__init__` | `grep -n 'from ai_trading\.'` (`__init__.py`) | 0 occurrences (grep exécuté) — imports relatifs ✅ |
| §R7 Registration manuelle tests | `grep -n 'register_model\|register_feature'` (tests) | 0 occurrences (grep exécuté) |
| §R6 Mutable defaults | `grep -n 'def .*=\[\]\|def .*={}'` | 0 occurrences (grep exécuté) |
| §R6 open() sans context manager | `grep -n '\.read_text\|open('` (src) | 0 occurrences — `Path.write_text()` utilisé ✅ |
| §R6 Comparaison booléenne identité | `grep -n 'is np\.bool_\|is True\|is False'` | 0 occurrences (grep exécuté) |
| §R6 Dict collision silencieuse | `grep -n '\[.*\] ='` | 7 matches : L83, 95, 98, 107, 193, 213, 215 — analysés : clés issues de tuples constants (`_PREDICTION_FLOAT_KEYS`, `_TRADING_FLOAT_KEYS`, `_TRADING_INT_KEYS`) ou clés fixes (`"mean"`, `"std"`, `"notes"`, `"comparison_type"`). **Faux positifs.** |
| §R9 Boucle Python range | `grep -n 'for .* in range(.*):' ` | 0 occurrences (grep exécuté) |
| §R6 isfinite check | `grep -n 'isfinite\|math.isfinite\|np.isfinite'` | 0 occurrences — NaN/inf caught by `allow_nan=False` at serialization ✅ |
| §R9 Appels numpy répétés | `grep -n 'np\.[a-z]*(.*for .* in '` | 0 occurrences (grep exécuté) |
| §R7 Fixtures dupliquées | `grep -n 'load_config.*configs/'` (tests) | 0 occurrences (grep exécuté) |
| §R7 Tests désactivés (skip/xfail) | `grep -n 'skip\|xfail'` (tests) | 0 occurrences (grep exécuté) |

### B2. Annotations par fichier

#### `ai_trading/artifacts/metrics_builder.py` (268 lignes)

**Corrections v1 vérifiées :**

- **L51-55** — `_REQUIRED_PREDICTION_KEYS` et `_REQUIRED_TRADING_KEYS` ajoutés. ✅ Correction du warning v1-2.
- **L77-79** — `_normalize_prediction` : validation `for key in _REQUIRED_PREDICTION_KEYS: if key not in prediction: raise KeyError(...)`. ✅ Strict.
- **L89-91** — `_normalize_trading` : validation `for key in _REQUIRED_TRADING_KEYS: if key not in trading: raise KeyError(...)`. ✅ Strict.
- **L238-240** — `write_metrics` : `json.dumps(..., allow_nan=False)`. ✅ Correction du warning v1-1.
- **L259-263** — `write_fold_metrics` : `_normalize_fold(fold_data)` puis `json.dumps(..., allow_nan=False)`. ✅ Correction des warnings v1-1 et v1-3.

**Analyse ligne par ligne (268 lignes, diff complet lu) :**

- **L63-65** — `_ensure_float` : `float(value)` convertit numpy float → Python float. Préserve `None` pour les champs nullable du schéma. ✅
- **L68-70** — `_ensure_int` : `int(value)` convertit numpy int → Python int. Usage interne, inputs = compteurs entiers provenant de `len()`. ✅
- **L103-106** — `_normalize_aggregate_block` : accès direct `block["mean"]`, `block["std"]` → `KeyError` si absent. ✅ Strict.
- **L111-127** — `_normalize_fold` : validation `_REQUIRED_FOLD_KEYS` (8 clés). ✅ Strict.
- **L175-188** — `build_metrics` : validation `run_id`, `folds_data` non vide, `strategy_info` keys, `aggregate_data` keys. ✅ Strict.
- **L190-199** — Détection duplicates `fold_id` via liste + `in`. O(n²) théorique, n = 3-5 folds. Acceptable.
- **L205-209** — `_normalize_fold` appliqué à chaque fold. ✅
- **L211-220** — `_normalize_aggregate_block` appliqué aux sous-dicts prediction/trading. Champs optionnels `notes`, `comparison_type` passés si présents. ✅
- **L234-240** — `write_metrics` : `run_dir.mkdir(parents=True, exist_ok=True)`. ✅ Path creation correcte (§R6).
- **L255-263** — `write_fold_metrics` : `fold_dir.mkdir(parents=True, exist_ok=True)`. ✅ Path creation correcte.
- **L121** — `period_test` et `threshold` passés tels quels (pas de normalisation interne). Le schéma JSON valide leur structure (`$ref: period`, `additionalProperties: false`). Acceptable — le module est un builder, pas un validateur exhaustif, et `jsonschema.validate()` est utilisé en test.

**RAS supplémentaire après lecture complète du diff.**

#### `ai_trading/artifacts/__init__.py` (31 lignes)

- Imports relatifs (`from .metrics_builder import ...`). ✅ Conforme §R7.
- `__all__` mis à jour avec `build_metrics`, `write_fold_metrics`, `write_metrics`. ✅
- RAS après lecture complète du diff (8 lignes ajoutées).

#### `tests/test_metrics_builder.py` (854 lignes, 49 tests)

**Corrections v1 vérifiées :**

- **L637-688** — 4 nouveaux tests de sous-clés manquantes : `test_missing_prediction_required_key_raises` (mae), `test_missing_trading_required_key_raises` (n_trades), `test_missing_prediction_directional_accuracy_raises`, `test_missing_trading_net_pnl_raises`. ✅ Correction du mineur v1-5.
- **L749-785** — 3 nouveaux tests NaN/inf : `test_write_metrics_rejects_nan`, `test_write_fold_metrics_rejects_nan`, `test_write_metrics_rejects_inf`. ✅ Testent le `allow_nan=False`.

**Analyse ligne par ligne :**

- **L24-29** — `SCHEMA_PATH` via `Path(__file__).resolve().parent.parent / "docs" / ...`. Portable. ✅
- **L32-34** — Fixture `metrics_schema` : charge le schéma JSON. ✅
- **L40-106** — Helpers `_minimal_*` : données synthétiques complètes et valides. ✅ Déterministe.
- `#046` dans les docstrings de chaque classe de test. ✅
- `tmp_path` pour tous les tests I/O. ✅ Portabilité chemins.
- Aucun `skip`/`xfail`. ✅
- Données synthétiques uniquement. ✅

**Panel de tests complet :**

| Classe | Tests | Couverture |
|---|---|---|
| `TestImportable` | 3 | AC-1 : import des 3 fonctions publiques |
| `TestSchemaValidation` | 7 | AC-2 : single fold, multi-fold, baseline, threshold none, 0 trades, notes, comparison_type |
| `TestFoldMetricsCoherence` | 3 | AC-3 : file creation, content match, coherence global/fold |
| `TestNSamplesFields` | 3 | AC-4 : presence, values, integer type |
| `TestFloat64Metrics` | 5 | AC-5 : prediction float, trading float, n_trades int, aggregate mean/std float |
| `TestIntegration` | 2 | AC-6 : end-to-end single et multi-fold |
| `TestStrictValidation` | 12 | AC-7 : empty run_id, empty folds, missing strategy_type/name, missing fold field, missing aggregate sub-keys, duplicate fold_ids, missing prediction/trading sub-keys |
| `TestWriteFunctions` | 8 | AC-8 : file creation, parent dirs, valid JSON, NaN/inf rejection |
| `TestBuildMetricsStructure` | 6 | AC-9 : top-level keys, strategy, folds list, aggregate, run_id passthrough, serializable |

### B3. Tests — résumé

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage `test_metrics_builder.py` | ✅ | Fichier correct |
| `#046` dans docstrings | ✅ | Toutes les 9 classes |
| Couverture des AC | ✅ | 9 AC → 9 classes de tests |
| Cas nominaux | ✅ | Schema validation, coherence, structure |
| Cas d'erreur | ✅ | 12 tests d'erreur (8 originaux + 4 sub-keys) |
| Cas de bords | ✅ | 0 trades, threshold none, 1 fold, nullable metrics None |
| Boundary fuzzing | ✅/N/A | Pas de paramètres numériques avec bornes continues (compteurs entiers) |
| Pas de `skip`/`xfail` | ✅ | Scan B1 : 0 occurrences |
| Déterministes | ✅ | Données synthétiques fixes, pas de seed nécessaire |
| Données synthétiques | ✅ | Helpers `_minimal_*`, pas de réseau |
| Portabilité chemins | ✅ | `tmp_path` partout, scan B1 : 0 `/tmp` |
| Tests registre réalistes | N/A | Pas de registre |
| Contrat ABC complet | N/A | Pas d'ABC |

### B4. Audit — Règles non négociables

#### B4a. Strict code (§R1)
- Scan B1 : 0 fallbacks silencieux, 0 except trop large. ✅
- Validation explicite : `_REQUIRED_FOLD_KEYS`, `_REQUIRED_PREDICTION_KEYS`, `_REQUIRED_TRADING_KEYS`. ✅
- `raise KeyError` / `raise ValueError` pour entrées invalides. ✅
- `allow_nan=False` → `ValueError` sur NaN/inf. ✅

#### B4a-bis. Defensive indexing (§R10)
- Pas d'indexation array/slice numérique. N/A pour ce module de sérialisation.

#### B4b. Config-driven (§R2)
- Le module ne lit aucune config — reçoit des dicts en entrée. N/A.

#### B4c. Anti-fuite (§R3)
- Module d'artefacts/sérialisation. Pas d'accès aux données temporelles. N/A.
- Scan B1 : 0 `.shift(-`. ✅

#### B4d. Reproductibilité (§R4)
- Pas de random nécessaire. Scan B1 : 0 legacy random. ✅

#### B4e. Float conventions (§R5)
- `_ensure_float` → Python `float` (float64). ✅
- `_ensure_int` → Python `int`. ✅

#### B4f. Anti-patterns Python (§R6)
- Scan B1 : 0 mutable defaults, 0 bool identity, 0 `open()` nu. ✅
- `Path.write_text()` raccourci. ✅
- Pas de comparaison float `==`. ✅
- Dict collision : 7 matches analysés → faux positifs (clés constantes). ✅
- `isfinite` absence compensée par `allow_nan=False` à la sérialisation. ✅

### B5. Qualité du code (§R7)

| Critère | Verdict | Preuve |
|---|---|---|
| snake_case | ✅ | Tout le code |
| Pas de code mort / TODO | ✅ | Scan B1 : 0 occurrences |
| Pas de print() | ✅ | Scan B1 : 0 occurrences |
| Imports propres / relatifs | ✅ | `__init__.py` relatifs, scan B1 : 0 imports absolus |
| DRY | ✅ | Pas de duplication entre `metrics_builder.py`, `manifest.py`, `run_dir.py` |
| Pas de noqa | ✅ | Scan B1 : 0 occurrences |
| Pas de fichiers générés | ✅ | |
| `__all__` à jour | ✅ | 3 fonctions exportées |

### B5-bis. Bonnes pratiques métier (§R9)
- Module de sérialisation d'artefacts — pas de calcul financier direct. N/A.

### B6. Cohérence avec les specs

| Critère | Verdict | Commentaire |
|---|---|---|
| Conforme à §15.3 spec v1.0 | ✅ | « metrics.json contient les métriques par fold et les agrégats inter-fold » — c'est exactement ce que fait `build_metrics` |
| Conforme à `metrics.schema.json` | ✅ | Structure de sortie validée par `jsonschema.validate()` dans 7 tests schéma + 2 intégration |
| `folds` : 8 champs required | ✅ | `_REQUIRED_FOLD_KEYS` |
| `metrics_fold.json` par fold | ✅ | `write_fold_metrics` avec normalisation |
| Plan WS-11.3 | ✅ | Builder + write global + write fold |
| Formules doc vs code | N/A | Module de sérialisation, pas de formules |

### B7. Cohérence intermodule (§R8)

| Critère | Verdict | Commentaire |
|---|---|---|
| `__init__.py` exporte les nouvelles fonctions | ✅ | `build_metrics`, `write_metrics`, `write_fold_metrics` |
| Pas d'imports croisés sur du code non-mergé | ✅ | Imports stdlib uniquement (`json`, `logging`, `Path`) |
| Signatures keyword-only, pas de default fallback | ✅ | `build_metrics(*, run_id, strategy_info, folds_data, aggregate_data)` |
| Pas de conflit avec `manifest.py`, `run_dir.py` | ✅ | Fonctions distinctes, pas de chevauchement |
| Clés de configuration | N/A | Module ne lit pas la config |

---

## Statut des items review v1

| # | Sévérité v1 | Description | Statut v2 | Preuve |
|---|---|---|---|---|
| 1 | WARNING | `json.dumps` sans `allow_nan=False` | ✅ CORRIGÉ | Diff `fce74f7` L238, L263 : `allow_nan=False` ajouté |
| 2 | WARNING | `_normalize_prediction`/`_normalize_trading` sans validation sous-clés | ✅ CORRIGÉ | Diff `fce74f7` L77-79, L89-91 : validation `_REQUIRED_PREDICTION_KEYS` / `_REQUIRED_TRADING_KEYS` |
| 3 | WARNING | `write_fold_metrics` sans normalisation | ✅ CORRIGÉ | Diff `fce74f7` L259 : `_normalize_fold(fold_data)` ajouté |
| 4 | MINEUR | Commit hors TDD `bed7d31 maj README` | ❌ NON CORRIGÉ | Toujours présent dans `git log` |
| 5 | MINEUR | Pas de test sous-clé prediction/trading manquante | ✅ CORRIGÉ | 4 nouveaux tests : `test_missing_prediction_required_key_raises`, `test_missing_trading_required_key_raises`, `test_missing_prediction_directional_accuracy_raises`, `test_missing_trading_net_pnl_raises` |

---

## Remarques

1. **[MINEUR]** Commit non-TDD sur la branche tâche (non corrigé depuis v1)
   - Description : Le commit `bed7d31 maj README pipeline` modifie `README.md` (297 insertions, 63 suppressions) sur la branche `task/046-metrics-builder`. Bien que placé avant le RED commit (pas entre RED et GREEN), il ajoute du bruit hors périmètre de la tâche dans la PR.
   - Suggestion : Rebaser ce commit sur `Max6000i1` indépendamment, ou le squasher hors de la branche.

---

## Résumé

| Sévérité | Count |
|---|---|
| BLOQUANT | 0 |
| WARNING | 0 |
| MINEUR | 1 |

Les 3 warnings de la review v1 ont été intégralement corrigés dans le commit FIX `fce74f7` : `allow_nan=False`, validation des sous-clés required, normalisation dans `write_fold_metrics`, accompagnés de 7 nouveaux tests (total 49, tous green). Code propre, bien structuré, conforme au schéma et à la spec. Seul le commit `bed7d31` hors périmètre reste à traiter.

---

RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 0
- Mineurs : 1
- Rapport : `docs/tasks/M5/046/review_v2.md`
