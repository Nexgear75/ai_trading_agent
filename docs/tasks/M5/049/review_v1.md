# Revue PR — [WS-12] #049 — Orchestrateur de run (runner)

Branche : `task/049-runner`
Tâche : `docs/tasks/M5/049__ws12_runner.md`
Date : 2026-03-03
Itération : v1

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

L'orchestrateur pipeline (`ai_trading/pipeline/runner.py`, 707 lignes) est fonctionnellement complet et bien structuré. Le pipeline end-to-end s'exécute avec succès pour DummyModel, NoTradeBaseline et BuyHoldBaseline. Les 1419 tests passent, ruff est clean. Les principaux problèmes identifiés sont : (1) duplication DRY du dict bypass θ et des noms de métriques prédiction, (2) test de causalité faible qui ne valide pas réellement l'absence de fuite, (3) boucle Python vectorisable pour l'alignement signaux/OHLCV, (4) `.get()` inconsistant au lieu d'un accès direct au dict, (5) imports lazy non justifiés.

---

## Phase A — Compliance

### Structure branche & commits
| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/049-runner` | ✅ | `git branch --show-current` → `task/049-runner` |
| Commit RED présent | ✅ | `147093f` — `[WS-12] #049 RED: tests orchestrateur runner (30 tests)` |
| Commit GREEN présent | ✅ | `ffd932a` — `[WS-12] #049 GREEN: orchestrateur runner — pipeline end-to-end` |
| Commit RED = tests uniquement | ✅ | `git show --stat 147093f` : 1 fichier `tests/test_runner.py` (753 insertions) |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat ffd932a` : `ai_trading/pipeline/runner.py` (707+), `docs/tasks/M5/049__ws12_runner.md` (44 mod), `tests/test_runner.py` (3 del) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1..HEAD` : 2 commits exactement (RED + GREEN) |

### Tâche
| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` dans le fichier de tâche |
| Critères d'acceptation cochés | ✅ (13/13) | Tous les critères `[x]` dans le fichier |
| Checklist cochée | ⚠️ (8/9) | La case « Pull Request ouverte » n'est pas cochée `[ ]` — normal, PR pas encore ouverte |

### Vérification critères d'acceptation vs code

| AC | Preuve code/test |
|---|---|
| Module importable | `TestModuleImport` (3 tests) |
| Run DummyModel → arborescence + JSON + métriques | `TestFullRunDummy` (9 tests) |
| Run no_trade → bypass θ, pnl=0, n_trades=0 | `TestFullRunNoTrade` (3 tests) |
| §14.4 warnings | `TestAcceptanceWarnings.test_warnings_emitted` |
| Bypass θ loggé INFO | `TestThetaBypassInfoLog.test_theta_bypass_logged_info` |
| STRATEGY_FRAMEWORK_MAP dérivation | `TestStrategyFrameworkMap` (4 tests) |
| config_snapshot.yaml inconditionnel | `TestConditionalArtifactsFalse.test_unconditional_artifacts_always_present` + `create_run_dir()` appelle `save_config_snapshot()` |
| Validation JSON Schema | `TestJsonSchemaValidation` (2 tests) + runner L682-688 |
| Artefacts conditionnels save_* | `TestConditionalArtifactsFalse` (3 tests) + `TestFullRunDummy` (tests save=true) |
| Test causalité | `TestCausality.test_causality_dummy_model` — **FAIBLE** (voir B2) |
| Tests nominaux + erreurs + bords | `TestErrorPaths` (2 tests) + classes nominales |
| Suite verte | ✅ 1419 passed |
| ruff clean | ✅ |

### CI
| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1419 passed**, 0 failed (11.96s) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

| Pattern recherché | Commande | Résultat | Classification |
|---|---|---|---|
| §R1 Fallbacks silencieux | `grep -n ' or \[\]\| or {}...' runner.py` | 3 matches (L471, L475, L512) | Faux positifs — sanitisation JSON (inf→null), normalisation méthode schema, formatage notes. Aucun fallback réel. |
| §R1 Except trop large | `grep -n 'except:$\|except Exception:' runner.py` | 0 occurrences | ✅ |
| §R7 Print résiduel | `grep -n 'print(' runner.py` | 0 occurrences | ✅ |
| §R3 Shift négatif | `grep -n '\.shift(-' runner.py` | 0 occurrences | ✅ |
| §R4 Legacy random API | `grep -rn 'np.random.seed...' runner.py test_runner.py` | 0 occurrences | ✅ |
| §R7 TODO/FIXME | `grep -rn 'TODO\|FIXME...'` | 0 occurrences | ✅ |
| §R7 Chemins hardcodés tests | `grep -rn '/tmp\|C:\\' test_runner.py` | 0 occurrences | ✅ |
| §R7 Imports absolus `__init__.py` | `grep -rn 'from ai_trading\.' pipeline/__init__.py` | 0 occurrences | ✅ |
| §R7 Registration manuelle tests | `grep -rn 'register_model' test_runner.py` | 0 occurrences | ✅ |
| §R6 Mutable defaults | `grep -rn 'def .*=\[\]\|def .*={}' runner.py test_runner.py` | 0 occurrences | ✅ |
| §R6 open() sans context manager | `grep -rn 'open\|.read_text' runner.py` | L104 (`with open`), L682/L686 (`.read_text()`) | ✅ — `with` utilisé, `.read_text()` acceptable |
| §R6 is True/is False | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences | ✅ |
| §R6 isfinite check | `grep 'isfinite' runner.py` | L471 (`np.isfinite`) | ✅ — θ sanitisé correctement |
| §R9 for in range | `grep 'for .* in range' runner.py` | L592 (métadonnées artefacts) | Faux positif — pas un hot path, itère sur métadonnées par fold |
| §R6 np vectorisable | `grep 'np\.[a-z]*(.*for .* in ' runner.py` | 0 occurrences | ✅ |
| §R7 noqa | `grep 'noqa' runner.py test_runner.py` | L21, L22, L220 — F401 imports side-effect | ✅ — justifiés (registration baselines, models, features) |
| §R7 per-file-ignores | `grep pyproject.toml` | Aucune entrée pour runner/test_runner | ✅ |
| §R7 Fixture duplication | `grep 'load_config.*configs/' test_runner.py` | 0 occurrences | ✅ |

### B2. Annotations par fichier

#### `ai_trading/pipeline/runner.py` (707 lignes)

- **L206** `from ai_trading.data.qa import run_qa_checks` — import lazy à l'intérieur de `run_pipeline()` au lieu du module level. Aucune justification (pas de circular import, pas de lazy loading nécessaire).
  Sévérité : **MINEUR**
  Suggestion : Déplacer l'import au niveau module, avec les autres imports `from ai_trading.data.*`.

- **L220** `import ai_trading.features  # noqa: F401` — import side-effect pour enregistrement features, placé à l'intérieur de `run_pipeline()`. Justifié pour garantir l'enregistrement avant `compute_features`, mais pourrait être au module level comme les L21-22.
  Sévérité : **MINEUR**
  Suggestion : Déplacer au module level à côté de `import ai_trading.baselines` et `import ai_trading.models`.

- **L322** `if strategy_name == "dummy": model = model_cls(seed=...)` — logique de branchement hardcodée pour l'instanciation de DummyModel. Si un autre modèle nécessite un `seed`, il faudra ajouter un nouveau `if`. Cela dit, c'est le seul modèle MVP avec cette signature.
  Sévérité : **MINEUR**
  Suggestion : À considérer pour le futur : unifier les signatures d'instanciation, ou utiliser un mécanisme config-driven pour passer le seed. Acceptable en MVP.

- **L355-362** Dict bypass θ (`cal_result = {"theta": None, ...}`) — Duplication exacte du dict retourné par `calibrate_threshold()` en mode signal (L191-198 de `threshold.py`). Si les clés changent dans `calibrate_threshold`, le runner driftera.
  Sévérité : **MINEUR**
  Suggestion : Appeler `calibrate_threshold(output_type="signal")` directement (il gère déjà le bypass) et supprimer le branchement local. L'overhead est négligeable et cela élimine la duplication. Alternativement, extraire le dict bypass en constante partagée.

- **L404-407** `for i, ts in enumerate(ts_test): if ts in ohlcv_test.index: ...` — Boucle Python sur les timestamps test pour aligner les signaux sur l'OHLCV. Vectorisable avec `pd.Series.reindex()` ou `np.searchsorted()`.
  Sévérité : **MINEUR**
  Suggestion : `signals_series = pd.Series(signals_test, index=ts_test); signals_full = signals_series.reindex(ohlcv_test.index, fill_value=0).values.astype(np.int32)`.

- **L481** `cal_result.get("quantile")` — Utilise `.get()` (soft access) alors que le dict a toujours la clé `"quantile"` (définie explicitement dans les deux chemins : bypass L357 et `calibrate_threshold` retour). Inconsistant avec L470 (`cal_result["theta"]`) qui utilise l'accès direct.
  Sévérité : **MINEUR**
  Suggestion : Remplacer par `cal_result["quantile"]`.

- **L524-535** Hardcoding des noms de métriques prédiction `("mae", "rmse", "directional_accuracy", "spearman_ic")` — Duplication avec `_PREDICTION_METRICS` dans `ai_trading/metrics/aggregation.py` (L38-42).
  Sévérité : **MINEUR**
  Suggestion : Importer `_PREDICTION_METRICS` depuis `aggregation.py` (en le renommant en `PREDICTION_METRICS` public) et l'utiliser dans la boucle.

- **L578** `framework = STRATEGY_FRAMEWORK_MAP[strategy_name]` — Pas de garde si `strategy_name` n'est pas dans le mapping. Si `VALID_STRATEGIES` et `STRATEGY_FRAMEWORK_MAP` driftent, KeyError. Cependant, `build_manifest()` (L142-145 de manifest.py) fait déjà cette validation avec un message explicite. Le risque est faible car `config.strategy.name` est validé contre `VALID_STRATEGIES` à la construction de la config, et les deux mappings ont actuellement les mêmes clés.
  Sévérité : RAS (risque théorique couvert par `build_manifest` en aval).

#### `tests/test_runner.py` (750 lignes)

- **L674-725** `TestCausality.test_causality_dummy_model` — Le test de causalité utilise DummyModel dont les prédictions sont data-indépendantes (basées uniquement sur le seed rng). Le test ne vérifie PAS réellement que modifier les prix futurs ne change pas les signaux passés. Les assertions finales (L715-721) vérifient uniquement `isinstance(pred[key], float)` — pas d'assertion sur l'identité des signaux. Le commentaire (L711-714) reconnaît explicitement la limitation.
  Sévérité : **WARNING**
  Suggestion : (1) Utiliser SMA baseline au lieu de DummyModel — SMA est data-dépendante mais causale. (2) Modifier les N dernières barres *après* la dernière barre du premier fold test, et vérifier que les métriques du premier fold sont identiques (`pytest.approx`). (3) Ou bien, construire un test unitaire séparé dans `test_feature_pipeline.py` qui valide la causalité des features.

- **L58-74** `_make_config_dict` — Bonne construction synthétique, fenêtres courtes pour performance. Config complète et cohérente.
  Sévérité : RAS

- **L428-473** `TestFullRunNoTrade` — Vérifie correctement le bypass θ (`method="none"`, `theta=None`), `net_pnl=0`, `n_trades=0`.
  Sévérité : RAS

- **L504-530** `TestAcceptanceWarnings` — Utilise `caplog` pour vérifier les warnings §14.4. Vérifie que `net_pnl_mean` apparaît dans les warnings pour `no_trade`. Correct.
  Sévérité : RAS

- **L626-666** `TestErrorPaths` — Teste : (1) FileNotFoundError si parquet absent, (2) ValueError si registry inconsistant (avec injection temporaire + cleanup). Correct et robuste.
  Sévérité : RAS

- **Couverture de bords manquante** : aucun test avec 0 folds (toutes les périodes trop courtes), ou 1 seul fold. Les tests utilisent 3000 barres avec des fenêtres courtes (60j train, 15j test) ce qui produit plusieurs folds, mais le cas limite n'est pas testé. Le splitter lui-même gère ce cas, mais l'intégration avec 0/1 fold n'est pas vérifiée.
  Sévérité : **MINEUR**
  Suggestion : Ajouter un test avec des fenêtres tellement grandes qu'un seul fold est produit, et un test qui vérifie que le pipeline lève une erreur claire si 0 folds.

### B3. Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_runner.py`, docstrings `#049` |
| Couverture des critères AC | ⚠️ | 12/13 AC couverts. AC causalité couvert mais faible (voir B2 WARNING) |
| Cas nominaux + erreurs + bords | ⚠️ | Nominaux: DummyModel, NoTrade, BuyHold. Erreurs: missing data, registry. Bords: 0 folds non testé |
| Boundary fuzzing | N/A | Pas de paramètres numériques directs à la fonction `run_pipeline` |
| Déterministes | ✅ | Seed fixé `_SEED = 42`, `rng = np.random.default_rng(seed)` |
| Portabilité chemins | ✅ | Tous les chemins via `tmp_path` (scan B1 : 0 `/tmp`) |
| Tests registre réalistes | N/A | Pas de test de registre en tant que tel |
| Contrat ABC complet | N/A | Runner n'est pas un ABC |

### B4. Code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 3 matches analysés = faux positifs (sanitisation JSON, normalisation schema, formatage). Pas de `except` large. Validation explicite aux entrées (`FileNotFoundError`, `ValueError`). |
| §R10 Defensive indexing | ✅ | `fold.train_indices`, `fold.val_indices`, `fold.test_indices` proviennent du splitter validé. `signals_full` initialisé à 0 (safe), assignation conditionelle `if ts in ohlcv_test.index`. `ohlcv_test` slicé par timestamps — pas de risque d'indexation négative. |
| §R2 Config-driven | ✅ | Tous les paramètres lus depuis `config.*` : `config.label.horizon_H_bars`, `config.costs.*`, `config.thresholding.*`, `config.backtest.*`, `config.artifacts.save_*`, `config.reproducibility.global_seed`, etc. Aucune constante magique dans le code. `STRATEGY_FRAMEWORK_MAP` est un mapping interne dérivé (non lu depuis YAML) comme spécifié dans la tâche. |
| §R3 Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. Scaler fit sur train uniquement (via `FoldTrainer.train_fold`). θ calibré sur val uniquement (L371-388). Features backward-looking (computed upstream). Splits via `WalkForwardSplitter` + `apply_purge` avec embargo. ohlcv complet passé aux baselines = conforme à la tâche (SMA a besoin du rolling complet). |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random. `set_global_seed()` appelé en L196-200. SHA-256 du parquet dans manifest. |
| §R5 Float conventions | ✅ | `X_seq` et `y` en float32 (produits par `build_samples`). Métriques calculées en float64 (`y_test.astype(np.float64)` L452-453). |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 `is True/False`, `open()` avec `with`, `.read_text()` accepté. `np.isfinite` vérifié avant bornes (L471). |

### B5. Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Toutes les fonctions, variables conformes |
| Pas de code mort/debug | ✅ | Scan B1 : 0 `print()`, 0 `TODO/FIXME` |
| Imports propres | ⚠️ | 2 imports lazy non justifiés (L206, L220) — MINEUR |
| DRY | ⚠️ | 2 duplications : dict bypass θ (L355-362 vs threshold.py L191-198), noms métriques prédiction (L524-535 vs aggregation.py `_PREDICTION_METRICS`) — MINEUR |

### B5-bis. Bonnes pratiques métier

| Critère | Verdict | Preuve |
|---|---|---|
| Exactitude concepts financiers | ✅ | Pipeline conforme au dataflow spec §3.1 |
| Nommage métier | ✅ | `equity_curve`, `trades`, `signals`, `y_hat`, `theta` — standard |
| Séparation responsabilités | ✅ | Runner orchestre, délègue aux modules spécialisés |
| §R9 Vectorisation | ⚠️ | Boucle Python L404-407 (alignement signaux) vectorisable — MINEUR |

### B6. Conformité spec v1.0

| Critère | Verdict | Preuve |
|---|---|---|
| Spécification §3.1 dataflow | ✅ | Pipeline suit exactement le flux : Ingestion → QA → Features → Samples → Split → Scale/Fit/Predict → θ → Backtest → Metrics → Aggregate → Artefacts |
| §14.4 critères d'acceptation | ✅ | `check_acceptance_criteria()` émet les warnings via `logger.warning()` pour net_pnl ≤ 0, profit_factor ≤ 1.0, MDD ≥ cap |
| §15.1 arborescence canonique | ✅ | `run_dir/manifest.json`, `metrics.json`, `config_snapshot.yaml`, `folds/fold_XX/` |
| θ bypass pour signal | ✅ | L350-363 : bypass explicite avec log INFO |
| Plan WS-12.2 | ✅ | Tous les points du plan implémentés |
| Formules doc vs code | ✅ | Pas de formules mathématiques dans le runner (délègue aux modules) |

### B7. Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures | ✅ | `FoldTrainer.train_fold()` : appel à L330-341 cohérent avec signature (model, X_train, y_train, X_val, y_val, X_test, run_dir, meta_*, ohlcv). `calibrate_threshold()` : appel L374-388 cohérent avec signature L130-143. `compute_prediction_metrics()` : appel L450-453 cohérent. `compute_trading_metrics()` : appel L455-461 cohérent. `aggregate_fold_metrics()` : appel L507 cohérent. |
| `VALID_STRATEGIES` / `STRATEGY_FRAMEWORK_MAP` | ✅ | Mêmes 10 clés dans les deux dicts. Vérifié : `dummy, xgboost_reg, cnn1d_reg, gru_reg, lstm_reg, patchtst_reg, rl_ppo, no_trade, buy_hold, sma_rule`. |
| Forwarding kwargs | ✅ | `ohlcv` passé au trainer → transmis à `model.fit()` et `model.predict()`. `meta_train/meta_val/meta_test` passés au trainer → transmis aux appels model. Tous les kwargs pertinents sont forwardés. |
| Registres | ✅ | `MODEL_REGISTRY` vérifié `<= VALID_STRATEGIES` (L188-194). `get_model_class()` utilisé pour résoudre la classe. |
| Clés configuration | ✅ | Toutes les clés config lues (`config.dataset.*`, `config.label.*`, `config.features.*`, `config.splits.*`, `config.scaling.*`, `config.strategy.*`, `config.thresholding.*`, `config.costs.*`, `config.backtest.*`, `config.metrics.*`, `config.reproducibility.*`, `config.artifacts.*`, `config.qa.*`) correspondent au modèle Pydantic. |
| Types retour modules | ✅ | `trainer_result["y_hat_val"]` / `["y_hat_test"]` correctement extraits. `model.output_type` et `model.execution_mode` correctement lus. |

---

## Liste des items

| # | Sévérité | Description | Fichier | Lignes |
|---|---|---|---|---|
| 1 | WARNING | Test causalité faible — DummyModel est data-indépendant, assertions sont des `isinstance` et non des comparaisons d'identité de signaux. Ne valide pas réellement l'AC. | `tests/test_runner.py` | L674-725 |
| 2 | MINEUR | DRY — dict bypass θ dupliqué entre runner et `calibrate_threshold()` | `ai_trading/pipeline/runner.py` | L355-362 |
| 3 | MINEUR | DRY — noms métriques prédiction hardcodés, duplication avec `_PREDICTION_METRICS` d'aggregation.py | `ai_trading/pipeline/runner.py` | L524-535 |
| 4 | MINEUR | Import lazy `run_qa_checks` non justifié — devrait être au module level | `ai_trading/pipeline/runner.py` | L206 |
| 5 | MINEUR | Import lazy `ai_trading.features` — pourrait être au module level comme L21-22 | `ai_trading/pipeline/runner.py` | L220 |
| 6 | MINEUR | `.get("quantile")` inconsistant — la clé existe toujours, utiliser `["quantile"]` | `ai_trading/pipeline/runner.py` | L481 |
| 7 | MINEUR | Boucle Python sur timestamps pour aligner signaux — vectorisable avec `reindex` | `ai_trading/pipeline/runner.py` | L404-407 |
| 8 | MINEUR | Pas de test pour 0 ou 1 fold (edge case intégration) | `tests/test_runner.py` | — |
| 9 | MINEUR | Instanciation modèle hardcodée (`if strategy_name == "dummy"`) | `ai_trading/pipeline/runner.py` | L322-325 |

---

## Résumé

```
RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 1
- Mineurs : 8
- Rapport : docs/tasks/M5/049/review_v1.md
```
