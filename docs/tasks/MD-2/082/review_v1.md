# Revue PR — [WS-D-3] #082 — Page 2 : distribution des trades et journal

Branche : `task/082-wsd3-trades-distribution-journal`
Tâche : `docs/tasks/MD-2/082__wsd3_trades_distribution_journal.md`
Date : 2026-03-06

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

La branche ajoute 5 fonctions métier dans `run_detail_logic.py` (compute_trade_stats, join_equity_after, build_trade_journal, paginate_dataframe, filter_trades) et le rendu Streamlit correspondant dans `2_run_detail.py`. 38 tests couvrent les cas nominaux, erreurs et bords. La conformité TDD est respectée (commits RED/GREEN propres). Un WARNING est identifié sur la validation du paramètre `sign` dans `filter_trades` (§R1 strict code) et deux points mineurs.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/NNN-short-slug` | ✅ | `git branch --show-current` → `task/082-wsd3-trades-distribution-journal` |
| Commit RED présent | ✅ | `7241ea8` — `[WS-D-3] #082 RED: tests distribution trades et journal paginé` |
| Commit GREEN présent | ✅ | `188dd88` — `[WS-D-3] #082 GREEN: distribution des trades et journal paginé` |
| Commit RED = tests uniquement | ✅ | `git show --stat 7241ea8` → 1 fichier : `tests/test_dashboard_trades_journal.py` (+536 lignes) |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 188dd88` → 4 fichiers : tâche md, 2_run_detail.py, run_detail_logic.py, test fix (-1 ligne) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1..HEAD` → exactement 2 commits (RED + GREEN) |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (12/12) |
| Checklist cochée | ✅ (8/9 — seule la PR non ouverte) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **2125 passed**, 0 failed, 27 deselected, 61 warnings |
| `ruff check scripts/dashboard/ tests/test_dashboard_trades_journal.py` | **All checks passed** |

---

## Phase B — Code Review

### B1 — Résultats du scan automatisé (GREP)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 — Fallbacks silencieux | `grep 'or []\|or {}\|if.*else'` | 7 matches total. 5 dans code existant (pré-PR). 2 dans code nouveau : L536 (`_NULL_DISPLAY if pd.isna(v) else v`) → **faux positif** (affichage "—" pour NaN documenté) ; L234 (`None if selected_fold == "Tous" else selected_fold`) → **faux positif** (conversion UI) |
| §R1 — Except trop large | `grep 'except:$\|except Exception:'` | 0 occurrences (grep exécuté) |
| §R7 — noqa | `grep 'noqa'` | 0 occurrences (grep exécuté) |
| §R7 — Print résiduel | `grep 'print('` | 0 occurrences (grep exécuté) |
| §R3 — Shift négatif | `grep '.shift(-'` | 0 occurrences (grep exécuté) |
| §R4 — Legacy random API | `grep 'np.random.seed\|randn\|RandomState\|random.seed'` | 0 occurrences (grep exécuté) |
| §R7 — TODO/FIXME | `grep 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences (grep exécuté) |
| §R7 — Chemins hardcodés (tests) | `grep '/tmp\|/var/tmp\|C:\\'` | 0 occurrences (grep exécuté) |
| §R7 — Imports absolus `__init__.py` | `grep 'from ai_trading\.'` | N/A (pas de `__init__.py` modifié) |
| §R7 — Registration manuelle tests | `grep 'register_model\|register_feature'` | 0 occurrences (grep exécuté) |
| §R6 — Mutable default arguments | `grep 'def.*=[]\|def.*={}'` | 0 occurrences (grep exécuté) |
| §R6 — open() sans context manager | `grep '.read_text\|open('` | 0 occurrences (grep exécuté) |
| §R6 — Comparaison booléenne identité | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences (grep exécuté) |
| §R6 — Dict collision | `grep '[.*] = .*'` | 1 match dans code nouveau L484 : `result[int(row["_orig_idx"])] = row["equity"]` → **faux positif** (`_orig_idx` est unique par construction : `range(len(trades_df))`) |
| §R9 — Boucle Python sur array | `grep 'for .* in range(.*):' ` | 0 occurrences dans code source (grep exécuté) |
| §R6 — isfinite | `grep 'isfinite'` | 0 occurrences dans code source (grep exécuté) — N/A, pas de validation de bornes numériques dans le nouveau code |
| §R9 — np comprehension vectorisable | `grep 'np.[a-z]*(.*for.*in'` | 0 occurrences (grep exécuté) |
| §R7 — Fixtures dupliquées | `grep 'load_config.*configs/'` | 0 occurrences (grep exécuté) |

### B2 — Annotations par fichier

#### `scripts/dashboard/pages/run_detail_logic.py` (nouveau code : +263 lignes, L367–L629)

- **L398** `"skewness": float(skew(net.values, bias=False))` : Utilisation correcte de `scipy.stats.skew(bias=False)` pour le coefficient de Fisher-Pearson ajusté. RAS.

- **L413** `_FOLD_NUM_RE = re.compile(r"fold_(\d+)")` : regex compilée au niveau module — correct.

- **L418–L421** `_fold_str_to_int` : Validation explicite avec `raise ValueError` si le pattern ne matche pas. Conforme §R1. RAS.

- **L445–L448** `trades_work` / `equity_work` : Construction de DataFrames de travail pour le merge asof. Le `_orig_idx` permet de reconstituer l'ordre original. RAS.

- **L456** `equity_work["fold_int"] = equity_df["fold"].astype(int)` : L'equity_df a un fold entier (0, 1, …) tandis que trades_df a "fold_00". Le code utilise `_fold_str_to_int` pour les trades et `.astype(int)` pour l'equity — cohérent avec les contrats de `load_trades()` et `load_equity_curve()`. RAS.

- **L480–L484** `for _, row in merged.iterrows(): result[int(row["_orig_idx"])] = row["equity"]` : Boucle Python sur les lignes d'un DataFrame (voir MINEUR #3 ci-dessous).

- **L524** `"Costs": trades_df["costs"].values` : La colonne `costs` est calculée par `load_trades()` dans `data_loader.py` (L319 : `result["costs"] = result["fees_paid"] + result["slippage_paid"]`). `build_trade_journal` passe correctement la valeur. Cohérent avec §6.6. RAS.

- **L534–L536** `journal["Equity after"] = equity_after.apply(lambda v: _NULL_DISPLAY if pd.isna(v) else v)` : Remplacement des NaN par "—" pour l'affichage. Conforme §6.6 (cellule affiche `—` si pas de correspondance). RAS.

- **L560** `if page < 1: raise ValueError(...)` : Validation explicite. Conforme §R1.

- **L563–L564** `start = (page - 1) * page_size; end = start + page_size` : Découpage correct par `iloc[start:end]`. Le dépassement en fin est géré nativement par iloc (retourne les lignes disponibles). RAS.

- **L588–L626** `filter_trades` : **Voir WARNING #1** — le paramètre `sign` n'est pas validé. Les valeurs `None`, `"winning"`, `"losing"` sont gérées, mais une valeur invalide (ex : `"foo"`) serait silencieusement ignorée.

#### `scripts/dashboard/pages/2_run_detail.py` (nouveau code : +120 lignes, L161–L277)

- **L172** `trades_df = load_trades(run_dir)` : Chargement paresseux, conformément à §11.2.

- **L174** `if trades_df is None or trades_df.empty:` : Dégradation gracieuse avec message informatif. Conforme §4.2 / §12.2. RAS.

- **L182** `fig_hist = chart_returns_histogram(trades_df)` / L184 `fig_box = chart_returns_boxplot(trades_df)` : Réutilisation des fonctions de `charts.py`. DRY respecté.

- **L189** `stats = compute_trade_stats(trades_df)` : Appelé dans le bloc `else` (trades non vides), donc l'exception ValueError pour empty ne peut pas se produire ici. RAS.

- **L195–L197** `zip(stat_cols, stat_labels, strict=True)` : Utilisation de `strict=True` — correct, garantit même longueur. RAS.

- **L217** `sign_options = ["Tous", "Gagnant", "Perdant"]` : Mapping FR → EN fait aux lignes 236–238. RAS.

- **L228–L231** `date_range = st.date_input(...)` : Widget Streamlit correctement configuré avec `min_value` et `max_value` contraints.

- **L241–L243** `if isinstance(date_range, tuple) and len(date_range) == 2:` : Gestion du retour potentiel incomplet de `st.date_input` (un seul date sélectionné → tuple de longueur 1). Pattern défensif correct.

- **L244** `date_end = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)` : Inclut toute la journée de fin (23:59:59). Convention correcte.

- **L256** `journal = build_trade_journal(filtered_trades, equity_df)` : `equity_df` provient de L122 (`load_equity_curve(run_dir)`), peut être `None` → correctement géré par `build_trade_journal`. RAS.

- **L260** `total_pages = max(1, math.ceil(total_rows / page_size))` : Minimum 1 page même si 0 lignes, pour éviter un max_value=0 dans le widget. RAS.

- RAS après lecture complète du diff.

#### `tests/test_dashboard_trades_journal.py` (535 lignes)

- RAS après lecture complète. Tests bien structurés par classe (TestComputeTradeStats, TestJoinEquityAfter, TestBuildTradeJournal, TestPaginateDataframe, TestFilterTrades). Docstrings contiennent `#082`. Seeds fixées (`seed=42`, `seed=123`, `seed=99`). Données synthétiques uniquement. Pas de dépendance réseau.

### B3 — Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_dashboard_trades_journal.py`, docstrings avec `#082` |
| Couverture des critères d'acceptation | ✅ | Voir mapping ci-dessous |
| Cas nominaux + erreurs + bords | ✅ | test_empty_trades_raises, test_single_trade, test_identical_returns, test_no_match_returns_nan, test_equity_none_returns_none, test_empty_trades, test_empty_dataframe, test_page_beyond_data, test_filter_empty_result |
| Boundary fuzzing pagination | ✅ | page=0 (raises), page=-1 (raises), page beyond data (empty), page=1 on empty (0 rows) |
| Boundary fuzzing stats | ✅ | empty (raises), single trade, identical returns |
| Déterministes | ✅ | Seeds fixées : 42, 123, 99 dans `_make_trades_df` via `np.random.default_rng(seed)` |
| Données synthétiques | ✅ | `_make_trades_df()` et `_make_equity_df()` — pas de réseau |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` dans les tests |
| Tests registre réalistes | N/A | Pas de registre impliqué |
| Contrat ABC complet | N/A | Pas d'ABC impliquée |
| Tests désactivés | ✅ | 0 `@pytest.mark.skip` / `xfail` |

**Mapping critères d'acceptation → tests :**

| Critère | Test(s) |
|---|---|
| Histogramme rendements nets | `test_nominal_all_stats_present` (stats pour l'histogramme), rendu testé via `chart_returns_histogram` (task #077) |
| Box plot par fold | Rendu testé via `chart_returns_boxplot` (task #077). Intégration dans la page vérifiée via imports |
| Statistiques mean/median/std/skewness/best/worst | `test_mean_matches_pandas`, `test_median_matches_pandas`, `test_std_matches_pandas`, `test_skewness_matches_scipy`, `test_best_trade`, `test_worst_trade` |
| Journal paginé 50 lignes/page | `test_first_page`, `test_second_page`, `test_last_page_partial`, `test_total_pages_calculation` |
| Costs = fees_paid + slippage_paid | `test_costs_column_computed` |
| merge_asof Equity after | `test_nominal_join_exact_match`, `test_backward_join`, `test_per_fold_join`, `test_no_match_returns_nan` |
| Filtres fold/signe/période | `test_filter_by_fold`, `test_filter_by_sign_winning`, `test_filter_by_sign_losing`, `test_filter_by_date_range`, `test_filter_combined` |
| Dégradation trades absents | `test_empty_trades`, `test_empty_trades_raises` |
| Equity after omis si absent | `test_equity_after_column_omitted_if_no_equity`, `test_equity_none_returns_none` |

### B4 — Audit du code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ⚠️ | Scan B1 : 2 faux positifs. **WARNING #1** : `filter_trades` ne valide pas `sign` (voir Remarques) |
| §R10 Defensive indexing | ✅ | `iloc[start:end]` dans `paginate_dataframe` — dépassement géré nativement par pandas. `result[int(row["_orig_idx"])]` — index unique garanti. |
| §R2 Config-driven | ✅ | Page size = 50 conforme §11.2 spec. Pas de paramètre configurable hardcodé. |
| §R3 Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. Code dashboard (lecture seule sur données historiques). Pas de look-ahead possible. |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random dans le code source. Tests : `np.random.default_rng(seed)` correctement utilisé. |
| §R5 Float conventions | ✅ | `np.float64` pour le résultat de `join_equity_after`. Métriques de stats en float Python (float64). |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 open() sans context manager, 0 comparaison booléenne identité. |

### B5 — Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Toutes les fonctions et variables suivent la convention |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print(), 0 TODO/FIXME |
| Imports propres / relatifs | ✅ | Imports organisés, pas d'imports inutilisés (ruff clean) |
| DRY | ✅ | Réutilisation de `chart_returns_histogram`, `chart_returns_boxplot`, `_NULL_DISPLAY`, `format_float`, `format_pct`, `load_trades`, `load_equity_curve` |
| Pas de fichiers générés | ✅ | Seuls 4 fichiers modifiés, tous du code source/tests/docs |

### B5-bis — Bonnes pratiques métier

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude concepts financiers | ✅ | Rendements nets, coûts, equity after — concepts corrects |
| Nommage métier cohérent | ✅ | `net_return`, `gross_return`, `equity`, `trades` |
| Séparation responsabilités | ✅ | Logique dans `run_detail_logic.py`, rendu dans `2_run_detail.py` |
| Invariants de domaine | ✅ | Pas de calcul financier complexe — les valeurs sont lues et affichées |
| Cohérence unités/échelles | ✅ | Rendements en décimal (cohérent avec le pipeline) |
| Patterns calcul financier | ✅ | `scipy.stats.skew`, `pd.merge_asof` — bonnes pratiques |

### B6 — Conformité spec v1.0

| Critère | Verdict |
|---|---|
| §6.5 — Distribution des trades | ✅ — Histogramme, box plot, 6 statistiques. Conforme. |
| §6.6 — Journal des trades | ✅ — 9 colonnes, merge_asof backward par fold, costs, filtres, "—" pour NaN. Conforme. |
| §11.2 — Pagination 50 lignes | ✅ — `page_size=50`. Conforme. |
| §4.2/§12.2 — Dégradation gracieuse | ✅ — Message informatif si trades.csv absent. |
| Plan WS-D-3.3 | ✅ — 9/9 tâches du plan implémentées. |
| Formules doc vs code | ✅ — Pas de formule mathématique complexe, les jointures et calculs sont conformes. |

### B7 — Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `load_trades()` → `pd.DataFrame | None`, `load_equity_curve()` → `pd.DataFrame | None`, `chart_returns_histogram(trades_df)` → `go.Figure` — tout cohérent |
| Noms de colonnes DataFrame | ✅ | `net_return`, `fold`, `exit_time_utc`, `costs`, `equity`, `time_utc` — identiques entre modules |
| Clés de configuration | N/A | Pas de lecture config YAML dans ce code |
| Registres et conventions | N/A | Pas de registre impliqué |
| Structures de données partagées | ✅ | `_NULL_DISPLAY` importé depuis `utils.py` |
| Conventions numériques | ✅ | `np.float64` pour equity, float Python pour stats |
| Imports croisés | ✅ | Tous les symboles importés (`chart_returns_histogram`, `chart_returns_boxplot`, `load_trades`, `format_float`, `format_pct`) existent dans la branche `Max6000i1` |
| Forwarding kwargs | N/A | Pas de wrapper/orchestrateur |

---

## Remarques

1. **[WARNING]** `filter_trades` — paramètre `sign` non validé (§R1)
   - Fichier : `scripts/dashboard/pages/run_detail_logic.py`
   - Ligne(s) : 600–604
   - Description : La fonction `filter_trades` accepte un paramètre `sign: str | None` documenté comme acceptant uniquement `None`, `"winning"` ou `"losing"`. Cependant, si une valeur invalide est passée (ex : `sign="foo"`), elle est silencieusement ignorée — le filtre n'est pas appliqué et la fonction retourne toutes les lignes. Cela viole le principe §R1 (strict code) : « Prefer explicit validation + failure (raise/return error) over 'best-effort' behavior ».
   - Suggestion : Ajouter une validation explicite au début de la fonction :
     ```python
     if sign is not None and sign not in ("winning", "losing"):
         raise ValueError(f"sign must be 'winning', 'losing', or None, got '{sign}'")
     ```

2. **[MINEUR]** `join_equity_after` — boucle Python `iterrows()` au lieu de vectorisation
   - Fichier : `scripts/dashboard/pages/run_detail_logic.py`
   - Ligne(s) : 480–484
   - Description : La boucle `for _, row in merged.iterrows(): result[int(row["_orig_idx"])] = row["equity"]` pourrait être remplacée par une assignation vectorisée `result[merged["_orig_idx"].astype(int).values] = merged["equity"].values`. C'est un anti-pattern §R9, même si le dashboard est un code non-critique en performance.
   - Suggestion : Remplacer par `result[merged["_orig_idx"].astype(int).values] = merged["equity"].values`.

3. **[MINEUR]** `paginate_dataframe` — `page_size` non validé
   - Fichier : `scripts/dashboard/pages/run_detail_logic.py`
   - Ligne(s) : 553–564
   - Description : Le paramètre `page_size` n'est pas validé. `page_size=0` produirait des pages toujours vides, `page_size=-1` produirait des slices incorrects. Risque faible car l'appelant utilise toujours `page_size=50`, mais la fonction est publique.
   - Suggestion : Ajouter `if page_size < 1: raise ValueError(f"page_size must be >= 1, got {page_size}")`.

---

## Résumé

| Sévérité | Compte |
|---|---|
| BLOQUANT | 0 |
| WARNING | 1 |
| MINEUR | 2 |

La branche est bien structurée (TDD RED/GREEN propre, 38 tests passants, ruff clean, 2125 tests globaux verts). La logique métier est conforme à la spec (§6.5, §6.6, §11.2). Le seul point WARNING est l'absence de validation du paramètre `sign` dans `filter_trades`, qui permet un comportement silencieux sur entrée invalide (§R1). Deux points mineurs (vectorisation `iterrows()`, validation `page_size`).
