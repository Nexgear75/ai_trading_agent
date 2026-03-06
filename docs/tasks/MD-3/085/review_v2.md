# Revue PR — [WS-D-5] #085 — Page 4 : navigation fold et equity curve

Branche : `task/085-wsd5-fold-navigation-equity`
Tâche : `docs/tasks/MD-3/085__wsd5_fold_navigation_equity.md`
Date : 2026-03-06
Itération : v2 (suite au FIX `5925bc6` corrigeant les 3 items de la v1)

## Verdict global : ✅ CLEAN

## Résumé

Les 3 items identifiés en v1 (WARNING drawdown manquant, MINEUR checklist incomplète, MINEUR fallback §R1) sont tous résolus par le commit FIX `5925bc6`. Le drawdown shading est correctement implémenté dans `chart_fold_equity()` avec un test dédié, le fallback `else 0` supprimé, et la checklist complétée. Tous les scans automatisés sont propres, la suite de tests (2140 passed) et ruff sont verts.

---

## Suivi des items v1

| # | Sévérité | Description | Statut v2 | Preuve |
|---|---|---|---|---|
| 1 | WARNING | Drawdown ombrée non implémenté dans `chart_fold_equity` | ✅ Résolu | FIX `5925bc6` : +26 lignes dans `charts.py` (§8.2 drawdown shaded area) + test `test_drawdown_shading` |
| 2 | MINEUR | Checklist incomplète (Commit GREEN non coché) | ✅ Résolu | FIX `5925bc6` : checklist mise à jour, `[x] Commit GREEN` coché |
| 3 | MINEUR | Pattern §R1 `value if value else 0` en L72 | ✅ Résolu | FIX `5925bc6` : `value=fold_names.index(selected_fold)` sans fallback |

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/085-*` | ✅ | `task/085-wsd5-fold-navigation-equity` |
| Commit RED présent | ✅ | `5b8e80c [WS-D-5] #085 RED: tests navigation fold et equity curve` — 1 fichier : `tests/test_dashboard_fold_analysis.py` (154 insertions) |
| Commit GREEN présent | ✅ | `a443b18 [WS-D-5] #085 GREEN: page analyse fold — navigation et equity` — 4 fichiers : task + 2 src + test ajustement |
| Commit FIX post-review | ✅ | `5925bc6 [WS-D-5] #085 FIX: drawdown shading dans chart_fold_equity, suppression fallback §R1, checklist` — 4 fichiers : charts.py + page + test_charts + task |
| RED contient uniquement tests | ✅ | `git show --stat 5b8e80c` : `tests/test_dashboard_fold_analysis.py` uniquement |
| GREEN contient implémentation + tâche | ✅ | `git show --stat a443b18` : task md + 2 src + test fixup |
| Pas de commits parasites | ✅ | 3 commits : RED → GREEN → FIX (corrections review v1). Séquence conforme. |

### Tâche

| Critère | Verdict | Commentaire |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` dans le fichier |
| Critères d'acceptation cochés | ✅ (9/9) | Tous cochés `[x]`. Critère #3 « zone de drawdown ombrée » maintenant implémenté (FIX `5925bc6`). |
| Checklist cochée | ✅ (8/9) | Tous cochés sauf `[ ] Pull Request ouverte` — attendu (PR pas encore créée). |

**Vérification des critères d'acceptation :**

| # | Critère | Preuve code/test |
|---|---|---|
| 1 | Dropdown run + fold fonctionnels | `4_fold_analysis.py:44` `st.selectbox("Sélectionner un run")` + `L67` `st.selectbox("Sélectionner un fold")`. Test : `test_returns_label_and_run_id_tuples`, `test_returns_sorted_fold_names`. |
| 2 | Slider alternatif | `4_fold_analysis.py:70-74` `st.slider("Navigation rapide", ...)`. Sync L77-78. |
| 3 | Equity curve + drawdown ombrée | `charts.py:471-497` drawdown shading via `fill="tonexty"` + `COLOR_DRAWDOWN`. Test : `test_drawdown_shading`. |
| 4 | Marqueurs ▲/▼ | `charts.py:499-527` (inchangé, task #077). Vérifié via `test_entry_markers`, `test_exit_markers`. |
| 5 | Dégradation si equity absente | `4_fold_analysis.py:86-88` `st.info(f"Pas de fichier equity_curve.csv...")` + `st.stop()`. |
| 6 | Dégradation si trades absents | `4_fold_analysis.py:92-93` DataFrame vide avec colonnes attendues. Test : `test_empty_trades`. |
| 7 | Tests couvrant sélection/affichage/dégradation | 10 tests fold_analysis + 6 tests chart_fold_equity (dont `test_drawdown_shading`). |
| 8 | Suite de tests verte | 2140 passed, 0 failed. |
| 9 | ruff check passe | All checks passed. |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **2140 passed**, 27 deselected, 61 warnings, 0 failed |
| `ruff check ai_trading/ tests/ scripts/` | **All checks passed** |

Phase A : **PASS**.

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux | `grep ' or []\| or {}\| if .* else '` sur SRC | **0 occurrences** (grep exécuté) — v1 MINEUR #3 résolu |
| §R1 Except trop large | `grep 'except:$\|except Exception:'` sur SRC | 0 occurrences |
| §R7 Print résiduel | `grep 'print('` sur SRC | 0 occurrences |
| §R3 Shift négatif | `grep '\.shift(-'` sur SRC | 0 occurrences |
| §R4 Legacy random API | `grep 'np.random.seed\|...'` sur ALL | 0 occurrences |
| §R7 TODO/FIXME | `grep 'TODO\|FIXME\|HACK\|XXX'` sur ALL | 0 occurrences |
| §R7 Chemins hardcodés | `grep '/tmp\|C:\\'` sur TESTS | 0 occurrences |
| §R7 Imports absolus `__init__` | N/A | Aucun `__init__.py` modifié |
| §R7 Registration manuelle tests | `grep 'register_model\|register_feature'` sur TESTS | 0 occurrences |
| §R6 Mutable defaults | `grep 'def .*=\[\]\|def .*={}'` sur ALL | 0 occurrences |
| §R6 open() sans context manager | `grep '\.read_text\|open('` sur SRC | 0 occurrences |
| §R6 Bool identity | `grep 'is np.bool_\|is True\|is False'` sur ALL | 0 occurrences |
| §R6 Dict collision | `grep '\[.*\] = '` sur SRC (hors def/commentaires) | 0 occurrences |
| §R9 for-range loops | `grep 'for .* in range(.*):` sur SRC | 0 occurrences |
| §R6 isfinite | `grep 'isfinite'` sur SRC | N/A (pas de paramètres numériques validés par bornes) |
| §R9 np comprehension | `grep 'np\.[a-z]*(.*for'` sur SRC | 0 occurrences |
| §R7 noqa | `grep 'noqa'` sur ALL | 0 occurrences |
| §R7 Fixtures dupliquées | `grep 'load_config.*configs/'` sur TESTS | 0 occurrences |
| §R7 per-file-ignores | `grep 'per-file-ignores' pyproject.toml` | Aucune entrée pour les fichiers modifiés |

### Annotations par fichier (B2)

#### `scripts/dashboard/charts.py` (modifié, +26 lignes nettes dans FIX)

- **L471-497** Drawdown shading : `running_max = df["equity"].cummax()`, puis deux traces Plotly (`tonexty` fill entre running_max invisible et equity). Pattern Plotly standard pour zone ombrée. `COLOR_DRAWDOWN` importé depuis `utils.py:21` (`rgba(231, 76, 60, 0.15)`). Hovertext `[f"DD: {d:.4f}" for d in dd]` — itération sur Series pandas, correct. Docstring mise à jour (supprimé la mention « handled separately by chart_equity_curve »). RAS.
- **Cohérence avec `chart_equity_curve`** (L55-105, inchangé) : utilise le même `COLOR_DRAWDOWN` et le même pattern `fill="tonexty"`. Pas de duplication de logique (code structurellement similaire mais rôle différent : un pour overview multi-fold, l'autre pour fold unique). RAS.

RAS après lecture complète du diff (31 lignes nettes).

#### `scripts/dashboard/pages/4_fold_analysis.py` (modifié, -1 ligne dans FIX)

- **L72** `value=fold_names.index(selected_fold),` — fallback `if selected_fold else 0` supprimé. `selected_fold` est garanti non-None par `st.selectbox` sur `fold_names` non vide (guard L62-64). RAS.
- **L28** `st.session_state.get("runs", [])` : idiome Streamlit pour lecture session_state. Validé immédiatement par `if not runs or runs_dir is None: st.stop()`. Acceptable.
- **L43** `run_id_map = {label: run_id for label, run_id in run_options}` : collision impossible car labels contiennent `run_id` (timestamp unique). RAS.
- **L90-93** Dégradation trades : `pd.DataFrame(columns=["entry_time_utc", "exit_time_utc"])` — colonnes cohérentes avec le contrat `chart_fold_equity`. RAS.

RAS après lecture complète du diff (95 lignes nettes).

#### `scripts/dashboard/pages/fold_analysis_logic.py` (nouveau, 74 lignes)

- **L14-36** `discover_folds()` : retourne liste triée de sous-dossiers dans `folds/`. Gère absence du répertoire (retourne `[]`). Filtre `is_dir()`. RAS.
- **L39-57** `build_run_selector_options()` : accès dict direct `run["run_id"]`, `run["strategy"]["name"]`. Données proviennent de `discover_runs()` qui valide en amont (frontière interne). RAS.
- **L60-74** `get_run_dir()` : composition simple de chemin. RAS.

RAS après lecture complète du diff (74 lignes).

#### `tests/test_dashboard_charts.py` (modifié, +14 lignes dans FIX)

- **L619-632** `test_drawdown_shading` : vérifie qu'exactement 1 trace a `fill="tonexty"` et `fillcolor=COLOR_DRAWDOWN`. Import de `COLOR_DRAWDOWN` depuis `utils` pour comparaison. Test structurel correct. Utilise `equity_df` et `trades_df` fixtures de la classe `TestChartFoldEquity`. RAS.

RAS après lecture complète du diff (14 lignes nettes).

#### `tests/test_dashboard_fold_analysis.py` (nouveau, 149 lignes)

- **Docstring** : `#085` présent dans la docstring module. ✅
- **Imports** : locaux dans chaque méthode — cohérent avec les autres tests dashboard.
- **`TestDiscoverFolds`** (5 tests) : sorted, empty dir, no dir, files ignored, single fold. Cas nominaux + bords couverts. ✅
- **`TestBuildRunSelectorOptions`** (3 tests) : tuple format, empty list, label content. ✅
- **`TestGetRunDir`** (2 tests) : path construction, return type. ✅
- Tous les chemins via `tmp_path`. Aucun chemin hardcodé. ✅ (scan B1)
- Pas d'aléatoire → déterministe par construction. ✅
- Données synthétiques in-memory. ✅

RAS après lecture complète du diff (149 lignes).

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_dashboard_fold_analysis.py`, `test_dashboard_charts.py`, `#085` en docstring |
| Couverture des critères | ✅ | 10 tests fold_analysis (logic) + 6 tests chart_fold_equity (dont `test_drawdown_shading`) |
| Cas nominaux + erreurs + bords | ✅ | Empty dir, no dir, single fold, files ignored, empty list, empty trades |
| Boundary fuzzing | ✅ | 0 folds, 1 fold, N folds, fichiers dans folds dir |
| Déterministes | ✅ | Pas d'aléatoire |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp`, tout via `tmp_path` |
| Tests registre réalistes | N/A | Pas de registre |
| Contrat ABC complet | N/A | Pas d'ABC |
| Tests désactivés | ✅ | Aucun `@skip` ou `xfail` |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 match fallback. Fallback v1 supprimé. Guards `st.stop()` en cas d'absence de données. |
| §R10 Defensive indexing | ✅ | Slider borné `0..len-1`, `fold_names` indexé après guard non-vide (L62-64). `cummax()` sur Series — pas de risque d'indexation hors bornes. |
| §R2 Config-driven | ✅ | N/A — page UI, pas de paramètres métier hardcodés. |
| §R3 Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. Pas de manipulation de données temporelles. |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random. Pas d'aléatoire. |
| §R5 Float conventions | ✅ | N/A — pas de calculs numériques (drawdown est pour affichage uniquement). |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 open, 0 bool identity. Hovertext list comprehension correcte. |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Tous les noms conformes |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO. Pas de code mort. |
| Imports propres | ✅ | ruff clean, pas d'imports `*` |
| DRY | ✅ | Réutilise `chart_fold_equity`, `load_fold_equity_curve`, `load_fold_trades`, `COLOR_DRAWDOWN` partagé. Drawdown pattern similaire entre `chart_equity_curve` et `chart_fold_equity` mais rôles distincts — pas de duplication problématique. |
| Pas de noqa | ✅ | Scan B1 : 0 noqa |
| `__init__.py` à jour | ✅ | N/A — pas de nouveau module dans ai_trading/ |
| Pas de fichiers générés | ✅ | Aucun artefact binaire dans la PR |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts | ✅ | Drawdown = `cummax - equity`, définition standard |
| Nommage métier cohérent | ✅ | `equity`, `trades`, `fold`, `drawdown` — termes standards |
| Séparation responsabilités | ✅ | Logic pure dans `fold_analysis_logic.py`, rendu dans `4_fold_analysis.py`, chart dans `charts.py` |
| Invariants de domaine | ✅ | N/A — page d'affichage |
| Cohérence unités/échelles | ✅ | N/A |
| Patterns de calcul | ✅ | `cummax()` pandas natif, pas de boucle Python |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Commentaire |
|---|---|---|
| Spécification §8.1 | ✅ | Dropdown run + fold + slider présents |
| Spécification §8.2 | ✅ | Equity curve OK, marqueurs OK, **drawdown ombrée OK** (résolu en v2) |
| Plan WS-D-5.1 | ✅ | Couverture complète des points du plan |
| Formules doc vs code | ✅ | Drawdown = `cummax(equity) - equity` — correct |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `chart_fold_equity(df, trades_df)` conforme à charts.py. `load_fold_equity_curve(fold_dir)` et `load_fold_trades(fold_dir)` conformes à data_loader.py. |
| Noms de colonnes DataFrame | ✅ | `entry_time_utc`, `exit_time_utc`, `time_utc`, `equity` — cohérents entre page, chart et data_loader |
| Clés de configuration | ✅ | N/A — pas de lecture config |
| Registres et conventions | ✅ | N/A |
| Structures de données partagées | ✅ | `runs` dict validé en amont par `discover_runs()` |
| Conventions numériques | ✅ | `COLOR_DRAWDOWN` partagé via `utils.py`, utilisé identiquement dans `chart_equity_curve` et `chart_fold_equity` |
| Imports croisés | ✅ | Tous les imports existent dans Max6000i1 |
| Forwarding kwargs | ✅ | N/A — pas de pattern wrapper/délégation |

---

## Remarques

Aucune.

## Résumé

Les 3 items de la revue v1 sont tous résolus. Le drawdown shading est implémenté et testé, le fallback §R1 supprimé, la checklist mise à jour. Architecture propre, scans automatisés clean (0 occurrences tous patterns), suite complète verte (2140 passed), ruff clean. Aucun nouvel item identifié.
