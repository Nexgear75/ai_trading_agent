# Revue PR — [WS-D-1] #075 — Data loader chargement CSV

Branche : `task/075-wsd1-data-loader-csv`
Tâche : `docs/tasks/MD-1/075__wsd1_data_loader_csv.md`
Date : 2026-03-05
Itération : v2 (post-corrections v1)

## Verdict global : ✅ CLEAN

## Résumé

Les deux items MINEUR identifiés en v1 ont été corrigés dans le commit FIX `949c700` : validation du paramètre `split` dans `load_predictions` avec test associé, et remplacement de l'assertion lexicographique par une boucle `assert col in columns`. L'implémentation reste propre, conforme à la spec, et tous les scans GREP sont clean. 23 tests passent (vs 22 en v1). Aucun item restant.

---

## Corrections v1 → v2

| # | Item v1 | Sévérité | Correction | Vérifié |
|---|---|---|---|---|
| M-1 | `load_predictions` — paramètre `split` non validé | MINEUR | L349-350 : `if split not in {"val", "test"}: raise ValueError(...)` + test `test_invalid_split_raises` | ✅ diff `949c700` L349-350 + test L384-389 |
| M-2 | Assertion lexicographique `>=` au lieu d'inclusion | MINEUR | L171-172 : `for col in [...]: assert col in result.columns` | ✅ diff `949c700` L171-172 |

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/075-*` | ✅ | `task/075-wsd1-data-loader-csv` |
| Commit RED présent | ✅ | `13abe60 [WS-D-1] #075 RED: tests data loader chargement CSV` — 1 fichier : `tests/test_dashboard_data_loader_csv.py` (432 insertions) |
| Commit GREEN présent | ✅ | `2175231 [WS-D-1] #075 GREEN: data loader chargement CSV` — 3 fichiers : source + tâche + fix mineur test |
| RED contient uniquement tests | ✅ | `git show --stat 13abe60` : seul `tests/test_dashboard_data_loader_csv.py` |
| GREEN contient implémentation + tâche | ✅ | `git show --stat 2175231` : `scripts/dashboard/data_loader.py` (+168), `docs/tasks/MD-1/075__wsd1_data_loader_csv.md` (+60), `tests/test_dashboard_data_loader_csv.py` (-1) |
| Commit FIX post-revue | ✅ | `949c700 [WS-D-1] #075 FIX: validate split param in load_predictions, fix misleading list comparison in test` — 2 fichiers : source (+2), test (+11/-1) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` : 3 commits (RED, GREEN, FIX) — séquence cohérente |

### Tâche

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | Ligne 3 : `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (8/8) | Tous `[x]` |
| Checklist cochée | ⚠️ (7/9) | 2 items non cochés : commit GREEN et PR — attendu à ce stade du workflow (merge pas encore fait) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/test_dashboard_data_loader_csv.py -v` | **23 passed**, 0 failed |
| `pytest tests/ -v --tb=short` | **1863 passed**, 27 deselected, 0 failed |
| `ruff check` (fichiers modifiés) | **All checks passed** |

**Phase A : PASS**

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

| Pattern recherché | Règle | Résultat |
|---|---|---|
| Fallbacks silencieux (`or []`, `or {}`, `if x else`) | §R1 | 0 occurrences dans `data_loader.py` — EXIT:1 |
| Except trop large (`except:`, `except Exception:`) | §R1 | 0 occurrences — EXIT:1 |
| Suppressions lint (`noqa`) | §R7 | 0 occurrences dans les 3 fichiers modifiés — EXIT:1 |
| Print résiduel (`print(`) | §R7 | 0 occurrences — EXIT:1 |
| Shift négatif (`.shift(-`) | §R3 | 0 occurrences — EXIT:1 |
| Legacy random API | §R4 | 0 occurrences — EXIT:1 |
| TODO/FIXME orphelins | §R7 | 0 occurrences — EXIT:1 |
| Chemins hardcodés OS-spécifiques | §R7 | 0 occurrences dans tests — EXIT:1 |
| Mutable default arguments | §R6 | 0 occurrences — EXIT:1 |
| `open()` sans context manager | §R6 | 0 occurrences dans source — EXIT:1. `Path.read_text(encoding="utf-8")` utilisé (pattern accepté §R6) |

### B2. Annotations par fichier

#### `scripts/dashboard/data_loader.py` (170 lignes ajoutées)

- **L220-L241** — Constantes `_EQUITY_CURVE_COLS`, `_FOLD_EQUITY_CURVE_COLS`, `_TRADES_COLS`, `_PREDICTIONS_COLS` : `frozenset` immuables. Correct.
  Sévérité : RAS

- **L244-L250** — `_validate_columns(df, required, filepath)` : `missing = required - set(df.columns)` → `raise ValueError`. Helper DRY.
  Sévérité : RAS

- **L257-L267** — `load_equity_curve` : vérifie `csv_path.exists()` → `None` si absent, sinon `read_csv` + `_validate_columns`. Conforme.
  Sévérité : RAS

- **L270-L280** — `load_fold_equity_curve` : même pattern avec `_FOLD_EQUITY_CURVE_COLS` (sans `fold`). Conforme §4.2.
  Sévérité : RAS

- **L283-L321** — `load_trades` : `folds_dir.is_dir()` check, itération triée, charge + valide + ajoute `fold = fold_dir.name`, concaténation `ignore_index=True`, calcul `costs = fees_paid + slippage_paid`. Formule conforme spec §6.6.
  Sévérité : RAS

- **L324-L334** — `load_fold_trades` : charge un seul `trades.csv`. Pas de `fold`/`costs` — correct.
  Sévérité : RAS

- **L337-L359** — `load_predictions(fold_dir, split)` :
  - **L349-350** : `if split not in {"val", "test"}: raise ValueError(...)` — **correction M-1 v1 vérifiée**. Validation stricte avant construction du chemin. Correct.
  Sévérité : RAS

- **L362-L384** — `load_fold_metrics` : `json.loads` + `isinstance(data, dict)` + `ValueError`. Pattern cohérent avec `load_run_metrics` existant.
  Sévérité : RAS

RAS après lecture complète du diff (170 lignes source).

#### `tests/test_dashboard_data_loader_csv.py` (439 lignes)

- **L171-172** — `for col in ["time_utc", "equity", "in_trade", "fold"]: assert col in result.columns` — **correction M-2 v1 vérifiée**. Pattern d'inclusion correct, cohérent avec les autres tests du fichier.
  Sévérité : RAS

- **L384-389** — `test_invalid_split_raises` : `pytest.raises(ValueError, match="split must be 'val' or 'test'")` avec `load_predictions(tmp_path, "train")` — **test M-1 v1 vérifié**. Cas d'erreur couvert.
  Sévérité : RAS

- **L47-L140** — Helpers synthétiques `_make_*_csv` : tous utilisent `tmp_path`, `pd.DataFrame.to_csv()`. Pattern `cols if cols is not None else DEFAULT` correct. Pas de mutable default.
  Sévérité : RAS

RAS après lecture complète du diff (439 lignes test).

#### `docs/tasks/MD-1/075__wsd1_data_loader_csv.md` (60 lignes ajoutées)

Mise à jour tâche : statut DONE, critères cochés. Conforme.
Sévérité : RAS

### B3. Vérification des tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_dashboard_data_loader_csv.py` |
| ID tâche `#075` dans docstrings | ✅ | Toutes les docstrings contiennent `#075` |
| Chaque critère couvert | ✅ | Voir mapping ci-dessous |
| Cas nominaux + erreurs + bords | ✅ | Valide, absent, colonnes manquantes, single fold, multi-fold, JSON invalide, non-dict, split invalide |
| Pas de test désactivé | ✅ | Aucun `skip`/`xfail` |
| Tests déterministes | ✅ | Aucun aléatoire, données synthétiques fixes |
| Données synthétiques | ✅ | Helpers `_make_*_csv` locaux |
| Portabilité chemins (`tmp_path`) | ✅ | Scan B1 : 0 `/tmp` hardcodé |

**Couverture des critères d'acceptation** :

| Critère d'acceptation | Test(s) |
|---|---|
| Chargement correct de chaque type CSV | `test_valid_file` dans chaque classe (6 tests) |
| Colonne `fold` ajoutée | `TestLoadTrades::test_valid_multi_fold` |
| Colonne `costs` calculée | `TestLoadTrades::test_valid_multi_fold` (L245-248 avec `pytest.approx`) |
| Retour `None` si absent | `test_absent_*` dans chaque classe (6 tests) |
| Validation colonnes obligatoires | `test_missing_columns_raises` dans chaque classe (6 tests) |
| Suite de tests verte | pytest 23 passed |
| ruff clean | All checks passed |
| **Split invalide** (ajout v2) | `TestLoadPredictions::test_invalid_split_raises` |

### B4. Audit du code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| Strict code (§R1) | ✅ | Scan B1 : 0 fallback, 0 except large. Validation `_validate_columns` + `split` validation L349. |
| Defensive indexing (§R10) | ✅ | N/A — pas d'indexing numérique dans le code ajouté |
| Config-driven (§R2) | ✅ | N/A — noms de fichiers CSV sont des conventions pipeline, pas des paramètres |
| Anti-fuite (§R3) | ✅ | Scan B1 : 0 `.shift(-`. Module de chargement, pas de calcul temporel |
| Reproductibilité (§R4) | ✅ | Scan B1 : 0 legacy random. Pas d'aléatoire |
| Float conventions (§R5) | ✅ | N/A — pas de conversion dtype. Types pandas par défaut (dashboard) |
| Anti-patterns Python (§R6) | ✅ | Scan B1 : 0 mutable default, 0 `open()` nu. `Path.read_text(encoding="utf-8")` OK. Float comparisons avec `pytest.approx` |

### B5. Qualité du code (§R7)

| Critère | Verdict | Preuve |
|---|---|---|
| snake_case cohérent | ✅ | Tous les noms conformes |
| Pas de code mort / TODO | ✅ | Scan B1 : 0 TODO/FIXME |
| Pas de `print()` | ✅ | Scan B1 : 0 occurrences |
| Imports propres | ✅ | `json`, `logging`, `Path`, `pd`, `yaml` — pas d'import inutilisé |
| Pas de `noqa` | ✅ | Scan B1 : 0 occurrences |
| DRY | ✅ | `_validate_columns` factorise la logique de validation |

### B5-bis. Bonnes pratiques métier (§R9)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude concepts financiers | ✅ | `costs = fees_paid + slippage_paid` conforme spec §6.6 |
| Nommage métier cohérent | ✅ | `equity_curve`, `trades`, `predictions`, `fold` — nommage explicite |
| Séparation des responsabilités | ✅ | Module de chargement uniquement, pas de calcul métier |
| Invariants de domaine | ✅ | N/A — lecture seule |
| Cohérence des unités | ✅ | N/A — pas de conversion |

### B6. Conformité spec v1.0

| Critère | Verdict | Preuve |
|---|---|---|
| `costs = fees_paid + slippage_paid` | ✅ | Spec §6.6, L321 |
| Colonne `fold` déduite du chemin | ✅ | Spec §6.6, L315 |
| Colonnes equity stitchée | ✅ | Spec §4.2 : `_EQUITY_CURVE_COLS` L220 |
| Colonnes equity par fold | ✅ | Spec §4.2 : `_FOLD_EQUITY_CURVE_COLS` L221 |
| Dégradation gracieuse `None` si absent | ✅ | Spec §4.2, toutes les fonctions |
| Pas d'exigence inventée | ✅ | Toutes les fonctions correspondent aux réfs de la tâche |
| Formules doc vs code | ✅ | Aucune divergence |

### B7. Cohérence intermodule (§R8)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures cohérentes | ✅ | Mêmes patterns que `load_run_metrics`, `load_run_manifest` existants |
| Noms de colonnes DataFrame | ✅ | Alignés avec la spec et les artefacts du pipeline |
| Pattern erreur cohérent | ✅ | `ValueError` avec filepath — même convention |
| Import `pandas` | ✅ | L15 `import pandas as pd` — nécessaire et correct |
| Structures de données partagées | ✅ | N/A — pas de dataclass partagée |
| Conventions numériques | ✅ | N/A |
| Imports croisés | ✅ | Aucun import d'autre module `ai_trading/` |

---

## Remarques

Aucune remarque. Les 2 items MINEUR de v1 sont corrigés.

## Actions requises

Aucune.

---

```
RÉSULTAT PARTIE B :
- Verdict : CLEAN
- Bloquants : 0
- Warnings : 0
- Mineurs : 0
- Rapport : docs/tasks/MD-1/075/review_v2.md
```
