# Revue PR — [WS-7] #033 — Bypass calibration θ pour RL et baselines

Branche : `task/033-theta-bypass`
Tâche : `docs/tasks/M3/033__ws7_theta_bypass.md`
Date : 2025-03-02
Itération : v1

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

L'implémentation du bypass de calibration θ pour les modèles `output_type="signal"` est fonctionnellement correcte, bien structurée et conforme à la spec §11.4/§11.5. Le processus TDD est respecté (RED puis GREEN), les 899 tests passent, ruff est clean. Cependant, la constante `_VALID_OUTPUT_TYPES` est dupliquée entre `threshold.py` et `base.py` (BLOQUANT DRY §R7), et le paramètre `output_type` a une valeur par défaut qui masque un input manquant (WARNING §R1).

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/NNN-short-slug` | ✅ | `git branch --show-current` → `task/033-theta-bypass` |
| Commit RED présent | ✅ | `35e91aa` — `[WS-7] #033 RED: tests bypass calibration θ pour signal models` |
| Commit GREEN présent | ✅ | `e7b09e2` — `[WS-7] #033 GREEN: bypass calibration θ pour RL et baselines` |
| Commit RED = tests uniquement | ✅ | `git show --stat 35e91aa` → 1 fichier : `tests/test_theta_bypass.py` (413 insertions) |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat e7b09e2` → 3 fichiers : `threshold.py` (+30), `033__ws7_theta_bypass.md` (modifié), `test_theta_bypass.py` (+15/-7) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1..HEAD` → exactement 2 commits (RED, GREEN) |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (10/10) |
| Checklist cochée | ✅ (8/9 — seule la case PR non encore cochée, ce qui est normal pré-merge) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **899 passed**, 0 failed ✅ |
| `ruff check ai_trading/ tests/` | **All checks passed!** ✅ |

---

## Phase B — Code Review

### B1 — Scan automatisé (GREP)

| Pattern recherché | Règle | Résultat |
|---|---|---|
| Fallbacks silencieux (`or []`, `or {}`, `if ... else`) | §R1 | 1 match L67 `threshold.py` — faux positif, c'est une docstring : `"1 if y_hat[t] > theta, else 0"` |
| Except trop large | §R1 | 0 occurrences ✅ |
| Suppressions lint `noqa` | §R7 | 3 matches dans `test_theta_bypass.py` (L39, L41, L53) — `# noqa: N803` pour `X_train`, `X_val`, `X`, noms imposés par l'ABC BaseModel → justifié |
| per-file-ignores | §R7 | `test_theta_bypass.py` absent de per-file-ignores ; utilise inline `# noqa` à la place. Cohérent avec le code mais diverge de la convention d'autres fichiers test (ex: `test_base_model.py`). Non bloquant. |
| Print résiduel | §R7 | 0 occurrences ✅ |
| Shift négatif (look-ahead) | §R3 | 0 occurrences ✅ |
| Legacy random API | §R4 | 0 occurrences ✅ |
| TODO/FIXME orphelins | §R7 | 0 occurrences ✅ |
| Chemins hardcodés tests | §R7 | 0 occurrences ✅ |
| Imports absolus `__init__.py` | §R7 | N/A — aucun `__init__.py` modifié |
| Registration manuelle tests | §R7 | 0 occurrences ✅ |
| Mutable default arguments | §R6 | 0 occurrences ✅ |
| open() sans context manager | §R6 | 0 occurrences ✅ |
| Comparaison booléenne par identité | §R6 | 0 occurrences ✅ |
| Dict collision silencieuse | §R6 | 0 occurrences ✅ |
| Boucle Python sur array numpy | §R9 | 0 occurrences ✅ |
| Validation bornes + isfinite | §R6 | 1 match L50 — `math.isfinite(q)` dans `compute_quantile_thresholds` (code pré-existant) ✅ |
| Appels numpy dans compréhension | §R9 | 0 occurrences ✅ |
| Fixtures dupliquées | §R7 | 0 occurrences (pas d'appel `load_config`) ✅ |
| `strategy.name` dans le code | spécifique | 0 occurrences dans le code source, 1 match en docstring test (L8) — correct ✅ |

### B2 — Annotations par fichier (lecture diff ligne par ligne)

#### `ai_trading/calibration/threshold.py` (diff : +30 lignes)

- **L128** `_VALID_OUTPUT_TYPES = frozenset({"regression", "signal"})` : **DRY violation** — cette constante est identique à celle définie dans `ai_trading/models/base.py` L51. Si un nouveau `output_type` est ajouté dans un fichier mais pas l'autre, le comportement diverge silencieusement.
  Sévérité : **BLOQUANT** (§R7 DRY — drift silencieux)
  Suggestion : importer depuis `ai_trading.models.base` (`from ai_trading.models.base import _VALID_OUTPUT_TYPES`) ou extraire vers un module partagé (`ai_trading/constants.py` ou `ai_trading/calibration/constants.py`). Vérifier l'absence de dépendance circulaire : `threshold.py` importe de `ai_trading.backtest.*` mais pas de `ai_trading.models.*` ; `base.py` n'importe pas de `calibration.*` → pas de cycle, import direct possible.

- **L143** `output_type: str = "regression"` : **Default masquant un input manquant** — per §R1 strict code, les paramètres ne doivent pas avoir de valeur par défaut qui masque un appel incorrect. Un futur orchestrateur qui omettrait `output_type` obtiendrait silencieusement la calibration regression au lieu d'une erreur explicite.
  Sévérité : **WARNING** (§R1)
  Suggestion : rendre `output_type` obligatoire (pas de default). Mettre à jour les callers existants dans `tests/test_theta_optimization.py` pour passer explicitement `output_type="regression"`.

- **L177-181** Validation `output_type` avec `ValueError` + message clair incluant les valeurs valides : ✅ correct, conforme strict code.

- **L184-193** Bypass branch — retourne un dict avec `theta=None`, `quantile=None`, `method="none"`, `net_pnl=None`, `mdd=None`, `n_trades=None`, `details=None` : ✅ conforme spec §11.5 (`threshold.method = "none"`, `theta = null`). Les clés du dict bypass sont cohérentes avec celles du dict retourné par la calibration normale (même 7 clés : `theta`, `quantile`, `method`, `net_pnl`, `mdd`, `n_trades`, `details`).

- **Bypass court-circuite toute validation de `y_hat_val`** : quand `output_type="signal"`, la fonction retourne immédiatement sans vérifier `y_hat_val.ndim`, `.size`, ni la cohérence avec `ohlcv_val`. C'est cohérent avec le design : la calibration n'a rien à faire des prédictions dans ce cas. Les prédictions seront validées par le backtest en aval. RAS.

- Pas de modification du reste de la fonction (calibration regression path inchangé). RAS après lecture complète du diff (30 lignes ajoutées).

#### `tests/test_theta_bypass.py` (nouveau fichier, 412 lignes)

- **L73-88** `_make_ohlcv` : helper quasi-identique à celui de `test_theta_optimization.py` L32-49 (même seed 42, même structure). Pattern préexistant (aussi dans `test_label_target.py`), mais la PR ajoute une copie supplémentaire.
  Sévérité : **MINEUR** (§R7 DRY tests — pré-existant mais amplifié)
  Suggestion : extraire `_make_ohlcv` dans `tests/conftest.py` et réutiliser. Hors scope immédiat car pattern préexistant.

- **L29-63** `_SignalModelStub(BaseModel)` : implémente correctement l'interface ABC avec `output_type = "signal"`. Paramètres `fit()` et `predict()` conformes au contrat BaseModel. ✅

- **L95-239** `TestCalibrateThetaBypassSignal` (6 tests) : couvre method=none, theta=None, quantile=None, details=None, all-zero signals, all-one signals. ✅

- **L247-323** `TestCalibrateThetaRegressionNormal` (3 tests) : vérifie que `output_type="regression"` exécute la calibration complète (method ≠ none, theta float, details list). ✅

- **L331-383** `TestCalibrateThetaOutputTypeValidation` (2 tests) : invalid output_type → ValueError, default → regression. ✅

- **L391-401** `TestSignalModelStubIntegration` (2 tests) : vérifie que le stub a `output_type="signal"` et que `predict()` retourne les prédictions binaires inchangées. ✅

- **L404-412** `TestDummyModelRegressionCalibration` (1 test) : vérifie que DummyModel déclare `output_type="regression"`. ✅

- **Seed determinism** : `_make_ohlcv` utilise `np.random.default_rng(42)` seed fixe. Tests regression utilisent `np.random.default_rng(123)`. ✅ déterministe.

- **Pas de dépendance réseau** : données synthétiques uniquement. ✅

- RAS après lecture complète du diff (412 lignes).

#### `docs/tasks/M3/033__ws7_theta_bypass.md` (diff : modifications)

- Statut passé à DONE ✅, critères cochés ✅, checklist mise à jour ✅. RAS.

### B3 — Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_theta_bypass.py`, docstring `#033` |
| Couverture des critères d'acceptation | ✅ | Voir mapping ci-dessous |
| Cas nominaux + erreurs + bords | ✅ | Nominal: 6+3 tests bypass/regression. Erreur: invalid output_type. Bords: all-zero, all-one signals. |
| Boundary fuzzing | ✅ | N/A pour ce module (pas de paramètre numérique à boundary-tester spécifiquement — le bypass est binaire sur output_type) |
| Déterministes | ✅ | Seeds 42, 123 fixées |
| Données synthétiques | ✅ | `_make_ohlcv` avec rng, pas de réseau |
| Portabilité chemins | ✅ | Scan B1: 0 `/tmp` |
| Tests registre réalistes | N/A | Pas de test de registre |
| Contrat ABC complet | ✅ | `_SignalModelStub` implémente fit/predict/save/load |

**Mapping critères d'acceptation → tests :**

| Critère | Test(s) |
|---|---|
| `output_type=="signal"` → bypass | `TestCalibrateThetaBypassSignal` (6 tests) |
| `output_type=="regression"` → normal | `TestCalibrateThetaRegressionNormal` (3 tests) |
| Retour bypass: method="none", theta=None | `test_bypass_returns_method_none`, `test_bypass_returns_theta_none`, `test_bypass_returns_quantile_none`, `test_bypass_no_details` |
| Signaux binaires passés directement | `test_signal_model_predictions_are_binary` |
| Pas de branchement sur strategy.name | Scan B1 : 0 occurrences de `strategy.name` dans le code |
| Test modèle factice signal | `TestSignalModelStubIntegration` |
| Test DummyModel regression | `TestDummyModelRegressionCalibration` |
| Tests erreurs + bords | `test_invalid_output_type_raises`, `test_bypass_all_zero_signals`, `test_bypass_all_one_signals` |

### B4 — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| Strict code (no fallbacks) | ⚠️ | Scan B1: 0 fallback réel (1 FP docstring). MAIS `output_type="regression"` default — voir WARNING #2. |
| Defensive indexing | ✅ | Pas d'indexation/slicing dans le code ajouté |
| Config-driven | ✅ | Le bypass est piloté par `output_type` (attribut modèle depuis config), pas de valeur hardcodée |
| Anti-fuite | ✅ | Scan B1: 0 `.shift(-`. Le bypass ne touche pas aux données — conforme |
| Reproductibilité | ✅ | Scan B1: 0 legacy random. Seeds fixées dans tests |
| Float conventions | N/A | Pas de nouveau calcul numérique (bypass retourne None) |
| Anti-patterns Python | ✅ | Scan B1: 0 mutable defaults, 0 open(), 0 comparaison identité |

### B5 — Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage et style | ✅ | snake_case, noms clairs |
| Pas de code mort/debug | ✅ | Scan B1: 0 print, 0 TODO/FIXME |
| Imports propres / relatifs | ✅ | Scan B1: aucun __init__.py modifié, imports propres |
| DRY | ❌ | `_VALID_OUTPUT_TYPES` dupliquée (BLOQUANT #1). `_make_ohlcv` dupliquée dans tests (MINEUR #3). |

### B5-bis — Bonnes pratiques métier

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | Le bypass est un concept pipeline, pas un calcul financier |
| Nommage métier cohérent | ✅ | `output_type`, `calibrate_threshold`, `bypass` — noms clairs |
| Séparation des responsabilités | ✅ | Le bypass est intégré dans la fonction de calibration, responsabilité unique |
| Invariants de domaine | ✅ | N/A pour le bypass (pas de calcul) |
| Cohérence des unités/échelles | ✅ | N/A |
| Patterns de calcul financier | ✅ | N/A |

### B6 — Conformité spec v1.0

| Critère | Verdict |
|---|---|
| §11.4 — baselines, pas de θ | ✅ — `output_type="signal"` → bypass, `method="none"` |
| §11.5 — RL, `threshold.method = "none"`, `theta = null` | ✅ — conforme exactement |
| Plan WS-7.4 — bypass RL et baselines | ✅ — détection par `output_type`, pas par `strategy.name` |
| Formules doc vs code | ✅ — pas de formule mathématique dans cette tâche |

### B7 — Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | Nouveau paramètre `output_type` ajouté avec default → backward-compatible |
| Clés dict retour | ✅ | Mêmes 7 clés dans bypass et calibration normale |
| Clés de configuration | ✅ | `output_type` vient du modèle (attribut classe), pas de la config YAML |
| Registres et conventions | N/A | Pas de registre modifié |
| Structures de données partagées | ⚠️ | `_VALID_OUTPUT_TYPES` dupliquée — voir BLOQUANT #1 |
| Conventions numériques | ✅ | Bypass retourne None, pas de dtype en jeu |
| Imports croisés | ✅ | Les imports de `threshold.py` (`backtest.costs`, `backtest.engine`) existent dans Max6000i1 |
| Forwarding kwargs | N/A | Pas de wrapper/orchestrateur modifié |

---

## Remarques

1. **[BLOQUANT]** `_VALID_OUTPUT_TYPES` dupliquée entre modules
   - Fichier : `ai_trading/calibration/threshold.py` L128
   - Aussi dans : `ai_trading/models/base.py` L51
   - Description : `frozenset({"regression", "signal"})` définie à l'identique dans deux modules. Si un nouveau `output_type` est ajouté dans un fichier sans l'autre, validation incohérente (drift silencieux).
   - Suggestion : importer `_VALID_OUTPUT_TYPES` depuis `ai_trading.models.base` dans `threshold.py` (pas de cycle d'import), OU extraire vers un module partagé.

2. **[WARNING]** Paramètre `output_type` avec valeur par défaut
   - Fichier : `ai_trading/calibration/threshold.py` L143
   - Description : `output_type: str = "regression"` — le default masque un input manquant. Un futur caller omettant ce paramètre obtiendrait silencieusement la calibration regression. Per §R1 strict code: "no default values that mask missing/invalid inputs."
   - Suggestion : rendre `output_type` obligatoire (supprimer `= "regression"`). Mettre à jour les callers dans `tests/test_theta_optimization.py` pour passer explicitement `output_type="regression"`.

3. **[MINEUR]** `_make_ohlcv` helper dupliqué dans les tests
   - Fichier : `tests/test_theta_bypass.py` L73-88
   - Aussi dans : `tests/test_theta_optimization.py` L32-49, `tests/test_label_target.py` L26
   - Description : Helper quasi-identique dupliqué dans 3+ fichiers de tests. Pattern préexistant mais amplifié par cette PR.
   - Suggestion : extraire dans `tests/conftest.py` lors d'un refactoring test global.

---

## Actions requises

1. **Importer ou mutualiser `_VALID_OUTPUT_TYPES`** (BLOQUANT #1) — supprimer la définition locale dans `threshold.py` et importer depuis `ai_trading.models.base`.
2. **Rendre `output_type` obligatoire** (WARNING #2) — supprimer le default `= "regression"` et mettre à jour tous les callers existants.
3. *(Optionnel, post-merge acceptable)* **Extraire `_make_ohlcv`** dans conftest.py (MINEUR #3).

---

```
RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 1
- Warnings : 1
- Mineurs : 1
- Rapport : docs/tasks/M3/033/review_v1.md
```
