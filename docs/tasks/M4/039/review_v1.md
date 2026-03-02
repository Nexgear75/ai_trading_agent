# Revue PR — [WS-9] #039 — Baseline SMA rule (Go/No-Go)

Branche : `task/039-baseline-sma-rule`
Tâche : `docs/tasks/M4/039__ws9_baseline_sma_rule.md`
Date : 2025-03-02
Itération : v1

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

L'implémentation de `SmaRuleBaseline` est correcte, conforme à la spec §13.3 et bien structurée. Les tests couvrent exhaustivement les critères d'acceptation (signal logic, causalité, config-driven, persistence, edge cases). Deux problèmes mineurs empêchent le verdict CLEAN : 15 occurrences de `Path("/tmp/unused")` hardcodé dans les tests (portabilité §R7) et la checklist de tâche incomplète.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/039-*` | ✅ | `task/039-baseline-sma-rule` |
| Commit RED présent | ✅ | `65e36c2` — `[WS-9] #039 RED: tests for SmaRuleBaseline (signal logic, causality, config, persistence, edge cases)` |
| Commit RED = tests uniquement | ✅ | `git show --stat 65e36c2` : `tests/test_baseline_sma_rule.py | 568 +++` (1 fichier) |
| Commit GREEN présent | ✅ | `ca7e506` — `[WS-9] #039 GREEN: SmaRuleBaseline — SMA crossover signal baseline with causality, config-driven fast/slow, temporal alignment` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat ca7e506` : `ai_trading/baselines/__init__.py`, `ai_trading/baselines/sma_rule.py`, `docs/tasks/M4/039__ws9_baseline_sma_rule.md`, `tests/test_baseline_sma_rule.py` (4 fichiers) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` : exactement 2 commits (RED + GREEN) |

**Note :** le GREEN commit modifie le test (+1 ligne : ajout return type annotation `-> type` sur `_import_sma_rule()`). C'est un refactoring mineur acceptable.

### Tâche

| Critère | Verdict | Détail |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (14/14) | Tous `[x]` |
| Checklist cochée | ⚠️ (7/9) | `[ ] Commit GREEN` et `[ ] Pull Request ouverte` non cochés |

**Remarque :** le commit GREEN existe (ca7e506). Les 2 items non cochés correspondent à des actions post-édition du fichier de tâche (paradoxe d'auto-référence pour le commit GREEN, et la PR est une action post-commit). → MINEUR.

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1063 passed**, 0 failed (6.26s) |
| `ruff check ai_trading/ tests/` | **All checks passed!** |

✅ Phase A passée — continuation en Phase B.

---

## Phase B — Code Review

### B1 — Résultats du scan automatisé (GREP)

| Pattern recherché | Règle | Résultat |
|---|---|---|
| Fallbacks silencieux (`or []`, `or {}`, etc.) | §R1 | 0 occurrences (grep exécuté) |
| Except trop large | §R1 | 0 occurrences (grep exécuté) |
| Print résiduel | §R7 | 0 occurrences (grep exécuté) |
| Shift négatif `.shift(-` | §R3 | 0 occurrences (grep exécuté) |
| Legacy random API | §R4 | 0 occurrences (grep exécuté) |
| TODO/FIXME/HACK/XXX | §R7 | 0 occurrences (grep exécuté) |
| Chemins hardcodés `/tmp` (tests) | §R7 | **15 occurrences** — `Path("/tmp/unused")` dans `tests/test_baseline_sma_rule.py` |
| Imports absolus `__init__.py` | §R7 | 0 occurrences (grep exécuté) — imports relatifs corrects |
| Registration manuelle dans tests | §R7 | 0 occurrences (grep exécuté) — utilise `importlib.reload` |
| Mutable defaults | §R6 | 0 occurrences (grep exécuté) |
| open() sans context manager | §R6 | 0 occurrences (grep exécuté) |
| Bool identité numpy `is True`/`is False` | §R6 | 0 occurrences (grep exécuté) |
| Boucle Python sur numpy | §R9 | 0 occurrences (grep exécuté) |
| isfinite check | §R6 | 0 occurrences — N/A (paramètres `fast`/`slow` sont `int`, NaN impossible) |
| Appels numpy répétés dans compréhension | §R9 | 0 occurrences (grep exécuté) |
| Fixtures dupliquées (`load_config.*configs/`) | §R7 | 0 occurrences — utilise `default_yaml_data` de conftest.py |
| noqa | §R7 | 3× `noqa: N803` (params ABC imposés : `X_train`, `X_val`, `X`) + 4× `noqa: F401` (re-exports init) — tous justifiés |
| per-file-ignores | §R7 | Ligne 51 de pyproject.toml — pas modifié par cette PR |

### B2 — Annotations par fichier

#### `ai_trading/baselines/sma_rule.py` (126 lignes)

- **L23-36** : Classe `SmaRuleBaseline(BaselinePersistenceMixin, BaseModel)` — attributs `output_type = "signal"`, `execution_mode = "standard"`, `_model_filename`, `_model_name` conformes au pattern des autres baselines (no_trade, buy_hold). ✅
- **L38-39** : `_fast: int | None = None`, `_slow: int | None = None` — sentinel pattern valide pour détecter predict-before-fit. ✅
- **L41-72** : `fit()` — lit `config.baselines.sma.fast/slow`, valide `fast >= slow` avec `raise ValueError`. Return `{}`. Conforme au contrat ABC. ✅
- **L69** : `if fast >= slow: raise ValueError(...)` — validation stricte, pas de fallback. ✅
- **L74-126** : `predict()` — calcul SMA via `rolling(window).mean()`, signal `sma_fast > sma_slow`, gestion NaN explicite, alignement temporel via `meta["decision_time"]`. ✅
- **L108-113** : Validations explicites : RuntimeError si pas appelé après fit, ValueError si ohlcv/meta is None. ✅
- **L116-118** : SMA calculée via `pd.Series.rolling(window).mean()` — backward-looking par construction, conforme §13.3. ✅
- **L120** : `raw_signal[nan_mask] = 0.0` — assignation par masque booléen sur Series pandas, pas de collision dict. Faux positif grep. ✅
- **L124** : `aligned = raw_signal.loc[decision_times].values.astype(np.float32)` — `.loc` correct pour indexation par timestamps. Si un timestamp n'est pas dans l'index, `KeyError` sera levé — c'est le comportement strict attendu (pas de fallback silencieux). ✅

**RAS après lecture complète du diff (126 lignes source).**

#### `ai_trading/baselines/__init__.py` (6 lignes)

- **L1** : Docstring mise à jour pour inclure `sma_rule`. ✅
- **L3** : `from . import buy_hold, no_trade, sma_rule` — import relatif correct. ✅
- **L6** : `from .sma_rule import SmaRuleBaseline` — export explicite. ✅

**RAS après lecture complète du diff (6 lignes).**

#### `tests/test_baseline_sma_rule.py` (568 lignes)

- **L41-47** : Fixture `_clean_model_registry` — save/clear/restore MODEL_REGISTRY. Pattern correct, conforme aux autres tests baselines. ✅
- **L49-55** : Variables module-level avec seed fixée `np.random.default_rng(999)`. ✅ Déterministe.
- **L58-62** : `_import_sma_rule()` utilise `importlib.reload(mod)` — conforme §R7 (test de registre réaliste). ✅
- **L185, L211, L234, L256, L278, L300, L325, L356, L380, L392, L424, L436, L493, L507, L537** : `run_dir=Path("/tmp/unused")` — **15 occurrences de chemin hardcodé**. Le `run_dir` n'est pas utilisé par `fit()` (SMA baseline n'écrit pas d'artefact en fit), donc fonctionnellement inoffensif. Mais §R7 exige `tmp_path` de pytest. Les autres tests baselines (no_trade, buy_hold) n'utilisent PAS `/tmp`. → **MINEUR** — remplacer par paramètre `tmp_path` ou constante inerte portable.
- **L398-441** : `TestSmaRuleCausality.test_future_modification_does_not_affect_past` — modifie les prix après barre 60, vérifie que les signaux pour t ≤ 60 sont identiques. Test de causalité conforme au critère d'acceptation. ✅
- **L445-472** : `TestSmaRulePersistence` — save/load directory, save/load fichier, load inexistant. Conforme au contrat ABC (directory ET fichier). ✅
- **L478-543** : `TestSmaRuleEdgeCases` — predict sans ohlcv, sans meta, sans fit, single sample. ✅
- **L550-561** : `TestSmaConfigInYaml.test_config_has_baselines_sma` — utilise fixture `default_yaml_data` de conftest.py. Vérifie fast=20, slow=50. ✅

### B3 — Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_baseline_sma_rule.py`, #039 dans docstrings |
| Couverture des critères d'acceptation | ✅ | 14/14 critères couverts (mapping ci-dessous) |
| Cas nominaux + erreurs + bords | ✅ | TestSmaRulePredict (6 tests), TestSmaRuleConfig (3 tests), TestSmaRuleEdgeCases (4 tests) |
| Boundary fuzzing | ✅ | fast > slow, fast == slow, single sample, warmup zone, constant prices |
| Déterministes | ✅ | seed=999 (module), seed=42 (binary test) |
| Données synthétiques | ✅ | `np.linspace`, `np.cumsum(rng.standard_normal(...))` |
| Portabilité chemins | ⚠️ | 15× `Path("/tmp/unused")` — voir §MINEUR-1 |
| Tests registre réalistes | ✅ | `importlib.reload(mod)` dans `_import_sma_rule()` |
| Contrat ABC complet | ✅ | save/load directory + fichier, load inexistant |
| Tests désactivés | ✅ | 0 `@pytest.mark.skip` ou `xfail` |

**Mapping critères d'acceptation → tests :**

| Critère | Test(s) |
|---|---|
| Hérite BaseModel, @register_model("sma_rule") | `test_inherits_base_model`, `test_registered_in_model_registry` |
| output_type="signal", execution_mode="standard" | `test_output_type_is_signal`, `test_execution_mode_is_standard` |
| fit() no-op | `test_fit_returns_empty_dict` |
| predict() SMA via rolling().mean() | `test_uptrend_produces_go_signals`, `test_downtrend_produces_nogo_signals` |
| Signal correct tendances | `test_uptrend_produces_go_signals`, `test_downtrend_produces_nogo_signals` |
| Premières décisions No-Go | `test_first_decisions_nogo_when_sma_slow_undefined` |
| Config fast/slow | `test_fast_slow_from_config` |
| Validation fast < slow + raise | `test_validation_fast_ge_slow_raises`, `test_validation_fast_eq_slow_raises` |
| Test de causalité | `test_future_modification_does_not_affect_past` |
| sma_rule résolvable | `test_get_model_class_resolves` |
| Soumis au backtest | N/A (intégration, pas testé unitairement — acceptable) |
| Tests nominaux + erreurs + bords | TestSmaRulePredict + TestSmaRuleEdgeCases |
| Suite verte | 1063 passed, 0 failed |
| ruff clean | All checks passed |

### B4 — Code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| Strict code (no fallbacks) §R1 | ✅ | Scan B1 : 0 fallback, 0 except large. Validation explicite dans `fit()` (ValueError) et `predict()` (RuntimeError, ValueError). |
| Defensive indexing §R10 | ✅ | `.loc[decision_times]` lèvera KeyError si timestamp absent — comportement strict correct. Pas de slicing risqué. |
| Config-driven §R2 | ✅ | `fast`/`slow` lus depuis `config.baselines.sma.fast/slow`. Config YAML : `baselines.sma.fast: 20`, `baselines.sma.slow: 50`. Pydantic valide `ge=2` + cross-validation `fast < slow`. |
| Anti-fuite §R3 | ✅ | Scan B1 : 0 `.shift(-`. `rolling().mean()` est backward-looking par construction. Test de causalité confirme. |
| Reproductibilité §R4 | ✅ | Scan B1 : 0 legacy random. Tests utilisent `np.random.default_rng(seed)`. Baseline déterministe (pas d'aléatoire). |
| Float conventions §R5 | ✅ | `predict()` retourne `float32` (`.astype(np.float32)` L124). |
| Anti-patterns Python §R6 | ✅ | Scan B1 : 0 mutable default, 0 open sans ctx, 0 bool identité. Pas de `.values` injustifié. |

### B5 — Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `sma_rule.py`, `SmaRuleBaseline`, `_model_filename`, etc. |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO/FIXME |
| Imports propres / relatifs | ✅ | `__init__.py` utilise imports relatifs. `sma_rule.py` imports corrects. |
| DRY | ✅ | Utilise `BaselinePersistenceMixin` partagé (save/load). Pas de duplication avec no_trade/buy_hold. |
| `__init__.py` à jour | ✅ | `from . import sma_rule` + `from .sma_rule import SmaRuleBaseline` |
| noqa justifiés | ✅ | 3× N803 (params ABC), 4× F401 (re-exports) — tous inévitables |

### B5-bis — Bonnes pratiques métier

| Critère | Verdict | Preuve |
|---|---|---|
| SMA conforme définition canonique | ✅ | `rolling(window).mean()` = $\frac{1}{n}\sum_{i=0}^{n-1} C_{t-i}$ (spec §13.3) |
| Nommage métier cohérent | ✅ | `sma_fast`, `sma_slow`, `raw_signal`, `decision_times` |
| Vectorisation | ✅ | Utilise pandas rolling natif, pas de boucle Python |

### B6 — Conformité spec v1.0

| Critère | Verdict | Détail |
|---|---|---|
| Spécification §13.3 | ✅ | Formule SMA_n(t) implémentée via `rolling(n).mean()`. Signal Go si SMA_fast > SMA_slow, sinon No-Go. Paramètres MVP fast=20, slow=50. |
| Plan WS-9.3 | ✅ | `SmaRuleBaseline` enregistrée dans MODEL_REGISTRY, soumise au backtest commun. |
| Formules doc vs code | ✅ | Spec : $Go \text{ si } SMA_{fast}(t) > SMA_{slow}(t)$. Code L119 : `sma_fast > sma_slow`. Strictement identique (pas ≥, mais >). |
| Contrainte spec `fast < slow` | ✅ | Validée en L69 (`fast >= slow → raise`) + Pydantic config (L403 de config.py) |

### B7 — Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures ABC | ✅ | `fit()` et `predict()` parfaitement alignés sur `BaseModel` (mêmes params, mêmes defaults). |
| BaselinePersistenceMixin | ✅ | Attributs `_model_filename`, `_model_name` définis. Pattern identique à no_trade et buy_hold. |
| Clés config | ✅ | `baselines.sma.fast/slow` — Pydantic `SmaConfig` avec `ge=2`, cross-validation dans pipeline config. |
| Forwarding kwargs | ✅ | `predict()` reçoit et utilise `meta` et `ohlcv` — pas de perte de contexte. |
| Cohérence des defaults | ✅ | `meta=None`, `ohlcv=None` — même convention que `BaseModel.predict()`. |

---

## Remarques

1. **[MINEUR]** 15 occurrences de `Path("/tmp/unused")` hardcodé dans les tests.
   - Fichier : `tests/test_baseline_sma_rule.py`
   - Lignes : 185, 211, 234, 256, 278, 300, 325, 356, 380, 392, 424, 436, 493, 507, 537
   - Règle : §R7 — « Portabilité des chemins dans les tests : aucun chemin hardcodé `/tmp/...`, toujours `tmp_path` de pytest. »
   - Impact : fonctionnellement nul (le `run_dir` n'est pas utilisé par `SmaRuleBaseline.fit()`), mais viole la convention de portabilité. Les tests des autres baselines (no_trade, buy_hold) n'utilisent pas `/tmp`.
   - Suggestion : ajouter `tmp_path` comme paramètre de test et remplacer `Path("/tmp/unused")` par `tmp_path`. Alternativement, les tests qui n'ont pas besoin de `tmp_path` pour autre chose peuvent passer directement `tmp_path` à `run_dir`.

2. **[MINEUR]** Checklist de tâche incomplète : 2 items non cochés.
   - Fichier : `docs/tasks/M4/039__ws9_baseline_sma_rule.md`
   - Lignes : dernières lignes de la checklist
   - Items : `[ ] Commit GREEN` et `[ ] Pull Request ouverte`
   - Impact : le commit GREEN existe (ca7e506). Le paradoxe d'auto-référence (cocher « Commit GREEN » dans le commit lui-même) est mineur mais la convention du projet exige la checklist complète.
   - Suggestion : cocher les deux items dans un commit de correction.

---

## Résumé

```
RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 0
- Mineurs : 2
- Rapport : docs/tasks/M4/039/review_v1.md
```
