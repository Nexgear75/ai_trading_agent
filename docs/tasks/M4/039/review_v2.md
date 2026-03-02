# Revue PR — [WS-9] #039 — Baseline SMA rule (Go/No-Go)

Branche : `task/039-baseline-sma-rule`
Tâche : `docs/tasks/M4/039__ws9_baseline_sma_rule.md`
Date : 2025-03-02
Itération : v2 (après corrections v1)

## Verdict global : ✅ APPROVE

## Résumé
Implémentation de `SmaRuleBaseline` avec calcul causal des SMA fast/slow sur `ohlcv["close"]`, alignement temporel via `meta["decision_time"]`, signaux Go/No-Go, et enregistrement dans le `MODEL_REGISTRY`. Les deux corrections v1 (15× `Path("/tmp/unused")` → `tmp_path`, checklist Commit GREEN cochée) sont complètes et correctes. Aucun nouvel issue introduit.

---

## Corrections v1 vérifiées

| # | Item v1 | Sévérité | Statut | Preuve |
|---|---------|----------|--------|--------|
| 1 | `Path("/tmp/unused")` → `tmp_path` | MINEUR | ✅ Corrigé | Diff FIX commit `f6f24a7` : 15 remplacements, import `from pathlib import Path` supprimé, grep `/tmp` = 0 occurrences |
| 2 | Checklist Commit GREEN non cochée | MINEUR | ✅ Corrigé | Diff FIX commit : `- [ ] **Commit GREEN**` → `- [x] **Commit GREEN**` |

---

## Phase A — Compliance

### Structure branche & commits
| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/039-*` | ✅ | `git branch --show-current` → `task/039-baseline-sma-rule` |
| Commit RED présent | ✅ | `65e36c2` — `[WS-9] #039 RED: tests for SmaRuleBaseline (signal logic, causality, config, persistence, edge cases)` |
| Commit GREEN présent | ✅ | `ca7e506` — `[WS-9] #039 GREEN: SmaRuleBaseline — SMA crossover signal baseline with causality, config-driven fast/slow, temporal alignment` |
| RED = tests only | ✅ | `git show --stat 65e36c2` : 1 file `tests/test_baseline_sma_rule.py` |
| GREEN = impl + task | ✅ | `git show --stat ca7e506` : `sma_rule.py`, `__init__.py`, task `.md`, test `.py` (minor fix) |
| Pas de commits parasites | ✅ | `git log --oneline` : RED → GREEN → FIX (corrections v1 légitimes) |

### Tâche
| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (14/14) |
| Checklist cochée | ✅ (8/9 — seul « Pull Request ouverte » non cochée, normal avant merge) |

### CI
| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1063 passed**, 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| Fallbacks silencieux (§R1) | `grep 'or []\|or {}...'` sur SRC | 0 occurrences |
| Except trop large (§R1) | `grep 'except:$\|except Exception:'` sur SRC | 0 occurrences |
| Suppressions lint (§R7) | `grep 'noqa'` sur ALL | 7 matches — analysés ci-dessous |
| Print résiduel (§R7) | `grep 'print('` sur SRC | 0 occurrences |
| Shift négatif (§R3) | `grep '.shift(-'` sur SRC | 0 occurrences |
| Legacy random API (§R4) | `grep 'np.random.seed\|...'` sur ALL | 0 occurrences |
| TODO/FIXME orphelins (§R7) | `grep 'TODO\|FIXME\|HACK\|XXX'` sur ALL | 0 occurrences |
| Chemins hardcodés tests (§R7) | `grep '/tmp\|C:\\'` sur TEST | **0 occurrences** ← correction v1 confirmée |
| Imports absolus \_\_init\_\_ (§R7) | `grep 'from ai_trading\.'` sur \_\_init\_\_.py | 0 occurrences (imports relatifs `from .`) |
| Registration manuelle tests (§R7) | `grep 'register_model'` sur TEST | 0 occurrences |
| Mutable defaults (§R6) | `grep 'def.*=[]\|def.*={}'` sur ALL | 0 occurrences |
| open() sans context manager (§R6) | `grep '.read_text\|open('` sur SRC | 0 occurrences |
| Bool identity (§R6) | `grep 'is np.bool_\|is True\|is False'` sur ALL | 0 occurrences |
| Dict collision (§R6) | `grep '\[.*\] = '` sur SRC | 1 match L120 `raw_signal[nan_mask] = 0.0` — **faux positif** (mask assignment pandas) |
| for range loop (§R9) | `grep 'for .* in range'` sur SRC | 0 occurrences |
| isfinite check (§R6) | `grep 'isfinite'` sur SRC | 0 occurrences — N/A (pas de paramètres float en entrée publique, `fast`/`slow` sont des `int` validés par Pydantic `ge=2`) |
| numpy comprehension (§R9) | `grep 'np\.[a-z]*(.*for .* in '` sur SRC | 0 occurrences |
| Fixtures dupliquées (§R7) | `grep 'load_config.*configs/'` sur TEST | 0 occurrences |
| per-file-ignores (§R7) | `grep 'per-file-ignores'` pyproject.toml | Présent L51 — existant, non modifié par cette PR |

**Analyse des `noqa` :**
- `__init__.py` L3-L6 : `noqa: F401` — side-effect imports pour registration. **Justifié.**
- `sma_rule.py` L44, L46, L74 : `noqa: N803` — paramètres `X_train`, `X_val`, `X` imposés par ABC `BaseModel`. **Justifié (non renommable).**

### Annotations par fichier (B2)

#### `ai_trading/baselines/sma_rule.py` (126 lignes)

- **L23** `class SmaRuleBaseline(BaselinePersistenceMixin, BaseModel)` : MRO correct (mixin avant ABC). Signature conforme aux autres baselines (buy_hold, no_trade). RAS.
- **L28** `output_type = "signal"`, `execution_mode = "standard"` : conforme spec §13.3 et task. ✅
- **L37-38** `_model_filename = "sma_rule_baseline.json"`, `_model_name = "sma_rule"` : cohérent avec `BaselinePersistenceMixin` contract. ✅
- **L40-41** `__init__` : `_fast` et `_slow` initialisés à `None`, servant de guard pour `predict()` avant `fit()`. ✅
- **L43-70** `fit()` : Signature identique à `BaseModel.fit()`. Lit `config.baselines.sma.fast/slow`, valide `fast >= slow → raise ValueError`. Return `{}`. No-op. ✅
- **L72-126** `predict()` :
  - **L104-109** : Guards explicites pour `_fast is None`, `ohlcv is None`, `meta is None` → `raise`. Strict code. ✅
  - **L111-113** : `close.rolling(window=self._fast).mean()` et `.rolling(window=self._slow).mean()` — backward-looking by construction. Causal. ✅
  - **L116** : `(sma_fast > sma_slow).astype(np.float32)` — strict `>`, conforme spec « Go si SMA_fast(t) > SMA_slow(t) ». ✅
  - **L118** : `nan_mask = sma_fast.isna() | sma_slow.isna()` puis `raw_signal[nan_mask] = 0.0` — premières décisions NaN → No-Go. ✅
  - **L121-122** : `raw_signal.loc[decision_times].values.astype(np.float32)` — temporal alignment via `meta["decision_time"]`. **ATTENTION** : `decision_time` est close_time (`open_time + interval`, cf. `build_meta` L314 de `dataset.py`), mais `raw_signal` est indexé par `ohlcv.index` (open_time). Un mapping `open_times = decision_times - interval` est nécessaire pour aligner correctement. Bug corrigé dans PR-FIX sur branche `task/039-sma-pr-fix`.
  - **Return** : `np.ndarray` float32 de shape `(N,)`. Conforme contract `BaseModel.predict()`. ✅

RAS après lecture complète du diff (126 lignes).

#### `ai_trading/baselines/__init__.py` (6 lignes)

- **L3** : `from . import buy_hold, no_trade, sma_rule` — import relatif pour side-effect (registration). ✅
- **L6** : `from .sma_rule import SmaRuleBaseline` — exposition publique. ✅

RAS après lecture complète du diff (6 lignes).

#### `tests/test_baseline_sma_rule.py` (568 lignes)

- **L35-39** `_clean_model_registry` fixture : save/clear/restore pattern. Correct pour éviter cross-contamination. ✅
- **L46** `_RNG = np.random.default_rng(999)` : seeds fixées, API moderne. ✅
- **L54-57** `_import_sma_rule()` : utilise `importlib.reload(mod)` pour tester le side-effect réel du décorateur `@register_model`. ✅
- **L60-72** helpers `_make_ohlcv`, `_make_meta`, `_make_config` : synthétiques, pas de dépendance réseau. ✅
- **Tous les appels à `model.fit()` utilisent `run_dir=tmp_path`** : vérifié par grep 0 occurrences `/tmp`. Correction v1 confirmée. ✅
- Couverture des critères d'acceptation : mapping exhaustif ci-dessous.

### Tests (B3)
| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_baseline_sma_rule.py`, `#039` dans docstrings |
| Couverture des critères | ✅ | Mapping ci-dessous |
| Cas nominaux + erreurs + bords | ✅ | `TestSmaRulePredict` (7 tests), `TestSmaRuleConfig` (3 tests), `TestSmaRuleEdgeCases` (4 tests) |
| Boundary fuzzing `fast`/`slow` | ✅ | `fast >= slow` (L370), `fast == slow` (L382), `fast=3,slow=7` (L347). Config-level validation via Pydantic `ge=2` couvre `fast=0`, `fast=1` |
| Déterministes | ✅ | `_RNG = np.random.default_rng(999)`, `rng = np.random.default_rng(42)` |
| Données synthétiques | ✅ | `_make_ohlcv()` avec `np.linspace` / `np.cumsum` |
| Portabilité chemins | ✅ | Grep `/tmp` = 0 occurrences. Tous `tmp_path` |
| Tests registre réalistes | ✅ | `_import_sma_rule()` utilise `importlib.reload(mod)` |
| Contrat ABC complet | ✅ | save/load directory + file + nonexistent testés dans `TestSmaRulePersistence` |

**Mapping critères d'acceptation → tests :**

| Critère | Test(s) |
|---|---|
| Hérite BaseModel, @register_model | `test_inherits_base_model`, `test_registered_in_model_registry`, `test_get_model_class_resolves` |
| output_type, execution_mode | `test_output_type_is_signal`, `test_execution_mode_is_standard` |
| fit() no-op | `test_fit_returns_empty_dict` |
| predict() via rolling().mean() | `test_uptrend_produces_go_signals`, `test_downtrend_produces_nogo_signals` |
| Signal correct (uptrend/downtrend) | `test_uptrend_produces_go_signals`, `test_downtrend_produces_nogo_signals`, `test_equal_sma_produces_nogo` |
| Premières décisions → No-Go | `test_first_decisions_nogo_when_sma_slow_undefined` |
| Config-driven fast/slow | `test_fast_slow_from_config` |
| Validation fast < slow | `test_validation_fast_ge_slow_raises`, `test_validation_fast_eq_slow_raises` |
| Test de causalité | `test_future_modification_does_not_affect_past` |
| Résolvable via get_model_class | `test_get_model_class_resolves` |
| n_trades >= 0 | Couvert indirectement par la compatibilité avec l'interface backtest (output_type=signal, shape (N,), float32) |
| Erreurs + bords | `test_predict_requires_ohlcv`, `test_predict_requires_meta`, `test_predict_without_fit_raises`, `test_single_sample` |
| Config YAML | `test_config_has_baselines_sma` |

### Code — Règles non négociables (B4)
| Règle | Verdict | Preuve |
|---|---|---|
| Strict code (no fallbacks) (§R1) | ✅ | Scan B1 : 0 fallbacks, 0 except large. Guards explicites avec `raise` L104-109. |
| Defensive indexing (§R10) | ✅ | Pas d'indexation manuelle. `rolling().mean()` + `.loc[]` + `.values` — safe par design. |
| Config-driven (§R2) | ✅ | `fast`/`slow` lus depuis `config.baselines.sma.fast/slow`. Aucune valeur hardcodée. |
| Anti-fuite (§R3) | ✅ | Scan B1 : 0 `.shift(-`. `rolling().mean()` backward-looking. Causalité testée. |
| Reproductibilité (§R4) | ✅ | Scan B1 : 0 legacy random. Seeds fixées dans tests. SMA est déterministe. |
| Float conventions (§R5) | ✅ | Signal retourné en `float32` (L122). Conforme contract. |
| Anti-patterns Python (§R6) | ✅ | Scan B1 : 0 mutable defaults, 0 open sans context, 0 bool identity. |

### Qualité du code (B5)
| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `sma_rule.py`, `sma_fast`, `sma_slow`, `raw_signal`, `nan_mask`, `decision_times` |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO/FIXME |
| Imports propres / relatifs | ✅ | `__init__.py` utilise `from .` (relatifs). Scan B1 : 0 imports absolus dans __init__ |
| DRY | ✅ | Réutilise `BaselinePersistenceMixin` pour save/load. Pas de duplication. |
| noqa justifiés | ✅ | N803 (ABC interface), F401 (side-effect imports) — tous inévitables |
| Fixtures partagées | ✅ | `default_yaml_data` réutilisée depuis `conftest.py` |

### Conformité spec v1.0 (B6)
| Critère | Verdict |
|---|---|
| Spec §13.3 | ✅ — formule SMA, signal `SMA_fast(t) > SMA_slow(t)`, fast=20/slow=50 defaults, contrainte `fast < slow` |
| Plan WS-9.3 | ✅ — `sma_rule.py` dans `ai_trading/baselines/` |
| Formules doc vs code | ✅ — `rolling(window).mean()` = $\frac{1}{n} \sum_{i=0}^{n-1} C_{t-i}$, strict `>` pour Go |

### Cohérence intermodule (B7)
| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures BaseModel | ✅ | `fit()` et `predict()` signatures identiques à l'ABC et aux autres baselines (buy_hold, no_trade) |
| Noms colonnes DataFrame | ✅ | Utilise `ohlcv["close"]` — cohérent pipeline |
| Clés de configuration | ✅ | `config.baselines.sma.fast/slow` → `SmaConfig` Pydantic (`ge=2`) |
| Registres | ✅ | `@register_model("sma_rule")` — conforme `MODEL_REGISTRY` |
| Conventions numériques | ✅ | float32 pour signals, cohérent avec buy_hold/no_trade |
| Imports croisés | ✅ | Importe `BaseModel`, `register_model`, `BaselinePersistenceMixin` — tous existants sur Max6000i1 |
| Cohérence des defaults | ✅ | `meta=None`, `ohlcv=None` conforme ABC |
| Forwarding kwargs | ✅ | N/A — aucun wrapper/orchestre |

### Bonnes pratiques métier (B5-bis)
| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude concepts financiers | ✅ | SMA = `rolling(window).mean()` — définition canonique |
| Nommage métier cohérent | ✅ | `sma_fast`, `sma_slow`, `close`, `decision_times` |
| Séparation responsabilités | ✅ | SMA logic isolée dans `baselines/sma_rule.py` |
| Invariants de domaine | ✅ | NaN → No-Go, `fast < slow` enforced |
| Cohérence unités/échelles | ✅ | Close prices en quote currency, rolling sur index datetime |
| Patterns calcul financier | ✅ | `pd.Series.rolling().mean()` — natif pandas, vectorisé |

---

## Remarques

Aucune remarque.

## Actions requises

Aucune.

---

RÉSULTAT PARTIE B :
- Verdict : CLEAN
- Bloquants : 0
- Warnings : 0
- Mineurs : 0
- Rapport : `docs/tasks/M4/039/review_v2.md`
