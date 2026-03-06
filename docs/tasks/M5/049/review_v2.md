# Revue PR — [WS-12] #049 — Orchestrateur de run (runner)

Branche : `task/049-runner`
Tâche : `docs/tasks/M5/049__ws12_runner.md`
Date : 2026-03-03
Itération : v2 (suite au FIX `c341ebd` adressant les 1W + 8M de la review_v1)

## Verdict global : ✅ CLEAN

## Résumé

Toutes les remarques de la review v1 (1 WARNING + 8 MINEURS) ont été correctement adressées par le commit FIX `c341ebd`. Le test de causalité utilise désormais la baseline SMA (data-dépendante et causale) avec comparaison stricte des métriques du premier fold. Les duplications DRY sont éliminées (import `PREDICTION_METRICS`, délégation complète à `calibrate_threshold`). Les imports sont au module level, la vectorisation `reindex` remplace la boucle Python, les tests edge-case 0/1 fold sont ajoutés. 1421 tests passent, ruff clean. Aucun nouvel item identifié.

---

## Phase A — Compliance

### Structure branche & commits
| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/049-runner` | ✅ | `git branch` → `task/049-runner` |
| Commit RED présent | ✅ | `147093f` — `[WS-12] #049 RED: tests orchestrateur runner (30 tests)` |
| Commit GREEN présent | ✅ | `ffd932a` — `[WS-12] #049 GREEN: orchestrateur runner — pipeline end-to-end` |
| Commit FIX post-review | ✅ | `c341ebd` — `[WS-12] #049 FIX: review_v1 — 1W + 8M (causality test, DRY, imports, vectorize, edge cases)` |
| Commit RED = tests uniquement | ✅ | `git show --stat 147093f` : 1 fichier `tests/test_runner.py` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat ffd932a` : `ai_trading/pipeline/runner.py`, `docs/tasks/M5/049__ws12_runner.md`, `tests/test_runner.py` |
| Commit FIX = source + tests | ✅ | `git show --stat c341ebd` : `ai_trading/metrics/aggregation.py`, `ai_trading/pipeline/runner.py`, `tests/test_aggregation.py`, `tests/test_runner.py` |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1..HEAD` : 3 commits (RED + GREEN + FIX) |

### Tâche
| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` dans le fichier de tâche |
| Critères d'acceptation cochés | ✅ (13/13) | Tous `[x]` |
| Checklist cochée | ⚠️ (8/9) | `[ ] Pull Request ouverte` — normal, PR pas encore ouverte |

### Vérification critères d'acceptation vs code (v2)

| AC | Preuve code/test |
|---|---|
| Module importable | `TestModuleImport` (3 tests) — runner.py L1 importable, exports `run_pipeline`, `VALID_STRATEGIES`, `STRATEGY_FRAMEWORK_MAP` |
| Run DummyModel → arborescence + JSON + métriques | `TestFullRunDummy` (9 tests) — vérifie run_dir, config_snapshot, manifest, metrics, fold dirs, pipeline.log, preds, equity, model |
| Run no_trade → bypass θ, pnl=0, n_trades=0 | `TestFullRunNoTrade` (3 tests) — vérifie completion, `n_trades==0`, `net_pnl≈0`, `method=="none"`, `theta==None` |
| §14.4 warnings | `TestAcceptanceWarnings.test_warnings_emitted` — caplog vérifie `net_pnl_mean` dans les WARNING |
| Bypass θ loggé INFO | `TestThetaBypassInfoLog.test_theta_bypass_logged_info` — caplog vérifie msg "bypass" au level INFO |
| STRATEGY_FRAMEWORK_MAP dérivation | `TestStrategyFrameworkMap` (4 tests) — vérifie toutes les stratégies MVP |
| config_snapshot.yaml inconditionnel | `TestConditionalArtifactsFalse.test_unconditional_artifacts_always_present` + `create_run_dir()` L73 |
| Validation JSON Schema | `TestJsonSchemaValidation` (2 tests) + runner L672-678 |
| Artefacts conditionnels save_* | `TestConditionalArtifactsFalse` (3 tests) + `TestFullRunDummy` (9 tests avec flags=true) |
| Test causalité | `TestCausality.test_causality_sma_baseline` — SMA baseline data-dépendante, perturbation 200 dernières barres, comparaison first-fold `pytest.approx(abs=1e-12)` |
| Tests nominaux + erreurs + bords | `TestErrorPaths` (2 tests) + `TestEdgeCaseFolds` (2 tests) + classes nominales |
| Suite verte | ✅ 1421 passed |
| ruff clean | ✅ |

### CI
| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1421 passed**, 0 failed (11.97s) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

Fichiers analysés :
- **Source** : `ai_trading/pipeline/runner.py`, `ai_trading/metrics/aggregation.py`
- **Tests** : `tests/test_runner.py`, `tests/test_aggregation.py`

| # | Pattern recherché | Règle | Résultat | Classification |
|---|---|---|---|---|
| 1 | Fallbacks silencieux (`or []`, `if...else`) | §R1 | 3 matches runner.py (L465, L469, L506) | Faux positifs — sanitisation JSON `inf→null` (L465), normalisation schema `fallback_no_trade→none` (L469), join notes vide (L506). Aucun fallback réel. |
| 2 | Except trop large | §R1 | 0 occurrences (grep exécuté) | ✅ |
| 3 | Print résiduel | §R7 | 0 occurrences (grep exécuté) | ✅ |
| 4 | Shift négatif | §R3 | 0 occurrences (grep exécuté) | ✅ |
| 5 | Legacy random API | §R4 | 0 occurrences (grep exécuté) | ✅ |
| 6 | TODO/FIXME | §R7 | 0 occurrences (grep exécuté) | ✅ |
| 7 | Chemins hardcodés tests | §R7 | 0 occurrences (grep exécuté) | ✅ |
| 8 | Imports absolus `__init__.py` | §R7 | 0 occurrences dans `pipeline/__init__.py` et `metrics/__init__.py` (grep exécuté) | ✅ |
| 9 | Registration manuelle tests | §R7 | 0 occurrences (grep exécuté) | ✅ |
| 10 | Mutable default arguments | §R6 | 0 occurrences (grep exécuté) | ✅ |
| 11 | open() sans context manager | §R6 | L107 `with open(path, "rb")`, L672/L676 `.read_text()` | ✅ — `with` utilisé, `.read_text()` acceptable |
| 12 | `is True`/`is False` | §R6 | 1 match `test_aggregation.py:365` — **pré-existant**, non modifié par cette branche | ✅ (hors scope) |
| 13 | `isfinite` check | §R6 | L465 `np.isfinite(raw_theta)`, aggregation L257 `math.isfinite(mdd_cap)` | ✅ — présents aux bonnes frontières |
| 14 | `for in range` (vectorisation) | §R9 | L582 — itère sur metadata par fold pour construire artefact paths | Faux positif — pas un hot path, itération sur métadonnées |
| 15 | np vectorisable compréhension | §R9 | 0 occurrences (grep exécuté) | ✅ |
| 16 | `noqa` | §R7 | runner.py L21-23 (F401 imports side-effect baselines/features/models) ; test_aggregation.py L365 (E712 pré-existant) | ✅ — F401 justifiés pour enregistrement registres |
| 17 | `per-file-ignores` | §R7 | Aucune entrée pour runner/test_runner dans pyproject.toml | ✅ |
| 18 | Fixture duplication | §R7 | 0 occurrences `load_config.*configs/` dans tests (grep exécuté) | ✅ |
| 19 | Dict collision silencieuse | §R6 | Matches analysés : L288-291 (initialisations lists), L519-527 (boucle aggregate — clés uniques car suffixes `_mean`/`_std` et `base` dans `PREDICTION_METRICS` exclusif), L584-606 (clés littérales constantes) | ✅ — aucune collision possible |

### B2. Annotations par fichier

#### `ai_trading/pipeline/runner.py` (697 lignes)

**Vérification des corrections v1 :**

| v1 # | Sévérité v1 | Correction | Preuve |
|---|---|---|---|
| 1 (WARNING) | Causalité faible | ✅ Réécrit | Test `TestCausality.test_causality_sma_baseline` utilise SMA baseline + comparaison `pytest.approx` des metrics fold 0 |
| 2 (MINEUR) | DRY bypass θ | ✅ Éliminé | Runner appelle `calibrate_threshold(output_type=output_type)` à L368-380 — plus de dict bypass local |
| 3 (MINEUR) | DRY métriques prédiction | ✅ Éliminé | `PREDICTION_METRICS` importé de `aggregation.py` (L50), utilisé L518/L524 |
| 4 (MINEUR) | Import lazy `run_qa_checks` | ✅ Module level | Import L45 `from ai_trading.data.qa import run_qa_checks` |
| 5 (MINEUR) | Import lazy features | ✅ Module level | Import L22 `import ai_trading.features  # noqa: F401` |
| 6 (MINEUR) | `.get("quantile")` | ✅ Accès direct | L472 `cal_result["quantile"]` |
| 7 (MINEUR) | Boucle vectorisable | ✅ Vectorisé | L403-406 `signals_series.reindex(ohlcv_test.index, fill_value=0)` |
| 8 (MINEUR) | Tests 0/1 fold | ✅ Ajoutés | `TestEdgeCaseFolds.test_single_fold` + `test_zero_folds_raises` |
| 9 (MINEUR) | `if strategy_name == "dummy"` | Accepté v1 | L322-325: toujours présent, commenté. DummyModel est le seul modèle MVP avec signature `seed=`. Accepté comme limitation MVP en v1. |

**Lecture diff complète v2 — observations :**

- **L1-68** : Imports module-level complets et ordonnés (stdlib → third-party → local). Tous les imports nécessaires sont présents. RAS.
- **L80-165** : Helpers `_load_raw_ohlcv`, `_sha256_file`, `_prepare_ohlcv_indexed`, `_setup_file_logging`, `_timeframe_to_hours`, `_write_predictions_csv`. Fonctions utilitaires propres, `with open` pour I/O, types de retour documentés. RAS.
- **L175-200** : Entrée `run_pipeline` — vérification registre, seed, chargement données. Validation explicite (`FileNotFoundError`, `ValueError`). RAS.
- **L220-270** : Features → labels → valid_mask → warmup → samples → splits. Chaîne complète. Embargo appliqué via `apply_purge`. RAS.
- **L275-280** : Création `run_dir` + file logging. `create_run_dir` crée les dossiers. RAS.
- **L286-295** : Initialisation listes de collecte. Pas de mutable defaults (variables locales). RAS.
- **L297-346** : Boucle per-fold : extraction données, meta dicts, instanciation, trainer. RAS.
- **L348-380** : θ calibration via `calibrate_threshold(output_type=output_type)`. Log INFO pour bypass signal. Délégation complète, pas de duplication. RAS.
- **L382-410** : Signal application + backtest. `signals_series.reindex` vectorisé. `execute_trades` + `apply_cost_model` + `build_equity_curve`. RAS.
- **L412-442** : Artefacts conditionnels. Flags `save_predictions`, `save_equity_curve`, `save_model` respectés. Cleanup model_artifacts si `save_model=False`. RAS.
- **L444-500** : Métriques par fold. `y_test.astype(np.float64)` pour précision. θ sanitisé avec `np.isfinite`. Normalisation `fallback_no_trade→none`. Accès direct `cal_result["quantile"]`. RAS.
- **L502-535** : Agrégation inter-fold. Import `PREDICTION_METRICS` pour split pred/trading. `check_acceptance_criteria` pour §14.4. RAS.
- **L556-680** : Manifest, metrics, equity stitch, JSON validation, cleanup logging. RAS.
- **L688-697** : `_get_python_version()` et `_get_platform()` avec `import sys`/`import platform` lazy — stdlib modules dans helpers privés appelés une seule fois. Différent du v1 issue (imports domaine dans `run_pipeline`). Acceptable. RAS.

#### `ai_trading/metrics/aggregation.py` (diff : rename + edge case)

- **L37** : `_PREDICTION_METRICS` → `PREDICTION_METRICS` (public). Utilisé par `runner.py` et `_AGGREGATED_METRICS`. Pas d'autre référence à l'ancien nom dans le code source. RAS.
- **L102-107** : Edge case single fold : `if len(arr) < 2: result["_std"] = 0.0`. Correct — `np.std(arr, ddof=1)` avec `n=1` est une division par zéro. Retourner 0.0 est mathématiquement défendable (variance d'un singleton = 0) et évite un RuntimeWarning numpy. RAS.

#### `tests/test_runner.py` (792 lignes)

- **L36-173** : Helpers et config synthétique. Données reproductibles (`seed=42`), chemins via `tmp_path`, config complète. RAS.
- **L180-203** : `TestModuleImport` — 3 tests d'importabilité. RAS.
- **L211-247** : `TestStrategyFrameworkMap` — 4 tests couvrant dummy, baselines, modèles pytorch/xgboost. RAS.
- **L255-356** : `TestFullRunDummy` — 9 tests vérifiant l'arborescence complète, JSON valides, artefacts conditionnels. RAS.
- **L364-407** : `TestFullRunNoTrade` — 3 tests pour bypass θ, `n_trades=0`, `net_pnl≈0`. RAS.
- **L415-442** : `TestThetaBypassInfoLog` — caplog INFO, filtre "bypass". RAS.
- **L450-476** : `TestAcceptanceWarnings` — caplog WARNING, filtre "net_pnl_mean". RAS.
- **L484-543** : `TestConditionalArtifactsFalse` — 3 tests avec flags=false + unconditional artifacts. RAS.
- **L551-583** : `TestJsonSchemaValidation` — 2 tests. RAS.
- **L591-633** : `TestErrorPaths` — missing data + registry inconsistency. Cleanup via `try/finally`. RAS.
- **L641-700** : `TestCausality.test_causality_sma_baseline` — **V2 : corrigé**. Utilise SMA baseline (data-dépendante, causale). Deux runs indépendants (`run1/run2`). Perturbation des 200 dernières barres close. Comparaison first fold trading metrics (`n_trades`, `net_pnl`, `net_return`, `max_drawdown`) avec `pytest.approx(abs=1e-12)`. Le premier fold test se termine bien avant la zone perturbée (≈position 2028 vs perturbation à 2800). Test robuste. RAS.
- **L708-742** : `TestEdgeCaseFolds` — **V2 : ajouté**. `test_single_fold` (2200 barres → 1 fold exactement), `test_zero_folds_raises` (500 barres → 0 folds → ValueError/IndexError). RAS.
- **L750-792** : `TestFullRunBuyHold` — buy_hold baseline, `n_trades=1`, `method="none"`. RAS.

#### `tests/test_aggregation.py` (diff : adaptation single fold)

- **L212-222** : `test_single_fold` — supprime `warnings.catch_warnings`, asserte `net_pnl_std == approx(0.0)` au lieu de `isnan`. Cohérent avec le changement aggregation. RAS.
- **L224-237** : `test_single_non_none_among_nones` — idem, `sharpe_std == approx(0.0)`. RAS.

### B3. Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_runner.py`, docstrings `#049` |
| Couverture des critères AC | ✅ | 13/13 AC couverts (causality test corrigé avec SMA) |
| Cas nominaux + erreurs + bords | ✅ | Nominaux: DummyModel, NoTrade, BuyHold. Erreurs: missing data, registry. Bords: 1 fold, 0 folds |
| Pas de test désactivé | ✅ | 0 `@pytest.mark.skip` ou `xfail` |
| Déterministes | ✅ | Seed fixé `_SEED = 42`, `rng = np.random.default_rng(seed)` |
| Données synthétiques | ✅ | `_build_ohlcv_df` en mémoire, pas de dépendance réseau |
| Portabilité chemins | ✅ | Tous via `tmp_path` (scan B1 : 0 `/tmp`) |
| Tests registre réalistes | N/A | Pas de test de registre via décorateur |
| Contrat ABC complet | N/A | Runner n'est pas un ABC |

### B4. Code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 #1-2 : 3 matches analysés = faux positifs (sanitisation JSON, normalisation schema, notes vides). 0 `except` large. Validation explicite `FileNotFoundError`, `ValueError`. |
| §R10 Defensive indexing | ✅ | Indices via `fold.train_indices` etc. (produits par splitter validé). `signals_full` via `reindex(fill_value=0)` — safe. Pas de risque d'indexation négative. |
| §R2 Config-driven | ✅ | Tous les paramètres lus depuis `config.*`. `STRATEGY_FRAMEWORK_MAP` est un mapping interne dérivé (spec + tâche). Aucune constante magique. |
| §R3 Anti-fuite | ✅ | Scan B1 #4 : 0 `.shift(-`. Scaler fit sur train (via `FoldTrainer`). θ calibré sur val (L368-380). Features backward-looking. Splits via `WalkForwardSplitter` + `apply_purge` avec embargo. |
| §R4 Reproductibilité | ✅ | Scan B1 #5 : 0 legacy random. `set_global_seed()` L196-200. SHA-256 parquet dans manifest. |
| §R5 Float conventions | ✅ | `X_seq`/`y` float32 (via `build_samples`). Métriques float64 (`y_test.astype(np.float64)` L446-447). |
| §R6 Anti-patterns | ✅ | Scan B1 : 0 mutable defaults, 0 `is True/False` dans code modifié, open avec `with`, `.read_text()`, `np.isfinite` avant bornes. |

### B5. Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Conformité complète |
| Pas de code mort/debug | ✅ | Scan B1 #3/#6 : 0 `print()`, 0 `TODO/FIXME` |
| Imports propres | ✅ | Module level, ordonnés, no `import *`. `noqa: F401` justifiés (side-effect registres) |
| DRY | ✅ | `PREDICTION_METRICS` importé (plus de hardcoding), θ bypass délégué à `calibrate_threshold` |
| `__init__.py` à jour | ✅ | `metrics/__init__.py` importe `aggregation` (relatif). `pipeline/__init__.py` propre. |
| Portabilité chemins tests | ✅ | `tmp_path` partout, scan B1 #7 : 0 `/tmp` |
| Fixtures partagées | ✅ | Config construite localement par `_make_config_dict` (approprié pour tests d'intégration runner) |

### B5-bis. Bonnes pratiques métier

| Critère | Verdict | Preuve |
|---|---|---|
| Exactitude concepts financiers | ✅ | Pipeline conforme au dataflow spec §3.1 |
| Nommage métier | ✅ | `equity_curve`, `trades`, `signals`, `y_hat`, `theta` — standard |
| Séparation responsabilités | ✅ | Runner orchestre uniquement — délègue aux modules spécialisés |
| §R9 Vectorisation | ✅ | `signals_series.reindex()` (corrigé v1). `for k in range(n_folds)` L582 : itération metadata, pas hot path. |

### B6. Conformité spec v1.0

| Critère | Verdict | Preuve |
|---|---|---|
| Spécification §3.1 dataflow | ✅ | Pipeline : Ingestion → QA → Features → Samples → Split → Scale/Fit/Predict → θ → Backtest → Metrics → Aggregate → Artefacts |
| §14.4 critères d'acceptation | ✅ | `check_acceptance_criteria()` émet warnings pour net_pnl ≤ 0, profit_factor ≤ 1.0, MDD ≥ cap |
| §15.1 arborescence canonique | ✅ | `run_dir/manifest.json`, `metrics.json`, `config_snapshot.yaml`, `folds/fold_XX/` |
| θ bypass pour signal | ✅ | L353-355 log INFO + délégation `calibrate_threshold(output_type=output_type)` |
| Plan WS-12.2 | ✅ | Tous les points du plan implémentés |
| Formules doc vs code | ✅ | Pas de formules mathématiques dans le runner (délègue aux modules) |

### B7. Cohérence intermodule

| Critère | Verdict | Preuve |
|---|---|---|
| Signatures et types de retour | ✅ | `FoldTrainer.train_fold()`, `calibrate_threshold()`, `compute_prediction_metrics()`, `compute_trading_metrics()`, `aggregate_fold_metrics()` — tous les appels cohérents avec signatures existantes |
| `PREDICTION_METRICS` | ✅ | Défini dans `aggregation.py` L37, importé dans `runner.py` L50, utilisé L518/L524 |
| `VALID_STRATEGIES` / `STRATEGY_FRAMEWORK_MAP` | ✅ | Mêmes 10 clés. `STRATEGY_FRAMEWORK_MAP` importé de `manifest.py`. |
| Forwarding kwargs | ✅ | `ohlcv`, `meta_train/val/test` transmis au trainer → modèle. `output_type` transmis à `calibrate_threshold`. |
| Clés configuration | ✅ | Toutes lues via `config.*` — correspondent au modèle Pydantic |
| Rename `PREDICTION_METRICS` | ✅ | Aucune référence résiduelle à `_PREDICTION_METRICS` dans le code source |
| Cohérence `aggregate_fold_metrics` single-fold | ✅ | Retourne `std=0.0` pour 1 fold. Tests `test_aggregation.py` adaptés. |

---

## Suivi des items v1

| v1 # | Sévérité | Description | Statut v2 |
|---|---|---|---|
| 1 | WARNING | Test causalité faible (DummyModel data-indépendant) | ✅ Corrigé — SMA baseline + assertions quantitatives |
| 2 | MINEUR | DRY — dict bypass θ dupliqué | ✅ Corrigé — délégation `calibrate_threshold(output_type=)` |
| 3 | MINEUR | DRY — noms métriques prédiction hardcodés | ✅ Corrigé — import `PREDICTION_METRICS` |
| 4 | MINEUR | Import lazy `run_qa_checks` | ✅ Corrigé — module level L45 |
| 5 | MINEUR | Import lazy `ai_trading.features` | ✅ Corrigé — module level L22 |
| 6 | MINEUR | `.get("quantile")` inconsistant | ✅ Corrigé — accès direct `["quantile"]` L472 |
| 7 | MINEUR | Boucle Python vectorisable (alignement signaux) | ✅ Corrigé — `reindex` L403-406 |
| 8 | MINEUR | Pas de test 0/1 fold | ✅ Corrigé — `TestEdgeCaseFolds` (2 tests) |
| 9 | MINEUR | `if strategy_name == "dummy"` hardcodé | Accepté MVP — seul modèle test avec signature `seed=`, commenté L320-321 |

---

## Liste des items v2

Aucun item identifié.

---

## Résumé

```
RÉSULTAT PARTIE B :
- Verdict : CLEAN
- Bloquants : 0
- Warnings : 0
- Mineurs : 0
- Rapport : docs/tasks/M5/049/review_v2.md
```
