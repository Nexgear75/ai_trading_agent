# Revue PR — [WS-D-1] #074 — Data loader découverte et validation runs (v2)

Branche : `task/074-wsd1-data-loader-discovery`
Tâche : `docs/tasks/MD-1/074__wsd1_data_loader_discovery.md`
Date : 2026-03-04
Itération : v2 (post-corrections v1)

## Verdict global : ✅ CLEAN

## Résumé

Les trois items identifiés en v1 (W-1, W-2, M-1) ont été correctement corrigés dans le commit `af60d74`. Le fallback `.get("strategy", {})` a été remplacé par un accès direct `data["strategy"]`, la validation de type `isinstance(data["strategy"], dict)` a été ajoutée dans `load_run_metrics()` avec 2 tests associés, et le test DRY trivial a été remplacé par un walk AST vérifiant l'absence de re-définition des constantes. Aucun nouvel item identifié.

---

## Vérification des corrections v1

| Item v1 | Correction attendue | Verdict | Preuve |
|---|---|---|---|
| **W-1** — `data.get("strategy", {})` fallback silencieux | Remplacer par `data["strategy"]` | ✅ Corrigé | `git diff fb13549...af60d74 -- scripts/dashboard/data_loader.py` : L205 `strategy = data["strategy"]` |
| **W-2** — Pas de validation de type sur `data["strategy"]` | Ajouter `isinstance(data["strategy"], dict)` + `raise ValueError` | ✅ Corrigé | `data_loader.py` L76-81 : validation ajoutée après check des clés requises. 2 tests ajoutés : `test_strategy_not_dict_raises`, `test_non_dict_strategy_excluded_and_logged` |
| **M-1** — Test DRY trivial (vérifiait `_REQUIRED_TOP_KEYS` avec underscore) | Remplacer par AST walk vérifiant `REQUIRED_TOP_KEYS` et `REQUIRED_STRATEGY_KEYS` | ✅ Corrigé | `test_no_duplicate_required_keys_constant` : `ast.walk` sur `compare_runs.py`, vérifie absence de `ast.Assign` pour les deux constantes |

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
| Commit FIX post-review | ✅ | `af60d74` — `[WS-D-1] #074 FIX: strict strategy validation + remove fallback .get + fix DRY test` — 2 files: `data_loader.py` (+10/-2), `test_dashboard_data_loader.py` (+59/-7) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → 3 commits (RED + GREEN + FIX post-review v1) |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (9/9) |
| Checklist cochée | ✅ (9/10 — seule la ligne PR non cochée, normal avant merge) |

#### Mapping critères d'acceptation → preuves

| Critère | Preuve |
|---|---|
| `discover_runs()` découvre les runs valides et exclut dummy | `data_loader.py` L170-212 + tests `TestDiscoverRuns` (9 tests) |
| `load_run_metrics()` valide clés requises + raise | `data_loader.py` L33-82 + tests `TestLoadRunMetrics` (8 tests) |
| `load_run_manifest()` charge manifest.json | `data_loader.py` L85-119 + tests `TestLoadRunManifest` (3 tests) |
| `load_config_snapshot()` charge config_snapshot.yaml | `data_loader.py` L122-159 + tests `TestLoadConfigSnapshot` (3 tests) |
| Runs invalides signalés par logging | `data_loader.py` L198/203 (`logger.warning`) + `test_broken_json_excluded_and_logged`, `test_missing_required_keys_excluded_and_logged`, `test_non_dict_strategy_excluded_and_logged` |
| Logique DRY avec compare_runs.py | `compare_runs.py` L30 importe `REQUIRED_STRATEGY_KEYS, REQUIRED_TOP_KEYS` depuis data_loader + tests `TestDRYWithCompareRuns` (2 tests) |
| Tests unitaires | 25 tests dans `test_dashboard_data_loader.py` |
| Suite verte | 1840 passed, 0 failed |
| ruff clean | All checks passed |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1840 passed**, 27 deselected, 0 failed |
| `ruff check ai_trading/ tests/ scripts/` | **All checks passed** |

**Phase A : PASS** → passage en Phase B.

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 — Fallbacks silencieux (`or []`, `or {}`, `if … else`) | `grep -n` sur `data_loader.py`, `compare_runs.py` | 0 occurrences (grep exécuté) |
| §R1 — Except trop large | `grep 'except:$\|except Exception:'` sur SRC | 0 occurrences (grep exécuté) |
| §R7 — noqa | `grep 'noqa'` sur CHANGED | 1 occurrence : `compare_runs.py:30` — `# noqa: E402` justifié (import après `sys.path.insert`) |
| §R7 — Print résiduel | `grep 'print('` sur `data_loader.py` | 0 occurrences (grep exécuté) |
| §R7 — Print résiduel | `grep 'print('` sur `compare_runs.py` | 4 matches L317/332/334/336 — **pré-existants** hors du diff (CLI main), non introduits par cette PR |
| §R3 — Shift négatif | `grep '.shift(-'` sur SRC | 0 occurrences (grep exécuté) |
| §R4 — Legacy random API | `grep 'np.random.seed…'` sur CHANGED | 0 occurrences (grep exécuté) |
| §R7 — TODO/FIXME | `grep 'TODO\|FIXME\|HACK\|XXX'` sur CHANGED | 0 occurrences (grep exécuté) |
| §R7 — Chemins hardcodés tests | `grep '/tmp\|C:\\'` sur TEST | 0 occurrences (grep exécuté) |
| §R7 — Imports absolus `__init__` | N/A | Aucun `__init__.py` modifié |
| §R7 — Registration manuelle tests | `grep 'register_model\|register_feature'` sur TEST | 0 occurrences (grep exécuté) |
| §R6 — Mutable defaults | `grep 'def.*=[]\|def.*={}'` sur CHANGED | 0 occurrences (grep exécuté) |
| §R6 — open() sans context manager | `grep '.read_text\|open('` sur SRC | 3 matches : `data_loader.py` L56/108/148 — tous `Path.read_text()`, pas de `open()` nu |
| §R6 — Bool identity | `grep 'is np.bool_\|is True\|is False'` sur CHANGED | 0 occurrences (grep exécuté) |
| §R6 — isfinite | `grep 'isfinite'` sur SRC | 0 occurrences (N/A — pas de paramètres numériques validés) |
| §R6 — Dict collision | `grep '[…] = '` sur SRC | Faux positifs uniquement (déclarations de variables) |
| §R9 — for range | `grep 'for .* in range'` sur SRC | 0 occurrences (grep exécuté) |
| §R9 — np comprehension | `grep 'np\.[a-z]*(.*for'` sur SRC | 0 occurrences (grep exécuté) |
| §R7 — Fixtures dupliquées | `grep 'load_config.*configs/'` sur TEST | 0 occurrences (grep exécuté) |
| §R6 — `.get()` résiduel | `grep '\.get('` sur `data_loader.py` | 1 match L207 : `strategy.get("name") == "dummy"` — **acceptable** (voir B2 analyse) |

### B2. Annotations par fichier

#### `scripts/dashboard/data_loader.py` (212 lignes)

- **L76-81** (ajout FIX) `if not isinstance(data["strategy"], dict): raise ValueError(...)` : Correction W-2 correctement implémentée. Placée après la validation des clés requises (strategy est garantie présente à ce point). Le message d'erreur est informatif.
  Sévérité : RAS

- **L205** `strategy = data["strategy"]` : Correction W-1 correctement implémentée. L'accès direct est sûr car `load_run_metrics()` a validé que la clé `"strategy"` existe et est un `dict`.
  Sévérité : RAS

- **L207** `if strategy.get("name") == "dummy":` : `.get("name")` sans default retourne `None` si la clé est absente. Ceci est **acceptable** car : (1) `load_run_metrics` valide que `strategy` est un `dict` mais ne valide PAS les sous-clés (seul `compare_runs.py` vérifie `REQUIRED_STRATEGY_KEYS`), (2) la sémantique est correcte : `None != "dummy"` → le run est conservé, (3) un accès direct `strategy["name"]` provoquerait un `KeyError` sur un run valide sans sous-clé `name`.
  Sévérité : RAS

- Reste du fichier (L1-159, L170-212) : RAS après lecture complète du diff (212 lignes). Validation stricte avec `raise`, encoding explicite, chaîne `from exc` sur toutes les exceptions re-levées.

#### `scripts/compare_runs.py` (diff : 14 insertions, 10 suppressions)

- **L25-29** : `_PROJECT_ROOT` + `sys.path.insert(0, ...)` — pattern standard pour scripts standalone. RAS.

- **L30** : `from scripts.dashboard.data_loader import REQUIRED_STRATEGY_KEYS, REQUIRED_TOP_KEYS  # noqa: E402` — DRY correctement implémenté. Le `noqa: E402` est justifié (import après `sys.path.insert`).

- **L84, L95** : `REQUIRED_TOP_KEYS` et `REQUIRED_STRATEGY_KEYS` remplacent les anciennes constantes locales `_REQUIRED_TOP_KEYS` et `_REQUIRED_STRATEGY_KEYS`. Valeurs identiques (`frozenset`). La logique de validation est inchangée.

- RAS après lecture complète du diff (24 lignes modifiées).

#### `tests/test_dashboard_data_loader.py` (470 lignes)

- **Nouveaux tests (FIX)** :
  - `test_strategy_not_dict_raises` (L296-306) : vérifie que `load_run_metrics` lève `ValueError` quand `strategy` est une string. Match sur `'strategy' must be a JSON object`. ✅ Couvre W-2.
  - `test_non_dict_strategy_excluded_and_logged` (L222-236) : vérifie que `discover_runs` exclut et logue un run avec strategy non-dict. ✅ Couvre W-2 au niveau discover.

- **Test DRY corrigé** `test_no_duplicate_required_keys_constant` (L433-470) : walk AST vérifiant que ni `REQUIRED_TOP_KEYS` ni `REQUIRED_STRATEGY_KEYS` ne sont assignées dans `compare_runs.py`. Vérifie les `ast.Assign` → `ast.Name.id`. ✅ Couvre M-1.

- **Docstrings** : toutes les méthodes de test contiennent `#074` dans leur docstring. ✅

- **Portabilité** : tous les répertoires temporaires utilisent `tmp_path`. Aucun chemin hardcodé. ✅

- **Déterminisme** : pas d'aléatoire. Données synthétiques fixes. ✅

- RAS après lecture complète (470 lignes).

#### `docs/tasks/MD-1/074__wsd1_data_loader_discovery.md`

- Statut DONE, critères cochés (9/9), checklist cohérente (9/10, PR non cochée). RAS.

### B3. Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_dashboard_data_loader.py`, `#074` dans docstrings |
| Couverture des critères | ✅ | 9/9 critères mappés (voir Phase A) |
| Cas nominaux + erreurs + bords | ✅ | Nominaux : runs valides, multiples. Erreurs : JSON cassé, clés manquantes, YAML cassé, fichier absent, type invalide. Bords : répertoire vide, entrées non-directory, strategy non-dict |
| Boundary fuzzing | ✅ ou N/A | Pas de paramètres numériques. Bords couverts : 0 runs, 1 run, 2 runs, string au lieu de dict |
| Tests désactivés | ✅ | Aucun `@pytest.mark.skip` ou `xfail` |
| Déterministes | ✅ | Pas d'aléatoire, données synthétiques fixes |
| Données synthétiques | ✅ | Helpers `_make_metrics_dict`, `_write_run` — pas de réseau |
| Portabilité chemins | ✅ | `tmp_path` partout, 0 `/tmp` hardcodé (grep B1) |
| Tests registre réalistes | N/A | Pas de registre concerné |
| Contrat ABC complet | N/A | Pas d'ABC concerné |

### B4. Code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 — Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback. Lecture B2 : L207 `.get("name")` analysé et accepté (pas un fallback, accès safe sur clé optionnelle) |
| §R10 — Defensive indexing | ✅ | Pas d'indexation numérique dans le code. Accès par clé dict uniquement, après validation |
| §R2 — Config-driven | ✅ ou N/A | Module utilitaire, pas de paramètre modifiable à externaliser |
| §R3 — Anti-fuite | ✅ ou N/A | Pas de données temporelles ni de split |
| §R4 — Reproductibilité | ✅ | Scan B1 : 0 legacy random API |
| §R5 — Float conventions | N/A | Pas de tenseurs ni de métriques numériques |
| §R6 — Anti-patterns Python | ✅ | Scan B1 : 0 mutable default, 0 `open()` nu (utilise `Path.read_text()`), 0 bool identity. Données désérialisées validées en type (`isinstance`) avant usage |

### B5. Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `load_run_metrics`, `discover_runs`, `REQUIRED_TOP_KEYS` (constante uppercase) |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO/FIXME |
| Imports propres / relatifs | ✅ | Imports standard (json, logging, Path, yaml). `noqa: E402` justifié dans compare_runs.py |
| DRY | ✅ | Constantes `REQUIRED_TOP_KEYS`, `REQUIRED_STRATEGY_KEYS` définies une seule fois dans `data_loader.py`, importées par `compare_runs.py`. Tests AST vérifient l'absence de re-définition |
| .gitignore | ✅ | Pas de fichiers générés dans la PR |

### B5-bis. Bonnes pratiques métier

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts | N/A | Module I/O, pas de calcul financier |
| Nommage métier | ✅ | `metrics`, `manifest`, `strategy`, `run` — termes cohérents avec le pipeline |
| Séparation des responsabilités | ✅ | data_loader = chargement/validation, compare_runs = comparaison |
| Invariants de domaine | N/A | Pas de calcul financier |
| Cohérence unités/échelles | N/A | Pas de valeurs numériques manipulées |
| Patterns calcul financier | N/A | Module I/O uniquement |

### B6. Conformité spec

| Critère | Verdict |
|---|---|
| Spec dashboard §4.1, §4.2, §4.3 | ✅ — découverte par scan `metrics.json`, exclusion dummy, dégradation contrôlée (logging + skip) |
| Plan WS-D-1.2 | ✅ — fonctions de chargement et validation conformes au plan |
| Formules doc vs code | N/A — pas de formule mathématique |

### B7. Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `load_run_metrics(Path) -> dict`, `discover_runs(Path) -> list[dict]` — cohérents avec le contrat attendu |
| Clés de configuration | N/A | Pas de lecture de config YAML du pipeline |
| Registres | N/A | Pas de registre |
| Imports croisés | ✅ | `compare_runs.py` importe `REQUIRED_STRATEGY_KEYS, REQUIRED_TOP_KEYS` depuis `data_loader.py` — symboles vérifiés existants |
| Forwarding kwargs | N/A | Pas de pattern wrapper |
| Structures partagées | ✅ | `REQUIRED_TOP_KEYS` et `REQUIRED_STRATEGY_KEYS` partagés correctement (DRY) |

---

## Remarques mineures

Aucune.

## Remarques et blocages

Aucun.

## Actions requises

Aucune.

---

```
RÉSULTAT PARTIE B :
- Verdict : CLEAN
- Bloquants : 0
- Warnings : 0
- Mineurs : 0
- Rapport : docs/tasks/MD-1/074/review_v2.md
```
