# Revue PR — [WS-7] #033 — Bypass calibration θ pour RL et baselines (v2)

Branche : `task/033-theta-bypass`
Tâche : `docs/tasks/M3/033__ws7_theta_bypass.md`
Date : 2025-03-02
Itération : v2 (post-corrections v1)

## Verdict global : ✅ CLEAN

## Résumé

La tâche #033 implémente le bypass de la calibration θ pour les modèles de type `output_type="signal"` (RL, baselines). Les 3 corrections de la v1 (DRY `VALID_OUTPUT_TYPES`, `output_type` obligatoire, extraction `make_calibration_ohlcv`) sont correctement appliquées. Le code est strict, conforme à la spec (§11.4, §11.5), et les 899 tests passent sans erreur.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/033-theta-bypass` | ✅ | `git branch --show-current` → `task/033-theta-bypass` |
| Commit RED présent | ✅ | `35e91aa` — `[WS-7] #033 RED: tests bypass calibration θ pour signal models` |
| Commit GREEN présent | ✅ | `e7b09e2` — `[WS-7] #033 GREEN: bypass calibration θ pour RL et baselines` |
| Commit RED = tests uniquement | ✅ | `git show --stat 35e91aa` → 1 fichier : `tests/test_theta_bypass.py` (413 insertions) |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat e7b09e2` → `ai_trading/calibration/threshold.py`, `docs/tasks/M3/033__ws7_theta_bypass.md`, `tests/test_theta_bypass.py` |
| Commit FIX = corrections v1 | ✅ | `21e6061` — `[WS-7] #033 FIX: DRY output_types, strict output_type param, extract _make_ohlcv` — 6 fichiers modifiés |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1..HEAD` → 3 commits (RED, GREEN, FIX) |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (10/10) |
| Checklist cochée | ✅ (8/9 — seul « PR ouverte » non coché, attendu) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **899 passed**, 0 failed (6.17s) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 — Fallbacks silencieux | `grep ' or []\|if.*else '` sur src | 1 match — `threshold.py:68` = faux positif (docstring : « 1 if y_hat[t] > theta, else 0 ») |
| §R1 — Except trop large | `grep 'except:$\|except Exception:'` sur src | 0 occurrences |
| §R7 — noqa | `grep 'noqa'` sur tous fichiers | 3 matches — `test_theta_bypass.py:39,41,53` = `# noqa: N803` sur `X_train`, `X_val`, `X` (noms imposés par ABC) — **justifiés** |
| §R7 — Print résiduel | `grep 'print('` sur src | 0 occurrences |
| §R3 — Shift négatif | `grep '.shift(-'` sur src | 0 occurrences |
| §R4 — Legacy random API | `grep 'np.random.seed\|randn\|RandomState\|random.seed'` | 0 occurrences |
| §R7 — TODO/FIXME | `grep 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences |
| §R7 — Chemins hardcodés tests | `grep '/tmp\|C:\\'` sur tests | 0 occurrences |
| §R7 — Imports absolus `__init__` | `grep 'from ai_trading\.'` sur `__init__.py` modifiés | Aucun `__init__.py` modifié dans cette PR |
| §R7 — Registration manuelle tests | `grep 'register_model\|register_feature'` sur tests | 1 match — `conftest.py:164` = commentaire de docstring, pas d'appel manuel |
| §R6 — Mutable defaults | `grep 'def.*=[]\|def.*={}'` | 0 occurrences |
| §R6 — open() sans context manager | `grep 'read_text\|open('` sur src | 0 occurrences |
| §R6 — Boolean identity | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences |
| §R6 — isfinite | `grep 'isfinite'` sur src | 1 match — `threshold.py:51` : `math.isfinite(q)` dans `compute_quantile_thresholds` — **correct** |
| §R9 — for range (vectorisation) | `grep 'for.*in range'` sur src | 0 occurrences |
| §R9 — np.*comprehension | `grep 'np\.[a-z]*(.*for.*in '` sur src | 0 occurrences |
| §R7 — Fixtures dupliquées | `grep 'load_config.*configs/'` sur tests | 0 occurrences |
| §R7 — per-file-ignores | `grep 'per-file-ignores' pyproject.toml` | Ligne 51 — contenu pré-existant, non modifié par cette PR |

### Annotations par fichier (B2)

#### `ai_trading/calibration/threshold.py`

**Diff : +27 lignes, -1 ligne** (import VALID_OUTPUT_TYPES + output_type param + bypass logic)

- **L14** `from ai_trading.models.base import VALID_OUTPUT_TYPES` : Import correct. La constante est définie une seule fois dans `base.py` et importée ici → DRY respecté (correction v1 #1).
- **L142** `output_type: str,` : Paramètre obligatoire, sans valeur par défaut → strict code respecté (correction v1 #2).
- **L176-179** Validation de `output_type` via `VALID_OUTPUT_TYPES` : Validation explicite avant usage, `ValueError` levée si invalide → conforme §R1.
- **L182-191** Bypass signal : retourne immédiatement un dict avec `method="none"`, `theta=None`, `quantile=None`, `details=None` → conforme spec §11.4/§11.5.
- **L182** Bypass placé **avant** la validation des autres paramètres (`y_hat_val`, `ohlcv_val`, `q_grid`, etc.) : ceci signifie que pour `output_type="signal"`, les paramètres `y_hat_val`, `ohlcv_val`, etc. ne sont **pas validés**. C'est cohérent avec le bypass total — ces paramètres ne sont pas utilisés. Acceptable.
- Docstring mise à jour avec description du bypass et du paramètre `output_type`. RAS.

RAS après lecture complète du diff (27 lignes ajoutées).

#### `ai_trading/models/base.py`

**Diff : +3 lignes, -3 lignes** (renommage `_VALID_OUTPUT_TYPES` → `VALID_OUTPUT_TYPES`)

- **L51** `VALID_OUTPUT_TYPES = frozenset({"regression", "signal"})` : Constante rendue publique (retrait du `_` prefix) pour permettre l'import par `threshold.py` → correction v1 #1 validée.
- **L162, L164** : Usages mis à jour dans `__init_subclass__` → cohérent.

RAS après lecture complète du diff (3 lignes modifiées).

#### `tests/test_theta_bypass.py`

**14 tests couvrant : bypass signal (6), regression normal (3), output_type validation (2), integration stub (2), DummyModel (1).**

- **L22** `from tests.conftest import make_calibration_ohlcv` : Import de la fixture partagée → correction v1 #3 validée.
- **L30-62** `_SignalModelStub(BaseModel)` : Stub local avec `output_type = "signal"`, implémente toutes les méthodes abstraites. `noqa: N803` justifiés (noms ABC). RAS.
- **L82-222** `TestCalibrateThetaBypassSignal` : 6 tests vérifient `method="none"`, `theta=None`, `quantile=None`, `details=None`, all-zero, all-one. Couverture exhaustive du bypass. RAS.
- **L229-310** `TestCalibrateThetaRegressionNormal` : 3 tests vérifient que regression passe en calibration normale (method ≠ "none", theta float, details list). RAS.
- **L318-357** `TestCalibrateThetaOutputTypeValidation` : Test `"invalid_type"` → `ValueError`. Test sans `output_type` → `TypeError`. Strict code vérifié.
- **L365-393** `TestSignalModelStubIntegration` + `TestDummyModelRegressionCalibration` : Tests d'intégration vérifient `output_type` des modèles concrets. RAS.

RAS après lecture complète du fichier (393 lignes).

#### `tests/test_theta_optimization.py`

**Diff : ajout de `output_type="regression"` à tous les appels `calibrate_threshold` + remplacement `_make_ohlcv` → `make_calibration_ohlcv`.**

- **L24** `from tests.conftest import make_calibration_ohlcv` : Import ajouté. RAS.
- **L30** Suppression de la fonction locale `_make_ohlcv` (20 lignes) → DRY respecté.
- Tous les appels `calibrate_threshold(...)` reçoivent maintenant `output_type="regression"` → conforme au nouveau paramètre obligatoire.
- Remplacement de `_make_ohlcv(n)` → `make_calibration_ohlcv(n)` dans 13 call sites. La fonction `make_calibration_ohlcv` utilise les mêmes seed/params que l'ancien `_make_ohlcv` de ce fichier → pas de changement de comportement pour ces tests.

RAS après lecture complète du diff (~100 lignes modifiées, toutes mécaniques).

#### `tests/test_label_target.py`

**Diff : suppression de `_make_ohlcv` local + import `make_calibration_ohlcv` + remplacement des appels.**

- **L19** Import ajouté, **L15** import `pandas` retiré (plus nécessaire sans `_make_ohlcv` local). RAS.
- La fonction `make_calibration_ohlcv` a des paramètres légèrement différents de l'ancien `_make_ohlcv` local (offset +50 vs +10, variation plus faible des opens). Les tests vérifient des propriétés mathématiques (log returns) calculées à partir des données générées, pas des valeurs hardcodées → pas de régression. Tous les 899 tests passent.

RAS après lecture complète du diff (~40 lignes modifiées).

#### `tests/conftest.py`

**Diff : +33 lignes — ajout de `make_calibration_ohlcv`.**

- **L106-132** `make_calibration_ohlcv(n, seed, start)` : Fonction déterministe (seed=42, `np.random.default_rng`), prix positifs (`np.abs + 50.0`), open/close distincts, OHLCV valide (high >= max(open,close), low <= min(open,close)). RAS.
- Docstring mentionne les 3 fichiers utilisateurs : `test_theta_optimization`, `test_theta_bypass`, `test_label_target`. RAS.

RAS après lecture complète du diff (33 lignes ajoutées).

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères | ✅ | Voir mapping ci-dessous |
| Cas nominaux + erreurs + bords | ✅ | 6 bypass nominal, 3 regression nominal, 2 erreurs (invalid type, missing param), 2 bords (all-zero, all-one) |
| Boundary fuzzing | ✅ | `output_type=""` → erreur, `output_type` omis → TypeError, signaux all-0, all-1 |
| Déterministes | ✅ | `np.random.default_rng(42)`, `np.random.default_rng(123)` |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` dans tests |
| Tests registre réalistes | N/A | Pas de test de registre dans #033 |
| Contrat ABC complet | N/A | Pas de modification des méthodes ABC |

**Mapping critères d'acceptation → tests :**

| # | Critère | Test(s) |
|---|---|---|
| 1 | signal → bypass total | `test_bypass_returns_method_none`, `test_bypass_returns_theta_none`, `test_bypass_returns_quantile_none`, `test_bypass_no_details` |
| 2 | regression → calibration normale | `test_regression_calibration_has_method_quantile_grid`, `test_regression_calibration_has_theta_float`, `test_regression_calibration_has_details` |
| 3 | Bypass: method="none", theta=None | `test_bypass_returns_method_none`, `test_bypass_returns_theta_none` |
| 4 | Signaux binaires passés directement | `test_signal_model_predictions_are_binary` |
| 5 | Pas de branchement sur strategy.name | `grep 'strategy.name' threshold.py` → 0 occurrences |
| 6 | Test signal model → bypass | `TestCalibrateThetaBypassSignal` (6 tests) + `TestSignalModelStubIntegration` |
| 7 | Test DummyModel regression → normal | `TestDummyModelRegressionCalibration::test_dummy_model_is_regression` + `TestCalibrateThetaRegressionNormal` |
| 8 | Nominaux + erreurs + bords | 6 nominaux + 2 erreurs + 2 bords + 3 regression + 1 DummyModel = 14 tests |
| 9 | Suite verte | 899 passed, 0 failed |
| 10 | Ruff clean | All checks passed |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 — Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback (1 faux positif docstring). `output_type` obligatoire, validation explicite + `raise ValueError`. |
| §R10 — Defensive indexing | ✅ | Pas d'indexation/slicing dans le nouveau code |
| §R2 — Config-driven | ✅ | Pas de valeur hardcodée — `output_type` transmis par l'appelant |
| §R3 — Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. Bypass ne touche pas aux données. |
| §R4 — Reproductibilité | ✅ | Scan B1 : 0 legacy random. Seeds `default_rng` dans tests/conftest. |
| §R5 — Float conventions | ✅ | Pas de tenseurs X_seq/y dans le diff. Bypass retourne `None`. |
| §R6 — Anti-patterns Python | ✅ | Scan B1 : 0 mutable default, 0 open() sans CM, 0 boolean identity. `isfinite` présent dans `compute_quantile_thresholds`. |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage et style | ✅ | snake_case, noms expressifs (`make_calibration_ohlcv`, `output_type`, `VALID_OUTPUT_TYPES`) |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO |
| Imports propres / relatifs | ✅ | Imports explicites, pas d'imports `*`. Aucun `__init__.py` modifié dans cette PR. |
| DRY | ✅ | `VALID_OUTPUT_TYPES` défini une seule fois (base.py L51) et importé (threshold.py L14). `make_calibration_ohlcv` défini une seule fois (conftest.py L106) et importé dans 3 fichiers de test. |
| noqa justifiés | ✅ | 3× `N803` pour params ABC `X_train`, `X_val`, `X` — imposés par l'interface, inévitables |

### Conformité spec v1.0 (B6)

| Critère | Verdict |
|---|---|
| Spécification §11.4 (baselines) | ✅ — `output_type="signal"` → bypass total, pas de θ |
| Spécification §11.5 (RL PPO) | ✅ — `theta = None`, `method = "none"` |
| Plan WS-7.4 | ✅ — Bypass basé sur `output_type`, pas sur `strategy.name` |
| Formules doc vs code | ✅ — Pas de formule mathématique dans #033 (bypass = skip) |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `calibrate_threshold` a un nouveau param `output_type: str` sans default — tous les appels existants dans `test_theta_optimization.py` mis à jour avec `output_type="regression"` |
| Clés de configuration | ✅ | Pas de nouvelle clé config — `output_type` vient du modèle |
| Imports croisés | ✅ | `threshold.py` importe `VALID_OUTPUT_TYPES` de `base.py` — symbole existant sur `Max6000i1` (renommé de `_VALID_OUTPUT_TYPES`) |
| Conventions numériques | N/A | Bypass retourne `None`, pas de calcul numérique |
| Forwarding complet kwargs | ✅ | `output_type` est un nouveau param de `calibrate_threshold` — il sera transmis par l'orchestrateur dans WS-12 |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts | ✅ | Signal models producent directement des signaux binaires → pas de θ, conforme au domaine |
| Nommage métier | ✅ | `output_type`, `bypass`, `signal`, `regression` — termes clairs |
| Séparation des responsabilités | ✅ | Le bypass est dans le module de calibration, pas dans le modèle |
| Invariants de domaine | ✅ | `VALID_OUTPUT_TYPES` = `{"regression", "signal"}` — validation stricte |

---

## Vérification des corrections v1

| # | Item v1 | Statut | Preuve |
|---|---|---|---|
| 1 | BLOQUANT: `VALID_OUTPUT_TYPES` DRY | ✅ Corrigé | `base.py:51` définit, `threshold.py:14` importe. `grep VALID_OUTPUT_TYPES` confirme 0 duplication. |
| 2 | WARNING: `output_type` obligatoire | ✅ Corrigé | `threshold.py:142` — `output_type: str` sans default. Test `test_default_output_type_is_regression` vérifie `TypeError` si omis. |
| 3 | MINEUR: `make_calibration_ohlcv` extrait | ✅ Corrigé | `conftest.py:106` définit. 3 fichiers de test importent. `grep 'def _make_ohlcv'` dans fichiers modifiés → 0 (supprimées). |

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
- Rapport : docs/tasks/M3/033/review_v2.md
```
