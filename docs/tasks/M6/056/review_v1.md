# Revue PR — [WS-13] #056 — Test full-scale make run-all BTCUSDT

Branche : `task/056-test-fullscale-run`
Tâche : `docs/tasks/M6/056__ws13_test_fullscale_run.md`
Date : 2026-03-03

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

La branche implémente correctement le test fullscale avec politique M6 (aucune fixture, mock ou donnée synthétique). Le processus TDD est respecté (RED → GREEN), les tests sont bien structurés et les checks CI passent (1621 passed, 0 failed, ruff clean). Quatre points mineurs sont identifiés : une variable morte, une inconsistance de filtrage dans les assertions, un commit RED incluant un fichier non-test, et un test d'equity curve plus tolérant que l'AC.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/056-*` | ✅ | `git branch --show-current` → `task/056-test-fullscale-run` |
| Commit RED présent | ✅ | `2113961 [WS-13] #056 RED: test fullscale make run-all BTCUSDT` |
| Commit GREEN présent | ✅ | `98be8df [WS-13] #056 GREEN: test fullscale make run-all BTCUSDT` |
| RED contient uniquement des fichiers de tests | ⚠️ | `git show --stat 2113961` : `pyproject.toml` + `tests/test_fullscale_btc.py`. Voir remarque #2. |
| GREEN contient implémentation + tâche | ✅ | `git show --stat 98be8df` : uniquement `docs/tasks/M6/056__ws13_test_fullscale_run.md` |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` : 2 commits exactement (RED + GREEN) |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (10/11 — 1 non coché = exécution réseau manuelle, noté explicitement) |
| Checklist cochée | ✅ (8/9 — 1 non coché = PR pas encore ouverte, normal à ce stade) |

**Vérification des critères cochés :**
- `[x] Marker fullscale enregistré` → preuve : `pyproject.toml` diff, `markers = ["fullscale: ..."]`
- `[x] addopts exclut fullscale` → preuve : `addopts = "-v --tb=short -m \"not fullscale\""`
- `[x] test_fullscale_btc.py existe` → preuve : fichier créé dans diff, `@pytest.mark.fullscale` L58
- `[x] pytest standard n'exécute pas fullscale` → preuve : `pytest tests/ -v` → 1621 passed, 11 deselected
- `[ ] pytest -m fullscale GREEN` → non coché, exécution réseau requise — OK
- `[x] Artefacts attendus` → preuve : tests L97-165 couvrent manifest.json, metrics.json, equity_curve, config_snapshot.yaml
- `[x] ≥ 1 fold` → preuve : test L133
- `[x] ≥ 70 000 lignes Parquet` → preuve : test L85, constante `MIN_PARQUET_ROWS = 70_000`
- `[x] Scénarios nominaux + erreurs + bords` → les 11 tests couvrent le nominal. Pour un test fullscale M6 (pas de mocks autorisés), les cas d'erreur réseau/données ne sont pas testables sans fixtures — acceptable.
- `[x] Suite standard verte` → preuve : 1621 passed, 0 failed
- `[x] ruff clean` → preuve : `ruff check ai_trading/ tests/` → All checks passed

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1621 passed**, 11 deselected, 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** |

✅ Phase A : PASS — on continue en Phase B.

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux | `grep ' or \[\]\| or {}\| or ""\| or 0\| if .* else '` | 0 occurrences (grep exécuté) |
| §R1 Except trop large | `grep 'except:\|except Exception:'` | 0 occurrences (grep exécuté) |
| §R7 noqa | `grep 'noqa'` | 0 occurrences (grep exécuté) |
| §R7 print résiduel | `grep 'print('` | 0 occurrences (grep exécuté) |
| §R3 Shift négatif | `grep '.shift(-'` | 0 occurrences (grep exécuté) |
| §R4 Legacy random API | `grep 'np.random.seed\|np.random.randn\|...'` | 0 occurrences (grep exécuté) |
| §R7 TODO/FIXME | `grep 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences (grep exécuté) |
| §R7 Chemins hardcodés | `grep '/tmp\|/var/tmp\|C:\\'` | 0 occurrences (grep exécuté) |
| §R7 Imports absolus __init__ | N/A | Aucun `__init__.py` modifié |
| §R7 Registration manuelle | `grep 'register_model\|register_feature'` | 0 occurrences (grep exécuté) |
| §R6 Mutable defaults | `grep 'def .*=\[\]\|def .*={}'` | 0 occurrences (grep exécuté) |
| §R6 open() | `grep 'open('` | 1 match L51 — utilise `with` ✅ |
| §R6 Comparaison booléenne identité | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences (grep exécuté) |
| §R9 Boucle Python range | `grep 'for .* in range'` | 0 occurrences (grep exécuté) |
| §R6 isfinite | `grep 'isfinite'` | 0 occurrences — N/A, pas de validation numérique |
| §R9 Numpy compréhension | `grep 'np\.[a-z]*(.*for .* in '` | 0 occurrences (grep exécuté) |
| §R7 Fixtures dupliquées | `grep 'load_config.*configs/'` | 0 occurrences (grep exécuté) |
| **M6 Policy** tmp_path/mock | `grep 'tmp_path\|mock\|Mock\|patch\|monkeypatch\|sample_ohlcv'` | 1 match L8 — docstring uniquement (faux positif) ✅ |
| **M6 Policy** fixtures | `grep '@pytest.fixture\|generate_.*data'` | 0 occurrences ✅ |

### B2. Annotations par fichier

#### `tests/test_fullscale_btc.py` (196 lignes — diff complet lu)

- **L26** `FULLSCALE_CONFIG = PROJECT_ROOT / "configs" / "fullscale_btc.yaml"` : variable définie mais jamais référencée dans aucun test. Le test `test_make_run_all_succeeds` (L70) utilise le littéral string `"CONFIG=configs/fullscale_btc.yaml"` directement dans la commande. Code mort.
  Sévérité : **MINEUR**
  Suggestion : supprimer la constante `FULLSCALE_CONFIG` ou l'utiliser dans la commande make (ex : `f"CONFIG={FULLSCALE_CONFIG.relative_to(PROJECT_ROOT)}"`).

- **L35** `def _find_latest_run_dir(pattern: str = "*_dummy") -> Path:` : le pattern par défaut `"*_dummy"` est cohérent avec la config fullscale (`name: dummy` dans `fullscale_btc.yaml` L97). Pas de problème.
  Sévérité : RAS

- **L51** `with open(path, encoding="utf-8") as f:` : context manager utilisé correctement.
  Sévérité : RAS

- **L53** `if not isinstance(data, dict):` : validation de type après JSON désérialisation conforme §R6.
  Sévérité : RAS

- **L68-78** `subprocess.run(["make", "run-all", "CONFIG=..."], ...)` : arguments passés en liste (pas de shell injection). `timeout=600` conforme à la tâche. `cwd=str(PROJECT_ROOT)` correct.
  Sévérité : RAS

- **L79-82** `result.stdout[-2000:]` : slicing de string — safe en Python (retourne la chaîne complète si < 2000 chars).
  Sévérité : RAS

- **L137** `fold_dirs = sorted(folds_dir.iterdir())` : n'applique PAS de filtre `if d.is_dir()`, contrairement à L176 et L192 qui filtrent. Si un fichier non-répertoire existe dans `folds/`, il serait compté. Variable nommée `fold_dirs` mais peut contenir des fichiers.
  Sévérité : **MINEUR**
  Suggestion : uniformiser avec les autres tests — `fold_dirs = sorted(d for d in folds_dir.iterdir() if d.is_dir())`.

- **L148-153** `assert stitched.is_file() or fallback.is_file()` : le test accepte `equity_curve.csv` comme alternative à `equity_curve_stitched.csv`. L'AC de la tâche spécifie explicitement `equity_curve_stitched.csv`. Le test est plus tolérant que l'AC.
  Sévérité : **MINEUR**
  Suggestion : tester strictement `equity_curve_stitched.csv` comme spécifié dans l'AC, ou documenter dans l'AC que les deux noms sont acceptés.

#### `pyproject.toml` (diff 6 lignes)

- **L67** `addopts = "-v --tb=short -m \"not fullscale\""` : correctement échappé, exclut les tests fullscale par défaut.
  Sévérité : RAS

- **L68-70** `markers = ["fullscale: ..."]` : marker correctement enregistré.
  Sévérité : RAS

- Inclusion de `pyproject.toml` dans le commit RED au lieu du commit GREEN.
  Sévérité : **MINEUR** (voir remarque #2)

#### `docs/tasks/M6/056__ws13_test_fullscale_run.md`

- Diff vérifié : passage `[ ]` → `[x]` cohérent avec le code produit. 1 critère réseau correctement laissé `[ ]` avec annotation. 1 item checklist PR correctement laissé `[ ]`.
  Sévérité : RAS

### B3. Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_fullscale_btc.py`, docstring `Task #056` |
| Couverture des critères | ✅ | 11 tests couvrent les 9 points de l'AC (voir mapping B2) |
| Cas nominaux | ✅ | 11 tests nominaux validant les artefacts |
| Cas erreurs/bords | N/A | Test fullscale M6 — pas de fixtures/mocks autorisés, erreurs réseau non testables |
| Déterministes | ✅ | Tests d'artefacts (assertions sur fichiers), pas d'aléatoire |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé. Utilise `Path(__file__).resolve().parent.parent` |
| Tests registre réalistes | N/A | Pas de registre impliqué |
| Contrat ABC complet | N/A | Pas d'ABC impliqué |
| Données synthétiques / M6 | ✅ | Scan B1 : 0 fixture, 0 mock, 0 tmp_path, 0 conftest data |

### B4. Code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback, 0 except large. Helpers `_find_latest_run_dir`/`_load_json` lèvent des exceptions explicites. |
| §R10 Defensive indexing | ✅ | Pas d'indexation array dangereuse. Slicing string L79-82 safe. |
| §R2 Config-driven | ✅ | Constantes en tête de fichier (`MIN_PARQUET_ROWS`, `PROJECT_ROOT`, chemins). Pas de valeur magique inline. |
| §R3 Anti-fuite | N/A | Pas de manipulation de données temporelles dans les tests. |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random. Tests déterministes (assertions sur fichiers). |
| §R5 Float conventions | N/A | Pas de manipulation de tenseurs ou métriques. |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable default, `open()` avec `with`, pas de `is True/False`, pas de dict collision. |

### B5. Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage et style | ✅ | snake_case, noms descriptifs |
| Pas de code mort/debug | ⚠️ | `FULLSCALE_CONFIG` inutilisé (L26) — MINEUR #1 |
| Imports propres / relatifs | ✅ | Imports stdlib → third-party → pas de local, ordre correct |
| DRY | ✅ | Pas de duplication significative |

### B6. Conformité spec / plan

| Critère | Verdict |
|---|---|
| Conforme spec §3, §17.3 | ✅ — test fullscale sur données BTCUSDT réelles |
| Conforme plan WS-13.2 | ✅ — marker fullscale, exclusion par défaut, `make run-all` |
| Formules doc vs code | N/A — pas de formule mathématique dans ce test |

### B7. Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types | N/A | Pas de code source `ai_trading/` modifié |
| Noms de colonnes | N/A | Pas de manipulation DataFrame (sauf `len(df)`) |
| Clés de configuration | N/A | Config lue via `make` en subprocess |
| Registres | N/A | |
| Structures partagées | N/A | |
| Conventions numériques | N/A | |
| Imports croisés | ✅ | Imports : `json`, `subprocess`, `Path`, `jsonschema`, `pandas`, `pytest` — tous disponibles |

### B5-bis. Bonnes pratiques métier

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude concepts financiers | N/A | Test d'intégration, pas de calcul financier |
| Nommage métier | ✅ | `equity_curve`, `folds`, `trades` — termes cohérents |
| Séparation responsabilités | ✅ | Test dédié à la validation d'artefacts post-exécution |
| Invariants de domaine | N/A | |
| Cohérence unités/échelles | N/A | |
| Patterns calcul financier | N/A | |

---

## Remarques

1. **[MINEUR]** Variable morte `FULLSCALE_CONFIG`
   - Fichier : `tests/test_fullscale_btc.py`
   - Ligne : 26
   - Suggestion : supprimer la constante ou l'utiliser dans la commande make : `f"CONFIG={FULLSCALE_CONFIG.relative_to(PROJECT_ROOT)}"`.

2. **[MINEUR]** `pyproject.toml` dans le commit RED
   - Fichier : `pyproject.toml`
   - Commit : `2113961` (RED)
   - Description : le commit RED devrait contenir uniquement des fichiers de tests. `pyproject.toml` contient des modifications de configuration test (marker registration, addopts), pas du code d'implémentation. Déviation mineure de processus.
   - Suggestion : dans le futur, séparer la config test infra dans le commit GREEN ou documenter l'exception.

3. **[MINEUR]** Filtrage inconsistant dans `test_at_least_one_fold`
   - Fichier : `tests/test_fullscale_btc.py`
   - Ligne : 137
   - Description : `sorted(folds_dir.iterdir())` sans filtre `if d.is_dir()`, contrairement aux tests L176 et L192 qui filtrent. Un fichier non-répertoire dans `folds/` serait compté comme un fold.
   - Suggestion : uniformiser — `fold_dirs = sorted(d for d in folds_dir.iterdir() if d.is_dir())`.

4. **[MINEUR]** Test equity_curve plus tolérant que l'AC
   - Fichier : `tests/test_fullscale_btc.py`
   - Lignes : 148-153
   - Description : le test accepte `equity_curve.csv` en plus de `equity_curve_stitched.csv`, mais l'AC spécifie uniquement `equity_curve_stitched.csv`. Risque de masquer une régression si le pipeline cesse de produire la version stitched.
   - Suggestion : tester strictement `equity_curve_stitched.csv` ou mettre à jour l'AC pour documenter que les deux noms sont acceptés.

---

## Actions requises

1. Supprimer la constante morte `FULLSCALE_CONFIG` (L26) ou l'utiliser dans la commande make.
2. Uniformiser le filtrage dans `test_at_least_one_fold` (L137) avec `if d.is_dir()`.
3. Aligner le test `test_equity_curve_exists` avec l'AC (strictement `equity_curve_stitched.csv`) ou mettre à jour l'AC.
4. (Optionnel) Documenter l'inclusion de `pyproject.toml` dans le commit RED comme exception liée à l'infrastructure de test.
