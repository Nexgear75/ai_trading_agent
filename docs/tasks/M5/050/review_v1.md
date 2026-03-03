# Revue PR — [WS-12] #050 — CLI entry point

Branche : `task/050-cli-entry-point`
Tâche : `docs/tasks/M5/050__ws12_cli_entry_point.md`
Date : 2026-03-03

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Le CLI est globalement bien structuré (argparse, sous-commandes, overrides, logging phase 1). Cependant, le mécanisme de sous-commande par défaut (`subparsers.default = "run"`) est cassé : `python -m ai_trading --config configs/default.yaml` (critère d'acceptation du plan WS-12.3) échoue avec une erreur argparse. Deux items mineurs supplémentaires (annotation de type, pattern fallback §R1).

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
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1..HEAD` → 2 commits exactement (RED + GREEN) |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (11/11) |
| Checklist cochée | ⚠️ (8/10) — commit GREEN et PR non cochés (procéduraux, commit existe bien) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1450 passed**, 0 failed ✅ |
| `ruff check ai_trading/ tests/` | **All checks passed** ✅ |

**Phase A : PASS** — Poursuite en Phase B.

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux | `grep 'or []\|...\|if.*else' __main__.py` | **1 match** L158 `overrides if overrides else None` → MINEUR (voir remarque 3) |
| §R1 Except trop large | `grep 'except:$\|except Exception:' __main__.py` | 0 occurrences ✅ |
| §R7 noqa | `grep 'noqa' *.py` | 0 occurrences ✅ |
| §R7 per-file-ignores | `grep pyproject.toml` | L51 existe (préexistant) — N/A pour cette PR |
| §R7 Print résiduel | `grep 'print(' __main__.py` | 0 occurrences ✅ |
| §R3 Shift négatif | `grep '.shift(-' __main__.py` | 0 occurrences ✅ |
| §R4 Legacy random | `grep 'np.random.seed...' *.py` | 0 occurrences ✅ |
| §R7 TODO/FIXME | `grep 'TODO\|FIXME' *.py` | 0 occurrences ✅ |
| §R7 Chemins hardcodés tests | `grep '/tmp' test_cli.py` | **6 matches** — faux positif (valeurs de test pour argument parsing, pas d'I/O disque) |
| §R7 Imports absolus __init__ | N/A | Aucun `__init__.py` modifié |
| §R7 Registration manuelle tests | `grep 'register_model\|register_feature'` | 0 occurrences ✅ |
| §R6 Mutable defaults | `grep 'def.*=[]\|def.*={}'` | 0 occurrences ✅ |
| §R6 open() sans context manager | `grep '.read_text\|open(' __main__.py` | 0 occurrences ✅ |
| §R6 Comparaison bool identité | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences ✅ |
| §R6 Dict collision | `grep '\[.*\] = ' __main__.py` | 1 match L95 `overrides: list[str] = []` — faux positif (déclaration, pas assignation en boucle) |
| §R9 Boucle Python numpy | `grep 'for.*in range' __main__.py` | 0 occurrences ✅ |
| §R6 isfinite check | `grep 'isfinite' __main__.py` | 0 occurrences (N/A — pas de paramètres float numériques) |
| §R9 numpy vectorisation | `grep 'np\.[a-z]*(.*for' __main__.py` | 0 occurrences ✅ |
| §R7 Fixtures dupliquées | `grep 'load_config.*configs/' test_cli.py` | 0 occurrences ✅ |

### Annotations par fichier (B2)

#### `ai_trading/__main__.py` (173 lignes)

- **L69-70** `subparsers.default = "run"` : **BLOQUANT**. Ce mécanisme argparse fixe uniquement la valeur de `args.command` à `"run"` quand aucune sous-commande n'est fournie. Mais les arguments communs (`--config`, `--strategy`, etc.) — définis via le parent `common` sur les sous-parsers — ne sont **pas** peuplés. Conséquences :
  - `python -m ai_trading --config configs/default.yaml` → erreur argparse « invalid choice: 'configs/default.yaml' ».
  - `python -m ai_trading` (aucun arg) → `AttributeError: 'Namespace' object has no attribute 'config'` à L151.
  - Le plan WS-12.3 exige explicitement que `python -m ai_trading --config configs/default.yaml` lance un run complet.
  - **Preuve** : exécution interactive — `build_parser().parse_args([])` retourne `Namespace(command='run')` avec `hasattr(args, 'config') == False`.
  - **Suggestion** : ajouter les arguments communs au parser principal également (avec les mêmes defaults) ET/OU utiliser `parser.set_defaults(command="run")` combiné avec `subparsers.required = False` plus une vérification des attributs manquants.

- **L124** `def _run_qa_command(config: PipelineConfig) -> None:` + **L139** `return report` : **MINEUR**. L'annotation de retour dit `None` mais la fonction retourne `report` (un `QAReport`). La valeur n'est pas capturée à L169, donc fonctionnellement neutre, mais l'annotation est incorrecte.
  - **Suggestion** : changer en `-> QAReport` ou retirer le `return report`.

- **L157-158** `overrides=overrides if overrides else None` : **MINEUR** (§R1). Pattern ternaire de fallback. `load_config` accepte `list[str] | None` ; passer `[]` directement est équivalent à `None` (boucle vide). Le ternaire est superflue.
  - **Suggestion** : `overrides=overrides or None` est plus concis, mais mieux encore : passer `overrides` directement.

- **L126** `import pandas as pd` (lazy import inside function) : RAS — pattern acceptable pour éviter l'import coûteux au top-level dans un CLI. Pas de problème.

- **L20** `from ai_trading.config import PipelineConfig, load_config` : `PipelineConfig` est utilisé comme annotation de type à L124. OK, pas d'import inutilisé.

- **Reste du fichier** : RAS après lecture complète du diff (173 lignes). Structure claire, nommage snake_case, logique de dispatch propre.

#### `tests/test_cli.py` (432 lignes)

- **L100** `test_default_subcommand_is_run` : **WARNING**. Ce test vérifie `parser.parse_args([]).command == "run"`, ce qui passe effectivement. Mais il ne vérifie pas que `main()` fonctionne sans sous-commande explicite. La combinaison avec le bug L69-70 crée un faux sentiment de sécurité — le test passe mais l'usage réel crashe.
  - **Suggestion** : ajouter un test d'intégration `test_main_no_subcommand_uses_run` qui appelle `main()` sans sous-commande (avec `--config` via mock) et vérifie que `run_pipeline` est appelé.

- **Tests d'intégration `main()`** : Tous les tests de `TestMainRun`, `TestMainFetch`, `TestMainQA` mocquent `_run_qa_command`/`fetch_ohlcv`/`run_pipeline` à un niveau approprié. Les vérifications d'appel sont correctes. RAS.

- **`_run_qa_command` non testé unitairement** : **WARNING**. La fonction `_run_qa_command` contient de la logique métier (construction de chemin parquet, lecture DataFrame, appel `run_qa_checks` avec paramètres config). Elle est uniquement testée indirectement via `TestMainQA` qui la mocque entièrement. Un bug dans la construction du chemin ou l'accès à `config.dataset.symbols[0]` ne serait pas détecté.
  - **Suggestion** : ajouter au moins 2 tests unitaires pour `_run_qa_command` : (1) nominal avec fichier parquet mockté, (2) erreur fichier absent.

- **Cas de bords manquants** : le test `test_missing_config_file_raises` couvre le fichier config absent. `test_invalid_set_key_raises` couvre la clé invalide. Les sous-commandes et arguments sont bien couverts. RAS sur la couverture de bords pour le CLI pur.

- **Portabilité `/tmp`** : les occurrences `/tmp/out` (L52, L123, L127, L148) sont des valeurs string pour tester le parsing d'arguments, pas de l'I/O disque. **Faux positif** — pas de violation §R7.

- **Seeding** : N/A (pas de composant aléatoire dans le CLI).

- **Données synthétiques** : N/A (pas de dépendance réseau, tests par mocking).

- **Reste du fichier** : RAS après lecture complète (432 lignes). Bonne organisation par classe de test, docstrings présentes, fixtures `tmp_path` utilisées correctement.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_cli.py`, `#050` dans la docstring (L1-3) |
| Couverture des critères d'acceptation | ⚠️ | Tous couverts sauf le cas sans sous-commande (plan WS-12.3 : `python -m ai_trading --config`) |
| Cas nominaux + erreurs + bords | ✅ | Nominal (run/fetch/qa), erreurs (fichier absent, clé invalide), bords (set multiple, aucun override) |
| Boundary fuzzing | N/A | Pas de paramètres numériques dans le CLI |
| Déterministes | ✅ | Pas d'aléatoire (mocks) |
| Portabilité chemins | ✅ | `/tmp` = faux positif (parsing string), `tmp_path` utilisé pour l'I/O |
| Tests registre réalistes | N/A | Pas de registre |
| Contrat ABC complet | N/A | Pas d'ABC |
| Tests désactivés (skip/xfail) | ✅ | Aucun test désactivé |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ⚠️ | L158 : ternaire `overrides if overrides else None` — MINEUR (§R1 match, fonctionnellement neutre) |
| §R10 Defensive indexing | ✅ | Pas de slicing/indexing numpy/pandas dans le CLI |
| §R2 Config-driven | ✅ | Config passée via `load_config`, pas de valeur hardcodée |
| §R3 Anti-fuite | ✅ | N/A (pas de données temporelles) |
| §R4 Reproductibilité | ✅ | N/A + scan B1 : 0 legacy random |
| §R5 Float conventions | ✅ | N/A (pas de tenseurs/métriques) |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 open() sans context manager, 0 comparaison bool identité |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Toutes les fonctions/variables en snake_case |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print(), 0 TODO/FIXME |
| Imports propres / relatifs | ✅ | Imports ordonnés stdlib → third-party → local. Pas d'imports inutilisés |
| DRY | ✅ | Pas de duplication observée |
| .gitignore | ✅ | Préexistant, pas de fichiers générés dans la PR |

### Conformité spec v1.0 (B6)

| Critère | Verdict |
|---|---|
| §16.2 Journalisation minimale | ✅ — `setup_logging("INFO", "text")` conforme |
| §17.5 Gestion de la configuration | ✅ — `load_config` avec overrides CLI conforme |
| Plan WS-12.3 | ❌ — Le plan exige `python -m ai_trading --config configs/default.yaml` → crash (BLOQUANT 1) |
| Formules doc vs code | ✅ | N/A (pas de formule mathématique) |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `run_pipeline(config)` → `Path`, `fetch_ohlcv(config)` → `IngestionResult`, `load_config(yaml_path, overrides)` — tous conformes |
| Noms de colonnes DataFrame | N/A | Pas de DataFrame manipulé directement (sauf dans `_run_qa_command` qui délègue à `run_qa_checks`) |
| Clés de configuration | ✅ | `config.dataset.symbols`, `config.dataset.timeframe`, `config.dataset.raw_dir`, `config.qa.zero_volume_min_streak` — toutes vérifiées dans config.py |
| Registres et conventions | N/A | Pas de registre utilisé |
| Structures de données partagées | ✅ | `IngestionResult.path`, `IngestionResult.row_count` — confirmé dans ingestion.py L50-52 |
| Conventions numériques | N/A | Pas de calcul numérique |
| Imports croisés | ✅ | Tous les symboles importés existent dans la branche courante |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts | N/A | CLI pur, pas de calcul financier |
| Nommage métier cohérent | ✅ | `fetch_ohlcv`, `run_qa_checks` — noms métier corrects |
| Séparation des responsabilités | ✅ | CLI = dispatch uniquement, logique déléguée aux modules |
| Invariants de domaine | N/A | |
| Cohérence des unités | N/A | |
| Patterns de calcul | N/A | |

---

## Remarques

1. **[BLOQUANT]** Sous-commande par défaut cassée — `python -m ai_trading --config configs/default.yaml` échoue.
   - Fichier : `ai_trading/__main__.py`
   - Ligne(s) : 69-70 (`subparsers.default = "run"`)
   - Preuve : `build_parser().parse_args([])` → `Namespace(command='run')` sans attribut `config`. `build_parser().parse_args(['--config', 'x.yaml'])` → `SystemExit(2)` « invalid choice ».
   - Impact : le critère d'acceptation du plan WS-12.3 n'est pas satisfait.
   - Suggestion : ajouter les arguments communs (`--config`, `--strategy`, `--output-dir`, `--set`) au parser principal (en plus des sous-parsers), et ajouter un test d'intégration `test_main_no_subcommand_with_config`.

2. **[WARNING]** `_run_qa_command` non testé unitairement.
   - Fichier : `tests/test_cli.py`
   - Ligne(s) : `TestMainQA` ligne 266-282 (mock `_run_qa_command` entièrement)
   - Impact : logique interne (chemin parquet, `symbols[0]`, appel `run_qa_checks`) jamais exercée par les tests.
   - Suggestion : ajouter 2 tests unitaires : nominal avec fixture parquet + erreur fichier absent.

3. **[MINEUR]** Pattern fallback §R1 à la ligne 158.
   - Fichier : `ai_trading/__main__.py`
   - Ligne(s) : 158 (`overrides=overrides if overrides else None`)
   - Suggestion : remplacer par `overrides=overrides or None`.

4. **[MINEUR]** Annotation de retour incohérente pour `_run_qa_command`.
   - Fichier : `ai_trading/__main__.py`
   - Ligne(s) : 124 (`-> None`) et 139 (`return report`)
   - Suggestion : changer en `-> QAReport` ou retirer le `return report`.

5. **[MINEUR]** Checklist tâche non entièrement cochée (commit GREEN + PR).
   - Fichier : `docs/tasks/M5/050__ws12_cli_entry_point.md`
   - Ligne(s) : dernières lignes de la checklist
   - Impact : cosmétique, le commit GREEN existe bien (`6621708`).

## Actions requises

1. **Fix BLOQUANT 1** : corriger le default subcommand pour que `python -m ai_trading --config configs/default.yaml` fonctionne. Ajouter les arguments communs au parser principal. Ajouter un test d'intégration couvrant ce scénario.
2. **Fix WARNING 2** : ajouter des tests unitaires pour `_run_qa_command` (nominal + erreur).
3. **Fix MINEUR 3** : simplifier le ternaire L158.
4. **Fix MINEUR 4** : corriger l'annotation de type `_run_qa_command`.
5. **Fix MINEUR 5** : cocher les items de checklist correspondants dans la tâche.
