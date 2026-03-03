# Revue PR — [WS-12] #050 — CLI entry point (v3)

Branche : `task/050-cli-entry-point`
Tâche : `docs/tasks/M5/050__ws12_cli_entry_point.md`
Date : 2026-03-03
Itération : v3 (suite corrections du rapport v2)

## Verdict global : ✅ CLEAN

## Résumé

L'unique item de la revue v2 (MINEUR — pattern `overrides or None` §R1 à la ligne 166) a été corrigé dans le commit `7f737bf` — le fallback a été supprimé, `overrides` est désormais passé directement. La suite de tests est verte (1456 passed), ruff est clean, et aucun nouvel item n'est identifié. Verdict CLEAN.

---

## Suivi des items v2

| # | Sévérité v2 | Description | Statut v3 | Preuve |
|---|---|---|---|---|
| 3 | MINEUR | Pattern `overrides or None` (§R1, L166) | ✅ CORRIGÉ | Commit `7f737bf` : `overrides=overrides or None` → `overrides=overrides`. Vérifié `ai_trading/__main__.py` L163–167 : `overrides=overrides,` (liste passée directement). |

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
| Commits FIX post-GREEN | ✅ | `506323e` — corrections suite revue v1 (tests verts). `7f737bf` — correction suite revue v2 (suppression `or None`). Tous post-revue, tests verts, acceptables. |

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
| `run --config` lance le pipeline | `TestMainRun.test_run_calls_pipeline` (L240–254) — mock `run_pipeline` appelé |
| `fetch --config` lance l'ingestion | `TestMainFetch.test_fetch_calls_ingestion` (L275–289) — mock `fetch_ohlcv` appelé |
| `qa --config` lance le QA | `TestMainQA.test_qa_calls_qa_command` (L300–315) — mock `_run_qa_command` appelé |
| `--set strategy.name=dummy` surcharge config | `TestMainRun.test_run_passes_overrides` (L256–272) — vérifie `"strategy.name=dummy" in overrides` |
| `--strategy dummy` raccourci | `TestStrategyShortcut.test_strategy_shortcut_applies` (L467–484) + `TestBuildOverrides.test_strategy_shortcut_produces_override` (L143–149) |
| Erreur si `--config` inexistant | `TestErrorHandling.test_missing_config_file_raises` (L393–400) — `FileNotFoundError` levée |
| Logging phase 1 configuré | `TestLoggingSetup.test_setup_logging_called_before_load_config` (L436–449) — `setup_logging("INFO", "text")` vérifié |
| Tests scénarios nominaux + erreurs + bords | 11 classes, 33 tests |
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

| Pattern recherché | Commande grep_search | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux (`or []`, `or {}`, `or ""`, `if…else`) | `ai_trading/__main__.py` | 0 occurrences ✅ |
| §R1 Except trop large | `ai_trading/__main__.py` | 0 occurrences ✅ |
| §R7 noqa | `ai_trading/__main__.py` + `tests/test_cli.py` | 0 occurrences ✅ |
| §R7 per-file-ignores pyproject.toml | `git diff` pyproject.toml | Pas de modification dans cette PR ✅ |
| §R7 Print résiduel | `ai_trading/__main__.py` | 0 occurrences ✅ |
| §R3 Shift négatif (`.shift(-`) | `ai_trading/__main__.py` | 0 occurrences ✅ |
| §R4 Legacy random API | `ai_trading/__main__.py` + `tests/test_cli.py` | 0 occurrences ✅ |
| §R7 TODO/FIXME/HACK/XXX | `ai_trading/__main__.py` + `tests/test_cli.py` | 0 occurrences ✅ |
| §R7 Chemins hardcodés tests (`/tmp`) | `tests/test_cli.py` | 10 matches — **faux positif** : valeurs string pour tester `--output-dir` en argument parsing, aucune I/O disque (ex : L52 `parse_args(["run", "--output-dir", "/tmp/out"])` compare un string, pas un path) |
| §R7 Imports absolus `__init__.py` | N/A | Aucun `__init__.py` modifié dans cette PR |
| §R7 Registration manuelle tests | `tests/test_cli.py` | 0 occurrences ✅ |
| §R6 Mutable default arguments | `ai_trading/__main__.py` + `tests/test_cli.py` | 0 occurrences ✅ |
| §R6 open() sans context manager | `ai_trading/__main__.py` | 0 occurrences ✅ |
| §R6 Bool identité (`is True`, `is False`) | `ai_trading/__main__.py` : 0, `tests/test_cli.py` : 1 match L365 `report.passed is True` — **faux positif** : `report` est un `MagicMock` Python, pas numpy/pandas |
| §R6 Dict collision en boucle | `ai_trading/__main__.py` | 0 occurrences ✅ |
| §R9 Boucle Python sur array numpy | `ai_trading/__main__.py` | 0 occurrences ✅ |
| §R6 isfinite check | `ai_trading/__main__.py` | 0 occurrences (N/A — pas de paramètres float à valider) |
| §R9 Appels numpy compréhension | `ai_trading/__main__.py` | 0 occurrences ✅ |
| §R7 Fixtures dupliquées (`load_config.*configs/`) | `tests/test_cli.py` | 0 occurrences ✅ |

### Annotations par fichier (B2)

#### `ai_trading/__main__.py` (182 lignes)

Diff complet lu (181 lignes de diff). Observations :

- **L33–57** `_add_common_arguments()` : helper DRY pour partager les arguments entre parser principal et subparsers. Valeurs par défaut explicites (`default=None` pour optionnels, `"configs/default.yaml"` pour `--config`). RAS.

- **L60–91** `build_parser()` : pattern correct avec `_add_common_arguments(parser)` sur le parser principal (L68) + `parents=[common]` sur les sous-parsers. `parser.set_defaults(command="run")` (L76) assure le défaut "run" sans sous-commande. RAS.

- **L100–112** `_build_overrides()` : merge les raccourcis `--strategy`/`--output-dir` et les `--set` en une unique `list[str]`. Tests `is not None` explicites (pas de fallback silencieux). Retour `list[str]` (vide ou peuplée). RAS.

- **L118–140** `_run_qa_command()` : type de retour `-> QAReport` correct. Lazy import `pandas` dans le corps — acceptable pour un CLI. Vérifie l'existence du parquet avant lecture (`is_file()` + `FileNotFoundError`). Accès `config.dataset.symbols[0]` : la config Pydantic valide `symbols: list[str]` (non-vide en pratique via default.yaml). RAS.

- **L148–177** `main()` :
  - L149 : `setup_logging("INFO", "text")` — phase 1 conforme à §16.2/§17.7 spec. Paramètres hardcodés acceptables (config non encore chargée).
  - L155–157 : validation anticipée du fichier config (`is_file()` + `FileNotFoundError`). Double validation avec `load_config` (qui fait le même check) — sans risque, message CLI plus explicite.
  - **L163–167** : `overrides=overrides` — correction v2 validée. La liste est passée directement, `[]` ou `["strategy.name=dummy"]`. Pas de fallback. ✅
  - L168–177 : dispatch `if/elif` sur `command ∈ {run, fetch, qa}`. Argparse garantit que `command` est l'une de ces valeurs ou `"run"` (défaut). Pas de branche `else` nécessaire.
  - L180–181 : `if __name__ == "__main__": main()` — guard standard présent.

RAS après lecture complète du diff (182 lignes).

#### `tests/test_cli.py` (544 lignes)

Diff complet lu (544 lignes — fichier entièrement nouveau). Observations :

- **L1–3** : docstring avec `Task #050 — WS-12`. Convention nommage OK (`test_cli.py`).
- **L21–73** `TestBuildParser` : 7 tests couvrant construction parser, arguments par défaut, config custom, strategy, output-dir, set single/multiple. RAS.
- **L82–133** `TestSubcommands` : 7 tests incluant les 3 ajoutés en FIX v1 (default subcommand sans sous-commande + args communs). RAS.
- **L142–197** `TestBuildOverrides` : 5 tests unitaires (strategy, output-dir, set, combinaison complète, aucun override → `[]`). RAS.
- **L205–272** `TestMainRun` : 3 tests d'intégration via mocks (sans sous-commande, avec sous-commande run, avec overrides). RAS.
- **L281–289** `TestMainFetch` : 1 test d'intégration via mock `fetch_ohlcv`. RAS.
- **L298–315** `TestMainQA` : 1 test d'intégration via mock `_run_qa_command`. RAS.
- **L321–385** `TestRunQACommand` : 2 tests unitaires (`test_nominal_runs_qa_checks` avec vrai parquet dans `tmp_path` + mock `run_qa_checks`, `test_missing_parquet_raises`). RAS.
- **L393–428** `TestErrorHandling` : config absente (`FileNotFoundError`), clé invalide (`KeyError`). RAS.
- **L436–449** `TestLoggingSetup` : vérifie `setup_logging("INFO", "text")` appelé en premier. RAS.
- **L458–484** `TestStrategyShortcut` : intégration complète du raccourci `--strategy`. RAS.
- **L493–544** `TestModuleInvocation` : 5 tests subprocess (`--help` global, subcommands visibles, `run --help`, `fetch --help`, `qa --help`). RAS.
- Aucun `@pytest.mark.skip` ou `xfail`. Tous les tests utilisent `tmp_path` pour les fichiers temporaires et des mocks pour les dépendances externes. Pas de dépendance réseau.

RAS après lecture complète (544 lignes).

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères d'acceptation | ✅ | 11/11 critères mappés (voir tableau Phase A ci-dessus) |
| Cas nominaux + erreurs + bords | ✅ | 11 classes, 33 tests : nominaux (run/fetch/qa + parsing), erreurs (config absente, clé invalide, parquet absent), bords (aucun override, default subcommand, tous args combinés) |
| Boundary fuzzing | ✅ (N/A) | Pas de paramètres numériques d'entrée dans ce module CLI |
| Déterministes | ✅ | Pas d'aléatoire dans les tests — résultats identiques à chaque exécution |
| Données synthétiques | ✅ | Mocks + parquet créé dans `tmp_path` ; subprocess `--help` seul (pas de réseau) |
| Portabilité chemins | ✅ | Scan B1 : `/tmp` matches sont des strings d'argument parsing (faux positif), tous les fichiers temporaires utilisent `tmp_path` |
| Tests registre réalistes | N/A | Pas de registre impliqué |
| Contrat ABC complet | N/A | Pas d'ABC dans ce module |
| Pas de skip/xfail | ✅ | Scan : 0 occurrences |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback. Lecture B2 : `_build_overrides` utilise `is not None` explicite ; `main()` lève `FileNotFoundError` (L156) ; pas de `except` |
| §R10 Defensive indexing | ✅ | Pas d'indexation sur array/série. `symbols[0]` protégé par validation Pydantic amont |
| §R2 Config-driven | ✅ | Paramètres pipeline lus depuis config. Seuls hardcodés : `"INFO"`/`"text"` (phase 1 logging, config pas encore chargée) et `"configs/default.yaml"` (défaut CLI) — acceptables |
| §R3 Anti-fuite | ✅ (N/A) | Module CLI, pas de traitement de données temporelles |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random |
| §R5 Float conventions | ✅ (N/A) | Pas de calcul numérique dans ce module |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable default, 0 `open()` sans context manager, 0 bool par identité numpy. `is True` L365 sur MagicMock = faux positif |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `_add_common_arguments`, `build_parser`, `_build_overrides`, `_run_qa_command`, `main` |
| Pas de code mort/debug | ✅ | Scan B1 : 0 `print()`, 0 TODO/FIXME |
| Imports propres | ✅ | stdlib (`argparse`, `logging`, `pathlib`) → local (`ai_trading.*`). Pas d'imports inutilisés (ruff clean) |
| DRY | ✅ | `_add_common_arguments` factorise les arguments communs |
| Pas de fichiers générés dans PR | ✅ | 3 fichiers modifiés uniquement (source, test, tâche) |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Commentaire |
|---|---|---|
| Spécification §17.5 | ✅ | CLI conforme : `python -m ai_trading {run,fetch,qa} --config $(CONFIG)` (spec L1125–1131). Surcharges CLI (`--set`, `--strategy`) conformes à §17.5 L1201 |
| Plan WS-12.3 | ✅ | CLI entry point implémenté dans `__main__.py` avec argparse |
| Formules doc vs code | ✅ (N/A) | Pas de formules mathématiques dans ce module |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| `run_pipeline(config)` → `Path` | ✅ | Signature `runner.py` L167 : `def run_pipeline(config: PipelineConfig) -> Path` — appel conforme L170 |
| `fetch_ohlcv(config)` → `IngestionResult` | ✅ | Signature `ingestion.py` L274 : `def fetch_ohlcv(config: PipelineConfig) -> IngestionResult` — appel conforme L173 ; `.path` et `.row_count` utilisés dans le log |
| `run_qa_checks(df, timeframe, zero_volume_min_streak)` → `QAReport` | ✅ | Signature `qa.py` L197 : 3 kwargs positionnels — appel conforme L135–138 |
| `load_config(yaml_path, overrides)` | ✅ | Signature `config.py` L492 : `yaml_path: str, overrides: list[str] \| None = None` — appel conforme L163–166. `overrides` est `list[str]` (jamais `None` grâce à `_build_overrides()`) |
| `setup_logging(level, fmt)` | ✅ | Signature `logging.py` L62 : `def setup_logging(level: str, fmt: str) -> None` — appel conforme L149 |
| Imports croisés | ✅ | Tous les symboles importés (`PipelineConfig`, `load_config`, `fetch_ohlcv`, `QAReport`, `run_qa_checks`, `run_pipeline`, `setup_logging`) existent dans `Max6000i1` |

---

## Remarques

Aucun item identifié. Tous les items des revues précédentes (v1 et v2) ont été corrigés et vérifiés.

---

## Résumé

Le code est propre, conforme à la spec et au plan, sans fallback silencieux ni anti-pattern. Les 33 tests couvrent les critères d'acceptation, les erreurs et les bords. La cohérence intermodule est vérifiée pour les 5 fonctions appelées. Verdict CLEAN.
