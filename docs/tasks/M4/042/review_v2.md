# Revue PR — [WS-10] #042 — Agrégation inter-fold et stitched equity

Branche : `task/042-aggregation`
Tâche : `docs/tasks/M4/042__ws10_aggregation.md`
Date : 2026-03-02
Itération : v2 (re-review après corrections v1)

## Verdict global : ✅ CLEAN

## Résumé

Re-review v2 de la tâche #042. Les 4 items identifiés en v1 (WARNING equity div/0, MINEUR docstring path, MINEUR mdd_cap boundary tests, MINEUR RuntimeWarnings) sont tous corrigés correctement dans le commit FIX `ae9e373`. Le code est propre, conforme à la spec §14.3/§14.4/§13.4 et les 42 tests passent (1202 total suite). Aucun nouvel item identifié.

---

## Contexte v1 → v2

| Item v1 | Sévérité | Fix | Vérifié |
|---|---|---|---|
| equity div/0 non protégé dans `stitch_equity_curves` | WARNING | Validation `original_start == 0.0` ajoutée L173-176 + test `test_equity_starting_at_zero_raises` | ✅ |
| docstring path `calibration.mdd_cap` → `thresholding.mdd_cap` | MINEUR | Corrigé L206 | ✅ |
| Tests mdd_cap boundary manquants (NaN, inf) | MINEUR | Tests `test_mdd_cap_nan_raises` et `test_mdd_cap_inf_raises` ajoutés | ✅ |
| RuntimeWarnings non supprimés dans tests single-fold | MINEUR | `warnings.catch_warnings()` ajouté dans `test_single_fold` et `test_single_non_none_among_nones` | ✅ |

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/042-aggregation` | ✅ | `git branch --show-current` → `task/042-aggregation` |
| Commit RED présent | ✅ | `aed355f` — `[WS-10] #042 RED: tests for aggregate_fold_metrics, stitch_equity_curves, check_acceptance_criteria, derive_comparison_type` |
| Commit RED = tests uniquement | ✅ | `git show --stat aed355f` → 1 fichier : `tests/test_aggregation.py` (514 insertions) |
| Commit GREEN présent | ✅ | `623c1df` — `[WS-10] #042 GREEN: aggregate_fold_metrics, stitch_equity_curves, check_acceptance_criteria, derive_comparison_type` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 623c1df` → 4 fichiers : `aggregation.py`, `__init__.py`, tâche, tests (ajustements) |
| Commit FIX post-review | ✅ | `ae9e373` — `[WS-10] #042 FIX: validate equity>0 in stitch, fix docstring path, add mdd_cap boundary tests, suppress RuntimeWarnings` |
| Pas de commits parasites | ✅ | 3 commits : RED → GREEN → FIX. Séquence correcte. |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (13/13) |
| Checklist cochée | ✅ (6/8 — les 2 non cochés sont commit GREEN et PR, responsabilité orchestrateur) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/test_aggregation.py -v --tb=short` | **42 passed**, 0 failed |
| `pytest tests/ -v --tb=short` | **1202 passed**, 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux | `grep 'or []', 'or {}', 'or ""', 'if...else'` | 0 occurrences |
| §R1 Except trop large | `grep 'except:$\|except Exception:'` | 0 occurrences |
| §R7 Suppressions lint (noqa) | `grep 'noqa'` | 3 matches : `__init__.py` L4-6 (F401, side-effect imports — justifié) |
| §R7 Print résiduel | `grep 'print('` | 0 occurrences |
| §R3 Shift négatif | `grep '.shift(-'` | 0 occurrences |
| §R4 Legacy random API | `grep 'np.random.seed\|randn\|RandomState\|random.seed'` | 0 occurrences |
| §R7 TODO/FIXME orphelins | `grep 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences |
| §R7 Chemins hardcodés | `grep '/tmp\|C:\\'` (tests) | 0 occurrences |
| §R7 Imports absolus __init__ | `grep 'from ai_trading\.'` (__init__.py) | 0 occurrences (relatif `from . import` utilisé) |
| §R7 Registration manuelle tests | `grep 'register_model\|register_feature'` | 0 occurrences |
| §R6 Mutable defaults | `grep 'def.*=\[\]\|def.*={}'` | 0 occurrences |
| §R6 open() sans context manager | `grep 'open(\|.read_text'` | 0 occurrences |
| §R6 Bool identité | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences |
| §R6 isfinite | `grep 'isfinite'` | 1 match : L218 `math.isfinite(mdd_cap)` — correct |
| §R9 Boucle Python sur numpy | `grep 'for .* in range(.*):' src` | 0 occurrences |
| §R9 Numpy compréhension | `grep 'np\.[a-z]*(.*for .* in '` | 0 occurrences |
| §R7 Fixtures dupliquées | `grep 'load_config.*configs/'` tests | 0 occurrences |
| §R7 per-file-ignores (pyproject.toml) | `grep` | Aucune entrée ajoutée par cette PR |

### Annotations par fichier (B2)

#### `ai_trading/metrics/aggregation.py` (276 lignes)

- **L19-52** : constantes `_TRADING_METRICS`, `_PREDICTION_METRICS`, `_AGGREGATED_METRICS`, `_EXCLUDED_METRICS`. Conforme à la liste exhaustive I-04 de la tâche. ✅
- **L60-102** `aggregate_fold_metrics` : validation len > 0, boucle sur `_AGGREGATED_METRICS`, filtrage None via `.get()`, `np.float64`, `ddof=1`, cast `float()`. RAS.
- **L112-186** `stitch_equity_curves` : validation colonnes requises, rescaling par `carry / original_start`, warning gap via logger. **Fix v1 vérifié** : L173-176 valide `original_start == 0.0` avant la division. ✅
- **L194-243** `check_acceptance_criteria` : **Fix v1 vérifié** : L218 `math.isfinite(mdd_cap) or mdd_cap <= 0` rejecte NaN/inf/négatif/zéro. L206 docstring corrigé `thresholding.mdd_cap`. ✅ Conditions `<=0`, `<=1.0`, `>= mdd_cap` conformes §14.4.
- **L252-275** `derive_comparison_type` : validation chaîne vide, `buy_hold` → contextual, tout le reste → go_nogo. Conforme spec.

RAS après lecture complète du diff (276 lignes source).

#### `ai_trading/metrics/__init__.py` (7 lignes)

- **L4** : ajout `aggregation, # noqa: F401`. Import relatif (`from . import`). Justifié (side-effect import pour disponibilité via le package). ✅

RAS.

#### `tests/test_aggregation.py` (543 lignes)

- **L1-3** : docstring avec `Task #042 — WS-10`. ✅
- **L14-19** : imports directs depuis `ai_trading.metrics.aggregation`. ✅
- **L100-109** `_make_equity_df` : helper synthétique, `pd.date_range` avec tz UTC. ✅ Données synthétiques.
- **L212-221** `test_single_fold` : **Fix v1 vérifié** — `warnings.catch_warnings()` + `simplefilter("ignore", RuntimeWarning)` avant l'appel. Vérifie `math.isnan(net_pnl_std)`. ✅
- **L226-237** `test_single_non_none_among_nones` : même fix RuntimeWarning. ✅
- **L398-403** `test_equity_starting_at_zero_raises` : **Fix v1 vérifié** — teste fold 1 avec equity [0.0, 0.5], attend `ValueError("equity starting at 0.0")`. ✅
- **L500-513** `test_mdd_cap_nan_raises` + `test_mdd_cap_inf_raises` : **Fix v1 vérifié** — testent `float("nan")` et `float("inf")`, attendent `ValueError("mdd_cap")`. ✅
- **L345** `test_export_csv` : utilise `tmp_path` (fixture pytest). ✅ Portabilité chemins.

RAS après lecture complète du diff (543 lignes tests).

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage `test_aggregation.py` | ✅ | Fichier unique, ID #042 en docstring |
| Couverture des critères d'acceptation | ✅ | Mapping ci-dessous |
| Cas nominaux + erreurs + bords | ✅ | 42 tests : 4 classes couvrant nominal (3 folds, 2 folds), erreurs (empty, missing cols, equity=0), bords (single fold, all None, NaN std) |
| Boundary fuzzing : mdd_cap | ✅ | `mdd_cap=0.0` (L488), `mdd_cap=-0.1` (L494), `mdd_cap=NaN` (L501), `mdd_cap=inf` (L508) |
| Boundary fuzzing : fold_metrics_list empty | ✅ | `test_empty_fold_list_raises` |
| Boundary fuzzing : fold_equities empty | ✅ | `test_empty_folds_list_raises` |
| Boundary fuzzing : single fold | ✅ | `test_single_fold`, `test_single_fold_no_rescaling` |
| Boundary fuzzing : equity start = 0 | ✅ | `test_equity_starting_at_zero_raises` |
| Déterministes | ✅ | Pas d'aléatoire, données synthétiques fixes |
| Portabilité chemins | ✅ | `tmp_path` utilisé, scan B1 = 0 `/tmp` |
| Tests registre réalistes | N/A | Pas de registre dans ce module |
| Contrat ABC complet | N/A | Pas d'ABC |
| Pas de test désactivé | ✅ | 0 `skip`/`xfail` |

**Mapping critères d'acceptation → tests** :

| Critère | Test(s) |
|---|---|
| 3 folds → mean/std (ddof=1) | `test_three_folds_mean_std_correct`, `test_two_folds_exact_values` |
| Métriques exclues absentes | `test_excluded_keys_absent` |
| Null handling | `test_null_handling_omits_none`, `test_all_none_metric_yields_none`, `test_single_non_none_among_nones` |
| E_start[k+1] == E_end[k] | `test_two_folds_continuation`, `test_three_folds_chain` |
| CSV export (time_utc, equity, in_trade, fold) | `test_export_csv`, `test_columns_present` |
| Gaps inter-fold → warning | `test_gap_detection_warning` |
| Warning net_pnl_mean ≤ 0 | `test_warning_net_pnl_negative`, `test_warning_net_pnl_zero` |
| Warning profit_factor_mean ≤ 1.0 | `test_warning_profit_factor_below_one`, `test_warning_profit_factor_exactly_one` |
| Warning max_drawdown_mean ≥ mdd_cap | `test_warning_mdd_exceeds_cap`, `test_warning_mdd_equals_cap` |
| comparison_type | `test_buy_hold_contextual`, `test_no_trade_go_nogo`, `test_sma_rule_go_nogo`, `test_xgboost_go_nogo` |
| Scénarios nominaux + erreurs + bords | Couverts par 42 tests (cf. liste) |
| Suite verte | 42 passed |
| ruff clean | All checks passed |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback, 0 except large. Validation explicite : `len == 0 → raise`, `missing cols → raise`, `equity == 0 → raise`, `isfinite + > 0`, `empty string → raise`. |
| §R10 Defensive indexing | ✅ | `ec_copy["equity"].iloc[-1]` et `original_equity[0]` sont sûrs car les DataFrames sont validés non-vides (colonnes requises vérifiées). `pd.concat` avec `ignore_index=True`. |
| §R2 Config-driven | ✅ | `mdd_cap` passé en paramètre (provient de `configs/default.yaml` L109). Aucune constante magique hardcodée — les listes de métriques sont des constantes de module clairement nommées. |
| §R3 Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. Pas de données futures accédées. Module d'agrégation opère sur des métriques déjà calculées. |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random. Module déterministe (mean/std/concat). |
| §R5 Float conventions | ✅ | `np.float64` explicite pour les arrays de métriques (L97). Cast `float()` pour les résultats. |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 open sans context manager, 0 bool identity. `math.isfinite` utilisé pour validation NaN/inf (L218). |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Tous identifiants snake_case. |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO/FIXME. |
| Imports propres / relatifs | ✅ | `__init__.py` utilise `from . import`. Imports triés. |
| DRY | ✅ | Pas de duplication. Constantes centralisées dans `_AGGREGATED_METRICS`. |
| noqa justifiés | ✅ | 3× `F401` dans `__init__.py` pour side-effect imports — inévitable. |

### Conformité spec v1.0 (B6)

| Critère | Verdict |
|---|---|
| §14.3 — agrégation mean/std (ddof=1) | ✅ — `np.std(arr, ddof=1)` L100 |
| §14.3 — métriques exclues I-04 | ✅ — `_EXCLUDED_METRICS` non itérées |
| §14.4 — avertissements acceptance | ✅ — 3 conditions vérifiées (net_pnl ≤ 0, profit_factor ≤ 1.0, mdd ≥ cap) |
| §13.4 — stitched equity E_start[k+1] = E_end[k] | ✅ — rescaling par `carry / original_start` |
| §13.4 — gaps inter-fold | ✅ — warning émis, equity constante (rescaling maintient continuité) |
| Plan WS-10.3 | ✅ — 4 fonctions implémentées conformément au plan |
| Formules doc vs code | ✅ — pas d'off-by-one détecté |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `aggregate_fold_metrics` retourne `dict[str, float | None]`, consommable par JSON/downstream. |
| Noms de colonnes DataFrame | ✅ | `time_utc`, `equity`, `in_trade`, `fold` — cohérent avec `engine.py` equity curve output. |
| Clés de configuration | ✅ | `mdd_cap` existe dans `configs/default.yaml` L109 (`thresholding.mdd_cap`). |
| Structures de données partagées | ✅ | Fold metrics dict compatible avec `compute_trading_metrics` / `compute_prediction_metrics` output. |
| Conventions numériques | ✅ | float64 pour métriques, cohérent avec `prediction.py` et `trading.py`. |
| Imports croisés | ✅ | Imports uniquement stdlib + numpy + pandas. Pas de dépendance intra-projet. |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | Agrégation mean/std sur folds, stitched equity avec continuation — standard walk-forward. |
| Nommage métier cohérent | ✅ | `net_pnl`, `max_drawdown`, `sharpe`, `profit_factor`, `equity` — noms métier corrects. |
| Séparation des responsabilités | ✅ | Module dédié à l'agrégation inter-fold, séparé de prediction et trading metrics. |
| Invariants de domaine | ✅ | Equity > 0 validé pour rescaling. mdd_cap > 0 validé. |
| Cohérence unités/échelles | ✅ | Toutes métriques en même échelle que les modules amont. |
| Patterns de calcul financier | ✅ | Vectorisé numpy (np.mean, np.std). Pas de boucle Python sur arrays. |

---

## Remarques

Aucune.

## Actions requises

Aucune.

---

```
RÉSULTAT PARTIE B :
- Verdict : CLEAN
- Bloquants : 0
- Warnings : 0
- Mineurs : 0
- Rapport : docs/tasks/M4/042/review_v2.md
```
