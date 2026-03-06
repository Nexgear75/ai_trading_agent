# Revue PR — [WS-D-5] #085 — Page 4 : navigation fold et equity curve

Branche : `task/085-wsd5-fold-navigation-equity`
Tâche : `docs/tasks/MD-3/085__wsd5_fold_navigation_equity.md`
Date : 2026-03-06

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

La PR implémente correctement la navigation run/fold (dropdown + slider) et l'affichage de l'equity curve via `chart_fold_equity()`. L'architecture est propre : logique métier extraite dans `fold_analysis_logic.py`, testable sans Streamlit. Toutefois, le critère « zone de drawdown ombrée » est coché `[x]` alors que `chart_fold_equity()` ne l'implémente pas (par design task #077). Un fallback §R1 mineur et un oubli de checklist complètent les observations.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/085-*` | ✅ | `task/085-wsd5-fold-navigation-equity` |
| Commit RED présent | ✅ | `5b8e80c [WS-D-5] #085 RED: tests navigation fold et equity curve` — 1 fichier : `tests/test_dashboard_fold_analysis.py` (154 insertions) |
| Commit GREEN présent | ✅ | `a443b18 [WS-D-5] #085 GREEN: page analyse fold — navigation et equity` — 4 fichiers : task + 2 src + test ajustement |
| RED contient uniquement tests | ✅ | `git show --stat 5b8e80c` : `tests/test_dashboard_fold_analysis.py` uniquement |
| GREEN contient implémentation + tâche | ✅ | `git show --stat a443b18` : task md + 2 src + test fixup |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` : 2 commits exactement (RED + GREEN) |

### Tâche

| Critère | Verdict | Commentaire |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` dans le fichier |
| Critères d'acceptation cochés | ⚠️ (9/9 cochés mais 1 non implémenté) | Critère #3 « zone de drawdown ombrée » coché `[x]` mais non implémenté — voir WARNING #1 |
| Checklist cochée | ❌ (8/10) | `[ ] Commit GREEN` et `[ ] Pull Request ouverte` non cochés — voir MINEUR #2 |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **2139 passed**, 27 deselected, 62 warnings, 0 failed |
| `ruff check ai_trading/ tests/ scripts/` | **All checks passed** |

Phase A : **PASS** (avec réserves mineures sur checklist).

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux | `grep ' or \[\]\| or {}\| if .* else '` sur SRC | **1 match** : `4_fold_analysis.py:72` — `value=fold_names.index(selected_fold) if selected_fold else 0` → MINEUR #3 |
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
| §R6 Dict collision | `grep '\[.*\] = '` sur SRC | 2 matches — faux positifs (assignation de variables typées, pas de dict en boucle) |
| §R9 for-range loops | `grep 'for .* in range(.*):` sur SRC | 0 occurrences |
| §R6 isfinite | `grep 'isfinite'` sur SRC | 0 occurrences — N/A (pas de paramètres numériques validés par bornes) |
| §R9 np comprehension | `grep 'np\.[a-z]*(.*for'` sur SRC | 0 occurrences |
| §R7 noqa | `grep 'noqa'` sur ALL | 0 occurrences |
| §R7 Fixtures dupliquées | `grep 'load_config.*configs/'` sur TESTS | 0 occurrences |

### Annotations par fichier (B2)

#### `scripts/dashboard/pages/fold_analysis_logic.py` (nouveau, 74 lignes)

- **L14-36** `discover_folds()` : Logique claire, retourne liste triée de noms de sous-dossiers dans `folds/`. Gère correctement l'absence du répertoire (retourne `[]`). Ignore les fichiers (filtre `is_dir()`). RAS.
- **L39-57** `build_run_selector_options()` : Accès dict direct `run["run_id"]`, `run["strategy"]["name"]` — aucune validation des clés. Acceptable car les données proviennent de `discover_runs()` qui valide en amont (frontière interne). RAS.
- **L60-74** `get_run_dir()` : Simple composition de chemin. RAS.

RAS après lecture complète du diff (74 lignes).

#### `scripts/dashboard/pages/4_fold_analysis.py` (modifié, +90 lignes)

- **L28** `st.session_state.get("runs", [])` : pattern `.get(key, default)`. Validé immédiatement par `if not runs: st.stop()`. Acceptable — idiomatique Streamlit.
- **L43** `run_id_map = {label: run_id for label, run_id in run_options}` : dict comprehension avec clés `label`. Risque de collision si deux runs ont le même label. Labels = `f"{run_id} — {strategy_name}"` — run_id est un timestamp unique, donc collision impossible en pratique. RAS.
- **L47-49** `if selected_label is None: st.stop()` : garde correcte pour le cas où `st.selectbox` retourne `None` (liste vide impossible car `run_options` vient de `runs` non vide).
- **L72** `value=fold_names.index(selected_fold) if selected_fold else 0` : **pattern §R1** `value if value else default`. `selected_fold` est toujours un `str` à ce stade (garde `if not fold_names: st.stop()` en L64 + `st.selectbox` sur liste non vide). Le `else 0` est du code mort. → **MINEUR #3**.
- **L77-78** Sync slider/dropdown : `if fold_names[fold_index] != selected_fold: selected_fold = fold_names[fold_index]`. Logique correcte, pas de risque d'index out-of-bounds car le slider est borné.
- **L84** `equity_df = load_fold_equity_curve(fold_dir)` : retourne `None` ou DataFrame. Géré correctement L86-88 (`st.info` + `st.stop()`).
- **L90-91** `if trades_df is None: trades_df = pd.DataFrame(columns=["entry_time_utc", "exit_time_utc"])` : dégradation gracieuse requise par la tâche. Colonnes cohérentes avec le contrat de `chart_fold_equity` (`entry_time_utc`, `exit_time_utc`). `chart_fold_equity` gère `len(trades_df) == 0` en retournant la courbe seule. RAS.
- **L93-94** `chart_fold_equity(equity_df, trades_df)` : signature conforme (2 positionnels DataFrame). Vérifié : `charts.py:443` `def chart_fold_equity(df, trades_df) -> go.Figure`. Cohérence intermodule OK.
- **Drawdown manquant** : la spec §8.2 requiert « Zone de drawdown ombrée ». `chart_fold_equity` docstring dit explicitement : "Drawdown shading is handled separately by chart_equity_curve (§6.3) and is not duplicated here by design." Le critère #3 de la tâche est coché `[x]` mais la fonctionnalité n'est pas rendue. → **WARNING #1**.

#### `tests/test_dashboard_fold_analysis.py` (nouveau, 149 lignes)

- **Docstring** : `#085` présent dans la docstring module. ✅
- **Imports** : locaux dans chaque méthode — pattern cohérent avec les autres tests dashboard.
- **`TestDiscoverFolds`** (5 tests) : sorted, empty dir, no dir, files ignored, single fold. Couverture des cas nominaux + bords. ✅
- **`TestBuildRunSelectorOptions`** (3 tests) : tuple format, empty list, label content. Cas nominal + vide. ✅
- **`TestGetRunDir`** (2 tests) : path construction, return type. ✅
- **Tous les chemins via `tmp_path`** : aucun chemin hardcodé. ✅
- **Déterminisme** : pas d'aléatoire dans ces tests. ✅
- **Données synthétiques** : structures in-memory, pas de réseau. ✅
- **Couverture des critères** : les tests couvrent la logique pure (discovery, selector, path). Les critères liés au rendu Streamlit (equity curve display, degradation UI, slider sync) ne sont pas testés directement — acceptable pour du code UI Streamlit, la logique testable est extraite.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_dashboard_fold_analysis.py`, `#085` en docstring |
| Couverture des critères | ✅ | Logic testée : discover_folds (5 tests), build_run_selector_options (3 tests), get_run_dir (2 tests) |
| Cas nominaux + erreurs + bords | ✅ | Empty dir, no dir, single fold, files ignored, empty list |
| Boundary fuzzing | ✅ | 0 folds, 1 fold, N folds, files in folds dir |
| Déterministes | ✅ | Pas d'aléatoire |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp`, tout via `tmp_path` |
| Tests registre réalistes | N/A | Pas de registre |
| Contrat ABC complet | N/A | Pas d'ABC |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| Strict code (no fallbacks) | ⚠️ | Scan B1 : 1 match L72 (MINEUR — dead code `else 0`). Reste du code valide + st.stop(). |
| Defensive indexing | ✅ | Slider borné `0..len-1`, fold_names indexé après guard non-vide |
| Config-driven | ✅ | N/A — page UI, pas de paramètres hardcodés métier |
| Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. Pas de données temporelles manipulées |
| Reproductibilité | ✅ | Scan B1 : 0 legacy random. Pas d'aléatoire |
| Float conventions | ✅ | N/A — pas de calculs numériques |
| Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 open, 0 bool identity |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Tous les noms respectent la convention |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO |
| Imports propres | ✅ | Pas d'imports inutilisés (ruff clean), pas d'imports `*` |
| DRY | ✅ | Réutilise chart_fold_equity, load_fold_equity_curve, load_fold_trades |
| Pas de noqa | ✅ | Scan B1 : 0 noqa |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Commentaire |
|---|---|---|
| Spécification §8.1 | ✅ | Dropdown run + fold + slider présents |
| Spécification §8.2 | ⚠️ | Equity curve OK, marqueurs OK. **Drawdown ombrée absent** (non implémenté dans `chart_fold_equity`) |
| Plan WS-D-5.1 | ⚠️ | Point 4 du plan mentionne « zone de drawdown » — non couvert |
| Formules doc vs code | ✅ | N/A — pas de formules mathématiques |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `chart_fold_equity(df, trades_df)` conforme à charts.py:443. `load_fold_equity_curve(fold_dir)` et `load_fold_trades(fold_dir)` conformes à data_loader.py |
| Noms de colonnes DataFrame | ✅ | `entry_time_utc`, `exit_time_utc` cohérents entre page et chart |
| Clés de configuration | ✅ | N/A — pas de lecture config |
| Registres et conventions | ✅ | N/A |
| Structures de données partagées | ✅ | `runs` dict validé en amont par `discover_runs()` |
| Conventions numériques | ✅ | N/A |
| Imports croisés | ✅ | Tous les imports existent dans Max6000i1 |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | N/A — page de navigation/affichage |
| Nommage métier cohérent | ✅ | `equity`, `trades`, `fold` — termes standards |
| Séparation des responsabilités | ✅ | Logique pure séparée dans `fold_analysis_logic.py`, rendu dans `4_fold_analysis.py` |
| Invariants de domaine | ✅ | N/A |
| Cohérence des unités/échelles | ✅ | N/A |
| Patterns de calcul financier | ✅ | N/A |

---

## Remarques

1. **[WARNING]** Critère #3 « Zone de drawdown ombrée » coché `[x]` mais non implémenté.
   - Fichier : `scripts/dashboard/pages/4_fold_analysis.py`
   - Contexte : La spec §8.2 requiert « Zone de drawdown ombrée ». `chart_fold_equity()` (task #077) l'exclut explicitement par design (docstring : "Drawdown shading is handled separately by chart_equity_curve"). La page n'appelle que `chart_fold_equity` → pas de drawdown rendu.
   - Suggestion : modifier `chart_fold_equity` pour inclure le drawdown shading (zone ombrée entre l'equity peak et l'equity courante), conformément à §8.2.

2. **[MINEUR]** Checklist incomplète : `[ ] Commit GREEN` et `[ ] Pull Request` non cochés.
   - Fichier : `docs/tasks/MD-3/085__wsd5_fold_navigation_equity.md`
   - Ligne(s) : dernières lignes de la checklist
   - Suggestion : Cocher `[x]` le commit GREEN (il existe : `a443b18`). La PR reste `[ ]` tant qu'elle n'est pas ouverte.

3. **[MINEUR]** Pattern §R1 : `value if value else default` en L72.
   - Fichier : `scripts/dashboard/pages/4_fold_analysis.py`
   - Ligne : 72
   - Code : `value=fold_names.index(selected_fold) if selected_fold else 0`
   - Contexte : `selected_fold` est toujours un `str` non vide à ce stade (guard `if not fold_names: st.stop()` en L64 + `st.selectbox` sur liste non vide). Le `else 0` est du code mort et viole formellement §R1.
   - Suggestion : Remplacer par `value=fold_names.index(selected_fold)` sans fallback.

## Résumé

Architecture propre avec séparation logique/rendu. Le code est fonctionnel, les tests couvrent la logique pure, et l'intermodule est cohérent. Le seul point de friction notable est le critère drawdown coché sans implémentation — à clarifier ou corriger.
