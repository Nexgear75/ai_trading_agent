# Revue PR — [WS-10] #042 — Agrégation inter-fold et stitched equity

Branche : `task/042-aggregation`
Tâche : `docs/tasks/M4/042__ws10_aggregation.md`
Date : 2026-03-02
Itération : v1

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé
Le module `metrics/aggregation.py` implémente correctement l'agrégation inter-fold (mean/std ddof=1), l'equity stitchée avec continuation, les avertissements §14.4 et la dérivation `comparison_type`. Le code est propre, bien structuré et les tests couvrent les cas nominaux, erreurs et bords. Cependant, 1 WARNING et 4 MINEURs sont identifiés, principalement un invariant non validé dans `stitch_equity_curves` (§R10) et des lacunes mineures de tests/docstring.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/042-aggregation` | ✅ | `git branch --show-current` → `task/042-aggregation` |
| Commit RED présent `[WS-10] #042 RED: ...` | ✅ | `aed355f` — `[WS-10] #042 RED: tests for aggregate_fold_metrics, stitch_equity_curves, check_acceptance_criteria, derive_comparison_type` |
| Commit RED = tests uniquement | ✅ | `git show --stat aed355f` → `tests/test_aggregation.py` (1 fichier, 514 insertions) |
| Commit GREEN présent `[WS-10] #042 GREEN: ...` | ✅ | `623c1df` — `[WS-10] #042 GREEN: aggregate_fold_metrics, stitch_equity_curves, check_acceptance_criteria, derive_comparison_type` |
| Commit GREEN = impl + task + tests | ✅ | `git show --stat 623c1df` → `ai_trading/metrics/__init__.py`, `ai_trading/metrics/aggregation.py`, `docs/tasks/M4/042__ws10_aggregation.md`, `tests/test_aggregation.py` (4 fichiers) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → exactement 2 commits (RED + GREEN) |

### Tâche

| Critère | Verdict | Détail |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` dans le diff |
| Critères d'acceptation cochés | ✅ (13/13) | Tous les 13 critères `[x]` dans le diff |
| Checklist cochée | ⚠️ (7/9) | 7/9 cochés. 2 non cochés : `Commit GREEN` et `Pull Request ouverte` — attendu car auto-référençants (le commit GREEN ne peut pas se checker lui-même) |

**Mapping critères → preuves :**

| Critère d'acceptation | Preuve (test ou code) |
|---|---|
| 3 folds → mean et std (ddof=1) corrects | `test_three_folds_mean_std_correct` — calcul vérifié avec `pytest.approx` vs `np.mean`/`np.std(ddof=1)` |
| Métriques exclues absentes | `test_excluded_keys_absent` — `sharpe_per_trade`, `n_samples_*` vérifiés absents |
| Null omis du calcul | `test_null_handling_omits_none`, `test_all_none_metric_yields_none`, `test_single_non_none_among_nones` |
| E_start[k+1] == E_end[k] | `test_two_folds_continuation`, `test_three_folds_chain` — assertions `pytest.approx` aux jointures |
| CSV (time_utc, equity, in_trade, fold) | `test_export_csv` + `test_columns_present` — écriture/relecture avec colonnes vérifiées |
| Gap → equity constante + warning | `test_gap_detection_warning` — warning capté + fold1_start == fold0_end |
| Warning net_pnl_mean <= 0 | `test_warning_net_pnl_negative`, `test_warning_net_pnl_zero` |
| Warning profit_factor_mean <= 1.0 | `test_warning_profit_factor_below_one`, `test_warning_profit_factor_exactly_one` |
| Warning max_drawdown_mean >= mdd_cap | `test_warning_mdd_exceeds_cap`, `test_warning_mdd_equals_cap` |
| comparison_type | `test_buy_hold_contextual`, `test_no_trade_go_nogo`, `test_sma_rule_go_nogo`, `test_xgboost_go_nogo` |
| Tests nominaux + erreurs + bords | 4 classes de tests couvrant 36 tests au total |
| Suite verte | voir CI ci-dessous |
| ruff clean | voir CI ci-dessous |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1199 passed**, 0 failed, 4 warnings (RuntimeWarning numpy attendu) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 — Fallbacks silencieux | `grep 'or []\|or {}...'` sur CHANGED_SRC | **0 occurrences** (grep exécuté) |
| §R1 — Except trop large | `grep 'except:$\|except Exception:'` sur CHANGED_SRC | **0 occurrences** (grep exécuté) |
| §R7 — Suppressions lint (noqa) | `grep 'noqa'` sur CHANGED | 3 occurrences dans `__init__.py` : `F401` pour imports re-export (`aggregation`, `prediction`, `trading`) — **justifié** (pattern standard pour side-effect imports) |
| §R7 — Print résiduel | `grep 'print('` sur CHANGED_SRC | **0 occurrences** (grep exécuté) |
| §R3 — Shift négatif | `grep '.shift(-'` sur CHANGED_SRC | **0 occurrences** (grep exécuté) |
| §R4 — Legacy random API | `grep 'np.random.seed\|...'` sur CHANGED | **0 occurrences** (grep exécuté) |
| §R7 — TODO/FIXME orphelins | `grep 'TODO\|FIXME\|HACK\|XXX'` sur CHANGED | **0 occurrences** (grep exécuté) |
| §R7 — Chemins hardcodés tests | `grep '/tmp\|C:\\'` sur CHANGED_TEST | **0 occurrences** (grep exécuté) |
| §R7 — Imports absolus `__init__` | `grep 'from ai_trading\.'` sur `__init__.py` | **0 occurrences** (utilise `from . import`) ✅ |
| §R7 — Registration manuelle tests | `grep 'register_model\|register_feature'` sur CHANGED_TEST | **0 occurrences** (N/A — pas de registre dans ce module) |
| §R6 — Mutable default arguments | `grep 'def .*=[]\|def .*={}'` sur CHANGED | **0 occurrences** (grep exécuté) |
| §R6 — open() sans context manager | `grep '.read_text\|open('` sur CHANGED_SRC | **0 occurrences** (grep exécuté) |
| §R6 — Comparaison booléenne identité | `grep 'is np.bool_\|is True\|is False'` sur CHANGED | **0 occurrences** (grep exécuté) |
| §R6 — Dict collision silencieuse | `grep '\[.*\] = .*'` sur aggregation.py hors def/# | 6 matches — **tous faux positifs** : clés `f"{metric}_mean/std"` avec `metric` itéré depuis `_AGGREGATED_METRICS` (tuple de chaînes uniques, pas de collision possible) |
| §R9 — Boucle Python sur array numpy | `grep 'for .* in range(.*):' ` sur CHANGED_SRC | **0 occurrences** (grep exécuté) |
| §R6 — isfinite validation | `grep 'isfinite'` sur CHANGED_SRC | 1 occurrence L213 : `math.isfinite(mdd_cap)` — validation correcte ✅ |
| §R9 — Appels numpy dans compréhension | `grep 'np\.[a-z]*(.*for .* in '` sur CHANGED_SRC | **0 occurrences** (grep exécuté) |
| §R7 — Fixtures dupliquées | `grep 'load_config.*configs/'` sur CHANGED_TEST | **0 occurrences** (grep exécuté) |

### Annotations par fichier (B2)

#### `ai_trading/metrics/aggregation.py` (270 lignes)

- **L89-102** — Boucle sur `_AGGREGATED_METRICS` avec `fold.get(metric)` : gestion correcte des None, conversion `float()` explicite, retour `float(np.mean(arr))` / `float(np.std(arr, ddof=1))` en float64. `_AGGREGATED_METRICS` est un tuple de chaînes uniques → pas de collision dict.
  Sévérité : RAS

- **L152-177** — Stitching logic : `carry_equity / original_start` rescale correctement.
  Sévérité : RAS sauf **L171** — voir item WARNING #1 ci-dessous.

- **L160-169** — Gap detection : compare timestamps entre folds et émet un `logger.warning`. La continuation (fold k+1 commence à E_end[k]) est gérée par le rescaling.
  Sévérité : RAS

- **L171** `original_start = original_equity[0]` puis L173 `scale = carry_equity / original_start` : **aucune validation que `original_start > 0`**. Si un fold a une equity commençant à 0.0, la division numpy float64 produit `inf` (RuntimeWarning) sans raise explicite. La corruption se propage silencieusement. L'amont (backtest, config `initial_equity > 0`) garantit normalement cette propriété, mais cette fonction publique ne valide pas l'invariant.
  Sévérité : **WARNING** (§R10 — invariants amont non validés, fonction publique)
  Suggestion : ajouter `if original_start == 0.0: raise ValueError(f"fold_equities[{k}] has equity starting at 0.0")` avant le calcul de scale.

- **L207** docstring : `"Maximum drawdown cap from config (``calibration.mdd_cap``)"` — le chemin config réel est `thresholding.mdd_cap` (cf. `configs/default.yaml` L109, `config.py` L151 class `ThresholdingConfig`).
  Sévérité : **MINEUR** (#1)
  Suggestion : remplacer `calibration.mdd_cap` par `thresholding.mdd_cap` dans la docstring.

- **L213** `if not math.isfinite(mdd_cap) or mdd_cap <= 0:` — validation correcte (rejette NaN, inf, 0, négatifs). ✅

- **L219-239** — Checks §14.4 : les 3 conditions (`net_pnl_mean <= 0`, `profit_factor_mean <= 1.0`, `max_drawdown_mean >= mdd_cap`) sont correctement vérifiées avec gestion None. Les warnings sont émis via `logger.warning` ET retournés en liste. ✅

- **L252-267** — `derive_comparison_type` : mapping `buy_hold → contextual`, else → `go_nogo`, validation de chaîne non vide. Conforme au plan.
  Sévérité : RAS

#### `ai_trading/metrics/__init__.py` (7 lignes)

- **L4** `aggregation,  # noqa: F401` : ajout du module `aggregation` avec import relatif (`from . import`). Pattern identique aux modules existants (`prediction`, `trading`). F401 justifié (import pour re-export namespace).
  Sévérité : RAS

#### `tests/test_aggregation.py` (522 lignes)

- **L211-219** (`test_single_fold`) et **L223-231** (`test_single_non_none_among_nones`) : ces tests déclenchent des numpy RuntimeWarnings (`Degrees of freedom <= 0 for slice`, `invalid value encountered in scalar divide`) visibles dans la sortie pytest. Les assertions `math.isnan()` sont correctes mais les warnings ne sont pas capturés via `pytest.warns(RuntimeWarning)`.
  Sévérité : **MINEUR** (#3)
  Suggestion : encapsuler dans `with pytest.warns(RuntimeWarning):` ou ajouter `@pytest.mark.filterwarnings("ignore::RuntimeWarning")` pour documenter le comportement attendu.

- **L370-381** (`test_mdd_cap_validation`, `test_mdd_cap_negative_raises`) : tests de bornes pour `mdd_cap` = 0.0 et -0.1. Pas de test pour `mdd_cap=float('nan')` ni `mdd_cap=float('inf')` alors que le code L213 les rejette via `isfinite`. Chemin non exercé par les tests.
  Sévérité : **MINEUR** (#2)
  Suggestion : ajouter `test_mdd_cap_nan_raises` et `test_mdd_cap_inf_raises`.

- Tests globalement bien structurés : 4 classes, 36 tests, couvrant cas nominaux + erreurs + bords. Helpers `_make_fold_metrics` et `_make_equity_df` propres et réutilisables.
  Sévérité : RAS

#### `docs/tasks/M4/042__ws10_aggregation.md`

- **Checklist L69-70** : items `Commit GREEN` et `Pull Request ouverte` non cochés ``[ ]`` dans le fichier alors que le commit GREEN existe (`623c1df`). Situation chicken-and-egg standard (le fichier est mis à jour DANS le commit GREEN).
  Sévérité : **MINEUR** (#4)
  Suggestion : cocher les 2 items manquants lors du prochain commit (ou dans le commit de correction).

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères AC | ✅ | Voir mapping ci-dessus — 13/13 critères couverts |
| Cas nominaux + erreurs + bords | ✅ | 36 tests : nominal (3 folds, 2 folds, single fold), erreur (empty list, missing cols), bord (all None, single non-None, NaN std) |
| Boundary fuzzing (`aggregate_fold_metrics`) | ✅ | fold_count=0 (raise), fold_count=1 (NaN std), fold_count=2, fold_count=3 |
| Boundary fuzzing (`check_acceptance_criteria`) | ⚠️ | mdd_cap=0 ✅, mdd_cap<0 ✅, mdd_cap=NaN ❌ (non testé), mdd_cap=inf ❌ (non testé) — MINEUR #2 |
| Déterministes | ✅ | Pas d'aléatoire, données synthétiques fixes |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` — utilise `tmp_path` (test_export_csv) |
| Tests registre réalistes | N/A | Pas de registre dans ce module |
| Contrat ABC complet | N/A | Pas d'ABC dans ce module |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 — Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallbacks, 0 except large. Validation explicite avec `raise ValueError` partout. |
| §R10 — Defensive indexing | ⚠️ | WARNING #1 : `carry_equity / original_start` sans validation `> 0`. |
| §R2 — Config-driven | ✅ | Pas de hardcoding. Métriques définies en constantes (`_AGGREGATED_METRICS`, `_EXCLUDED_METRICS`), conformes à la spec I-04. `mdd_cap` reçu en paramètre. |
| §R3 — Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. Module d'agrégation post-backtest, pas de risque look-ahead. |
| §R4 — Reproductibilité | ✅ | Scan B1 : 0 legacy random. Pas d'aléatoire — calculs déterministes mean/std. |
| §R5 — Float conventions | ✅ | `np.float64` utilisé pour arrays (L100-101). Résultats convertis en `float()` Python (float64 natif). |
| §R6 — Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 open(), 0 bool identité. Pas de désérialisation externe. |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Toutes les fonctions, variables et constantes conformes |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO/FIXME |
| Imports propres / relatifs | ✅ | `__init__.py` utilise `from . import` (relatif). Pas d'imports inutilisés. Ordre stdlib → third-party → local respecté. |
| DRY | ✅ | Pas de duplication identifiée. `_AGGREGATED_METRICS` et `_EXCLUDED_METRICS` centralisés. |
| Suppressions lint minimales | ✅ | 3 `noqa: F401` dans `__init__.py` — justifiés (pattern re-export standard) |
| `__init__.py` à jour | ✅ | `aggregation` ajouté avec import relatif |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Commentaire |
|---|---|---|
| Spécification §14.3 | ✅ | Agrégation mean/std(ddof=1), courbe stitchée, §14.4 warnings — tout conforme |
| Plan WS-10.3 | ✅ | Fonctions conformes : `aggregate_fold_metrics`, `stitch_equity_curves`, `check_acceptance_criteria`, `derive_comparison_type` |
| Métriques I-04 | ✅ | 10 trading + 4 prediction — liste conforme au plan L825. Exclusions `sharpe_per_trade`, `n_samples_*` correctes. |
| Formules doc vs code | ✅ | `E_start[k+1] = E_end[k]` implémenté par rescaling `scale = carry_equity / original_start` + `ec_copy["equity"] = original_equity * scale`. ddof=1 conforme au plan L1067. |
| comparison_type §13.4 | ✅ | `buy_hold → contextual`, else → `go_nogo` — conforme au plan L825 |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Contrat amont trading metrics | ✅ | `fold.get(metric)` compatible avec les dicts retournés par `compute_trading_metrics()` (returns `float \| None`). Vérifié via grep de `trading.py` — retourne `None` (pas NaN) pour edge cases. |
| Contrat amont prediction metrics | ✅ | `compute_prediction_metrics()` retourne `dict[str, float \| None]` (grep vérifié). Les clés correspondent aux 4 métriques de `_PREDICTION_METRICS`. |
| Contrat aval (metrics_builder) | ✅ | `aggregate_fold_metrics` retourne `dict[str, float \| None]` avec clés `<metric>_mean/_std` — compatible avec la structure `aggregate_block` du schéma JSON spec (§15.1). |
| Config (thresholding.mdd_cap) | ✅ | `Field(gt=0, le=1)` dans `ThresholdingConfig` → bornes validées en config. Fonction reçoit `mdd_cap: float` (séparation correcte). |
| Equity DataFrame columns | ✅ | Attendu `time_utc, equity, in_trade` — cohérent avec les colonnes produites par `build_equity_curve()` dans `backtest/engine.py`. |

---

## Items identifiés

### WARNING

**1. [WARNING] `stitch_equity_curves` — invariant equity > 0 non validé (§R10)**
- Fichier : `ai_trading/metrics/aggregation.py`
- Ligne(s) : 171, 173
- Code : `original_start = original_equity[0]` → `scale = carry_equity / original_start`
- Description : La fonction publique ne valide pas que `original_start > 0` avant la division. Si un fold a une equity commençant à 0.0, la division numpy float64 produit `inf` sans raise explicite (RuntimeWarning seulement). L'invariant amont (config `initial_equity > 0` + backtest engine) garantit normalement cette propriété, mais §R10 recommande une validation explicite pour les fonctions publiques.
- Suggestion : Ajouter avant L173 :
  ```python
  if original_start == 0.0:
      raise ValueError(
          f"fold_equities[{k}] has equity starting at 0.0, "
          "cannot rescale."
      )
  ```

### MINEURS

**1. [MINEUR] Docstring `check_acceptance_criteria` — chemin config incorrect**
- Fichier : `ai_trading/metrics/aggregation.py`
- Ligne(s) : 207
- Description : La docstring référence `calibration.mdd_cap` alors que le chemin config réel est `thresholding.mdd_cap` (cf. `configs/default.yaml` L109, `config.py` L151 `ThresholdingConfig`).
- Suggestion : Remplacer `calibration.mdd_cap` par `thresholding.mdd_cap`.

**2. [MINEUR] Tests manquants — boundary `mdd_cap` NaN/inf**
- Fichier : `tests/test_aggregation.py`
- Ligne(s) : après L381
- Description : Le code L213 valide `math.isfinite(mdd_cap)` mais aucun test n'exerce les cas `mdd_cap=float('nan')` et `mdd_cap=float('inf')`. Ce sont des chemins de validation non couverts.
- Suggestion : Ajouter 2 tests :
  ```python
  def test_mdd_cap_nan_raises(self):
      agg = {"net_pnl_mean": 0.10}
      with pytest.raises(ValueError, match="mdd_cap"):
          check_acceptance_criteria(agg, mdd_cap=float("nan"))

  def test_mdd_cap_inf_raises(self):
      agg = {"net_pnl_mean": 0.10}
      with pytest.raises(ValueError, match="mdd_cap"):
          check_acceptance_criteria(agg, mdd_cap=float("inf"))
  ```

**3. [MINEUR] RuntimeWarnings numpy non capturées dans les tests**
- Fichier : `tests/test_aggregation.py`
- Ligne(s) : 211-219, 223-231
- Description : `test_single_fold` et `test_single_non_none_among_nones` déclenchent des numpy RuntimeWarnings (`Degrees of freedom <= 0 for slice`) visibles dans la sortie pytest (4 warnings). Les assertions sont correctes mais le comportement attendu n'est pas documenté dans le test.
- Suggestion : Ajouter `@pytest.mark.filterwarnings("ignore:Degrees of freedom:RuntimeWarning")` sur ces tests, ou utiliser `with pytest.warns(RuntimeWarning):`.

**4. [MINEUR] Checklist tâche incomplète**
- Fichier : `docs/tasks/M4/042__ws10_aggregation.md`
- Ligne(s) : 69-70
- Description : Items `Commit GREEN` et `Pull Request ouverte` non cochés `[ ]` dans la checklist, alors que le commit GREEN existe (623c1df). Situation chicken-and-egg standard.
- Suggestion : Cocher ces items dans le prochain commit de correction.

---

## Résumé

L'implémentation est solide et conforme à la spec §14.3/§14.4 et au plan WS-10.3. Les 4 fonctions sont correctement implémentées avec une bonne séparation des préoccupations. Les tests sont exhaustifs (36 cas) couvrant nominal, erreurs et bords. Un WARNING concerne un invariant non validé dans `stitch_equity_curves` (equity start > 0 avant division), et 4 MINEURs touchent la docstring, des tests boundary manquants, des warnings numpy non capturées et la checklist tâche.

```
RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 1
- Mineurs : 4
- Rapport : docs/tasks/M4/042/review_v1.md
```
