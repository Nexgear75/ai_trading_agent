# Revue PR — [WS-D-3] #081 — Page 2 : equity curve stitchée et métriques par fold

Branche : `task/081-wsd3-equity-fold-metrics`
Tâche : `docs/tasks/MD-2/081__wsd3_equity_fold_metrics.md`
Date : 2026-03-06
Itération : v2 (suite au FIX commit 3203767 corrigeant les 5 items de la v1)

## Verdict global : ✅ CLEAN

## Résumé

2e itération de revue. Les 5 items de la v1 (1 WARNING `normalize_equity` code mort + 4 MINEURS sur fallbacks `.get(key, default)` et checklist) sont tous corrigés dans le commit `3203767`. Le code mort et ses 6 tests ont été supprimés, les accès dict sont maintenant stricts (`fold["trading"]`, `fold["prediction"]`, `threshold["method"]`), et la checklist est à jour. 26 tests passent (6 supprimés = normalize_equity), suite complète 2087 passed, ruff clean. Aucun nouvel item identifié.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche | ✅ | `task/081-wsd3-equity-fold-metrics` (output `git branch --show-current`) |
| Commit RED présent | ✅ | `58db860 [WS-D-3] #081 RED: tests equity curve normalisation et métriques par fold` — 1 fichier : `tests/test_dashboard_equity_fold.py` (500 insertions) |
| Commit GREEN présent | ✅ | `dffd6af [WS-D-3] #081 GREEN: equity curve stitchée et métriques par fold` — 4 fichiers : impl + tâche + test ajustement |
| RED = tests uniquement | ✅ | `git show --stat 58db860` → seul `tests/test_dashboard_equity_fold.py` |
| GREEN = impl + tâche | ✅ | `git show --stat dffd6af` → `run_detail_logic.py`, `2_run_detail.py`, `test_dashboard_equity_fold.py`, tâche MD |
| Pas de commits parasites | ✅ | 3 commits : RED → GREEN → FIX (post-review, conforme au workflow itératif) |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (12/12) |
| Checklist cochée | ✅ (8/9 — seul item non coché : "PR ouverte", ce qui est correct car la PR n'est pas encore créée) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/test_dashboard_equity_fold.py -v` | **26 passed**, 0 failed |
| `pytest tests/ -v` (suite complète) | **2087 passed**, 27 deselected, 0 failed |
| `ruff check scripts/dashboard/ tests/test_dashboard_equity_fold.py` | **All checks passed** |

→ Phase A : **PASS**. Passage en Phase B.

---

## Phase B — Code Review

### B1 — Résultats du scan automatisé (GREP)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks `or []`/`or {}`/`or 0` | `grep -n 'or \[\]\|or {}\|or ""\|or 0\b\|if .* else '` sur fichiers src | 3 hits dans code #081 — analysés B2, tous légitimes |
| §R1 Except trop large | `grep -n 'except:$\|except Exception:'` | 0 occurrences |
| §R7 Suppressions lint (noqa) | `grep -n 'noqa'` | 0 occurrences |
| §R7 Print résiduel | `grep -n 'print('` | 0 occurrences |
| §R3 Shift négatif | `grep -n '\.shift(-'` | 0 occurrences |
| §R4 Legacy random API | `grep -n 'np.random.seed\|random.seed'` | 0 occurrences |
| §R7 TODO/FIXME orphelins | `grep -n 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences |
| §R7 Chemins hardcodés (tests) | `grep -n '/tmp\|/var/tmp\|C:\\'` | 0 occurrences |
| §R7 Imports absolus `__init__` | N/A | Aucun `__init__.py` modifié |
| §R7 Registration manuelle tests | N/A | Pas de registre |
| §R6 Mutable defaults | `grep -nE 'def.*=\[\]\|def.*=\{\}'` | 0 occurrences |

### B2 — Annotations par fichier

#### `scripts/dashboard/pages/run_detail_logic.py` (106 lignes ajoutées dans le diff final)

**Vérification des corrections v1 :**

- ✅ **v1 WARNING #1** : `normalize_equity()` (ex-L270-293) **supprimée**. `grep -n 'normalize_equity' run_detail_logic.py` → 0 résultats.
- ✅ **v1 MINEUR #2** : `fold.get("trading", {})` → `fold["trading"]` (L312). Confirmé par diff FIX.
- ✅ **v1 MINEUR #2** : `fold.get("prediction", {})` → `fold["prediction"]` (L313). Confirmé par diff FIX.
- ✅ **v1 MINEUR #3** : `threshold.get("method", _NULL_DISPLAY)` → `threshold["method"]` (L322). Confirmé par diff FIX.
- ✅ **v1 MINEUR #2** (build_pnl_bar_data) : `fold.get("trading", {})` → `fold["trading"]` (L358). Confirmé par diff FIX.

**Analyse du code restant :**

- **L272-273** `threshold.get("method")` / `threshold.get("theta")` dans `_fmt_theta()` : `.get()` sans default, retourne None. Cohérent : `theta` est nullable, et `method` est vérifié ensuite par `threshold["method"]` à L322 (qui lèvera KeyError si absent). Pas de fallback silencieux.
  Sévérité : RAS.

- **L281** `threshold.get("selected_quantile")` dans `_fmt_quantile()` : `.get()` sans default. `selected_quantile` est nullable dans le schéma JSON. Correct.
  Sévérité : RAS.

- **L316-317** `trading.get("n_trades")` / `trading.get("sharpe_per_trade")` : `.get()` sans default, retourne None. Nullable JSON fields passés à des format functions qui gèrent None → "—". Correct.
  Sévérité : RAS.

- **L324-334** Tous les `.get()` sur `trading` et `prediction` : sans default. Les format functions (`format_pct`, `format_float`) acceptent `float | None` et retournent "—" pour None. Correct.
  Sévérité : RAS.

- **L329** `str(n_trades) if n_trades is not None else _NULL_DISPLAY` : ternaire pour nullable → "—". Conforme §9.3.
  Sévérité : RAS.

- **L336** `n_trades if n_trades is not None else 0` : passe 0 quand n_trades est null. `format_sharpe_per_trade(None, 0)` retourne "—" car sharpe_pt est None. Comportement testé (`test_n_trades_null_sharpe_per_trade_null`). Correct.
  Sévérité : RAS.

- **L363** `pnl if pnl is not None else 0.0` : null PnL → 0 pour bar chart. Comportement intentionnel et testé (`test_null_pnl_uses_zero`). Acceptable en couche de présentation.
  Sévérité : RAS.

RAS après lecture complète du diff (106 lignes src).

#### `scripts/dashboard/pages/2_run_detail.py` (53 lignes ajoutées)

- **L104** `equity_df = load_equity_curve(run_dir)` — Réutilise data_loader. ✅
- **L106** `if equity_df is None` → `st.info(...)` — Dégradation information §4.2. ✅
- **L108-112** Check `first_equity <= 0` → `st.error(...)` — Strict code : erreur explicite au lieu de normalisation silencieuse. ✅
- **L114-119** `chart_equity_curve(equity_df, fold_boundaries=True, drawdown=True, in_trade_zones=True)` — Conforme §6.3. ✅
- **L130** `fold_table = build_fold_metrics_table(metrics)` — Appel correct. ✅
- **L132-133** `st.dataframe(fold_table, use_container_width=True, hide_index=True)` — OK. ✅
- **L135-138** PnL bar chart conditionnel. ✅
- **L140** Message informatif si table vide. ✅

RAS après lecture complète du diff (53 lignes).

#### `tests/test_dashboard_equity_fold.py` (438 lignes dans l'état final)

**Vérification correction v1 :**
- ✅ **v1 WARNING #1** (tests) : `TestNormalizeEquity` (6 tests) **supprimée**. `grep -n 'normalize_equity\|TestNormalizeEquity'` → 0 résultats. Docstring module mise à jour (retrait mention normalize_equity).

**Analyse :**
- 4 classes de test : `TestBuildFoldMetricsTable` (13 tests), `TestBuildPnlBarData` (3 tests), `TestFormattingDetails` (10 tests). Total : **26 tests**.
- Toutes les docstrings portent `#081`. ✅
- Données synthétiques uniquement (helpers `_make_fold_entry`, `_make_metrics_with_folds`, `_make_equity_df`). ✅
- Pas de dépendance réseau. ✅
- Pas de `@pytest.mark.skip` ni `xfail`. ✅
- Imports locaux à chaque méthode (pas de dépendance au scope module). ✅

RAS après lecture complète du diff (438 lignes).

#### `docs/tasks/MD-2/081__wsd3_equity_fold_metrics.md`

- ✅ **v1 MINEUR #5** : Checklist "Commit GREEN" cochée `[x]`.
- "PR ouverte" reste `[ ]` → correct (PR pas encore créée).

### B3 — Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_dashboard_equity_fold.py`, ID `#081` en docstrings |
| Couverture critères | ✅ | 12 critères → 26 tests (mapping vérifié ci-dessous) |
| Cas nominaux + erreurs + bords | ✅ | Nominal, null values, empty folds, n_trades boundaries, scientific notation |
| Boundary fuzzing | ✅ | n_trades=1, 2, 3, None; empty folds; sharpe_pt>1000 |
| Déterministes | ✅ | Données synthétiques uniquement, pas d'aléatoire |
| Portabilité chemins | ✅ | Scan B1: 0 `/tmp` |
| Tests registre réalistes | N/A | Pas de registre |
| Contrat ABC complet | N/A | Pas d'ABC |

**Mapping critères d'acceptation → tests :**

| Critère | Tests |
|---|---|
| Equity normalisée à 1.0, frontières, drawdown, in-trade | Couvert par appel `chart_equity_curve` dans `2_run_detail.py` + check `first_equity <= 0` |
| Tableau métriques par fold — colonnes §6.4 | `test_nominal_columns`, `test_nominal_row_count` |
| θ via fold.threshold.theta | `test_theta_from_threshold_object`, `test_theta_float_format` |
| threshold.method affiché | `test_method_displayed` |
| threshold.selected_quantile affiché | `test_quantile_displayed` |
| method="none" → θ = "—" | `test_method_none_theta_em_dash`, `test_method_none_quantile_em_dash` |
| ⚠️ pour n_trades ≤ 2 | `test_sharpe_per_trade_warning_low_trades`, `test_sharpe_per_trade_warning_boundary_n_trades_1`, `test_sharpe_per_trade_boundary_n_trades_3_no_warning` |
| null → "—" | `test_null_trading_values_em_dash`, `test_null_prediction_values_em_dash`, `test_n_trades_null_sharpe_per_trade_null` |
| Bar chart PnL | `test_nominal_extracts_fold_and_pnl`, `test_null_pnl_uses_zero`, `test_empty_folds` |
| Message si equity absente | Couvert par `2_run_detail.py` L106: `st.info(...)` (Streamlit code, non testé unitairement — acceptable) |
| Tests couvrent nominaux + erreurs + bords | ✅ Voir tableau |
| Suite de tests verte | ✅ 26 passed + 2087 passed (suite complète) |
| ruff clean | ✅ All checks passed |

### B4 — Code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 `or []`/`or {}`/defaults dans nouveau code. `.get()` sans default = nullable field access. Accès requis stricts : `fold["threshold"]`, `fold["trading"]`, `fold["prediction"]`, `threshold["method"]`. |
| §R10 Defensive indexing | ✅ | `equity_df["equity"].iloc[0]` seul accès indexé, protégé par `equity_df is None` en amont + check `<= 0` |
| §R2 Config-driven | ✅ | θ lu depuis `metrics.json` → `fold["threshold"]["theta"]`. Pas de valeur hardcodée. |
| §R3 Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. Données lues/affichées, jamais recalculées. |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random. Pas d'aléatoire dans ce module. |
| §R5 Float conventions | N/A | Couche de présentation, pas de tenseurs/métriques calculées. |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 open(), 0 bool identity. Pas de `.values` implicite. |

### B5 — Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `build_fold_metrics_table`, `build_pnl_bar_data`, `_fmt_theta`, `_fmt_quantile` |
| Pas de code mort | ✅ | `normalize_equity` supprimée (v1 WARNING corrigé). grep confirme 0 occurrences. |
| Pas de print/debug | ✅ | Scan B1 : 0 `print(` |
| Pas de TODO orphelin | ✅ | Scan B1 : 0 TODO/FIXME |
| Imports propres | ✅ | Imports ordonnés, pas d'imports inutilisés (ruff clean) |
| DRY | ✅ | Réutilise `format_pct`, `format_float`, `format_sharpe_per_trade`, `_NULL_DISPLAY`, `load_equity_curve`, `chart_equity_curve`, `chart_pnl_bar` |

### B5-bis — Bonnes pratiques métier

| Critère | Verdict |
|---|---|
| Exactitude des concepts financiers | ✅ — Equity, PnL %, Sharpe, MDD, Win Rate — utilisation correcte |
| Nommage métier cohérent | ✅ — `equity`, `net_pnl`, `sharpe`, `mdd`, `hit_rate` |
| Séparation des responsabilités | ✅ — Logique dans `run_detail_logic.py`, rendu dans `2_run_detail.py`, graphiques dans `charts.py` |
| Invariants de domaine | ✅ — `equity[0] > 0` validé avant affichage |
| Cohérence des unités/échelles | ✅ — Ratios en %, Sharpe en float |

### B6 — Conformité spec

| Critère | Verdict |
|---|---|
| §6.3 Courbe d'équité stitchée | ✅ — `load_equity_curve` + `chart_equity_curve(fold_boundaries=True, drawdown=True, in_trade_zones=True)` |
| §6.4 Métriques par fold | ✅ — 14 colonnes conforme |
| §6.4 θ via threshold object | ✅ — `fold["threshold"]` accédé, `_fmt_theta` formate theta |
| §6.4 method="none" → "—" | ✅ — `_fmt_theta()` retourne `_NULL_DISPLAY` |
| §6.4 ⚠️ n_trades ≤ 2 | ✅ — Délégué à `format_sharpe_per_trade()` |
| §6.4 null → "—" | ✅ — Via format functions + `_NULL_DISPLAY` |
| §6.4 Bar chart PnL | ✅ — `build_pnl_bar_data()` + `chart_pnl_bar()` |
| §4.2 Dégradation equity absente | ✅ — `st.info(...)` si None |
| Formules doc vs code | ✅ — Pas de divergence |

### B7 — Cohérence intermodule

| Critère | Verdict |
|---|---|
| Signatures et types de retour | ✅ — `chart_equity_curve`, `chart_pnl_bar`, `load_equity_curve` — signatures conformes |
| Noms de colonnes DataFrame | ✅ — `equity`, `in_trade`, `fold`, `time_utc` — cohérents avec `data_loader.py` |
| Structures de données partagées | ✅ — Dict `{fold, net_pnl}` conforme à `chart_pnl_bar` |
| Imports croisés | ✅ — Tous les symboles importés existent sur `Max6000i1` |

---

## Remarques

Aucune.

## Résumé

Tous les items de la v1 sont corrigés : code mort `normalize_equity` supprimé avec ses 6 tests, accès dict rendus stricts (`.get(key, default)` → `dict[key]`), checklist mise à jour. 26 tests passent, suite complète 2087 passed, ruff clean. Le code est propre, conforme à la spec et aux règles du projet. Aucun nouvel item identifié.

---

```
RÉSULTAT PARTIE B :
- Verdict : CLEAN
- Bloquants : 0
- Warnings : 0
- Mineurs : 0
- Rapport : docs/tasks/MD-2/081/review_v2.md
```
