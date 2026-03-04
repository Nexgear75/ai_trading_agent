# Revue PR — [WS-D-1] #074 — Data loader découverte et validation runs

Branche : `task/074-wsd1-data-loader-discovery`
Tâche : `docs/tasks/MD-1/074__wsd1_data_loader_discovery.md`
Date : 2026-03-04

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Implémentation propre des fonctions de découverte et validation des runs dans `data_loader.py`, avec factorisation DRY réussie depuis `compare_runs.py`. Deux warnings identifiés : un fallback silencieux `.get("strategy", {})` dont le default est unreachable après validation, et l'absence de validation de type sur la valeur `strategy` dans `load_run_metrics()`. Un mineur sur le test DRY.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche | ✅ | `task/074-wsd1-data-loader-discovery` |
| Commit RED présent | ✅ | `586470c` — `[WS-D-1] #074 RED: tests data loader découverte et validation runs` |
| Commit GREEN présent | ✅ | `fb13549` — `[WS-D-1] #074 GREEN: data loader découverte et validation runs` |
| RED = tests uniquement | ✅ | `git show --stat 586470c` → 1 file: `tests/test_dashboard_data_loader.py` (+427) |
| GREEN = implémentation + tâche | ✅ | `git show --stat fb13549` → 4 files: `data_loader.py` (+199), `compare_runs.py` (+14/-10), `test_dashboard_data_loader.py` (+4/-4), tâche MD |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → exactement 2 commits (RED + GREEN) |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (9/9) |
| Checklist cochée | ✅ (9/10 — seule la ligne PR non cochée, normal avant merge) |

#### Mapping critères d'acceptation → preuves

| Critère | Preuve |
|---|---|
| `discover_runs()` découvre les runs valides et exclut dummy | `data_loader.py` L162-205 + tests `TestDiscoverRuns` (7 tests) |
| `load_run_metrics()` valide clés requises + raise | `data_loader.py` L33-76 + tests `TestLoadRunMetrics` (7 tests) |
| `load_run_manifest()` charge manifest.json | `data_loader.py` L79-113 + tests `TestLoadRunManifest` (3 tests) |
| `load_config_snapshot()` charge config_snapshot.yaml | `data_loader.py` L116-153 + tests `TestLoadConfigSnapshot` (3 tests) |
| Runs invalides signalés par logging | `data_loader.py` L192/197 (`logger.warning`) + tests `test_broken_json_excluded_and_logged`, `test_missing_required_keys_excluded_and_logged` |
| Logique DRY avec compare_runs.py | `compare_runs.py` L30 importe `REQUIRED_STRATEGY_KEYS, REQUIRED_TOP_KEYS` depuis data_loader + tests `TestDRYWithCompareRuns` |
| Tests unitaires | 22 tests dans `test_dashboard_data_loader.py` |
| Suite verte | 1838 passed, 0 failed |
| ruff clean | All checks passed |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -x -q --tb=short` | **1838 passed**, 27 deselected, 0 failed |
| `ruff check scripts/ tests/test_dashboard_data_loader.py tests/test_compare_runs.py` | **All checks passed** |

**Phase A : PASS** → passage en Phase B.

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 — Fallbacks silencieux (`or []`, `or {}`, `if … else`) | `grep -n` sur SRC | 0 occurrences (grep exécuté). _Note : `.get("strategy", {})` non capté par ce pattern mais identifié en B2._ |
| §R1 — Except trop large | `grep 'except:$\|except Exception:'` sur SRC | 0 occurrences (grep exécuté) |
| §R7 — noqa | `grep 'noqa'` sur CHANGED | 1 occurrence : `compare_runs.py:30` — `# noqa: E402` justifié (import après `sys.path.insert`) |
| §R7 — Print résiduel | `grep 'print('` sur SRC | 4 matches dans `compare_runs.py` L317/332/334/336 — **pré-existants** (CLI main, hors diff) |
| §R3 — Shift négatif | `grep '.shift(-'` sur SRC | 0 occurrences (grep exécuté) |
| §R4 — Legacy random API | `grep 'np.random.seed…'` sur CHANGED | 0 occurrences (grep exécuté) |
| §R7 — TODO/FIXME | `grep 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences (grep exécuté) |
| §R7 — Chemins hardcodés tests | `grep '/tmp\|C:\\'` sur TEST | 0 occurrences (grep exécuté) |
| §R7 — Imports absolus `__init__` | `grep 'from ai_trading\.'` sur `__init__.py` | N/A (pas de `__init__.py` dans `scripts/dashboard/` — pré-existant, pas un défaut de cette PR) |
| §R7 — Registration manuelle tests | `grep 'register_model\|register_feature'` sur TEST | 0 occurrences (grep exécuté) |
| §R6 — Mutable defaults | `grep 'def.*=[]\|def.*={}'` | 0 occurrences (grep exécuté) |
| §R6 — open() sans context manager | `grep 'open('` sur SRC | 0 occurrences (utilise `Path.read_text()` partout) |
| §R6 — Bool identity | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences (grep exécuté) |
| §R6 — isfinite | `grep 'isfinite'` sur SRC | 0 occurrences (N/A — pas de paramètres numériques validés) |
| §R6 — Dict collision | `grep '[…] = '` sur SRC | 1 match `data_loader.py:183` — `results: list[dict] = []` — faux positif (déclaration de variable) |
| §R9 — for range | `grep 'for .* in range'` sur SRC | 0 occurrences (grep exécuté) |
| §R9 — np comprehension | `grep 'np\.[a-z]*(.*for'` sur SRC | 0 occurrences (grep exécuté) |
| §R7 — Fixtures dupliquées | `grep 'load_config.*configs/'` sur TEST | 0 occurrences (grep exécuté) |
| §R7 — per-file-ignores | `grep 'per-file-ignores' pyproject.toml` | L52 — pré-existant, non modifié |

### B2. Annotations par fichier

#### `scripts/dashboard/data_loader.py` (nouveau fichier, 205 lignes)

- **L200** `strategy = data.get("strategy", {})` : fallback silencieux (§R1). Après `load_run_metrics()` qui valide que `"strategy"` ∈ `REQUIRED_TOP_KEYS`, la clé est **garantie** présente dans `data`. Le default `{}` est du code mort (unreachable). Devrait être `data["strategy"]`.
  Sévérité : **WARNING**
  Suggestion : remplacer par `strategy = data["strategy"]`

- **L200-201** `data.get("strategy", {})` + `isinstance(strategy, dict)` : `load_run_metrics()` valide la présence de la clé `strategy` mais **ne valide pas son type**. Si `metrics.json` contient `"strategy": "string"`, `load_run_metrics` passe sans erreur, `discover_runs` inclut le run (car `isinstance("string", dict)` est False → skip le check dummy → le run est ajouté), et le code aval (`compare_runs.compare_strategies()`) plante sur `strategy["name"]`. La validation de type des données désérialisées est incomplète (§R6).
  Sévérité : **WARNING**
  Suggestion : dans `load_run_metrics()`, après la validation des clés requises, ajouter :
  ```python
  if not isinstance(data["strategy"], dict):
      raise ValueError(
          f"File {metrics_path}: 'strategy' must be a JSON object, "
          f"got {type(data['strategy']).__name__}"
      )
  ```

- **L156-205** (`discover_runs`) : la spec §4.3 mentionne « Existence de `manifest.json` et `metrics.json` (obligatoires) ». La fonction ne vérifie que `metrics.json`. Cependant, §5.1 dit « sous-répertoires contenant un `metrics.json` valide » pour la découverte, et la tâche #074 spécifie le même périmètre. La validation de `manifest.json` est assurée par `load_run_manifest()` qui existe et sera appelée par le dashboard lors du chargement complet d'un run. **Design acceptable** — non signalé comme défaut.

- Reste du fichier (L1-153) : RAS après lecture complète. Validation stricte avec `raise`, pas de fallback, encoding explicite, chaîne `from exc` sur toutes les exceptions re-levées. Code clair et bien structuré.

#### `scripts/compare_runs.py` (diff : 14 insertions, 10 suppressions)

- **L25-29** : ajout de `_PROJECT_ROOT` + `sys.path.insert(0, ...)` pour permettre l'import `from scripts.dashboard.data_loader import ...`. Pattern standard pour scripts standalone. RAS.

- **L30** : `from scripts.dashboard.data_loader import REQUIRED_STRATEGY_KEYS, REQUIRED_TOP_KEYS  # noqa: E402` — DRY correctement implémenté. Le `noqa: E402` est **justifié** car l'import est après la manipulation de `sys.path` (L25-28). Pas d'alternative propre sans restructurer le script.

- **L84, L95** : utilisation de `REQUIRED_TOP_KEYS` et `REQUIRED_STRATEGY_KEYS` (sans underscore) en remplacement de `_REQUIRED_TOP_KEYS` et `_REQUIRED_STRATEGY_KEYS`. Fonctionnellement identique — les valeurs `frozenset` sont les mêmes.

- RAS après lecture complète du diff (24 lignes modifiées). La refactorisation est minimale et correcte.

#### `tests/test_dashboard_data_loader.py` (nouveau fichier, 431 lignes)

- **L412-425** (`test_no_duplicate_required_keys_constant`) : le test vérifie que `_REQUIRED_TOP_KEYS` (avec underscore, l'ancien nom privé) n'est pas redéfini dans `compare_runs.py`. Puisque le constant a été renommé en `REQUIRED_TOP_KEYS` (sans underscore), le test passe trivialement car `_REQUIRED_TOP_KEYS` n'existe plus nulle part. Le test ne vérifie **pas** que `REQUIRED_TOP_KEYS` (sans underscore) n'est pas redéfini localement. Combiné au test `test_compare_runs_imports_from_data_loader` (qui vérifie la présence de l'import), la couverture DRY est partielle.
  Sévérité : **MINEUR**
  Suggestion : remplacer le check par une vérification que `REQUIRED_TOP_KEYS` (sans underscore) n'apparaît en position d'assignation dans `compare_runs.py` :
  ```python
  # Verify REQUIRED_TOP_KEYS is not re-assigned in compare_runs.py
  for node in ast.walk(tree):
      if isinstance(node, ast.Assign):
          for target in node.targets:
              if isinstance(target, ast.Name) and target.id == "REQUIRED_TOP_KEYS":
                  pytest.fail("REQUIRED_TOP_KEYS redefined in compare_runs.py")
  ```

- **Helpers** (`_make_metrics_dict`, `_write_run`) : bien construits, génèrent des structures réalistes avec tous les niveaux nécessaires (`aggregate.trading.mean`, etc.). Pas de données hardcodées problématiques.

- **Couverture des critères** : tous les critères d'acceptation sont couverts par au moins un test. Les tests couvrent : run valide, runs multiples, dummy exclu, répertoire vide, metrics.json absent, JSON cassé, clés manquantes, entrées non-répertoire, manifest absent/cassé, config absente/cassée, et DRY.

- **Portabilité** : tous les répertoires temporaires utilisent `tmp_path` de pytest. Aucun chemin hardcodé.

- **Déterminisme** : pas d'aléatoire dans les tests (données synthétiques fixes). Déterministes par construction.

- RAS pour le reste après lecture complète (431 lignes).

#### `docs/tasks/MD-1/074__wsd1_data_loader_discovery.md`

- Statut DONE, critères cochés, checklist cohérente. RAS.

### B3. Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères d'acceptation | ✅ | Mapping complet ci-dessus (9/9 critères couverts) |
| Cas nominaux + erreurs + bords | ✅ | Nominaux: run valide, multiples runs. Erreurs: JSON cassé, clés manquantes, fichier absent, non-dict JSON. Bords: répertoire vide, non-directory entries. |
| Boundary fuzzing | ✅ | N/A (pas de paramètres numériques) |
| Déterministes | ✅ | Données synthétiques fixes, pas d'aléatoire |
| Portabilité chemins | ✅ | Scan B1: 0 `/tmp`. Tous les tests utilisent `tmp_path`. |
| Tests registre réalistes | N/A | Pas de registre impliqué |
| Contrat ABC complet | N/A | Pas d'ABC impliquée |

### B4. Code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ⚠️ | **WARNING** sur `data.get("strategy", {})` L200. Scan B1: 0 match grep. Analyse manuelle B2: 1 fallback identifié. |
| §R10 Defensive indexing | ✅ | Pas d'indexation par expression calculée |
| §R2 Config-driven | N/A | Module utilitaire dashboard, pas de paramétrage pipeline |
| §R3 Anti-fuite | ✅ | Scan B1: 0 `.shift(-`. Pas de données temporelles manipulées. |
| §R4 Reproductibilité | ✅ | Scan B1: 0 legacy random. Pas d'aléatoire. |
| §R5 Float conventions | N/A | Pas de tenseurs ni métriques float |
| §R6 Anti-patterns Python | ⚠️ | **WARNING** : validation de type incomplète sur `strategy` désérialisé (L200). Scan B1: 0 mutable default, 0 open(), 0 bool identity. |

### B5. Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Vérifié dans diff complet |
| Pas de code mort/debug | ✅ | Scan B1: 0 TODO/FIXME, 0 print dans data_loader |
| Imports propres | ✅ | Scan B1: 0 import absolu `__init__`. Imports triés et groupés. |
| DRY | ✅ | `compare_runs.py` importe `REQUIRED_TOP_KEYS`, `REQUIRED_STRATEGY_KEYS` depuis `data_loader`. Aucune redéfinition locale. `grep -rn '_REQUIRED_TOP_KEYS\|_REQUIRED_STRATEGY_KEYS'` → 0 match hors tests/pycache. |

### B5-bis. Bonnes pratiques métier

| Critère | Verdict | Commentaire |
|---|---|---|
| Nommage métier | ✅ | `discover_runs`, `load_run_metrics`, `load_run_manifest`, `load_config_snapshot` — noms clairs |
| Séparation des responsabilités | ✅ | Chaque loader encapsule un fichier spécifique. Discovery aggreège. |
| Invariants de domaine | N/A | Module I/O, pas de calcul financier |

### B6. Conformité spec

| Critère | Verdict | Commentaire |
|---|---|---|
| Spec §4.1 — Structure artefacts | ✅ | `metrics.json`, `manifest.json`, `config_snapshot.yaml` correspondant à l'arborescence spec |
| Spec §4.2 — Fichiers exploités | ✅ | Les 3 loaders couvrent les fichiers obligatoires |
| Spec §4.3 — Validation à l'import | ✅ | Clés requises vérifiées, dummy exclu, dégradation contrôlée (logging sans blocage) |
| Spec §5.1 — Découverte automatique | ✅ | `discover_runs` scanne le répertoire, filtre par metrics.json, exclut dummy |
| Plan WS-D-1.2 | ✅ | Fonctions de discovery et validation implémentées |
| Formules doc vs code | N/A | Pas de formules mathématiques |

### B7. Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `discover_runs` → `list[dict]`, loaders → `dict` — cohérent avec les usages prévus |
| Clés de configuration | N/A | Pas de lecture config pipeline |
| Structures de données partagées | ✅ | `REQUIRED_TOP_KEYS` et `REQUIRED_STRATEGY_KEYS` partagées entre `data_loader` et `compare_runs` |
| Imports croisés | ✅ | `compare_runs.py` importe depuis `scripts.dashboard.data_loader` — module existe dans la branche |
| Conventions numériques | N/A | Pas de calcul numérique |

---

## Remarques

1. **[WARNING]** Fallback silencieux `.get("strategy", {})` (§R1)
   - Fichier : `scripts/dashboard/data_loader.py`
   - Ligne : 200
   - Description : après `load_run_metrics()` qui valide la présence de la clé `strategy`, le default `{}` est unreachable. C'est du code mort qui masquerait une erreur si la validation était accidentellement supprimée.
   - Suggestion : remplacer `data.get("strategy", {})` par `data["strategy"]`

2. **[WARNING]** Validation de type incomplète sur données désérialisées (§R6)
   - Fichier : `scripts/dashboard/data_loader.py`
   - Lignes : 66-76 (load_run_metrics) + 200-201 (discover_runs)
   - Description : `load_run_metrics()` valide que la clé `strategy` existe mais ne vérifie pas son type. Si `metrics.json` contient `"strategy": "xgboost"` (string au lieu d'objet), le run est inclus par `discover_runs` et provoque une erreur ultérieure dans `compare_strategies()`. Le guard `isinstance(strategy, dict)` en L200 atténue le problème dans `discover_runs` (le dummy check est skipé, le run est inclus) mais ne résout pas le fond : le run est invalide et devrait être rejeté.
   - Suggestion : dans `load_run_metrics()`, après la validation des clés requises, ajouter un check de type :
     ```python
     if not isinstance(data["strategy"], dict):
         raise ValueError(...)
     ```

3. **[MINEUR]** Test DRY vérifie l'ancien nom de constante (§R7)
   - Fichier : `tests/test_dashboard_data_loader.py`
   - Lignes : 412-425
   - Description : `test_no_duplicate_required_keys_constant` vérifie que `_REQUIRED_TOP_KEYS` (avec underscore, ancien nom privé) n'est pas redéfini. Puisque la constante a été renommée en `REQUIRED_TOP_KEYS`, le test passe trivialement. Ne protège pas contre une redéfinition de `REQUIRED_TOP_KEYS` (sans underscore).
   - Suggestion : utiliser AST walk pour vérifier qu'aucun `ast.Assign` ne cible `REQUIRED_TOP_KEYS` dans `compare_runs.py`.

---

## Actions requises

1. **data_loader.py L200** : remplacer `data.get("strategy", {})` par `data["strategy"]`.
2. **data_loader.py L66-76** : ajouter validation `isinstance(data["strategy"], dict)` dans `load_run_metrics()` après le check des clés requises.
3. **test_dashboard_data_loader.py L412-425** : mettre à jour `test_no_duplicate_required_keys_constant` pour vérifier le nom actuel `REQUIRED_TOP_KEYS`.
