# Revue PR — [WS-6] #034 — Pré-gate G-Doc (vérification structurelle M3)

Branche : `task/034-gate-doc`
Tâche : `docs/tasks/M3/034__ws6_gate_doc.md`
Date : 2025-03-02
Itération : v1

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Tâche purement test (18 tests, 0 code de production) couvrant les 6 critères G-Doc. La qualité est globalement bonne : structure TDD respectée, tests passants (917/917), ruff clean, bonne utilisation des fixtures partagées. Un item MINEUR identifié : code mort (`_SignalStub` définie mais jamais utilisée).

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/034-gate-doc` | ✅ | `git branch --show-current` → `task/034-gate-doc` |
| Commit RED présent | ✅ | `f1c2488 [WS-6] #034 RED: tests pré-gate G-Doc (6 critères structurels)` |
| Commit GREEN présent | ✅ | `b3320ca [WS-6] #034 GREEN: pré-gate G-Doc validé (18 tests, 6 critères)` |
| Commit RED = tests uniquement | ✅ | `git show --stat f1c2488` → 1 file: `tests/test_gate_doc.py` (+290 lines) |
| Commit GREEN = tâche uniquement | ✅ | `git show --stat b3320ca` → 1 file: `docs/tasks/M3/034__ws6_gate_doc.md` (+17/-17) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1..HEAD` → 2 commits exactement |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (9/9) |
| Checklist cochée | ✅ (7/9 — les 2 non cochés sont « Commit GREEN » et « Pull Request » = items post-commit, attendu) |

**Vérification critère-par-critère :**

| Critère d'acceptation | Test(s) associé(s) | Verdict |
|---|---|---|
| G-Doc 1 : `output_type == "regression"` | `TestCriterion1OutputType::test_output_type_value` (L90) | ✅ |
| G-Doc 2 : `execution_mode == "standard"` | `TestCriterion2ExecutionMode::test_execution_mode_value` (L105) | ✅ |
| G-Doc 3 : `MODEL_REGISTRY ⊆ VALID_STRATEGIES` | `TestCriterion3RegistryCoherence::test_registry_subset_of_valid_strategies` (L122) | ✅ |
| G-Doc 4 : docstrings conformes | `TestCriterion4Docstrings` (7 tests, L134-198) | ✅ |
| G-Doc 5 : bypass θ signal | `TestCriterion5BypassTheta` (2 tests, L204-237) | ✅ |
| G-Doc 6 : θ indépendant y_hat_test | `TestCriterion6AntiLeakCalibration::test_theta_independent_of_y_hat_test` (L249) | ✅ |
| Tous les tests passent | `pytest tests/test_gate_doc.py -v` → 18 passed | ✅ |
| Suite complète verte | `pytest tests/ -v` → 917 passed, 0 failed | ✅ |
| Ruff clean | `ruff check ai_trading/ tests/` → All checks passed | ✅ |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **917 passed**, 0 failed |
| `pytest tests/test_gate_doc.py -v` | **18 passed**, 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| Fallbacks silencieux (§R1) | `grep ' or []\| or {}...'` | 0 occurrences |
| Except trop large (§R1) | `grep 'except:$\|except Exception:'` | 0 occurrences |
| Print résiduel (§R7) | `grep 'print('` | 0 occurrences |
| Shift négatif (§R3) | `grep '.shift(-'` | 0 occurrences |
| Legacy random API (§R4) | `grep 'np.random.seed\|...'` | 0 occurrences |
| TODO/FIXME orphelins (§R7) | `grep 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences |
| Chemins hardcodés (§R7) | `grep '/tmp\|C:\\'` | 0 occurrences |
| noqa suppressions (§R7) | `grep 'noqa'` | 3 matches (L38, L40, L52) — analyse ci-dessous |
| Registration manuelle (§R7) | `grep 'register_model\|register_feature'` | 0 occurrences |
| Mutable defaults (§R6) | `grep 'def .*=\[\]\|def .*={}'` | 0 occurrences |
| `is True/is False` (§R6) | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences |
| skip/xfail (§B3) | `grep 'skip\|xfail'` | 0 occurrences |

**Analyse noqa (L38, L40, L52)** : 3× `# noqa: N803` pour paramètres `X_train`, `X_val`, `X` dans `_SignalStub`. Convention projet pour noms de matrices — justifié. Cependant, `_SignalStub` elle-même est du code mort (voir remarque 1), donc ces suppressions sont inutiles.

### Annotations par fichier (B2)

> Périmètre : aucun fichier source `ai_trading/` modifié. Seul `tests/test_gate_doc.py` est dans le diff (296 lignes de diff, 290 lignes ajoutées).

#### `tests/test_gate_doc.py`

- **L31-61** `class _SignalStub(BaseModel)` : Classe définie mais **jamais instanciée ni référencée** dans aucun test. `grep -n '_SignalStub'` confirme une seule occurrence (L31, la définition). Les tests du critère 5 passent `output_type="signal"` directement à `calibrate_threshold` sans utiliser ce stub. Code mort.
  Sévérité : **MINEUR**
  Suggestion : Supprimer la classe `_SignalStub` et ses imports devenus inutiles (`Path`, `Any` potentiellement, `inspect` reste nécessaire pour le critère 6). Vérifier si `Path` et `Any` sont utilisés ailleurs avant suppression.

- **L69-79** `_CALIB_KWARGS` : Constantes de calibration hardcodées — correct pour des données de test synthétiques. RAS.

- **L87-96** `TestCriterion1OutputType` : Deux assertions pertinentes — valeur et localisation en tant qu'attribut de classe. RAS.

- **L102-113** `TestCriterion2ExecutionMode` : Bonne vérification que `execution_mode` est hérité (pas dans `__dict__` de DummyModel). RAS.

- **L119-128** `TestCriterion3RegistryCoherence` : Test de sous-ensemble `<=` correct (pas d'égalité — conforme à la note de la tâche sur M4). `"dummy" in MODEL_REGISTRY` confirme le minimum M3. RAS.

- **L134-198** `TestCriterion4Docstrings` : 7 tests couvrant BaseModel, DummyModel, les 4 méthodes abstraites, vérification formes (`"N"`, `"float32"`) et test `__isabstractmethod__`. Complet et bien structuré. RAS.

- **L204-237** `TestCriterion5BypassTheta` : 2 tests vérifiant le bypass. Utilise `make_calibration_ohlcv(n)` de conftest (bonne réutilisation). Assertions sur `method=="none"`, `theta is None`, `quantile is None`, `details is None`. RAS.

- **L249-290** `TestCriterion6AntiLeakCalibration` : Approche en deux volets : (a) recalibration identique → même θ, (b) inspection de signature pour garantie structurelle (`"y_hat_test" not in param_names`). Les variables `y_hat_test_a`/`y_hat_test_b` sont créées pour illustrer le scénario mais assignées à `_` — pattern inhabituel mais fonctionnel et commenté. Vérification indépendante : `inspect.signature(calibrate_threshold)` confirme que `y_hat_test` n'est pas un paramètre. RAS sur la logique.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_gate_doc.py`, `#034` dans la docstring du module |
| Couverture des critères | ✅ | 6/6 critères → 6 classes de test, 18 tests (mapping ci-dessus) |
| Cas nominaux + bords | ✅ | Attributs classe vs instance (C1-C2), héritage vérifié (C2), sous-ensemble vs égalité (C3), signature inspection (C6) |
| Boundary fuzzing | N/A | Pas de paramètres numériques d'entrée à fuzzer (tests structurels) |
| Déterministes | ✅ | `np.random.default_rng(99)` pour C6, `make_calibration_ohlcv(seed=42)` pour C5 et C6 |
| Données synthétiques | ✅ | `make_calibration_ohlcv` + `rng.standard_normal` — aucun réseau |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp`, aucun chemin OS-spécifique |
| Tests registre réalistes | N/A | Le test C3 vérifie `MODEL_REGISTRY` importé (side-effect du module load), pas de registration manuelle |
| Pas de skip/xfail | ✅ | Scan B1 : 0 occurrences |
| Réutilisation fixtures | ✅ | `make_calibration_ohlcv` importée de `tests.conftest` (pas dupliquée) |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| Strict code (no fallbacks) (§R1) | ✅ | Scan B1 : 0 fallback, 0 except large |
| Config-driven (§R2) | N/A | Pas de code de production modifié |
| Anti-fuite (§R3) | ✅ | Scan B1 : 0 `.shift(-`. Critère 6 teste explicitement l'anti-fuite calibration |
| Reproductibilité (§R4) | ✅ | Scan B1 : 0 legacy random. Seeds fixées (`default_rng(99)`, `seed=42`) |
| Float conventions (§R5) | ✅ | `np.float32` utilisé correctement pour y_hat et signaux synthétiques |
| Anti-patterns Python (§R6) | ✅ | Scan B1 : 0 mutable default, 0 `is True/False`. Imports corrects |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage et style | ✅ | snake_case, classes TestCriterionN cohérentes |
| Pas de code mort/debug | ❌ | `_SignalStub` (L31-61) jamais utilisée → voir remarque 1 |
| Imports propres | ✅ | Imports séparés correctement (stdlib → third-party → local) |
| noqa justifiés | ⚠️ | 3× N803 justifiés par convention spec, mais dans du code mort |
| DRY | ✅ | `_CALIB_KWARGS` partagé entre C5 et C6, `make_calibration_ohlcv` réutilisé |

### Conformité spec v1.0 (B6)

| Critère | Verdict |
|---|---|
| Spécification (§10, §11) | ✅ — Les 6 critères G-Doc du plan sont couverts |
| Plan d'implémentation | ✅ — Conforme au pré-gate G-Doc décrit dans le plan |
| Formules doc vs code | N/A — Pas de formules dans cette tâche |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Imports croisés | ✅ | `calibrate_threshold`, `VALID_STRATEGIES`, `MODEL_REGISTRY`, `BaseModel`, `DummyModel` existent dans Max6000i1 |
| Signatures | ✅ | `calibrate_threshold` signature vérifiée par `inspect.signature` dans le test même |

---

## Remarques

1. **[MINEUR]** Code mort : classe `_SignalStub` (L31-61)
   - Fichier : `tests/test_gate_doc.py`
   - Ligne(s) : 31-61
   - La classe `_SignalStub(BaseModel)` est définie avec ses méthodes `fit`, `predict`, `save`, `load` mais **jamais instanciée ni référencée** (confirmé par `grep -n '_SignalStub'` → 1 seule occurrence à la définition). Les tests du critère 5 utilisent `output_type="signal"` comme paramètre direct de `calibrate_threshold`. Ceci entraîne également 3 suppressions `# noqa: N803` inutiles et des imports potentiellement superflus (`Path`, `Any` — à vérifier si utilisés ailleurs).
   - Suggestion : Supprimer `_SignalStub` et ses 3 `# noqa: N803`. Vérifier que `Path` est encore nécessaire (utilisé nulle part sinon → supprimer). `Any` est utilisé dans le même fichier si `_SignalStub` est retirée → vérifier. `inspect` reste nécessaire pour le critère 6.

---

## Résumé

Tâche de qualité : 18 tests couvrant fidèlement les 6 critères G-Doc du plan, structure TDD respectée (RED/GREEN propres), aucune régression (917 tests verts), ruff clean. Un seul item MINEUR identifié (code mort `_SignalStub`), insuffisant pour CLEAN mais sans impact fonctionnel.

---

```
RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 0
- Mineurs : 1
- Rapport : docs/tasks/M3/034/review_v1.md
```
