# Revue PR — [WS-12] #050 — CLI entry point (v2)

Branche : `task/050-cli-entry-point`
Tâche : `docs/tasks/M5/050__ws12_cli_entry_point.md`
Date : 2026-03-03
Itération : v2 (suite corrections du rapport v1)

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Toutes les corrections demandées dans la revue v1 ont été traitées : le BLOQUANT (sous-commande par défaut cassée) est corrigé, le WARNING (`_run_qa_command` non testé) est résolu avec 2 tests unitaires, et les MINEURs (annotation de type, checklist tâche) sont corrigés. Seul le pattern `overrides or None` (§R1) persiste à la ligne 166 — le ternaire a été simplifié mais le fallback silencieux reste. Un MINEUR empêche le verdict CLEAN.

---

## Suivi des items v1

| # | Sévérité v1 | Description | Statut v2 | Preuve |
|---|---|---|---|---|
| 1 | BLOQUANT | Sous-commande par défaut cassée | ✅ CORRIGÉ | `_add_common_arguments(parser)` ajouté au parser principal + `parser.set_defaults(command="run")` (L67–73). Tests ajoutés : `test_default_subcommand_has_config`, `test_default_subcommand_accepts_config`, `test_default_subcommand_accepts_all_common_args`, `test_run_no_subcommand_calls_pipeline`. |
| 2 | WARNING | `_run_qa_command` non testé unitairement | ✅ CORRIGÉ | Classe `TestRunQACommand` ajoutée (L321–385) : `test_nominal_runs_qa_checks` + `test_missing_parquet_raises`. |
| 3 | MINEUR | Pattern fallback `overrides if overrides else None` (§R1) | ⚠️ PARTIEL | Ternaire simplifié en `overrides or None` (L166) — même sémantique, le fallback silencieux `[] → None` persiste. `load_config` accepte `[]` identiquement à `None` (L524 : `if overrides:`), donc le `or None` est superflue. |
| 4 | MINEUR | Annotation `-> None` vs `-> QAReport` | ✅ CORRIGÉ | L118 : `-> QAReport`, import `QAReport` ajouté L21. |
| 5 | MINEUR | Checklist tâche non entièrement cochée | ✅ CORRIGÉ | Tous items cochés `[x]` (9/9). |

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/050-cli-entry-point` | ✅ | `git branch --show-current` → `task/050-cli-entry-point` |
| Commit RED présent | ✅ | `2f161fe` — `[WS-12] #050 RED: tests CLI entry point` |
| Commit GREEN présent | ✅ | `6621708` — `[WS-12] #050 GREEN: CLI entry point` |
| RED contient uniquement des tests | ✅ | `git show --stat 2f161fe` → `tests/test_cli.py` seul (429 insertions) |
| GREEN contient implémentation + tâche | ✅ | `git show --stat 6621708` → `ai_trading/__main__.py`, `tests/test_cli.py`, `docs/tasks/M5/050__ws12_cli_entry_point.md` |
| Commit FIX post-GREEN | ✅ | `506323e` — `[WS-12] #050 FIX: default subcommand with common args, QA unit tests, type annotation, fallback cleanup` — correction suite à revue v1, tests verts, acceptable. |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (11/11) |
| Checklist cochée | ✅ (9/9) |

#### Vérification critère par critère

| Critère d'acceptation | Preuve code/test |
|---|---|
| `--help` affiche aide générale | `TestModuleInvocation.test_help_exits_zero` + `test_help_shows_subcommands` (L499–523) |
| `run --config` lance le pipeline | `TestMainRun.test_run_calls_pipeline` (L240–254) |
| `fetch --config` lance l'ingestion | `TestMainFetch.test_fetch_calls_ingestion` (L275–289) |
| `qa --config` lance le QA | `TestMainQA.test_qa_calls_qa_command` (L300–315) |
| `--set strategy.name=dummy` surcharge config | `TestMainRun.test_run_passes_overrides` (L256–272) |
| `--strategy dummy` raccourci | `TestStrategyShortcut.test_strategy_shortcut_applies` (L467–484) + `TestBuildOverrides.test_strategy_shortcut_produces_override` (L143–149) |
| Erreur si `--config` inexistant | `TestErrorHandling.test_missing_config_file_raises` (L393–400) |
| Logging phase 1 configuré | `TestLoggingSetup.test_setup_logging_called_before_load_config` (L428–449) |
| Tests scénarios nominaux + erreurs + bords | 11 classes de tests, 33 tests au total |
| Suite de tests verte | 1456 passed, 0 failed |
| `ruff check` passe | All checks passed |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1456 passed**, 0 failed ✅ |
| `ruff check ai_trading/ tests/` | **All checks passed** ✅ |

**Phase A : PASS** — Poursuite en Phase B.

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux | `grep -n 'or \[\]\|or {}\|or ""\|or 0\|if .* else ' ai_trading/__main__.py` | 0 occurrences ✅ (le pattern `or None` n'est pas capturé par ce grep mais identifié manuellement L166) |
| §R1 Except trop large | `grep -n 'except:$\|except Exception:' ai_trading/__main__.py` | 0 occurrences ✅ |
| §R7 noqa | `grep -rn 'noqa' ai_trading/__main__.py tests/test_cli.py` | 0 occurrences ✅ |
| §R7 per-file-ignores | `grep pyproject.toml` | Préexistant L51-56, aucun ajout pour cette PR ✅ |
| §R7 Print résiduel | `grep -n 'print(' ai_trading/__main__.py` | 0 occurrences ✅ |
| §R3 Shift négatif | `grep -n '.shift(-' ai_trading/__main__.py` | 0 occurrences ✅ |
| §R4 Legacy random | `grep -rn 'np.random.seed\|np.random.randn\|random.seed' ai_trading/__main__.py tests/test_cli.py` | 0 occurrences ✅ |
| §R7 TODO/FIXME | `grep -rn 'TODO\|FIXME\|HACK\|XXX' ai_trading/__main__.py tests/test_cli.py` | 0 occurrences ✅ |
| §R7 Chemins hardcodés tests | `grep -n '/tmp' tests/test_cli.py` | 8 matches — **faux positif** : valeurs string pour tester `--output-dir` en argument parsing, pas d'I/O disque |
| §R7 Imports absolus __init__ | `grep -n 'from ai_trading\.' ai_trading/__init__.py` | 0 occurrences ✅ (aucun `__init__.py` modifié) |
| §R7 Registration manuelle tests | `grep -rn 'register_model\|register_feature' tests/test_cli.py` | 0 occurrences ✅ |
| §R6 Mutable defaults | `grep -rn 'def .*=\[\]\|def .*={}' ai_trading/__main__.py tests/test_cli.py` | 0 occurrences ✅ |
| §R6 open() sans context manager | `grep -n '.read_text\|open(' ai_trading/__main__.py` | 0 occurrences ✅ |
| §R6 Bool identité | `grep -rn 'is np.bool_\|is True\|is False' ai_trading/__main__.py tests/test_cli.py` | 1 match L365 : `report.passed is True` — **faux positif** : `report` est un `MagicMock` Python, pas numpy/pandas |
| §R6 Dict collision | `grep -rn '\[.*\] = ' ai_trading/__main__.py` | 1 match L103 `overrides: list[str] = []` — **faux positif** : déclaration typée, pas assignation en boucle |
| §R9 Boucle Python numpy | `grep -n 'for.*in range' ai_trading/__main__.py` | 0 occurrences ✅ |
| §R6 isfinite | `grep -n 'isfinite' ai_trading/__main__.py` | 0 occurrences (N/A — pas de paramètres float) |
| §R9 numpy compréhension | `grep -n 'np.[a-z]*(.*for' ai_trading/__main__.py` | 0 occurrences ✅ |
| §R7 Fixtures dupliquées | `grep -n 'load_config.*configs/' tests/test_cli.py` | 0 occurrences ✅ |
| `or None` (§R1 variant) | `grep -rn 'or None' ai_trading/__main__.py` | 1 match L166 : `overrides=overrides or None` → **MINEUR** |

### Annotations par fichier (B2)

#### `ai_trading/__main__.py` (181 lignes)

Diff complet lu ligne par ligne (181 lignes). Observations :

- **L33–57** `_add_common_arguments()` : fonction helper extraite pour partager les arguments entre le parser principal et les sous-parsers. Pattern DRY correct. Tous les arguments ont des valeurs par défaut explicites (`default=None` ou `default="configs/default.yaml"`). RAS.

- **L60–91** `build_parser()` : parser principal avec `_add_common_arguments(parser)` (L68) + parent `common` pour les sous-parsers. `parser.set_defaults(command="run")` (L76) — correction v1 validée, les arguments communs sont désormais disponibles sans sous-commande. RAS.

- **L100–112** `_build_overrides()` : merge les raccourcis `--strategy`/`--output-dir` et les `--set`. Tests explicites `is not None`. Retourne une `list[str]`. RAS.

- **L118–140** `_run_qa_command()` : annotation `-> QAReport` correcte (fix v4). `config.dataset.symbols[0]` : safe car `PipelineConfig` valide via Pydantic que `symbols` a au moins un élément. Lazy import `pandas` dans le corps — pattern acceptable pour un CLI. Vérifie l'existence du parquet avant lecture (`is_file()` + `FileNotFoundError`). RAS.

- **L148–177** `main()` :
  - L149 : `setup_logging("INFO", "text")` — phase 1 conforme (§16.2 spec). Paramètres hardcodés acceptables car la config n'est pas encore chargée.
  - L155–157 : validation anticipée du fichier config avec `FileNotFoundError` explicite. Note : `load_config` (L517) fait la même vérification — double validation mais pas de bug, et le message CLI est plus direct.
  - **L166** : `overrides=overrides or None` — **MINEUR §R1**. `_build_overrides` retourne `[]` quand aucun override n'est fourni. `load_config` gère `[]` identiquement à `None` (L524 : `if overrides:` évalue les deux à `False`). Le `or None` est superflue et constitue un fallback silencieux. **Suggestion** : remplacer par `overrides=overrides` (passer la liste directement).
  - L168–177 : dispatch par `if/elif` sur `command`. Argparse garantit que `command ∈ {run, fetch, qa}` ou `"run"` par défaut. Pas de branche `else` nécessaire.

#### `tests/test_cli.py` (544 lignes)

Diff complet lu ligne par ligne (544 lignes). Observations :

- **L1–3** : docstring avec `Task #050 — WS-12`. Convention nommage OK (`test_cli.py`). ✅

- **L21–73** `TestBuildParser` : 7 tests couvrant parser construction, arguments par défaut, overrides. RAS.

- **L82–133** `TestSubcommands` : 7 tests incluant les 3 nouveaux tests ajoutés en FIX (`test_default_subcommand_has_config`, `test_default_subcommand_accepts_config`, `test_default_subcommand_accepts_all_common_args`). Correction v1 validée. RAS.

- **L142–197** `TestBuildOverrides` : 5 tests unitaires pour `_build_overrides`. Couvre strategy, output-dir, set, combinaison, aucun override → `[]`. RAS.

- **L205–272** `TestMainRun` : 3 tests dont `test_run_no_subcommand_calls_pipeline` (nouveau, correction v1). Mocks appropriés (`run_pipeline`, `load_config`, `setup_logging`). Vérification des appels. RAS.

- **L281–289** `TestMainFetch` : 1 test d'intégration. RAS.

- **L298–315** `TestMainQA` : 1 test d'intégration. RAS.

- **L321–385** `TestRunQACommand` : 2 tests unitaires (nouveau, correction v1). `test_nominal_runs_qa_checks` crée un vrai parquet dans `tmp_path`, mocke `run_qa_checks`, vérifie les kwargs transmis. `test_missing_parquet_raises` vérifie le `FileNotFoundError`. RAS.

- **L365** `assert report.passed is True` : `report` est un `MagicMock` Python (`.passed = True`), pas numpy/pandas → `is True` est correct et idiomatique ici. Faux positif.

- **L393–428** `TestErrorHandling` : config absente + clé invalide. RAS.

- **L436–449** `TestLoggingSetup` : vérifie que `setup_logging` est appelé avec `"INFO"`, `"text"`. RAS.

- **L458–484** `TestStrategyShortcut` : vérifie le raccourci `--strategy`. RAS.

- **L493–544** `TestModuleInvocation` : 5 tests subprocess vérifiant `--help` pour chaque sous-commande. `timeout=10` approprié. RAS.

#### `docs/tasks/M5/050__ws12_cli_entry_point.md`

- Statut DONE, tous critères `[x]`, checklist `[x]`. RAS.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_cli.py`, `#050` dans la docstring (L1–3) |
| Couverture des critères d'acceptation | ✅ | 11/11 critères mappés à des tests (voir tableau Phase A) |
| Cas nominaux + erreurs + bords | ✅ | Nominal (run/fetch/qa + sans sous-commande), erreurs (config absente, clé invalide, parquet absent), bords (aucun override → `[]`, multiple `--set`) |
| Boundary fuzzing | N/A | Pas de paramètres numériques dans le CLI |
| Boundary fuzzing taux/proportions | N/A | Pas de taux/proportions |
| Déterministes | ✅ | Pas d'aléatoire (mocks uniquement) |
| Portabilité chemins | ✅ | `/tmp/out` = string pour argparse (faux positif), `tmp_path` utilisé pour I/O réel |
| Tests registre réalistes | N/A | Pas de registre |
| Contrat ABC complet | N/A | Pas d'ABC |
| Tests désactivés | ✅ | 0 `skip`/`xfail` |
| Données synthétiques | ✅ | Mocks + `tmp_path`, pas de dépendance réseau |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ⚠️ | L166 : `overrides or None` — MINEUR (fallback superflue, fonctionnellement neutre). Scan B1 : 0 match pour les autres patterns §R1. |
| §R10 Defensive indexing | ✅ | Pas de slicing/indexing numpy/pandas dans le CLI |
| §R2 Config-driven | ✅ | Config via `load_config()`, `setup_logging("INFO", "text")` justifié (phase 1, config non disponible) |
| §R3 Anti-fuite | ✅ | N/A (pas de données temporelles). Scan B1 : 0 `.shift(-` |
| §R4 Reproductibilité | ✅ | N/A. Scan B1 : 0 legacy random |
| §R5 Float conventions | ✅ | N/A (pas de tenseurs/métriques) |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 `open()` sans context manager, 0 comparaison booléenne numpy. `is True` L365 = faux positif (MagicMock). |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Toutes fonctions/variables en snake_case |
| Pas de code mort/debug | ✅ | Scan B1 : 0 `print()`, 0 `TODO`/`FIXME` |
| Imports propres / relatifs | ✅ | Imports ordonnés stdlib → third-party → local. Pas d'imports inutilisés. `PipelineConfig` utilisé en annotation L118. `QAReport` utilisé en annotation L118. |
| DRY | ✅ | `_add_common_arguments` factorise les arguments CLI. Pas de duplication entre modules. |
| .gitignore | ✅ | Pas de fichiers générés dans la PR |
| noqa | ✅ | 0 suppression lint (scan B1) |

### Conformité spec v1.0 (B6)

| Critère | Verdict |
|---|---|
| §16.2 Journalisation minimale | ✅ — `setup_logging("INFO", "text")` conforme phase 1 |
| §17.5 Gestion de la configuration | ✅ — `load_config` avec overrides CLI conforme |
| Plan WS-12.3 | ✅ — `python -m ai_trading --config configs/default.yaml` fonctionne (corrigé v1) |
| Formules doc vs code | N/A — pas de formule mathématique |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `run_pipeline(config: PipelineConfig) -> Path` (runner.py L167), `fetch_ohlcv(config: PipelineConfig) -> IngestionResult` (ingestion.py L274), `load_config(yaml_path: str, overrides: list[str] \| None) -> PipelineConfig` (config.py L492), `setup_logging(level: str, fmt: str) -> None` (logging.py L62) — tous conformes aux appels dans `__main__.py` |
| Noms de colonnes DataFrame | N/A | Pas de manipulation directe de DataFrame dans le CLI (`_run_qa_command` délègue à `run_qa_checks`) |
| Clés de configuration | ✅ | `config.dataset.symbols`, `config.dataset.timeframe`, `config.dataset.raw_dir`, `config.qa.zero_volume_min_streak` — vérifiées dans le modèle Pydantic |
| Registres et conventions | N/A | Pas de registre utilisé |
| Structures de données partagées | ✅ | `QAReport` importé de `ai_trading.data.qa`, `IngestionResult.path`/`.row_count` conforme à ingestion.py |
| Conventions numériques | N/A | Pas de calcul numérique |
| Imports croisés | ✅ | Tous les symboles importés existent dans la branche (`PipelineConfig`, `load_config`, `fetch_ohlcv`, `QAReport`, `run_qa_checks`, `run_pipeline`, `setup_logging`) |
| Forwarding kwargs | ✅ | `run_pipeline(config)`, `fetch_ohlcv(config)`, `load_config(yaml_path=, overrides=)` — tous les paramètres pertinents sont transmis |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | N/A | CLI pur, pas de calcul financier |
| Nommage métier cohérent | ✅ | `fetch_ohlcv`, `run_qa_checks`, `run_pipeline` — noms métier corrects |
| Séparation des responsabilités | ✅ | CLI = dispatch, logique déléguée aux modules métier |
| Invariants de domaine | N/A | |
| Cohérence des unités | N/A | |
| Patterns de calcul financier | N/A | |

---

## Remarques

1. **[MINEUR]** Pattern fallback §R1 persistant à la ligne 166.
   - Fichier : `ai_trading/__main__.py`
   - Ligne(s) : 166 (`overrides=overrides or None`)
   - Contexte : `_build_overrides()` retourne `[]` quand aucun override n'est fourni. `load_config()` (config.py L524) utilise `if overrides:` qui évalue `[]` et `None` identiquement. Le `or None` est donc une conversion silencieuse de `[]` vers `None` sans effet fonctionnel.
   - Suggestion : remplacer par `overrides=overrides` (passer la liste directement, sans conversion).

## Actions requises

1. **Fix MINEUR 1** : remplacer `overrides=overrides or None` par `overrides=overrides` à la ligne 166 de `ai_trading/__main__.py`.
