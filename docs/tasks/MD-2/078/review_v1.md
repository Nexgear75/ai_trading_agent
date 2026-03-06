# Revue PR — [WS-D-2] #078 — Point d'entrée Streamlit et navigation multi-pages

Branche : `task/078-wsd2-app-entry-navigation`
Tâche : `docs/tasks/MD-2/078__wsd2_app_entry_navigation.md`
Date : 2026-03-05

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

L'implémentation est propre, bien architecturée (séparation logique pure / Streamlit, imports lazy) et conforme à la spec §5.1, §9.4, §10.2, §11.1. La résolution `resolve_runs_dir()` est rigoureuse avec validation stricte. Deux points à corriger : la fonction `main()` n'est pas testée (les critères d'acceptation #1 et #6 ne sont vérifiables que par lecture du code), et la checklist du fichier de tâche a deux items non cochés alors que le commit GREEN existe.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/NNN-short-slug` | ✅ | `git branch --show-current` → `task/078-wsd2-app-entry-navigation` |
| Commit RED présent | ✅ | `c12f708` — `[WS-D-2] #078 RED: tests app entry point et navigation` |
| Commit RED = tests uniquement | ✅ | `git show --stat c12f708` → `tests/test_app_entry.py | 207 +++` (1 seul fichier) |
| Commit GREEN présent | ✅ | `52bc9d5` — `[WS-D-2] #078 GREEN: app entry point et navigation multi-pages` |
| Commit GREEN = impl + tâche | ✅ | `git show --stat 52bc9d5` → `scripts/dashboard/app.py` + `docs/tasks/MD-2/078__wsd2_app_entry_navigation.md` |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → 2 commits exactement (RED + GREEN) |

### Tâche

| Critère | Verdict | Commentaire |
|---|---|---|
| Statut DONE | ✅ | Ligne 2 : `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (10/10) | Tous `[x]` |
| Checklist cochée | ❌ (8/10) | 2 items non cochés : `[ ] Commit GREEN`, `[ ] Pull Request ouverte` |

> **Remarque** : le commit GREEN (`52bc9d5`) existe bien. L'item `[ ] Commit GREEN` devrait être `[x]`. L'item `[ ] Pull Request ouverte` est attendu (PR pas encore créée).

### CI

| Check | Résultat |
|---|---|
| `pytest tests/test_app_entry.py -v --tb=short` | **15 passed**, 0 failed |
| `pytest tests/ -v --tb=short` (suite complète) | **1994 passed**, 27 deselected, 0 failed |
| `ruff check scripts/ tests/test_app_entry.py` | **All checks passed** |

✅ Phase A passe — suite en Phase B.

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| Fallbacks silencieux (`or []`, `or {}`, etc.) | `grep -n ' or \[\]\| or {}\| or ""\| or 0\b\| if .* else '` sur `scripts/dashboard/app.py` | 0 occurrences |
| Except trop large | `grep -n 'except:$\|except Exception:'` sur `scripts/dashboard/app.py` | 0 occurrences |
| Suppressions lint (`noqa`) | `grep -n 'noqa'` sur SRC + TEST | 0 occurrences |
| Print résiduel | `grep -n 'print('` sur `scripts/dashboard/app.py` | 0 occurrences |
| Shift négatif (look-ahead) | `grep -n '\.shift(-'` sur `scripts/dashboard/app.py` | 0 occurrences |
| Legacy random API | `grep -n 'np.random.seed\|...'` sur SRC + TEST | 0 occurrences |
| TODO/FIXME orphelins | `grep -n 'TODO\|FIXME\|HACK\|XXX'` sur SRC + TEST | 0 occurrences |
| Chemins hardcodés OS | `grep -n '/tmp\|C:\\'` sur `tests/test_app_entry.py` | 0 occurrences |
| Imports absolus `__init__` | `grep -n 'from ai_trading\.'` sur `scripts/dashboard/app.py` | 0 occurrences |
| Mutable defaults | `grep -rn 'def.*=\[\]\|def.*={}'` sur `scripts/dashboard/app.py` | 0 occurrences |

### Annotations par fichier (B2)

#### `scripts/dashboard/app.py` (140 lignes ajoutées)

- **L22-28** `PAGE_DEFINITIONS` : définitions statiques des 4 pages avec chemins absolus calculés à l'import via `_DASHBOARD_DIR`. Les 4 fichiers (`1_overview.py`, `2_run_detail.py`, `3_comparison.py`, `4_fold_analysis.py`) existent dans `scripts/dashboard/pages/`. ✅ Conforme à §10.2.

- **L37-40** `resolve_runs_dir(cli_args, env, default)` : signature explicite, pas de valeur par défaut implicite masquant un manque. Les 3 paramètres sont obligatoires. ✅ Conforme §R1.

- **L72-73** `raw_path = _parse_runs_dir_from_args(cli_args)` puis cascade `if raw_path is None` : logique de précédence correcte CLI > env > default. ✅ Conforme §5.1.

- **L83** `resolved = Path(raw_path).resolve()` : résolution de chemin pour prévenir les traversals. ✅ Conforme §11.1.

- **L86-92** Validation stricte : `FileNotFoundError` si inexistant, `NotADirectoryError` si fichier. Pas de fallback silencieux. ✅ Conforme §R1.

- **L97-105** `_parse_runs_dir_from_args` : parsing correct des deux syntaxes `--runs-dir VALUE` et `--runs-dir=VALUE`. La condition `i + 1 < len(args)` prévient l'IndexError quand `--runs-dir` est le dernier argument. ✅

- **L104** `arg.split("=", 1)[1]` : le `maxsplit=1` est correct — gère les valeurs contenant `=`. ✅

- **L114** `import streamlit as st` en import lazy dans `main()` : bonne pratique — permet d'importer `resolve_runs_dir` et `PAGE_DEFINITIONS` sans Streamlit installé (pour les tests). ✅

- **L118** `st.set_page_config(layout="wide", page_title="AI Trading Dashboard")` : conforme au plan WS-D-2.1 et spec §9.4. ✅

- **L121-124** Appel à `resolve_runs_dir` avec les bons arguments : `sys.argv[1:]`, `os.environ.get(...)`, `"runs/"`. ✅ Conforme §10.3.

- **L127-130** `if "runs" not in st.session_state` : chargement unique des runs dans session_state. Pattern correct pour Streamlit. ✅

- **L133-137** Navigation multi-pages via `st.Page` + `st.navigation`. ✅ Conforme §10.2.

- **EDGE CASE — `--runs-dir=` (chaîne vide)** : `_parse_runs_dir_from_args(["--runs-dir="])` retourne `""`. Ensuite `Path("").resolve()` renvoie `cwd()`, ce qui passe la validation si cwd est un répertoire. Même comportement si `AI_TRADING_RUNS_DIR=""`. Le répertoire courant serait scanné silencieusement au lieu d'une erreur. Pas de test pour ce cas.
  Sévérité : **MINEUR**
  Suggestion : Ajouter une validation `if not raw_path:` après résolution de la cascade (avant `Path(raw_path).resolve()`), ou simplement un test documentant le comportement actuel.

#### `tests/test_app_entry.py` (207 lignes ajoutées)

- **L1-10** Docstring avec `Task #078` — conforme à la convention (ID tâche dans docstring, pas dans nom de fichier). ✅

- **L27-39** `test_default_when_no_cli_no_env` : utilise `tmp_path` (portabilité). Vérifie que le default est utilisé quand CLI et env sont absents. ✅

- **L41-56** `test_cli_arg_takes_precedence_over_env` : crée deux répertoires distincts, vérifie que CLI l'emporte. ✅

- **L58-70** `test_env_var_takes_precedence_over_default` : env > default. ✅

- **L72-84** `test_cli_arg_with_equals_syntax` : teste la syntaxe `--runs-dir=<path>`. ✅

- **L86-96** `test_error_if_directory_does_not_exist` : vérifie `FileNotFoundError`. ✅

- **L98-110** `test_error_if_path_is_file_not_directory` : vérifie `NotADirectoryError`. ✅

- **L112-126** `test_path_is_resolved_for_security` : vérifie que le traversal `..` est résolu. Assertion `".." not in str(result)`. ✅

- **L128-136** `test_env_var_nonexistent_directory_errors` + **L138-146** `test_default_nonexistent_directory_errors` : couvrent les erreurs pour les 3 sources (CLI, env, default). ✅

- **L148-161** `test_cli_unknown_args_ignored` : args inconnus ne cassent pas le parsing. ✅

- **L163-171** `test_returns_path_object` : vérifie le type de retour. ✅

- **L180-187** `test_page_definitions_exist` : 4 pages, type `list`. ✅

- **L189-195** `test_page_definitions_order` : ordre exact des titres. ✅

- **L197-203** `test_page_definitions_have_required_keys` : clés `path` et `title` présentes. ✅

- **L205-210** `test_page_files_exist` : vérifie que chaque fichier page existe sur disque. ✅

- RAS supplémentaire après lecture complète du diff (207 lignes).

#### `docs/tasks/MD-2/078__wsd2_app_entry_navigation.md` (61 lignes ajoutées)

- **L60** `[ ] Commit GREEN` : non coché alors que le commit `52bc9d5` existe.
  Sévérité : **MINEUR**
  Suggestion : Cocher `[x]`.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_app_entry.py`, `Task #078` dans docstring |
| Couverture des critères d'acceptation | ⚠️ | Voir mapping ci-dessous |
| Cas nominaux + erreurs + bords | ✅ | 3 cas d'erreur (non-existent CLI/env/default, file-not-dir), bords (unknown args, equals syntax, traversal) |
| Boundary fuzzing | ✅ | N/A pour ce module (pas de paramètres numériques) |
| Déterministes | ✅ | Pas d'aléatoire, résultats déterministes |
| Données synthétiques | ✅ | `tmp_path` uniquement, pas de réseau |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé, tout via `tmp_path` |
| Tests registre | N/A | Pas de registre |
| Contrat ABC | N/A | Pas d'ABC |

**Mapping critères → tests :**

| Critère d'acceptation | Test(s) | Verdict |
|---|---|---|
| `st.set_page_config(layout="wide", page_title="AI Trading Dashboard")` | Aucun test | ⚠️ Vérifié par lecture code L118 |
| `--runs-dir` CLI fonctionnel | `test_cli_arg_takes_precedence_over_env`, `test_cli_arg_with_equals_syntax` | ✅ |
| `AI_TRADING_RUNS_DIR` env var | `test_env_var_takes_precedence_over_default`, `test_env_var_nonexistent_directory_errors` | ✅ |
| Précédence CLI > env > default | `test_cli_arg_takes_precedence_over_env`, `test_env_var_takes_precedence_over_default`, `test_default_when_no_cli_no_env` | ✅ |
| Erreur si répertoire inexistant | `test_error_if_directory_does_not_exist`, `test_env_var_nonexistent_directory_errors`, `test_default_nonexistent_directory_errors` | ✅ |
| `discover_runs()` + `st.session_state` | Aucun test | ⚠️ Vérifié par lecture code L127-130 |
| 4 pages accessibles | `test_page_definitions_exist`, `test_page_definitions_order`, `test_page_files_exist` | ✅ |
| Tests nominaux + erreurs + bords | 11 tests resolve + 4 tests pages | ✅ |
| Suite verte | 15 passed, 0 failed | ✅ |
| ruff clean | All checks passed | ✅ |

> **WARNING** : Les critères #1 (`st.set_page_config`) et #6 (`discover_runs` + `session_state`) sont marqués `[x]` dans la tâche mais ne sont couverts par aucun test. Ils sont vérifiables uniquement par lecture du code source. La fonction `main()` n'a aucun test unitaire.

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback, 0 except large. Validation explicite `FileNotFoundError` / `NotADirectoryError`. |
| §R10 Defensive indexing | ✅ | L101 `i + 1 < len(args)` prévient IndexError. L104 `split("=", 1)` correct. |
| §R2 Config-driven | ✅ | Le default `"runs/"` est conforme à la spec §5.1. Pas de hardcoding de paramètres modifiables. |
| §R3 Anti-fuite | N/A | Module dashboard, pas de données ML. |
| §R4 Reproductibilité | N/A | Pas d'aléatoire. Scan B1 : 0 legacy random. |
| §R5 Float conventions | N/A | Pas de calculs numériques. |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults. Pas de `open()` sans context manager. Pas de `==` sur floats. |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `resolve_runs_dir`, `_parse_runs_dir_from_args`, `PAGE_DEFINITIONS` (constante upper_case). |
| Pas de code mort/debug | ✅ | Scan B1 : 0 `print()`, 0 TODO/FIXME. |
| Imports propres | ✅ | stdlib (`os`, `sys`, `pathlib`) en top-level. Streamlit et `data_loader` en lazy import dans `main()`. Scan B1 : 0 `noqa`. |
| DRY | ✅ | Pas de duplication. La logique de parsing est dans `_parse_runs_dir_from_args`. |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Commentaire |
|---|---|---|
| §5.1 Sélection des runs | ✅ | Paramètre `--runs-dir`, env var `AI_TRADING_RUNS_DIR`, défaut `runs/`. Précédence correcte. |
| §9.4 Responsivité | ✅ | `st.set_page_config(layout="wide")` L118. |
| §10.2 Structure du code | ✅ | `app.py` point d'entrée, 4 pages dans `pages/`. Structure conforme. |
| §10.3 Commande de lancement | ✅ | `sys.argv[1:]` parsing compatible avec `streamlit run app.py -- --runs-dir`. |
| §11.1 Sécurité | ✅ | `Path.resolve()` L83. Lecture seule (pas de modification d'artefacts). |
| Plan WS-D-2.1 | ✅ | Les 4 tâches du plan sont implémentées. |
| Formules doc vs code | N/A | Pas de formules mathématiques. |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `discover_runs(runs_dir: Path) -> list[dict]` — L121 passe bien un `Path`. |
| Clés de configuration | N/A | Ce module ne lit pas `configs/default.yaml`. |
| Registres | N/A | |
| Structures de données partagées | ✅ | `PAGE_DEFINITIONS: list[dict[str, str]]` — structure cohérente, consommé par `st.Page`. |
| Imports croisés | ✅ | `from scripts.dashboard.data_loader import discover_runs` — existe sur `Max6000i1`. |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Séparation des responsabilités | ✅ | `app.py` = configuration + routing uniquement. Data loading délégué à `data_loader.py`. |
| Autres critères métier finance | N/A | Module dashboard UI, pas de calculs financiers. |

---

## Remarques

1. **[WARNING]** Fonction `main()` non testée — critères d'acceptation partiellement non vérifiés par test.
   - Fichier : `tests/test_app_entry.py`
   - Description : Les critères #1 (`st.set_page_config`) et #6 (`discover_runs` + `session_state`) sont cochés `[x]` dans la tâche mais aucun test ne les vérifie. La fonction `main()` (L113-140 de `app.py`) n'a aucun test unitaire. La vérification n'est possible que par lecture du code.
   - Suggestion : Ajouter au moins un test de `main()` avec mock de `streamlit` vérifiant : (a) `st.set_page_config` appelé avec les bons paramètres, (b) `discover_runs` appelé, (c) résultat stocké dans `st.session_state`. Exemple minimal :
     ```python
     def test_main_calls_set_page_config(tmp_path, monkeypatch):
         # mock streamlit, discover_runs, sys.argv, etc.
         ...
     ```

2. **[MINEUR]** Checklist tâche : `[ ] Commit GREEN` non coché.
   - Fichier : `docs/tasks/MD-2/078__wsd2_app_entry_navigation.md`
   - Ligne(s) : 60
   - Description : Le commit GREEN `52bc9d5` existe mais l'item checklist reste `[ ]`.
   - Suggestion : Cocher `[x]`.

3. **[MINEUR]** `--runs-dir=` (chaîne vide) résout silencieusement vers `cwd()`.
   - Fichier : `scripts/dashboard/app.py`
   - Ligne(s) : 83
   - Description : `_parse_runs_dir_from_args(["--runs-dir="])` retourne `""`, puis `Path("").resolve()` donne le répertoire courant. Même comportement avec `AI_TRADING_RUNS_DIR=""`. Le cwd est silencieusement scanné. Aucun test ne couvre ce cas.
   - Suggestion : Soit ajouter une garde `if raw_path is not None and raw_path == "": raise ValueError(...)` après la cascade de résolution, soit documenter le comportement avec un test explicite.

---

## Résumé

```
RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 1
- Mineurs : 2
- Rapport : docs/tasks/MD-2/078/review_v1.md
```
