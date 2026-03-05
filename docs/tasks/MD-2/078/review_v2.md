# Revue PR — [WS-D-2] #078 — Point d'entrée Streamlit et navigation multi-pages (v2)

Branche : `task/078-wsd2-app-entry-navigation`
Tâche : `docs/tasks/MD-2/078__wsd2_app_entry_navigation.md`
Date : 2026-03-05
Itération : v2 (suite au FIX `fcb705c`)

## Verdict global : ✅ CLEAN

## Résumé

Seconde itération de revue. Les 3 items identifiés en v1 (1 WARNING + 2 MINEURS) ont tous été corrigés adéquatement dans le commit FIX `fcb705c`. La fonction `main()` est désormais testée via 3 tests avec mock Streamlit complet. La validation des chaînes vides (`--runs-dir=`, `AI_TRADING_RUNS_DIR=""`) lève explicitement `ValueError`. La checklist tâche est à jour. Aucun nouveau problème détecté.

---

## Vérification des corrections v1

| # | Sévérité v1 | Description | Correction | Verdict |
|---|---|---|---|---|
| 1 | WARNING | `main()` non testée — critères #1 et #6 non vérifiés par test | Ajout de `TestMain` (3 tests) : `test_set_page_config_called`, `test_discover_runs_stored_in_session_state`, `test_navigation_called_with_all_pages`. Mock complet de Streamlit + `discover_runs`. | ✅ Corrigé |
| 2 | MINEUR | Checklist `[ ] Commit GREEN` non coché | Changé en `[x]` dans le diff `52bc9d5..fcb705c` | ✅ Corrigé |
| 3 | MINEUR | `--runs-dir=` (chaîne vide) résout silencieusement vers `cwd()` | Ajout d'une garde `if not raw_path: raise ValueError(...)` à L79 de `app.py` + 2 tests (`test_empty_cli_arg_raises_value_error`, `test_empty_env_var_raises_value_error`) | ✅ Corrigé |

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
| Commit FIX post-review | ✅ | `fcb705c` — `[WS-D-2] #078 FIX: tests main() mockés, validation empty --runs-dir, checklist tâche` |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1..HEAD` → 3 commits exactement (RED + GREEN + FIX) |

### Tâche

| Critère | Verdict | Commentaire |
|---|---|---|
| Statut DONE | ✅ | Ligne 2 : `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (10/10) | Tous `[x]` |
| Checklist cochée | ✅ (9/10) | 9/10 cochés. Seul `[ ] Pull Request ouverte` reste (attendu — PR pas encore créée). |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/test_app_entry.py -v --tb=short` | **20 passed**, 0 failed |
| `pytest tests/ -v --tb=short` (suite complète) | **1999 passed**, 27 deselected, 0 failed |
| `ruff check scripts/dashboard/app.py tests/test_app_entry.py` | **All checks passed** |

✅ Phase A passe — suite en Phase B.

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| Fallbacks silencieux (`or []`, `or {}`, etc.) | `grep -rn 'or \[\]\|or {}\|or ""\|if .* else '` sur `scripts/dashboard/app.py` | 0 occurrences (grep exécuté) |
| Except trop large | `grep -rn 'except:$\|except Exception:'` sur `scripts/dashboard/app.py` | 0 occurrences (grep exécuté) |
| Print résiduel | `grep -rn 'print('` sur `scripts/dashboard/app.py` | 0 occurrences (grep exécuté) |
| Shift négatif (look-ahead) | `grep -rn '\.shift(-'` sur `scripts/dashboard/app.py` | 0 occurrences (grep exécuté) |
| Legacy random API | `grep -rn 'np\.random\.seed\|...'` sur SRC + TEST | 0 occurrences (grep exécuté) |
| TODO/FIXME orphelins | `grep -rn 'TODO\|FIXME\|HACK\|XXX'` sur SRC + TEST | 0 occurrences (grep exécuté) |
| Chemins hardcodés OS | `grep -rn '/tmp\|/var/tmp'` sur `tests/test_app_entry.py` | 0 occurrences (grep exécuté) |
| Suppressions lint (`noqa`) | `grep -rn 'noqa'` sur SRC + TEST | 0 occurrences (grep exécuté) |
| Imports absolus `__init__` | `grep -rn 'from ai_trading\.'` sur SRC + TEST | 0 occurrences (grep exécuté) |
| Registration manuelle tests | `grep -rn 'register_model\|register_feature'` sur TEST | 0 occurrences (grep exécuté) |
| Mutable defaults | `grep -rn 'def .*=\[\]\|def .*={}'` sur SRC + TEST | 0 occurrences (grep exécuté) |
| Comparaison booléenne par identité | `grep -rn 'is np\.bool_\|is True\|is False'` sur SRC + TEST | 0 occurrences (grep exécuté) |

### Annotations par fichier (B2)

#### `scripts/dashboard/app.py` (147 lignes — diff total vs Max6000i1)

Relecture complète du diff. Focus sur les corrections apportées par le FIX `fcb705c` :

- **L79-83** (NOUVEAU) `if not raw_path: raise ValueError(...)` : garde explicite rejetant les chaînes vides après la cascade de résolution. Couvre le cas `--runs-dir=` et `AI_TRADING_RUNS_DIR=""`. Le message d'erreur est descriptif et mentionne les 3 sources. ✅ Correction adéquate du MINEUR #3 v1.

- **L22-28** `PAGE_DEFINITIONS` : inchangées. Chemins absolus calculés à l'import via `_DASHBOARD_DIR`. Les 4 fichiers page existent. ✅

- **L37-40** `resolve_runs_dir(cli_args, env, default)` : signature stricte, 3 paramètres obligatoires. ✅

- **L72-78** Cascade de résolution CLI > env > default : logique inchangée, correcte. ✅

- **L85** `Path(raw_path).resolve()` : résolution sécurité §11.1. ✅

- **L88-94** Validation `FileNotFoundError` / `NotADirectoryError` : stricte, pas de fallback. ✅

- **L99-107** `_parse_runs_dir_from_args` : parsing `--runs-dir VALUE` et `--runs-dir=VALUE`. Guard `i + 1 < len(args)` correct. `split("=", 1)` correct. ✅

- **L115** `import streamlit as st` lazy dans `main()` : permet l'import de `resolve_runs_dir` sans Streamlit. ✅

- **L120** `st.set_page_config(layout="wide", page_title="AI Trading Dashboard")` : conforme §9.4. ✅

- **L123-126** Appel `resolve_runs_dir` avec `sys.argv[1:]`, `os.environ.get(...)`, `"runs/"`. ✅

- **L129-132** `if "runs" not in st.session_state` : chargement unique, pattern Streamlit correct. ✅

- **L135-139** Navigation multi-pages `st.Page` + `st.navigation` + `nav.run()`. ✅

- **L142** `if __name__ == "__main__": main()` : point d'entrée standard. ✅

RAS après lecture complète du diff (147 lignes).

#### `tests/test_app_entry.py` (356 lignes — diff total vs Max6000i1)

Relecture complète. Focus sur les ajouts FIX `fcb705c` :

- **L173-190** `test_empty_cli_arg_raises_value_error` / `test_empty_env_var_raises_value_error` (NOUVEAUX) : couvrent le cas `--runs-dir=` (chaîne vide) et `AI_TRADING_RUNS_DIR=""`. Vérifient `ValueError` avec match `"empty"`. ✅ Correction adéquate du MINEUR #3 v1.

- **L228-244** `_FakeSessionState` : helper pour mocker `st.session_state` avec accès par attribut. `dict` subclass, `__getattr__`/`__setattr__` corrects. Raises `AttributeError` on missing key. ✅

- **L249-280** `test_set_page_config_called` : mock complet de `streamlit` via `monkeypatch.setitem(sys.modules, ...)`. Vérifie `st.set_page_config.assert_called_once_with(layout="wide", page_title="AI Trading Dashboard")`. ✅ Correction adéquate du WARNING #1 v1 — critère d'acceptation #1 désormais couvert.

- **L282-316** `test_discover_runs_stored_in_session_state` : vérifie que `discover_runs` est appelé avec le bon `runs_dir` et que `session_state["runs"]` et `session_state["runs_dir"]` sont correctement remplis. ✅ Correction adéquate du WARNING #1 v1 — critère d'acceptation #6 désormais couvert.

- **L318-356** `test_navigation_called_with_all_pages` : vérifie que `st.Page` est appelé 4× avec les bons args, `st.navigation` est appelé avec la liste de pages, et `nav.run()` est exécuté. ✅ Couverture complète de la logique de navigation.

- **L14** `import sys` (NOUVEAU) : nécessaire pour `monkeypatch.setitem(sys.modules, ...)` dans `TestMain`. ✅

- Les 15 tests existants (v1) sont inchangés. Tous les `tmp_path` pour portabilité. ✅

RAS après lecture complète du diff (356 lignes).

#### `docs/tasks/MD-2/078__wsd2_app_entry_navigation.md`

- **L60** `[x] Commit GREEN` : corrigé (était `[ ]` en v1). ✅ Correction adéquate du MINEUR #2 v1.
- Dernier item `[ ] Pull Request ouverte` reste non coché — attendu (PR pas encore créée). ✅

RAS après lecture du fichier.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_app_entry.py`, `Task #078` dans docstring |
| Couverture des critères d'acceptation | ✅ | 10/10 couverts (voir mapping ci-dessous) |
| Cas nominaux + erreurs + bords | ✅ | 13 tests resolve (nominaux + erreurs + empty string + traversal + unknown args), 4 tests pages, 3 tests main |
| Boundary fuzzing | ✅ | N/A pour ce module (pas de paramètres numériques). Chaîne vide testée. |
| Déterministes | ✅ | Pas d'aléatoire |
| Données synthétiques | ✅ | `tmp_path` uniquement |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé |
| Tests registre | N/A | Pas de registre |
| Contrat ABC | N/A | Pas d'ABC |

**Mapping critères d'acceptation → tests :**

| # | Critère d'acceptation | Test(s) | Verdict |
|---|---|---|---|
| 1 | `st.set_page_config(layout="wide", page_title="AI Trading Dashboard")` | `TestMain::test_set_page_config_called` | ✅ |
| 2 | `--runs-dir` CLI fonctionnel | `test_cli_arg_takes_precedence_over_env`, `test_cli_arg_with_equals_syntax` | ✅ |
| 3 | `AI_TRADING_RUNS_DIR` env var | `test_env_var_takes_precedence_over_default`, `test_env_var_nonexistent_directory_errors` | ✅ |
| 4 | Précédence CLI > env > default | `test_cli_arg_takes_precedence_over_env`, `test_env_var_takes_precedence_over_default`, `test_default_when_no_cli_no_env` | ✅ |
| 5 | Erreur si répertoire inexistant | `test_error_if_directory_does_not_exist`, `test_env_var_nonexistent_*`, `test_default_nonexistent_*` | ✅ |
| 6 | `discover_runs()` + `st.session_state` | `TestMain::test_discover_runs_stored_in_session_state` | ✅ |
| 7 | 4 pages accessibles | `test_page_definitions_exist`, `test_page_definitions_order`, `test_page_files_exist`, `TestMain::test_navigation_called_with_all_pages` | ✅ |
| 8 | Tests nominaux + erreurs + bords | 20 tests couvrant les 3 catégories | ✅ |
| 9 | Suite verte | 20 passed, 0 failed | ✅ |
| 10 | ruff clean | All checks passed | ✅ |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback, 0 except large. `ValueError` sur chaîne vide, `FileNotFoundError`/`NotADirectoryError` sur chemin invalide. |
| §R10 Defensive indexing | ✅ | L101 `i + 1 < len(args)` prévient IndexError. L104 `split("=", 1)` correct. |
| §R2 Config-driven | ✅ | Défaut `"runs/"` conforme spec §5.1. Pas de hardcoding. |
| §R3 Anti-fuite | N/A | Module dashboard UI. |
| §R4 Reproductibilité | N/A | Pas d'aléatoire. Scan B1 : 0 legacy random. |
| §R5 Float conventions | N/A | Pas de calculs numériques. |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 bool identity. Pas de `open()` sans context manager. |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `resolve_runs_dir`, `_parse_runs_dir_from_args`, `PAGE_DEFINITIONS` (constante UPPER_CASE) |
| Pas de code mort/debug | ✅ | Scan B1 : 0 `print()`, 0 TODO/FIXME |
| Imports propres | ✅ | stdlib en top-level, Streamlit + data_loader en lazy import. Scan B1 : 0 `noqa`. |
| DRY | ✅ | Pas de duplication. |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Commentaire |
|---|---|---|
| §5.1 Sélection des runs | ✅ | `--runs-dir`, env var, défaut `runs/`. Précédence correcte. |
| §9.4 Responsivité | ✅ | `st.set_page_config(layout="wide")`. |
| §10.2 Structure du code | ✅ | `app.py` point d'entrée, 4 pages. |
| §10.3 Commande de lancement | ✅ | `sys.argv[1:]` compatible avec `streamlit run app.py -- --runs-dir`. |
| §11.1 Sécurité | ✅ | `Path.resolve()`. |
| Formules doc vs code | N/A | Pas de formules mathématiques. |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `discover_runs(runs_dir: Path)` — appelé avec `Path` résolu. |
| Clés de configuration | N/A | Ce module ne lit pas `configs/default.yaml`. |
| Structures de données partagées | ✅ | `PAGE_DEFINITIONS` consommé par `st.Page`. |
| Imports croisés | ✅ | `from scripts.dashboard.data_loader import discover_runs` — existe sur `Max6000i1`. |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Séparation des responsabilités | ✅ | `app.py` = configuration + routing uniquement. |
| Autres critères métier finance | N/A | Module dashboard UI. |

---

## Remarques

Aucune remarque. Les 3 items v1 ont été corrigés de manière adéquate et complète. Aucun nouveau problème identifié.

---

## Résumé

Les 3 corrections du commit FIX `fcb705c` sont adéquates : (1) `main()` est désormais testée avec 3 tests mockant Streamlit, couvrant `set_page_config`, `discover_runs` + `session_state`, et la navigation multi-pages ; (2) la checklist tâche est à jour ; (3) les chaînes vides sont explicitement rejetées avec `ValueError`. 20 tests passent, ruff clean, aucun nouveau problème détecté.

```
RÉSULTAT PARTIE B :
- Verdict : CLEAN
- Bloquants : 0
- Warnings : 0
- Mineurs : 0
- Rapport : docs/tasks/MD-2/078/review_v2.md
```
