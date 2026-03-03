# Revue PR — [WS-12] #048 — Seed manager

Branche : `task/048-seed-manager`
Tâche : `docs/tasks/M5/048__ws12_seed_manager.md`
Date : 2026-03-03

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Le module `seed.py` et ses tests sont bien implémentés, lisibles, avec une couverture correcte des critères d'acceptation. Cependant, une **incohérence intermodule** existe entre la validation Pydantic de `config.py` (`global_seed: Field(ge=0)` → accepte 0) et la validation dans `seed.py` (`seed < 1` → rejette 0), ce qui provoquerait une erreur runtime pour une config valide. Deux items mineurs complètent le rapport.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/048-seed-manager` | ✅ | `git branch --show-current` → `task/048-seed-manager` |
| Commit RED présent | ✅ | `3a992dd` — `[WS-12] #048 RED: tests seed manager` |
| Commit GREEN présent | ✅ | `c2adc5b` — `[WS-12] #048 GREEN: seed manager` |
| Commit RED contient uniquement tests | ✅ | `git show --stat 3a992dd` → `tests/test_seed_manager.py` (1 file, 288 insertions) |
| Commit GREEN contient implémentation + tâche | ✅ | `git show --stat c2adc5b` → `ai_trading/utils/seed.py`, `docs/tasks/M5/048__ws12_seed_manager.md`, `tests/test_seed_manager.py` (3 files, 100 ins, 24 del) |
| Pas de commits parasites entre RED et GREEN | ✅ | `git log --oneline Max6000i1...HEAD` → exactement 2 commits |

### Tâche

| Critère | Verdict | Commentaire |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` dans le fichier tâche |
| Critères d'acceptation cochés | ✅ (10/10) | Tous `[x]` |
| Checklist cochée | ⚠️ (7/9) | 2 items non cochés : « Commit GREEN » et « Pull Request ouverte » — le commit GREEN existe factuellement (`c2adc5b`) mais la checklist n'a pas été mise à jour pour ces items processus |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1388 passed** en 8.85s, 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** |

**Phase A : PASS** (les 2 items checklist non cochés sont un problème mineur documenté, pas un critère de blocage Phase A).

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| # | Pattern recherché | Règle | Résultat |
|---|---|---|---|
| 1 | Fallbacks silencieux (`or []`, `or {}`, …) | §R1 | 0 occurrences (grep exécuté) |
| 2 | Except trop large (`except:`, `except Exception:`) | §R1 | 0 occurrences (grep exécuté) |
| 3 | `noqa` — suppressions lint | §R7 | 2 matches : `seed.py:49` (`# noqa: NPY002` — justifié : legacy `np.random.seed()` requis pour seed globale) ; `test_seed_manager.py:29` (`# noqa: F401` — justifié : import pour vérif d'existence uniquement) |
| 4 | `per-file-ignores` dans pyproject.toml | §R7 | Non modifié dans cette branche |
| 5 | `print()` résiduel | §R7 | 0 occurrences (grep exécuté) |
| 6 | `.shift(-` (look-ahead) | §R3 | 0 occurrences (grep exécuté) |
| 7 | Legacy random API | §R4 | 2 matches : `seed.py:48` `random.seed(seed)` et `seed.py:49` `np.random.seed(seed)` — **attendu** : c'est le rôle du seed manager |
| 8 | TODO/FIXME/HACK/XXX | §R7 | 0 occurrences (grep exécuté) |
| 9 | Chemins hardcodés `/tmp` | §R7 | 0 occurrences dans les tests (grep exécuté) |
| 10 | Imports absolus `__init__.py` | §R7 | N/A — aucun `__init__.py` modifié |
| 11 | Registration manuelle tests | §R7 | 0 occurrences (grep exécuté) |
| 12 | Mutable default arguments | §R6 | 0 occurrences (grep exécuté) |
| 13 | `open()` sans context manager | §R6 | 0 occurrences (grep exécuté) |
| 14 | Comparaison booléenne par identité | §R6 | 0 occurrences (grep exécuté) |
| 15 | Dict collision silencieuse | §R6 | 0 occurrences (grep exécuté) |
| 16 | Boucle Python sur array numpy | §R9 | 0 occurrences (grep exécuté) |
| 17 | `isfinite` check | §R6 | 0 occurrences — N/A pour ce module (seed est `int`, pas `float`) |
| 18 | Appels numpy compréhension | §R9 | 0 occurrences (grep exécuté) |
| 19 | Fixtures dupliquées (config) | §R7 | 0 occurrences (grep exécuté) |

### Annotations par fichier (B2)

#### `ai_trading/utils/seed.py` (76 lignes — lecture complète)

- **L39–40** `isinstance(seed, bool) or not isinstance(seed, int)` : Correct — vérifie que `bool` (sous-classe de `int`) est rejeté avant le check `int`. RAS.
- **L43–45** `if seed < 1: raise ValueError(...)` : Correct vs la tâche (« strictly positive »). **Mais incohérent avec `config.py` L304** `Field(ge=0)` qui accepte `seed=0`. Voir remarque #1 (WARNING).
- **L48** `random.seed(seed)` : Conforme à la spec §16.1.
- **L49** `np.random.seed(seed)  # noqa: NPY002` : Legacy API justifiée — le rôle est explicitement de fixer la seed globale numpy. Le `noqa` est inévitable et documenté.
- **L50** `os.environ["PYTHONHASHSEED"] = str(seed)` : Conforme à la tâche.
- **L57–59** `try: import torch / except ImportError:` : Import optionnel correct. Log INFO présent. RAS.
- **L62** `torch.manual_seed(seed)` : Conforme §16.1.
- **L63** `torch.cuda.manual_seed_all(seed)` : Conforme à la tâche.
- **L69–76** Fallback `warn_only=True` : Le `except RuntimeError` est spécifique (pas large). Le fallback est documenté dans la docstring et la tâche comme exception au strict-no-fallback. Le warning est loggé au niveau WARNING. Conforme.

RAS après lecture complète du diff (76 lignes).

#### `tests/test_seed_manager.py` (288 lignes — lecture complète)

- **Docstring L1–12** : Identifiant `#048` présent. Mapping AC1–AC8 documenté.
- **TestSeedManagerImport** (L23–36) : Import + callable check. RAS.
- **TestSetGlobalSeedBasic** (L39–80) : Tests `random`, `numpy`, `PYTHONHASHSEED`. Séquences comparées via `==` (random) et `np.testing.assert_array_equal` (numpy). RAS.
- **TestReproducibility** (L83–116) : Double appel même seed → séquences identiques. Différentes seeds → séquences différentes. RAS.
- **TestValidation** (L119–170) : seed=-1, 0, float, None, string, bool → erreurs explicites. Large seed `2**31 - 1` accepté. RAS.
- **TestPyTorchOptional** (L173–202) : `mock.patch.dict(sys.modules, {"torch": None})` pour simuler l'absence de PyTorch. Vérifie le log INFO et `deterministic_torch=True` sans crash. RAS.
- **TestPyTorchDeterministic** (L205–268) : Mock complet de `torch` via `MagicMock`. Vérifie appels `manual_seed`, `cuda.manual_seed_all`, `use_deterministic_algorithms`. Test du fallback `warn_only=True` avec `side_effect=[RuntimeError, None]`. Vérifie le WARNING loggé. RAS.
- **TestEdgeCases** (L271–288) : `seed=1` (boundary), appels consécutifs. RAS.

RAS après lecture complète du diff (288 lignes).

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ⚠️ | Le plan spécifie `test_seed.py` (implementation.md L1042), le fichier réel est `test_seed_manager.py`. Écart mineur, voir remarque #3. |
| ID tâche dans docstring | ✅ | `(#048)` en L1 de la docstring |
| Couverture des critères AC | ✅ | AC1: TestSeedManagerImport, AC2: TestSetGlobalSeedBasic, AC3: TestPyTorchDeterministic, AC4: TestPyTorchOptional, AC5: TestPyTorchDeterministic.test_deterministic_fallback_warn_only, AC6: TestReproducibility, AC7: TestValidation, AC8: TestEdgeCases |
| Cas nominaux + erreurs + bords | ✅ | Nominaux (random/numpy/PYTHONHASHSEED), erreurs (TypeError, ValueError × 6 types), bords (seed=1, seed=2³¹−1, appels consécutifs) |
| Boundary fuzzing seed | ✅ | seed=0 (invalid boundary), seed=1 (min valid), seed=-1 (négatif), seed=2³¹−1 (max 32-bit), seed=True (bool), seed=None, seed=float, seed=string |
| Déterministes | ✅ | Seeds fixes (42, 99, 123) dans tous les tests |
| Pas de dépendance réseau | ✅ | Données synthétiques uniquement (random/numpy séquences) |
| Portabilité chemins | ✅ | Aucun chemin `/tmp` (scan B1 #9) |
| Tests registre réalistes | N/A | Module non concerné (pas de registre) |
| Contrat ABC complet | N/A | Module non concerné (pas d'ABC) |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 #1, #2 : 0 fallback silencieux, 0 except large. Le seul `except RuntimeError` est l'exception documentée pour le fallback `warn_only` CUDA. |
| §R10 Defensive indexing | N/A | Pas d'indexation array dans ce module |
| §R2 Config-driven | ✅ | Le module reçoit `seed` et `deterministic_torch` en argument — la lecture depuis config sera faite par l'orchestrateur (WS-12.2). Pas de valeur hardcodée. |
| §R3 Anti-fuite | N/A | Module utilitaire, pas de données temporelles |
| §R4 Reproductibilité | ✅ | Scan B1 #7 : `random.seed()` et `np.random.seed()` sont le rôle du module. Pas de legacy API utilisée *hors* du seed manager. |
| §R5 Float conventions | N/A | Pas de tenseurs ni métriques dans ce module |
| §R6 Anti-patterns Python | ✅ | Scans B1 #12–18 : 0 mutable defaults, 0 open(), 0 bool identité, 0 dict collision. `isinstance(seed, bool)` avant `isinstance(seed, int)` correct. |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `set_global_seed`, `deterministic_torch`, `logger` |
| Pas de code mort/debug | ✅ | Scan B1 #5 (print), #8 (TODO) : 0 occurrences |
| Imports propres | ✅ | stdlib → third-party → local, pas d'imports inutilisés |
| `noqa` justifiés | ✅ | `NPY002` (legacy API requise), `F401` (import existence) |
| DRY | ✅ | Aucune duplication |
| `__init__.py` à jour | ✅ | `ai_trading/utils/__init__.py` existe avec docstring. Le module `seed` n'a pas besoin d'import side-effect dans `__init__.py` (appelé explicitement). |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Commentaire |
|---|---|---|
| Spécification §16.1 | ✅ | Seeds fixés pour : numpy/random (L48–49), PyTorch (L62–63), PYTHONHASHSEED (L50). XGBoost `random_state` explicitement délégué au modèle (conformément à la spec et la tâche). |
| Plan WS-12.1 | ✅ | Fonction `set_global_seed(seed, deterministic_torch)` conforme. Fallback CUDA documenté. Import optionnel PyTorch. |
| Formules doc vs code | N/A | Pas de formule mathématique dans ce module |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signature compatible | ✅ | `set_global_seed(seed: int, deterministic_torch: bool)` — l'orchestrateur (WS-12.2, pas encore implémenté) passera `config.reproducibility.global_seed` et `config.reproducibility.deterministic_torch`. Types cohérents. |
| Config model vs validation | ⚠️ | **Incohérence** : `config.py` L304 `global_seed: int = Field(ge=0)` accepte `seed=0`, mais `seed.py` L43 `if seed < 1: raise ValueError` rejette 0. Voir remarque #1. |

---

## Remarques

1. **[WARNING] Incohérence intermodule : validation seed=0 divergente entre config.py et seed.py**
   - Fichier : `ai_trading/config.py` L304 vs `ai_trading/utils/seed.py` L43–45
   - Constat : `ReproducibilityConfig.global_seed` est défini avec `Field(ge=0)` → accepte `seed=0`. Mais `set_global_seed()` lève `ValueError` si `seed < 1`. Un utilisateur configurant `global_seed: 0` passerait la validation Pydantic mais obtiendrait une erreur runtime dans le seed manager.
   - Suggestion : aligner les deux validations. La tâche spécifie « strictly positive (>= 1) ». Modifier `config.py` : `global_seed: int = Field(ge=1)` pour que l'erreur soit détectée au chargement de la config, pas au runtime.

2. **[MINEUR] Checklist de tâche partiellement non cochée**
   - Fichier : `docs/tasks/M5/048__ws12_seed_manager.md`
   - Constat : 2 items de la checklist restent `[ ]` (« Commit GREEN » et « Pull Request ouverte ») alors que le commit GREEN existe (`c2adc5b`).
   - Suggestion : cocher ces items lors du prochain commit.

3. **[MINEUR] Nom du fichier de test vs plan d'implémentation**
   - Fichier : `tests/test_seed_manager.py`
   - Constat : le plan (`docs/plan/implementation.md` L1042) prescrit `test_seed.py`, le fichier réel est `test_seed_manager.py`.
   - Suggestion : aligner le nom du fichier sur le plan (`test_seed.py`) ou mettre à jour le plan pour refléter le choix `test_seed_manager.py`.

---

## Résumé

Le code est propre, minimaliste et conforme au rôle défini en spec §16.1 et plan WS-12.1. Les tests couvrent l'ensemble des critères d'acceptation avec des mocks appropriés pour PyTorch. L'incohérence de validation entre `config.py` (`ge=0`) et `seed.py` (`>= 1`) constitue le seul point d'attention fonctionnel (WARNING) — elle est hors périmètre strict de cette branche mais crée un bug latent d'intégration à corriger.
