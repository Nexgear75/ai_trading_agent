# Revue PR — [WS-D-4] #083 — Page 3 : sélection des runs et tableau comparatif

Branche : `task/083-wsd4-comparison-table`
Tâche : `docs/tasks/MD-3/083__wsd4_comparison_table.md`
Date : 2026-03-09

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

L'implémentation est solide : logique métier correctement extraite dans `comparison_logic.py`, réutilisation DRY des fonctions d'`overview_logic.py`, tests complets (32 tests, 0 échec), linter clean. Deux points mineurs identifiés : une expression à double négation difficile à lire et des checkboxes non cochées dans la tâche malgré l'existence du commit GREEN.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/083-*` | ✅ | `task/083-wsd4-comparison-table` (HEAD) |
| Commit RED présent | ✅ | `322b3f8` — `[WS-D-4] #083 RED: tests sélection runs et tableau comparatif` |
| Commit RED contient uniquement des tests | ✅ | `git show --stat 322b3f8` → `tests/test_dashboard_comparison.py | 486 +++` (1 fichier) |
| Commit GREEN présent | ✅ | `96aee8e` — `[WS-D-4] #083 GREEN: sélection runs et tableau comparatif` |
| Commit GREEN contient implémentation + tâche | ✅ | `git show --stat 96aee8e` → 4 fichiers : task, 2 source, 1 test (ajustement) |
| Pas de commits parasites entre RED et GREEN | ✅ | `git log --oneline Max6000i1...HEAD` → exactement 2 commits |

### Tâche

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` dans le fichier de tâche |
| Critères d'acceptation cochés | ✅ (9/9) | Tous `[x]` |
| Checklist cochée | ⚠️ (7/9) | Commit GREEN `[ ]` et PR `[ ]` non cochés — voir MINEUR #2 |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/test_dashboard_comparison.py -v --tb=short` | **32 passed**, 0 failed |
| `ruff check scripts/dashboard/ tests/test_dashboard_comparison.py` | **All checks passed** |

Phase A : **PASS** — poursuite en Phase B.

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

| Pattern recherché | Règle | Commande | Résultat |
|---|---|---|---|
| Fallbacks silencieux | §R1 | `grep -n ' or []\| or {}\| or ""\| or 0\b\| if .* else ' SRC` | 1 match : `3_comparison.py:95` — **faux positif** : ternaire `"✅" if passed else "❌"` (pas un fallback) |
| Except trop large | §R1 | `grep -n 'except:$\|except Exception:' SRC` | 0 occurrences |
| Suppressions lint (noqa) | §R7 | `grep -n 'noqa' ALL` | 0 occurrences |
| Print résiduel | §R7 | `grep -n 'print(' SRC` | 0 occurrences |
| Shift négatif (look-ahead) | §R3 | `grep -n '.shift(-' SRC` | 0 occurrences |
| Legacy random API | §R4 | `grep -n 'np.random.seed\|...' ALL` | 0 occurrences |
| TODO/FIXME orphelins | §R7 | `grep -n 'TODO\|FIXME\|HACK\|XXX' ALL` | 0 occurrences |
| Chemins hardcodés | §R7 | `grep -n '/tmp\|/var/tmp\|C:\\' TEST` | 0 occurrences |
| Mutable default arguments | §R6 | `grep -n 'def .*=[]\|def .*={}' ALL` | 0 occurrences |
| open() sans context manager | §R6 | `grep -n '.read_text\|open(' SRC` | 0 occurrences |
| Bool identity (numpy/pandas) | §R6 | `grep -n 'is True\|is False' ALL` | 11 matches tests — **faux positifs** : `check_criterion_14_4` retourne un `bool` Python natif, `is True`/`is False` est correct sur singletons Python |
| Dict collision silencieuse | §R6 | `grep -n '\[.*\] = ' SRC` | 7 matches — **tous faux positifs** : assignations sur clés uniques (colonnes DF, clés de dict constant) |
| Boucle Python range() | §R9 | `grep -n 'for .* in range(.*):' SRC` | 1 match : `3_comparison.py:120` — boucle sur DataFrame pour styling Streamlit, pas un hot path, acceptable |
| isfinite checks | §R6 | `grep -n 'isfinite' SRC` | 0 occurrences — N/A : pas de validation de bornes numériques en entrée publique |
| Fixtures dupliquées | §R7 | `grep -n 'load_config.*configs/' TEST` | 0 occurrences |
| Registration manuelle | §R7 | `grep -n 'register_model\|register_feature' TEST` | 0 occurrences |

### B2. Annotations par fichier

#### `scripts/dashboard/pages/comparison_logic.py` (228 lignes)

- **L22-28** `_HIGHLIGHT_COLUMNS` : dictionnaire statique, clés littérales uniques. MDD avec `True` (higher value = less negative = better) : sémantiquement correct. RAS.

- **L37-54** `build_comparison_dataframe()` : délègue à `build_overview_dataframe(runs)` pour DRY. Signature compatible vérifiée (`overview_logic.py:44`). RAS.

- **L62-88** `highlight_best_worst()` : itère sur `_HIGHLIGHT_COLUMNS`, utilise `idxmax/idxmin` sur séries non-nulles. Giste correct : si toutes None → best/worst = None. Si une seule valeur → best == worst (pas de highlight appliqué dans le rendu). RAS.

- **L95-125** `check_criterion_14_4()` :
  - L108-110 : `.get()` sur clés métriques retournant None, suivi d'un check explicite `if ... is None: return False` — correct, pas un fallback silencieux §R1.
  - L112 : `config_snapshot["thresholding"]["mdd_cap"]` — accès strict, KeyError si structure invalide. Conforme §R1.
  - **L125** `return not max_drawdown <= mdd_cap` : expression à double négation. Équivalent exact à `return max_drawdown > mdd_cap`. Logique vérifiée :
    - mdd=-0.03, cap=-0.10 → `not (-0.03 <= -0.10)` → `not False` → True ✓ (drawdown moins sévère que le cap)
    - mdd=-0.15, cap=-0.10 → `not (-0.15 <= -0.10)` → `not True` → False ✓ (drawdown plus sévère)
    - mdd=-0.10, cap=-0.10 → `not (-0.10 <= -0.10)` → `not True` → False ✓ (strictement)
  - Sévérité : **MINEUR** (readability) — voir Remarque #1.

- **L133-165** `_none_to_zero()` + `build_radar_data()` : conversion explicite None→0.0 pour rendu radar chart, documenté dans docstring. Pas un fallback §R1 — c'est le comportement attendu pour la visualisation. RAS.

- **L173-200** `get_aggregate_notes()` : accès via `.get("notes")`, vérification explicite None + empty string → None. Correct. RAS.

- **L208-222** `format_comparison_dataframe()` : délègue à `format_overview_dataframe`. DRY ✓. RAS.

#### `scripts/dashboard/pages/3_comparison.py` (138 lignes)

- **L33-38** Guard `st.session_state["runs"]` avec `st.error` + `st.stop()`. Correct. RAS.

- **L40** `runs_dir = st.session_state.get("runs_dir")` : `runs_dir` peut être None. Géré correctement à L82 (`if runs_dir is not None`). Quand None → `config_snapshot` reste None → `check_criterion_14_4` retourne False → ❌ affiché. Comportement dégradé mais explicite (logging warning). RAS.

- **L49-52** `run_labels` dict comprehension : clé `"{name} ({run_id})"`. Pas de risque de collision car `run_id` est unique (timestamp). RAS.

- **L54-57** Multisélect avec `max_selections=10`. Minimum enforced programmatiquement à L59 (`< 2` → info + stop). Conforme §7.1. RAS.

- **L80-96** Boucle §14.4 : `try`/`except FileNotFoundError` pour `load_config_snapshot`. Correct — fichier légitimement absent. Log warning avec `run_id`. RAS.

- **L105-114** `_style_cell()` : closure sur `highlights` (outer scope). Condition `best != worst` empêche le highlight quand tous égaux. Sémantiquement correct. RAS.

- **L120-128** `for idx in range(len(df_formatted))` : boucle Python pour styling. N'est pas un hot path (exécuté une seule fois au rendu). `enumerate` serait plus idiomatique mais pas bloquant. RAS.

- **L130** `st.markdown(df_styled.to_markdown(index=False), unsafe_allow_html=True)` : rendu tableau markdown avec coloring Streamlit. RAS.

- **L135-138** Affichage des notes/warnings via `st.warning`. Conforme §7.2. RAS.

#### `tests/test_dashboard_comparison.py` (486 lignes)

- **Docstrings** : tous les tests contiennent `#083` dans la docstring. Conforme convention. ✅
- **Helper `_make_metrics()`** : synthétise un dict metrics valide. Pas de dépendance réseau. ✅
- **Helper `_make_config_snapshot()`** : synthétise un config_snapshot minimal. ✅
- **Imports locaux** : chaque méthode de test fait un `from ... import` local. Pattern cohérent avec le rest du projet. ✅

Classes de tests et couverture :

| Classe | Tests | Couverture |
|---|---|---|
| `TestBuildComparisonDataframe` | 5 | empty, single, three, None values, columns match overview |
| `TestHighlightBestWorst` | 4 | basic (3 runs), ties, single run, all None |
| `TestCheckCriterion144` | 11 | all pass, pnl fails, pnl=0 fails, pf fails, pf=1.0 fails, mdd fails, mdd=cap fails, None config, None pnl, None pf, None mdd |
| `TestBuildRadarData` | 3 | normal, None→0.0, multiple runs |
| `TestGetAggregateNotes` | 3 | present, absent, empty string |
| `TestFormatComparisonDataframe` | 6 | pnl %, sharpe float, mdd %, win rate %, trades int, None→dash |

Total : **32 tests**. Couverture des critères d'acceptation :

| Critère d'acceptation | Tests couvrant |
|---|---|
| Multiselect 2-10 runs | `TestBuildComparisonDataframe` (1-3 runs), logique multiselect dans 3_comparison.py |
| Tableau comparatif colonnes §5.2 | `test_columns_match_overview`, `test_three_runs` |
| Surbrillance best/worst | `TestHighlightBestWorst` (4 tests) |
| Icône ✅/❌ §14.4 avec MDD config | `TestCheckCriterion144` (11 tests, dont missing config) |
| Notes/warnings | `TestGetAggregateNotes` (3 tests) |
| Message < 2 runs | Non testé unitairement (logique Streamlit dans page) — acceptable |
| Suite verte | 32 passed ✅ |
| ruff clean | All checks passed ✅ |

RAS sur les tests. Couverture bords + erreurs excellente.

### B3. Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_dashboard_comparison.py`, `#083` dans docstrings |
| Couverture critères d'acceptation | ✅ | Mapping ci-dessus : 9/9 critères couverts |
| Cas nominaux + erreurs + bords | ✅ | 32 tests : empty, single, ties, all None, None métriques, None config, boundary values |
| Boundary fuzzing | ✅ | pnl=0, pf=1.0, mdd=cap → tous rejetés (strictly) |
| Déterministes | ✅ | Pas d'aléatoire dans les tests |
| Données synthétiques | ✅ | `_make_metrics()` et `_make_config_snapshot()` |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé |
| Tests registre | N/A | Pas de registre |
| Contrat ABC | N/A | Pas d'ABC |

### B4. Code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback réel, `.get()` suivi de check `is None` explicite |
| §R2 Config-driven | ✅ | MDD cap lu depuis `config_snapshot.yaml` (`thresholding.mdd_cap`), pas hardcodé |
| §R3 Anti-fuite | N/A | Dashboard lecture seule, pas de données temporelles à protéger |
| §R4 Reproductibilité | N/A | Dashboard sans composante aléatoire |
| §R5 Float conventions | N/A | Dashboard : pas de tenseurs, pas de métriques calculées |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable default, 0 open() sans context, `is True/False` sur Python bool (faux positifs) |
| §R10 Defensive indexing | ✅ | `highlight_best_worst` gère séries vides (all None case), `idxmax/idxmin` sur `non_null` non-empty |

### B5. Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Tous les identifiants conformes |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO, 0 noqa |
| Imports propres | ✅ | Pas d'import inutilisé, pas d'import *, ordre correct |
| DRY | ✅ | `build_comparison_dataframe` et `format_comparison_dataframe` délèguent à `overview_logic` |

### B6. Conformité spec

| Critère | Verdict | Preuve |
|---|---|---|
| §7.1 Multiselect 2-10 runs | ✅ | `st.sidebar.multiselect(..., max_selections=10)` + check `< 2` |
| §7.2 Tableau comparatif colonnes §5.2 | ✅ | Déléguée à `build_overview_dataframe` qui produit les colonnes §5.2 |
| §7.2 Surbrillance best vert / worst rouge | ✅ | `highlight_best_worst()` + `_style_cell()` avec `**:green[...]**` / `*:red[...]*` |
| §7.2 aggregate.notes | ✅ | `get_aggregate_notes()` + `st.warning()` |
| §14.4 Criterion check | ✅ | `check_criterion_14_4()` vérifie P&L>0, PF>1.0, MDD > mdd_cap (convention valeurs négatives) |
| §9.3 Formatting | ✅ | Délégué à `format_overview_dataframe` (même conventions) |

### B7. Cohérence intermodule

| Critère | Verdict | Preuve |
|---|---|---|
| Signatures et types de retour | ✅ | `build_overview_dataframe(runs: list[dict]) -> pd.DataFrame` correspond à l'appel `comparison_logic.py:54` |
| Clés métriques | ✅ | `net_pnl`, `sharpe`, `max_drawdown`, `hit_rate`, `n_trades`, `profit_factor` — cohérents avec overview_logic et metrics.json |
| `load_config_snapshot` | ✅ | Signature `load_config_snapshot(run_dir: Path) -> dict` appelée correctement à L86 avec `Path(runs_dir) / run_id` |
| Imports croisés | ✅ | `overview_logic`, `data_loader` existent dans Max6000i1 |

### B5-bis. Bonnes pratiques métier

| Critère | Verdict | Preuve |
|---|---|---|
| Exactitude concepts financiers | ✅ | MDD convention négative respectée, highlight "higher=better" correct pour MDD |
| Nommage métier | ✅ | `net_pnl`, `sharpe`, `max_drawdown`, `profit_factor` — noms standards |
| Séparation responsabilités | ✅ | Logique dans `comparison_logic.py`, rendu dans `3_comparison.py` |

---

## Remarques

1. **[MINEUR]** Expression à double négation dans `check_criterion_14_4`
   - Fichier : `scripts/dashboard/pages/comparison_logic.py`
   - Ligne : 125
   - Code actuel : `return not max_drawdown <= mdd_cap`
   - Suggestion : remplacer par `return max_drawdown > mdd_cap` — sémantiquement identique, plus lisible.

2. **[MINEUR]** Checkboxes de fin de tâche non cochées malgré commit existant
   - Fichier : `docs/tasks/MD-3/083__wsd4_comparison_table.md`
   - Lignes : checklist Commit GREEN `[ ]` et PR `[ ]`
   - Suggestion : cocher `[x]` le Commit GREEN (96aee8e existe) et la PR quand elle sera ouverte.

---

## Résumé

| Sévérité | Count |
|---|---|
| BLOQUANT | 0 |
| WARNING | 0 |
| MINEUR | 2 |

```
RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 0
- Mineurs : 2
- Rapport : docs/tasks/MD-3/083/review_v1.md
```
