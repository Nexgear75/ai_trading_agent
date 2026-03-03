# Revue PR — [WS-12] #052 — Script de comparaison inter-stratégies

Branche : `task/052-compare-runs`
Tâche : `docs/tasks/M5/052__ws12_compare_runs.md`
Date : 2026-03-03

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Le script `scripts/compare_runs.py` implémente correctement la comparaison inter-stratégies avec séparation Go/No-Go / contextuelle, production CSV/Markdown et vérification §14.4. Le TDD est respecté (RED → GREEN propres). Cependant, 2 warnings liés au strict code (`.get()` silencieux sur les métriques trading) et à la conformité spec §14.4 (exclusion de buy_hold) empêchent l'approbation directe. 1 item mineur additionnel.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/052-compare-runs` | ✅ | `git branch --show-current` → `task/052-compare-runs` |
| Commit RED `[WS-12] #052 RED: tests comparaison inter-stratégies` | ✅ | hash `4af8ee0` — format conforme |
| Commit GREEN `[WS-12] #052 GREEN: script comparaison inter-stratégies` | ✅ | hash `25314a6` — format conforme |
| Commit RED = tests uniquement | ✅ | `git show --stat 4af8ee0` → `tests/test_compare_runs.py` (1 fichier, 557 insertions) |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 25314a6` → `scripts/compare_runs.py`, `scripts/__init__.py`, `pyproject.toml`, `docs/tasks/M5/052__ws12_compare_runs.md`, `tests/test_compare_runs.py` (5 fichiers) |
| Pas de commits parasites | ✅ | `git log --oneline` → 2 commits uniquement (RED + GREEN) |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (9/9) |
| Checklist cochée | ✅ (8/9 — item « Pull Request ouverte » non coché, attendu à ce stade) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/test_compare_runs.py -v --tb=short` | **23 passed**, 0 failed |
| `pytest tests/ --tb=short -q` | **1500 passed**, 0 failed |
| `ruff check scripts/ tests/test_compare_runs.py` | **All checks passed** |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 — Fallbacks silencieux (`or []`, `or {}`, etc.) | `grep -n ' or \[\]\|...' scripts/compare_runs.py` | 0 occurrences (grep exécuté) |
| §R1 — Except trop large | `grep -n 'except:$\|except Exception:'` | 0 occurrences (grep exécuté) |
| §R7 — Suppressions lint (`noqa`) | `grep -rn 'noqa' ...` | 0 occurrences (grep exécuté) |
| §R7 — Print résiduel | `grep -n 'print(' scripts/compare_runs.py` | 4 matches (L289, L304, L306, L308) — **faux positifs** : `print()` dans `main()` CLI entry point pour sortie utilisateur, usage légitime pour un script CLI |
| §R3 — Shift négatif (look-ahead) | `grep -n '.shift(-'` | 0 occurrences (grep exécuté) |
| §R4 — Legacy random API | `grep -rn 'np.random.seed\|...'` | 0 occurrences (grep exécuté) |
| §R7 — TODO/FIXME orphelins | `grep -rn 'TODO\|FIXME\|...'` | 0 occurrences (grep exécuté) |
| §R7 — Chemins hardcodés OS (tests) | `grep -rn '/tmp\|C:\\'` tests/ | 0 occurrences (grep exécuté) |
| §R7 — Imports absolus `__init__.py` | `grep -rn 'from ai_trading\.' scripts/__init__.py` | 0 occurrences (grep exécuté) — fichier vide |
| §R7 — Registration manuelle tests | `grep -rn 'register_model\|register_feature'` tests/ | 0 occurrences (grep exécuté) — N/A |
| §R6 — Mutable default arguments | `grep -rn 'def .*=\[\]\|def .*={}'` | 0 occurrences (grep exécuté) |
| §R6 — `open()` sans context manager | `grep -rn '.read_text\|open(' scripts/compare_runs.py` | 1 match: L71 `p.read_text(encoding="utf-8")` — **faux positif** : `Path.read_text()` est un raccourci accepté |
| §R6 — Booléen identité (`is True/False`) | `grep -rn 'is True\|is False'` tests/ | 4 matches (L347, L371, L396, L472) — **faux positifs** : `check_criterion_14_4()` retourne un `bool` Python natif, `is True`/`is False` est correct |
| §R6 — Dict collision silencieuse | `grep -rn '\[.*\] = .*' scripts/compare_runs.py` | 3 matches (L65, L126, L229) — **faux positifs** : initialisations de listes vides, pas d'assignation par clé calculée |
| §R9 — Boucle Python sur array numpy | `grep -rn 'for .* in range(.*):' scripts/compare_runs.py` | 0 occurrences (grep exécuté) |
| §R6 — isfinite validation | `grep -rn 'isfinite' scripts/compare_runs.py` | 0 occurrences — pas de paramètres numériques en entrée publique à valider (les valeurs viennent de JSON désérialisé) |
| §R9 — Appels numpy compréhension | `grep -rn 'np\.[a-z]*(.*for .* in '` | 0 occurrences (grep exécuté) |
| §R7 — Fixtures dupliquées | `grep -rn 'load_config.*configs/' tests/test_compare_runs.py` | 0 occurrences (grep exécuté) |
| per-file-ignores | `grep -n 'per-file-ignores' pyproject.toml` | Pas de changement lié à cette PR |

### Annotations par fichier (B2)

#### `scripts/compare_runs.py` (314 lignes)

- **L145-L150** `.get()` silencieux sur les métriques trading :
  ```python
  "net_pnl_mean": trading_mean.get("net_pnl"),
  "max_drawdown_mean": trading_mean.get("max_drawdown"),
  "sharpe_mean": trading_mean.get("sharpe"),
  ...
  ```
  `.get()` retourne `None` si la clé est absente, ce qui silencieusement injecte `None`/`NaN` dans le DataFrame. Les comparaisons ultérieures dans `check_criterion_14_4` (L196: `best_pnl > baseline["net_pnl_mean"]`) deviennent silencieusement `False` avec NaN (IEEE 754). Le code devrait utiliser `trading_mean["net_pnl"]` (KeyError explicite si manquant) ou valider la présence de ces clés dans `load_metrics`.
  Sévérité : **WARNING**
  Suggestion : Remplacer les `.get()` par `[]` direct, ou ajouter une validation des clés `aggregate.trading.mean` dans `load_metrics`.

- **L131** Accès `aggregate["trading"]["mean"]` sans validation structurelle :
  La validation dans `load_metrics` vérifie `_REQUIRED_TOP_KEYS` (`run_id`, `strategy`, `aggregate`) et `_REQUIRED_STRATEGY_KEYS` (`strategy_type`, `name`), mais ne valide pas la structure interne de `aggregate`. Un fichier `metrics.json` avec `"aggregate": {}` passe `load_metrics` mais crashe dans `compare_strategies` avec un `KeyError: 'trading'` cryptique.
  Sévérité : **MINEUR**
  Suggestion : Valider dans `load_metrics` que `aggregate` contient `trading.mean` (ou documenter explicitement le contrat).

- **L133-L140** Fallback `else: comp_type = "go_nogo"` pour stratégies inconnues :
  ```python
  if "comparison_type" in aggregate:
      comp_type = aggregate["comparison_type"]
  elif strategy["name"] in _CONTEXTUAL_STRATEGY_NAMES:
      comp_type = "contextual"
  else:
      comp_type = "go_nogo"
  ```
  Toute stratégie non listée dans `_CONTEXTUAL_STRATEGY_NAMES` et sans `comparison_type` explicite dans le JSON est silencieusement classée `go_nogo`. C'est un comportement raisonnable mais constitue un fallback implicite. Acceptable car le premier chemin (`aggregate["comparison_type"]`) sert de source de vérité, et le fallback est une heuristique de compatibilité.
  Sévérité : OK — noté pour information, pas d'action requise.

- **L160-L200** `check_criterion_14_4` exclut buy_hold du critère §14.4 :
  Le docstring dit : *"The comparison is restricted to go_nogo strategies only (buy & hold is excluded as it is a contextual baseline per §13.4)."*
  Cependant, la spec §14.4 dit explicitement : *"le meilleur modèle bat au moins une baseline (no-trade **et/ou buy & hold**) en P&L net ou MDD"*. L'implémentation exclut buy_hold en se basant sur §13.4, mais §14.4 est un critère distinct qui inclut explicitement buy_hold. Si le modèle ne bat aucune baseline go_nogo mais bat buy_hold, le critère §14.4 devrait être satisfait selon la spec, mais l'implémentation retournerait `False`.
  Sévérité : **WARNING**
  Suggestion : Soit inclure buy_hold dans la vérification §14.4 (toutes les baselines), soit documenter explicitement cette déviation comme un choix de design validé.

- **L289, L304, L306, L308** `print()` dans `main()` :
  Usage légitime dans un CLI entry point. Les messages sont écrits sur stdout/stderr selon le contexte.
  Sévérité : OK — faux positif.

#### `tests/test_compare_runs.py` (557 lignes)

- RAS après lecture complète du diff (557 lignes). Tests bien structurés, docstrings avec `#052`, données synthétiques, `tmp_path` pour les chemins temporaires, couverture nominale + erreurs + bords.

#### `scripts/__init__.py`

- Fichier vide. Nécessaire pour que `scripts/` soit un package importable (cf. `pythonpath = ["."]` dans `pyproject.toml`). RAS.

#### `pyproject.toml`

- **L66** Ajout `pythonpath = ["."]` dans `[tool.pytest.ini_options]` :
  Nécessaire pour que pytest puisse résoudre `from scripts.compare_runs import ...` dans les tests. Effet : ajoute le répertoire racine au `sys.path` de pytest. Pas d'effet de bord sur le reste du projet.
  Sévérité : OK.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_compare_runs.py`, docstrings avec `#052` |
| Couverture des critères d'acceptation | ✅ | Voir mapping ci-dessous |
| Cas nominaux + erreurs + bords | ✅ | `TestLoadMetrics` (6 tests : nominal single/multi + 4 erreurs), `TestCompareStrategies` (6 tests), `TestCheckCriterion144` (6 tests : pass/fail/MDD/no-model/no-baseline/buy_hold_excluded), `TestOutputFiles` (2 tests), `TestCLI` (3 tests : success/missing/no-args) |
| Boundary fuzzing | ✅ | Liste vide (load_metrics), 0 modèle, 0 baseline, model pire que toutes baselines, model gagne par MDD seul |
| Déterministes | ✅ | Pas d'aléatoire, données synthétiques déterministes |
| Données synthétiques | ✅ | `_make_metrics()` helper, pas de réseau |
| Portabilité chemins | ✅ | `tmp_path` partout, scan B1 : 0 `/tmp` |
| Tests registre réalistes | N/A | Pas de registre dans ce module |
| Contrat ABC complet | N/A | Pas d'ABC dans ce module |

**Mapping critères d'acceptation → tests :**

| # | Critère d'acceptation | Test(s) |
|---|---|---|
| 1 | Script existe et exécutable | `TestCLI::test_cli_runs_successfully` |
| 2 | Identifie meilleure stratégie avec 2+ fichiers | `TestCompareStrategies::test_identifies_best_strategy` |
| 3 | Critère §14.4 vérifié et affiché | `TestCheckCriterion144` (6 tests) + `TestCLI::test_cli_runs_successfully` |
| 4 | Go/No-Go vs contextuelle séparés | `TestCompareStrategies::test_go_nogo_and_contextual_separated` |
| 5 | Tableau CSV/Markdown produit et lisible | `TestOutputFiles::test_write_csv`, `TestOutputFiles::test_write_markdown` |
| 6 | Erreur explicite si metrics.json invalide/introuvable | `TestLoadMetrics::test_load_missing_file_raises`, `test_load_invalid_json_raises`, `test_load_missing_required_keys_raises`, `test_load_empty_list_raises` |
| 7 | Tests cas nominaux + erreurs + bords | Couvert par l'ensemble des 23 tests |
| 8 | Suite de tests verte | 23 passed, 0 failed |
| 9 | ruff check passe | All checks passed |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ⚠️ | Scan B1 : 0 `or []`/`or {}`, 0 except large. **Mais** 6× `.get()` en L145-L150 retournent None silencieusement (voir annotations B2). |
| §R10 Defensive indexing | ✅ | Pas d'indexation array/slice dans ce module. Itérations DataFrame via `.iterrows()` et `.idxmax()`. |
| §R2 Config-driven | ✅ | Script standalone post-MVP, pas de config YAML attendue. Paramètres via CLI args. Conforme à la tâche. |
| §R3 Anti-fuite | ✅ | N/A — pas de calcul sur données temporelles. Scan B1 : 0 `.shift(-`. |
| §R4 Reproductibilité | ✅ | N/A — pas d'aléatoire. Scan B1 : 0 legacy random. |
| §R5 Float conventions | ✅ | N/A — pas de tenseurs. Métriques lues depuis JSON (float64 par défaut). |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, `read_text()` accepté, 0 `is np.bool_`. `is True/False` sur `bool` natif (faux positif). |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Tous noms conformes : `load_metrics`, `compare_strategies`, `check_criterion_14_4`, `write_csv`, `write_markdown`, `_df_to_md_table` |
| Pas de code mort/debug | ✅ | Scan B1 : 0 TODO/FIXME, `print()` = CLI output légitime |
| Imports propres | ✅ | Imports standards → tiers → aucun local intra-package. Pas d'import inutilisé. |
| DRY | ✅ | Pas de duplication de logique. Helper `_make_metrics` dans les tests bien factorisé. |
| `.gitignore` | ✅ | Pas de fichiers générés dans la PR |
| `__init__.py` à jour | ✅ | `scripts/__init__.py` créé (nécessaire pour pythonpath import) |

### Conformité spec v1.0 (B6)

| Critère | Verdict |
|---|---|
| §13.4 — Séparation Go/No-Go vs contextuelle | ✅ — Le DataFrame contient une colonne `comparison_type`, le Markdown produit deux sections séparées. |
| §14.4 — Critère d'acceptation | ⚠️ — L'implémentation exclut buy_hold du critère §14.4, alors que la spec inclut explicitement "no-trade et/ou buy & hold". Voir WARNING #2. |
| Plan d'implémentation WS-12.5 | ✅ — Script CLI standalone post-MVP, conforme au plan. |
| Formules doc vs code | ✅ — §14.4 : "bat au moins une baseline en P&L net ou MDD" → code : `best_pnl > baseline["net_pnl_mean"]` OR `best_mdd < baseline["max_drawdown_mean"]`. Logique OR conforme. |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | API publique bien typée : `load_metrics(paths: list[Path]) -> list[dict]`, etc. |
| Noms de colonnes DataFrame | ✅ | Colonnes issues de `metrics.json` schema : `net_pnl`, `max_drawdown`, `sharpe`, etc. |
| Clés de configuration | N/A | Script standalone, pas de lecture de config YAML. |
| Registres | N/A | Pas d'inscription dans un registre. |
| Structures de données partagées | ✅ | `metrics.json` schema compatible avec `ai_trading/artifacts/metrics_builder.py`. |
| Conventions numériques | ✅ | Float64 par défaut (JSON → Python float, pandas float64). |
| Imports croisés | ✅ | Aucun import de `ai_trading/`. Module standalone dans `scripts/`. |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | Comparaison P&L net et MDD conforme aux concepts. |
| Nommage métier cohérent | ✅ | `net_pnl_mean`, `max_drawdown_mean`, `sharpe_mean`, `profit_factor_mean`. |
| Séparation des responsabilités | ✅ | Chaque fonction = une responsabilité (load, compare, check, write). |
| Invariants de domaine | ✅ | Vérifie présence de modèles et baselines avant comparaison (raises ValueError). |
| Cohérence des unités/échelles | ✅ | Métriques lues directement depuis metrics.json, pas de transformation. |
| Patterns de calcul financier | N/A | Pas de calcul financier direct (lecture et comparaison de métriques pré-calculées). |

---

## Remarques

1. **[WARNING]** `.get()` silencieux sur métriques trading dans `compare_strategies()`.
   - Fichier : `scripts/compare_runs.py`
   - Ligne(s) : 145-150
   - Description : Les 6 appels `trading_mean.get("net_pnl")`, `.get("max_drawdown")`, etc. retournent `None` si la clé est absente. Ces `None` deviennent `NaN` dans le DataFrame. `check_criterion_14_4` compare ensuite ces valeurs avec `>` et `<` — avec NaN, ces comparaisons retournent silencieusement `False` (IEEE 754), masquant le problème. Violation §R1 (strict code : pas de fallback masquant un input manquant).
   - Suggestion : Remplacer `.get("net_pnl")` par `trading_mean["net_pnl"]` (KeyError explicite), ou mieux, ajouter une constante `_REQUIRED_TRADING_MEAN_KEYS = frozenset({"net_pnl", "max_drawdown", "sharpe", ...})` et valider dans `load_metrics` comme pour les autres clés requises.

2. **[WARNING]** Exclusion de buy_hold du critère §14.4 — déviation par rapport à la spec.
   - Fichier : `scripts/compare_runs.py`
   - Ligne(s) : 165-200
   - Description : La spec §14.4 dit : *"le meilleur modèle bat au moins une baseline (no-trade et/ou buy & hold) en P&L net ou MDD"*. L'implémentation filtre sur `comparison_type == "go_nogo"`, excluant buy_hold. Si un modèle ne bat aucune baseline go_nogo mais bat buy_hold en MDD, la spec dit §14.4 est satisfait, mais le code retourne `False`.
   - Suggestion : Soit modifier `check_criterion_14_4` pour inclure toutes les baselines (go_nogo + contextual), soit documenter cette déviation comme un choix de design validé et mettre à jour le docstring avec la justification explicite.

3. **[MINEUR]** Validation partielle de la structure `aggregate` dans `load_metrics`.
   - Fichier : `scripts/compare_runs.py`
   - Ligne(s) : 60-96 (validation) vs 131 (accès)
   - Description : `load_metrics` valide les clés top-level (`run_id`, `strategy`, `aggregate`) et les clés strategy (`strategy_type`, `name`), mais ne valide pas que `aggregate` contient `trading.mean`. Un JSON avec `"aggregate": {}` passe `load_metrics` mais crashe dans `compare_strategies` avec `KeyError: 'trading'` sans message clair.
   - Suggestion : Ajouter la validation de `aggregate["trading"]["mean"]` dans `load_metrics`, ou au minimum documenter le contrat.

## Résumé

Le script est bien structuré, les tests couvrent les scénarios pertinents (23 tests, cas nominaux + erreurs + bords), et le TDD est respecté. Deux points empêchent l'approbation : (1) les `.get()` sur les métriques trading violent le principe strict code et masquent silencieusement les données manquantes via NaN, (2) l'exclusion de buy_hold du critère §14.4 dévie de la formulation explicite de la spec. Un item mineur additionnel sur la validation structurelle de `aggregate`.

---

RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 2
- Mineurs : 1
- Rapport : `docs/tasks/M5/052/review_v1.md`
