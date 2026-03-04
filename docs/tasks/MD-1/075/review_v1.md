# Revue PR — [WS-D-1] #075 — Data loader chargement CSV

Branche : `task/075-wsd1-data-loader-csv`
Tâche : `docs/tasks/MD-1/075__wsd1_data_loader_csv.md`
Date : 2026-03-05

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

L'implémentation est propre et conforme à la spec : 6 fonctions CSV/JSON, dégradation gracieuse, validation de colonnes, calcul `costs`, colonne `fold` déduite du chemin. Tous les scans GREP sont clean, 22 tests passent. Deux items mineurs empêchent le verdict CLEAN : une assertion trompeuse dans les tests (comparaison lexicographique de listes au lieu d'un test d'inclusion) et l'absence de validation du paramètre `split` dans `load_predictions`.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/075-*` | ✅ | `task/075-wsd1-data-loader-csv` |
| Commit RED présent | ✅ | `13abe60 [WS-D-1] #075 RED: tests data loader chargement CSV` — 1 fichier : `tests/test_dashboard_data_loader_csv.py` (432 insertions) |
| Commit GREEN présent | ✅ | `2175231 [WS-D-1] #075 GREEN: data loader chargement CSV` — 3 fichiers : `scripts/dashboard/data_loader.py` (+168), `docs/tasks/MD-1/075__wsd1_data_loader_csv.md` (+60), `tests/test_dashboard_data_loader_csv.py` (-1) |
| RED contient uniquement tests | ✅ | `git show --stat 13abe60` : seul `tests/test_dashboard_data_loader_csv.py` |
| GREEN contient implémentation + tâche | ✅ | `git show --stat 2175231` : source + tâche + fix mineur test |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` : exactement 2 commits |

### Tâche

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | Ligne 3 : `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (8/8) | Tous `[x]` |
| Checklist cochée | ⚠️ (7/9) | 2 items non cochés : commit GREEN et PR — attendu à ce stade du workflow |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1862 passed**, 27 deselected, 0 failed |
| `ruff check` (fichiers modifiés) | **All checks passed** |

**Phase A : PASS** — aucun blocage, suite vers Phase B.

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

| Pattern recherché | Règle | Résultat |
|---|---|---|
| Fallbacks silencieux (`or []`, `or {}`, `if x else`) | §R1 | 0 occurrences dans `data_loader.py` (grep exécuté) |
| Except trop large (`except:`, `except Exception:`) | §R1 | 0 occurrences (grep exécuté) |
| Suppressions lint (`noqa`) | §R7 | 0 occurrences dans les 3 fichiers modifiés (grep exécuté) |
| Print résiduel (`print(`) | §R7 | 0 occurrences (grep exécuté) |
| Shift négatif (`.shift(-`) | §R3 | 0 occurrences (grep exécuté) |
| Legacy random API | §R4 | 0 occurrences (grep exécuté) |
| TODO/FIXME orphelins | §R7 | 0 occurrences (grep exécuté) |
| Chemins hardcodés OS-spécifiques | §R7 | 0 occurrences dans tests (grep exécuté) |
| Imports absolus `__init__.py` | §R7 | N/A — aucun `__init__.py` modifié |
| Registration manuelle tests | §R7 | 0 occurrences (grep exécuté) |
| Mutable default arguments | §R6 | 0 occurrences (grep exécuté). Les helpers de test utilisent `cols: list[str] | None = None` avec `if cols is not None else` — pattern correct |
| `open()` sans context manager | §R6 | 4 matches `.read_text()` — tous via `Path.read_text(encoding="utf-8")`, pattern accepté per §R6 |
| Comparaison booléenne par identité | §R6 | 0 occurrences (grep exécuté) |
| Dict collision silencieuse | §R6 | `df["fold"] = fold_dir.name` (L313) et `result["costs"] = ...` (L319) — assignation sur colonne DataFrame, pas de risque de collision dict. Faux positif. |
| Boucle Python sur array numpy | §R9 | 0 occurrences dans source (grep exécuté) |
| `isfinite` check | §R6 | 0 occurrences — N/A, pas de paramètres numériques validés par bornes dans le code ajouté |
| Appels numpy répétés dans compréhension | §R9 | 0 occurrences (grep exécuté) |
| Fixtures dupliquées (`load_config.*configs/`) | §R7 | 0 occurrences dans tests (grep exécuté) |

### B2. Annotations par fichier

#### `scripts/dashboard/data_loader.py` (168 lignes ajoutées)

- **L215-L239** — Constantes `_EQUITY_CURVE_COLS`, `_FOLD_EQUITY_CURVE_COLS`, `_TRADES_COLS`, `_PREDICTIONS_COLS` : utilisation de `frozenset` — correct pour des ensembles immuables partagés.
  Sévérité : RAS

- **L242-L248** — `_validate_columns(df, required, filepath)` : helper DRY utilisé par toutes les fonctions CSV. `missing = required - set(df.columns)` puis `raise ValueError`. Pattern correct et strict.
  Sévérité : RAS

- **L255-L265** — `load_equity_curve` : vérifie `csv_path.exists()` → `None` si absent, sinon `read_csv` + `_validate_columns`. Conforme au contrat documenté.
  Sévérité : RAS

- **L268-L278** — `load_fold_equity_curve` : même pattern que ci-dessus avec `_FOLD_EQUITY_CURVE_COLS` (sans colonne `fold`). Conforme à la spec §4.2.
  Sévérité : RAS

- **L281-L319** — `load_trades` : vérifie `folds_dir.is_dir()`, itère les sous-dossiers triés, charge chaque `trades.csv`, valide les colonnes, ajoute `fold = fold_dir.name`, concatène avec `ignore_index=True`, calcule `costs = fees_paid + slippage_paid`. Formule conforme à spec §6.6 (`costs = fees_paid + slippage_paid`). Colonne `fold` déduite du chemin conforme à spec §6.6.
  Sévérité : RAS

- **L322-L332** — `load_fold_trades` : charge un seul `trades.csv` sans ajout de `fold` ni `costs`. Correct — ces colonnes sont spécifiques à la concaténation multi-fold.
  Sévérité : RAS

- **L335-L354** — `load_predictions(fold_dir, split)` : construit `f"preds_{split}.csv"`. Le paramètre `split` n'est pas validé. La docstring indique `"val"` ou `"test"` mais aucun `raise` si la valeur est invalide. Un string arbitraire produirait un fichier inexistant → `None`, ce qui est du fallback silencieux (le code ne distingue pas « fichier réellement absent » de « paramètre invalide »).
  Sévérité : **MINEUR** (voir remarque 1)

- **L357-L381** — `load_fold_metrics` : pattern identique aux loaders JSON existants (`load_run_metrics`, `load_run_manifest`). `json.loads` + `isinstance(data, dict)` + `ValueError` si non-dict. Conforme et cohérent avec le reste du module.
  Sévérité : RAS

#### `tests/test_dashboard_data_loader_csv.py` (432 lignes)

- **L47-L140** — Helpers `_make_equity_csv`, `_make_fold_equity_csv`, `_make_trades_csv`, `_make_preds_csv`, `_make_run_with_folds` : créent des fixtures CSV synthétiques avec `pd.DataFrame.to_csv()`. Tous utilisent `tmp_path` (portabilité). Pattern `cols if cols is not None else DEFAULT` est correct pour des helpers de test.
  Sévérité : RAS

- **L170** — `assert list(result.columns) >= ["time_utc", "equity", "in_trade", "fold"]` : comparaison lexicographique de listes, **pas** un test d'inclusion. Fonctionne ici car les colonnes produites sont exactement ces 4 dans cet ordre, mais le pattern est trompeur. Contrairement aux autres tests de la même classe qui utilisent correctement `for col in ...: assert col in result.columns` (L195, L237, etc.).
  Sévérité : **MINEUR** (voir remarque 2)

- **L162-L185** — `TestLoadEquityCurve` : 3 tests (valide, absent, colonnes manquantes). Couverture correcte.
  Sévérité : RAS

- **L192-L213** — `TestLoadFoldEquityCurve` : 3 tests (valide, absent, colonnes manquantes). OK.
  Sévérité : RAS

- **L220-L280** — `TestLoadTrades` : 5 tests (multi-fold, no folds dir, folds sans trades, colonnes manquantes, single fold). Vérifie `fold` column, `costs` column avec `pytest.approx`. Couverture excellente.
  Sévérité : RAS

- **L287-L315** — `TestLoadFoldTrades` : 3 tests (valide, absent, colonnes manquantes). OK.
  Sévérité : RAS

- **L322-L357** — `TestLoadPredictions` : 4 tests (val, test, absent, colonnes manquantes). Couvre les deux splits. OK.
  Sévérité : RAS

- **L364-L400** — `TestLoadFoldMetrics` : 4 tests (valide, absent, JSON invalide, non-dict). OK.
  Sévérité : RAS

- **Couverture globale des critères d'acceptation** :

| Critère d'acceptation | Test(s) |
|---|---|
| Chargement correct de chaque type CSV | `test_valid_file` dans chaque classe |
| Colonne `fold` ajoutée | `TestLoadTrades::test_valid_multi_fold` L240 |
| Colonne `costs` calculée | `TestLoadTrades::test_valid_multi_fold` L245-248 |
| Retour `None` si absent | `test_absent_*` dans chaque classe |
| Validation colonnes obligatoires | `test_missing_columns_raises` dans chaque classe |
| Tests unitaires avec fixtures synthétiques | Helpers `_make_*_csv` + tous les tests |

### B3. Vérification des tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage `test_dashboard_data_loader_csv.py` | ✅ | Nom du fichier conforme |
| ID tâche `#075` dans docstrings | ✅ | Toutes les docstrings contiennent `#075` |
| Chaque critère couvert par un test | ✅ | Tableau ci-dessus |
| Cas nominaux + erreurs + bords | ✅ | Valide, absent, colonnes manquantes, single fold, multi-fold, JSON invalide, non-dict |
| Pas de test désactivé (`skip`, `xfail`) | ✅ | Aucun match grep |
| Tests déterministes | ✅ | Aucun aléatoire, données synthétiques fixes |
| Données synthétiques (pas réseau) | ✅ | Helpers `_make_*_csv` créent les CSV localement |
| Portabilité chemins (`tmp_path`) | ✅ | Tous les tests utilisent `tmp_path` |

### B4. Audit du code

#### B4a. Strict code (§R1)
- ✅ Aucun fallback silencieux dans le code source (grep exécuté).
- ✅ Aucun `except` trop large (grep exécuté). Les `except json.JSONDecodeError` et `except yaml.YAMLError` sont ciblés.
- ✅ Validation explicite : `_validate_columns` lève `ValueError` si colonnes manquantes.
- ⚠️ `load_predictions(split)` : paramètre non validé (MINEUR — remarque 1).

#### B4b. Config-driven (§R2)
- ✅ N/A — pas de paramètres modifiables hardcodés. Les noms de fichiers (`equity_curve.csv`, `trades.csv`, `preds_val.csv`, etc.) sont des conventions du pipeline, pas des paramètres configurables.

#### B4c. Anti-fuite (§R3)
- ✅ N/A — module de chargement, pas de calcul temporel.

#### B4d. Reproductibilité (§R4)
- ✅ N/A — pas d'aléatoire.

#### B4e. Float conventions (§R5)
- ✅ N/A — pas de conversion dtype explicite. Les CSV sont chargés avec les types pandas par défaut, ce qui est correct pour un module dashboard.

#### B4f. Anti-patterns Python (§R6)
- ✅ Pas de mutable default arguments (grep exécuté).
- ✅ Pas de `open()` sans context manager — utilisation de `Path.read_text()`.
- ✅ `pd.read_csv()` gère le context manager implicitement.
- ✅ Comparaisons float avec `pytest.approx` dans les tests.

### B5. Qualité du code (§R7)

| Critère | Verdict |
|---|---|
| snake_case cohérent | ✅ |
| Pas de code mort / TODO | ✅ (grep exécuté) |
| Pas de `print()` | ✅ (grep exécuté) |
| Imports propres | ✅ : `json`, `logging`, `Path`, `pd`, `yaml` — pas d'imports inutilisés |
| Pas de `noqa` | ✅ (grep exécuté) |
| DRY | ✅ : `_validate_columns` factorise la logique de validation |

### B5-bis. Bonnes pratiques métier (§R9)
- ✅ Calcul `costs = fees_paid + slippage_paid` conforme à la spec §6.6.
- ✅ Colonne `fold` déduite du chemin (`fold_dir.name`) conforme à la spec §6.6.

### B6. Cohérence avec les specs

| Critère | Verdict | Preuve |
|---|---|---|
| `costs = fees_paid + slippage_paid` | ✅ | Spec §6.6 : « Le dashboard doit calculer `costs = fees_paid + slippage_paid`. » — Implémentation L319 |
| Colonne `fold` déduite du chemin | ✅ | Spec §6.6 : « Le numéro de fold est déduit du chemin fichier `folds/fold_XX/trades.csv`. » — Implémentation L313 |
| Colonnes equity curve stitchée | ✅ | Spec §4.2 : `time_utc`, `equity`, `in_trade`, `fold` — `_EQUITY_CURVE_COLS` L218 |
| Colonnes equity curve par fold | ✅ | Spec §4.2 : `time_utc`, `equity`, `in_trade` (pas de `fold`) — `_FOLD_EQUITY_CURVE_COLS` L219 |
| Dégradation gracieuse `None` si absent | ✅ | Spec §4.2 : « fonctionner en mode dégradé si certains sont absents » |
| Pas d'exigence inventée | ✅ | Toutes les fonctions correspondent aux réfs de la tâche |

### B7. Cohérence intermodule (§R8)

| Critère | Verdict | Preuve |
|---|---|---|
| Signatures cohérentes avec le module existant | ✅ | Les fonctions existantes (`load_run_metrics`, `load_run_manifest`, `load_config_snapshot`, `discover_runs`) suivent les mêmes patterns |
| Noms de colonnes DataFrame | ✅ | Colonnes alignées avec la spec et les artefacts du pipeline |
| Pattern erreur cohérent | ✅ | `ValueError` avec message incluant le filepath — même convention que les fonctions existantes |
| Import `pandas` ajouté | ✅ | L15 `import pandas as pd` — nouvel import nécessaire et correct |

---

## Remarques

1. **[MINEUR]** `load_predictions` — paramètre `split` non validé
   - Fichier : `scripts/dashboard/data_loader.py`
   - Ligne(s) : 336, 349
   - Description : Le paramètre `split` accepte n'importe quel string. La docstring indique `"val"` ou `"test"` mais aucune validation n'est effectuée. Un appel avec `split="train"` ou `split=""` produirait un retour `None` sans distinction entre « fichier réellement absent » et « paramètre invalide ».
   - Suggestion : Ajouter une validation explicite en début de fonction :
     ```python
     if split not in {"val", "test"}:
         raise ValueError(f"split must be 'val' or 'test', got {split!r}")
     ```
     Et ajouter un test correspondant dans `TestLoadPredictions`.

2. **[MINEUR]** Assertion trompeuse — comparaison lexicographique de listes
   - Fichier : `tests/test_dashboard_data_loader_csv.py`
   - Ligne(s) : 170
   - Description : `assert list(result.columns) >= ["time_utc", "equity", "in_trade", "fold"]` utilise la comparaison lexicographique de listes Python (`>=`), qui n'est **pas** un test d'inclusion/sous-ensemble. Ici le test passe car les colonnes sont exactement dans le même ordre, mais le pattern est trompeur et fragile (un changement d'ordre de colonnes casserait le test de manière non évidente). Les autres tests du même fichier utilisent correctement `for col in ...: assert col in result.columns`.
   - Suggestion : Remplacer par :
     ```python
     for col in ["time_utc", "equity", "in_trade", "fold"]:
         assert col in result.columns
     ```

---

## Résumé

Code de qualité, bien structuré, conforme à la spec et aux conventions du projet. Les 22 tests couvrent tous les critères d'acceptation (nominal, absent, colonnes manquantes, multi-fold, single fold, JSON invalide). Deux items mineurs identifiés : validation du paramètre `split` et assertion trompeuse dans un test. Aucun item bloquant ni warning.
