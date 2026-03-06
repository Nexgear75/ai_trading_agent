# Revue PR — [WS-D-3] #082 — Page 2 : distribution des trades et journal

Branche : `task/082-wsd3-trades-distribution-journal`
Tâche : `docs/tasks/MD-2/082__wsd3_trades_distribution_journal.md`
Date : 2026-03-06
Itération : v2

## Verdict global : ✅ CLEAN

## Résumé

2e itération de revue. Les 3 items de la v1 (1 WARNING, 2 MINEURS) sont tous corrigés dans le commit `4b112f7`. La validation du paramètre `sign` est ajoutée dans `filter_trades`, la boucle `iterrows()` a été vectorisée dans `join_equity_after`, et la validation de `page_size` est ajoutée dans `paginate_dataframe`. 4 tests supplémentaires couvrent les corrections. 42 tests passants, 2129 tests globaux verts, ruff clean. 0 item restant.

---

## Vérification des corrections v1

| # | Sévérité v1 | Description | Corrigé ? | Preuve |
|---|---|---|---|---|
| 1 | WARNING | `filter_trades` — `sign` non validé (§R1) | ✅ | `git diff 188dd88..4b112f7` : L613-616 ajoute `if sign is not None and sign not in ("winning", "losing"): raise ValueError(...)`. Tests `test_filter_invalid_sign_raises` et `test_filter_invalid_sign_empty_string_raises` ajoutés et passants. |
| 2 | MINEUR | `join_equity_after` — `iterrows()` au lieu de vectorisation | ✅ | `git diff 188dd88..4b112f7` : L480-484 remplace `for _, row in merged.iterrows()` par `valid = merged.dropna(subset=["equity"]); idxs = valid["_orig_idx"].astype(int).values; result[idxs] = valid["equity"].values`. Vectorisation correcte. |
| 3 | MINEUR | `paginate_dataframe` — `page_size` non validé | ✅ | `git diff 188dd88..4b112f7` : L576-577 ajoute `if page_size < 1: raise ValueError(...)`. Tests `test_page_size_zero_raises` et `test_page_size_negative_raises` ajoutés et passants. |

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/NNN-short-slug` | ✅ | `task/082-wsd3-trades-distribution-journal` |
| Commit RED présent | ✅ | `7241ea8` — `[WS-D-3] #082 RED: tests distribution trades et journal paginé` |
| Commit GREEN présent | ✅ | `188dd88` — `[WS-D-3] #082 GREEN: distribution des trades et journal paginé` |
| Commit RED = tests uniquement | ✅ | `git show --stat 7241ea8` → 1 fichier : `tests/test_dashboard_trades_journal.py` (+536 lignes) |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 188dd88` → 4 fichiers : tâche md, 2_run_detail.py, run_detail_logic.py, test fix (-1 ligne) |
| Commit FIX post-review v1 | ✅ | `4b112f7` — `[WS-D-3] #082 FIX: validate sign param, vectorize join_equity_after, validate page_size` — 2 fichiers : `run_detail_logic.py` (+13/-2), `test_dashboard_trades_journal.py` (+36) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1..HEAD` → 3 commits : RED, GREEN, FIX |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (12/12) |
| Checklist cochée | ✅ (8/9 — seule la PR non ouverte, attendu) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/test_dashboard_trades_journal.py -v` | **42 passed**, 0 failed, 1 warning |
| `pytest tests/ -v --tb=short` | **2129 passed**, 0 failed, 27 deselected, 61 warnings |
| `ruff check ai_trading/ tests/ scripts/` | **All checks passed** |

---

## Phase B — Code Review

### B1 — Résultats du scan automatisé (GREP)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 — Fallbacks silencieux | `grep 'or []\|or {}\|if.*else'` | 7 matches total. 5 dans code existant (pré-PR). 2 dans code nouveau : L538 (`_NULL_DISPLAY if pd.isna(v) else v`) → **faux positif** (affichage "—" pour NaN documenté §6.6). L234 (`None if selected_fold == "Tous" else selected_fold`) → **faux positif** (conversion UI) |
| §R1 — Except trop large | `grep 'except:$\|except Exception:'` | 0 occurrences (grep exécuté) |
| §R7 — noqa | `grep 'noqa'` | 0 occurrences (grep exécuté) |
| §R7 — Print résiduel | `grep 'print('` | 0 occurrences (grep exécuté) |
| §R3 — Shift négatif | `grep '.shift(-'` | 0 occurrences (grep exécuté) |
| §R4 — Legacy random API | `grep 'np.random.seed\|randn\|RandomState\|random.seed'` | 0 occurrences (grep exécuté) |
| §R7 — TODO/FIXME | `grep 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences (grep exécuté) |
| §R7 — Chemins hardcodés (tests) | `grep '/tmp\|/var/tmp\|C:\\'` | 0 occurrences (grep exécuté) |
| §R7 — Imports absolus `__init__.py` | N/A | Pas de `__init__.py` modifié |
| §R7 — Registration manuelle tests | `grep 'register_model\|register_feature'` | 0 occurrences (grep exécuté) |
| §R6 — Mutable default arguments | `grep 'def.*=[]\|def.*={}'` | 0 occurrences (grep exécuté) |
| §R6 — open() sans context manager | `grep '.read_text\|open('` | 0 occurrences (grep exécuté) |
| §R6 — Comparaison booléenne identité | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences (grep exécuté) |
| §R6 — Dict collision | `grep '[.*] = .*'` | 1 match L484 `result[idxs] = valid["equity"].values` → **faux positif** (`_orig_idx` unique par construction + `dropna` filtrage) |
| §R9 — Boucle Python sur array | `grep 'for .* in range(.*):' SRC` | 0 occurrences (grep exécuté) |
| §R6 — isfinite | `grep 'isfinite'` | 0 occurrences — N/A, pas de validation bornes numériques dans le nouveau code |
| §R9 — np comprehension vectorisable | `grep 'np.[a-z]*(.*for.*in'` | 0 occurrences (grep exécuté) |
| §R7 — Fixtures dupliquées | `grep 'load_config.*configs/'` | 0 occurrences (grep exécuté) |

### B2 — Annotations par fichier

#### `scripts/dashboard/pages/run_detail_logic.py` (code nouveau + FIX : L367–L638)

- **L394–L395** `if trades_df.empty: raise ValueError(...)` : Validation explicite. Conforme §R1. RAS.

- **L403** `"skewness": float(skew(net.values, bias=False))` : `scipy.stats.skew(bias=False)` pour coefficient Fisher-Pearson ajusté. Correct. RAS.

- **L413** `_FOLD_NUM_RE = re.compile(r"fold_(\d+)")` : Regex compilée au niveau module. RAS.

- **L418–L421** `_fold_str_to_int` : Validation explicite avec `raise ValueError` si pattern ne matche pas. Conforme §R1. RAS.

- **L447–L456** `trades_work` / `equity_work` DataFrames de travail : `_orig_idx = range(len(trades_df))` garantit unicité. `equity_df["fold"].astype(int)` cohérent avec le contrat `load_equity_curve()` (fold entier). RAS.

- **L461** `result = np.full(len(trades_df), np.nan, dtype=np.float64)` : Float64 pour equity. Conforme §R5. RAS.

- **L478–L484** Merge asof + assignation vectorisée : `valid = merged.dropna(subset=["equity"])`, puis `result[idxs] = valid["equity"].values`. Correction v1 MINEUR #2 appliquée. Vectorisation correcte, gestion des NaN propre via `dropna`. RAS.

- **L524** `"Costs": trades_df["costs"].values` : `costs` pré-calculé par `load_trades()` (`fees_paid + slippage_paid`). Conforme §6.6. RAS.

- **L536–L538** `equity_after.apply(lambda v: _NULL_DISPLAY if pd.isna(v) else v)` : Remplacement NaN → "—" pour l'affichage. Conforme §6.6. RAS.

- **L574** `if page < 1: raise ValueError(...)` : Validation page. Conforme §R1. RAS.

- **L576** `if page_size < 1: raise ValueError(...)` : Correction v1 MINEUR #3 appliquée. Validation explicite. Conforme §R1. RAS.

- **L613–L616** `if sign is not None and sign not in ("winning", "losing"): raise ValueError(...)` : Correction v1 WARNING #1 appliquée. Validation explicite avec message clair. Conforme §R1. RAS.

- **L618** `mask = pd.Series(True, index=trades_df.index)` : Construction du masque booléen. Pattern correct. RAS.

- RAS après lecture complète du diff (272 lignes nouvelles).

#### `scripts/dashboard/pages/2_run_detail.py` (code nouveau : L161–L277)

- **L172** `trades_df = load_trades(run_dir)` : Chargement paresseux. RAS.

- **L174** `if trades_df is None or trades_df.empty:` : Dégradation gracieuse. Conforme §4.2/§12.2. RAS.

- **L182/L184** `chart_returns_histogram(trades_df)` / `chart_returns_boxplot(trades_df)` : Réutilisation DRY. RAS.

- **L195–L197** `zip(stat_cols, stat_labels, strict=True)` : Sécurisé. RAS.

- **L234** `fold_filter = None if selected_fold == "Tous" else selected_fold` : Conversion UI → paramètre. Pattern correct. RAS.

- **L236–L238** Mapping `sign` FR → EN : `"Gagnant" → "winning"`, `"Perdant" → "losing"`, `"Tous" → None`. Exhaustif. RAS.

- **L241–L243** `isinstance(date_range, tuple) and len(date_range) == 2` : Gestion retour incomplet `st.date_input`. Pattern défensif correct. RAS.

- **L244** `date_end = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)` : Inclut toute la journée de fin (23:59:59). RAS.

- **L256** `journal = build_trade_journal(filtered_trades, equity_df)` : `equity_df` de L122, peut être `None`. Géré correctement. RAS.

- **L260** `total_pages = max(1, math.ceil(total_rows / page_size))` : Min 1 page pour éviter widget `max_value=0`. RAS.

- RAS après lecture complète du diff (120 lignes nouvelles).

#### `tests/test_dashboard_trades_journal.py` (571 lignes)

- **L24–L89** Helpers `_make_trades_df` / `_make_equity_df` : Seeds fixées (`np.random.default_rng(seed)`). Données synthétiques. Conforme §R4. RAS.

- **L535–L549** `test_filter_invalid_sign_raises` + `test_filter_invalid_sign_empty_string_raises` : Tests de la correction WARNING #1. Vérifient `ValueError` pour `sign="foo"` et `sign=""`. Conforme. RAS.

- **L552–L571** `TestPaginatePageSizeValidation` : Tests de la correction MINEUR #3. Vérifient `ValueError` pour `page_size=0` et `page_size=-5`. Conforme. RAS.

- RAS après lecture complète du diff (571 lignes). Docstrings contiennent `#082`. 6 classes de tests. Seeds fixées (42, 123, 99).

### B3 — Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_dashboard_trades_journal.py`, docstrings avec `#082` |
| Couverture des critères d'acceptation | ✅ | 12/12 critères couverts (mapping identique à v1 + tests de validation ajoutés) |
| Cas nominaux + erreurs + bords | ✅ | 42 tests dont : empty (raises), single, identical, NaN/no-match, page beyond, page_size=0, sign invalide, empty string sign |
| Boundary fuzzing pagination | ✅ | `page=0` (raises), `page=-1` (raises), `page_size=0` (raises), `page_size=-5` (raises), page beyond data (empty) |
| Boundary fuzzing stats | ✅ | empty (raises), single trade, identical returns |
| Boundary fuzzing sign | ✅ | `sign="foo"` (raises), `sign=""` (raises), `sign=None` (all), `sign="winning"`, `sign="losing"` |
| Déterministes | ✅ | Seeds fixées : 42, 123, 99 via `np.random.default_rng(seed)` |
| Données synthétiques | ✅ | `_make_trades_df()` et `_make_equity_df()` — pas de réseau |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` dans les tests |
| Tests registre réalistes | N/A | Pas de registre impliqué |
| Contrat ABC complet | N/A | Pas d'ABC impliquée |
| Tests désactivés | ✅ | 0 `@pytest.mark.skip` / `xfail` |

### B4 — Audit du code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 2 faux positifs documentés. Validations explicites : `sign` (L613), `page_size` (L576), `page` (L574), `trades_df.empty` (L394), `_fold_str_to_int` (L419). |
| §R10 Defensive indexing | ✅ | `iloc[start:end]` — dépassement géré nativement. `result[idxs]` — index unique par construction. |
| §R2 Config-driven | ✅ | `page_size=50` conforme §11.2. Pas de paramètre configurable hardcodé. |
| §R3 Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. Dashboard = lecture seule données historiques. |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random. Tests : `np.random.default_rng`. |
| §R5 Float conventions | ✅ | `np.float64` pour equity array. Stats en float Python (64-bit). |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 open() sans ctx manager, 0 bool identité. |

### B5 — Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Toutes fonctions/variables conformes |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print(), 0 TODO/FIXME |
| Imports propres / relatifs | ✅ | Ruff clean. Pas d'imports inutilisés. |
| DRY | ✅ | Réutilisation `chart_*`, `_NULL_DISPLAY`, `format_float`, `format_pct`, `load_trades`, `load_equity_curve` |
| Pas de fichiers générés | ✅ | 4 fichiers dans la PR, tous code source/tests/docs |

### B5-bis — Bonnes pratiques métier

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude concepts financiers | ✅ | Rendements nets, coûts, equity after — corrects |
| Nommage métier cohérent | ✅ | `net_return`, `gross_return`, `equity`, `trades` |
| Séparation responsabilités | ✅ | Logique dans `run_detail_logic.py`, rendu dans `2_run_detail.py` |
| Invariants de domaine | ✅ | Données lues et affichées, pas de calcul critique |
| Cohérence unités/échelles | ✅ | Rendements en décimal (cohérent pipeline) |
| Patterns calcul financier | ✅ | `scipy.stats.skew`, `pd.merge_asof` — bonnes pratiques. Vectorisation correcte. |

### B6 — Conformité spec v1.0

| Critère | Verdict |
|---|---|
| §6.5 — Distribution des trades | ✅ — Histogramme, box plot, 6 statistiques (mean, median, std, skewness, best, worst). Conforme. |
| §6.6 — Journal des trades | ✅ — 9 colonnes (Fold, Entry/Exit time, Entry/Exit price, Gross return, Costs, Net return, Equity after). merge_asof backward par fold. Costs = fees_paid + slippage_paid. "—" pour NaN. Conforme. |
| §11.2 — Pagination 50 lignes | ✅ — `page_size=50`. Conforme. |
| §4.2/§12.2 — Dégradation gracieuse | ✅ — Message informatif si trades.csv absent. Equity after omis si equity_curve absent. |
| Plan WS-D-3.3 | ✅ — Tous les éléments du plan implémentés. |
| Formules doc vs code | ✅ — Pas de formule complexe. Jointures et calculs conformes à la spec. |

### B7 — Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `load_trades() → DataFrame|None`, `load_equity_curve() → DataFrame|None`, `chart_returns_histogram(df) → Figure` — cohérent |
| Noms de colonnes DataFrame | ✅ | `net_return`, `fold`, `exit_time_utc`, `costs`, `equity`, `time_utc` — identiques entre modules |
| Clés de configuration | N/A | Pas de lecture config YAML |
| Registres et conventions | N/A | Pas de registre impliqué |
| Structures de données partagées | ✅ | `_NULL_DISPLAY` importé de `utils.py` — cohérent |
| Conventions numériques | ✅ | `np.float64` pour equity, float Python pour stats |
| Imports croisés | ✅ | Tous les symboles importés existent dans `Max6000i1` |
| Forwarding kwargs | N/A | Pas de wrapper/orchestrateur |

---

## Remarques

Aucune.

---

## Résumé

| Sévérité | Compte |
|---|---|
| BLOQUANT | 0 |
| WARNING | 0 |
| MINEUR | 0 |

Les 3 items de la v1 sont tous correctement corrigés dans le commit `4b112f7` avec 4 tests supplémentaires. 42 tests passants localement, 2129 tests globaux verts, ruff clean. Code conforme à la spec (§6.5, §6.6, §11.2), aux règles non négociables (§R1–§R10), et au plan d'implémentation. Branche prête pour merge.
