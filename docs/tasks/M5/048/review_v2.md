# Revue PR — [WS-12] #048 — Seed manager (v2)

Branche : `task/048-seed-manager`
Tâche : `docs/tasks/M5/048__ws12_seed_manager.md`
Date : 2026-03-03
Itération : v2 (suite review v1 → REQUEST CHANGES, 1 WARNING + 2 MINEURs)

## Verdict global : ✅ CLEAN

## Résumé

Les 3 items identifiés en v1 (incohérence config `ge=0` vs seed `>= 1`, checklist incomplète, nom de fichier test) sont tous corrigés dans le commit FIX `31968b8`. Le module `seed.py` et ses tests sont propres, conformes à la spec §16.1 et au plan WS-12.1. Aucun nouvel item identifié.

---

## Suivi des items v1

| # | Sévérité | Description | Statut |
|---|---|---|---|
| 1 | WARNING | `config.py` `Field(ge=0)` vs `seed.py` `seed < 1` — incohérence intermodule | ✅ CORRIGÉ — `config.py` L304 modifié en `Field(ge=1)` + test `test_global_seed_zero_raises` ajouté dans `test_config_validation.py` |
| 2 | MINEUR | Checklist tâche partiellement non cochée (Commit GREEN, PR ouverte) | ✅ CORRIGÉ — tous les items `[x]` dans la tâche |
| 3 | MINEUR | Fichier test nommé `test_seed_manager.py` au lieu de `test_seed.py` (plan) | ✅ CORRIGÉ — renommé en `test_seed.py` dans le commit FIX |

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/048-seed-manager` | ✅ | `git branch --show-current` → `task/048-seed-manager` |
| Commit RED présent | ✅ | `3a992dd` — `[WS-12] #048 RED: tests seed manager` |
| Commit GREEN présent | ✅ | `c2adc5b` — `[WS-12] #048 GREEN: seed manager` |
| Commit RED contient uniquement tests | ✅ | `git show --stat 3a992dd` → `tests/test_seed_manager.py` (1 fichier, 288 insertions) |
| Commit GREEN contient implémentation + tâche | ✅ | `git show --stat c2adc5b` → `ai_trading/utils/seed.py`, `docs/tasks/M5/048__ws12_seed_manager.md`, `tests/test_seed_manager.py` (3 fichiers) |
| Pas de commits parasites entre RED et GREEN | ✅ | `git log --oneline Max6000i1..HEAD` → RED, GREEN, FIX (le FIX est post-GREEN, correction de review v1) |

### Commit FIX (post-review v1)

| Critère | Verdict | Preuve |
|---|---|---|
| Format | ✅ | `31968b8` — `[WS-12] #048 FIX: align global_seed validation ge=1, rename test file, complete checklist` |
| Contenu | ✅ | `git show --stat 31968b8` → `ai_trading/config.py` (1 ligne), `tests/test_config_validation.py` (+5 lignes), rename `test_seed_manager.py` → `test_seed.py`, tâche mise à jour |
| Tests toujours verts | ✅ | Vérifié ci-dessous (pytest 1389 passed) |

### Tâche

| Critère | Verdict | Commentaire |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` dans le fichier tâche |
| Critères d'acceptation cochés | ✅ (10/10) | Tous `[x]` |
| Checklist cochée | ✅ (9/9) | Tous `[x]` (corrigé depuis v1) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1389 passed** en 9.13s, 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** |

**Phase A : PASS**

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| # | Pattern recherché | Règle | Commande | Résultat |
|---|---|---|---|---|
| 1 | Fallbacks silencieux | §R1 | `grep -rn 'or \[\]\|or {}\|or 0\b'` sur src | 0 occurrences |
| 2 | Except trop large | §R1 | `grep -rn 'except:$\|except Exception:'` sur src | 0 occurrences |
| 3 | `noqa` | §R7 | `grep -rn 'noqa'` sur tous fichiers modifiés | 2 matches : `seed.py:49` (`NPY002` — justifié : legacy `np.random.seed()` requis pour seed globale, pas d'alternative pour fixer le state global), `test_seed.py:29` (`F401` — justifié : import pour vérification d'existence) |
| 4 | `per-file-ignores` | §R7 | `grep pyproject.toml` | Non modifié dans cette branche |
| 5 | `print()` résiduel | §R7 | `grep -rn 'print('` sur src | 0 occurrences |
| 6 | `.shift(-` (look-ahead) | §R3 | `grep -rn '\.shift(-'` sur src | 0 occurrences |
| 7 | Legacy random API | §R4 | `grep -rn 'np\.random\.seed\|random\.seed'` | 2 matches dans `seed.py:48-49` — **attendu** : c'est le rôle du module (fixer le state global) |
| 8 | TODO/FIXME/HACK/XXX | §R7 | `grep -rn 'TODO\|FIXME'` sur tous fichiers | 0 occurrences |
| 9 | Chemins hardcodés | §R7 | `grep -rn '/tmp\|C:\\'` sur tests | 0 occurrences |
| 10 | Imports absolus `__init__.py` | §R7 | N/A — aucun `__init__.py` modifié |
| 11 | Registration manuelle tests | §R7 | `grep -rn 'register_model\|register_feature'` sur tests | 0 occurrences |
| 12 | Mutable default arguments | §R6 | `grep -rn 'def .*=\[\]'` | 0 occurrences |
| 13 | `open()` sans context manager | §R6 | `grep -rn 'open('` sur src | 0 occurrences |
| 14 | Bool identité | §R6 | `grep -rn 'is True\|is False\|is np\.bool_'` | 0 occurrences |
| 15 | Dict collision | §R6 | N/A — pas de dict dans boucle |
| 16 | Boucle Python sur array | §R9 | `grep -rn 'for .* in range'` sur src | 0 occurrences |
| 17 | `isfinite` check | §R6 | N/A — seed est `int`, pas `float` |
| 18 | Numpy compréhension | §R9 | `grep -rn 'np\.[a-z]*(.*for'` sur src | 0 occurrences |
| 19 | Fixtures dupliquées | §R7 | `grep -rn 'load_config.*configs/'` sur tests | 0 occurrences |

### Annotations par fichier (B2)

#### `ai_trading/utils/seed.py` (76 lignes — lecture complète du diff)

- **L39–40** `isinstance(seed, bool) or not isinstance(seed, int)` : Correct — `bool` est sous-classe de `int`, le check `isinstance(seed, bool)` en premier empêche `True`/`False` de passer. RAS.
- **L43–45** `if seed < 1: raise ValueError(...)` : Validation strictement positive (>= 1). **Cohérent avec `config.py` L304** `Field(ge=1)` après le FIX. RAS.
- **L48** `random.seed(seed)` : Conforme spec §16.1. RAS.
- **L49** `np.random.seed(seed)  # noqa: NPY002` : Legacy API justifiée — seul moyen de fixer le state global numpy pour le code existant utilisant `np.random.rand()` etc. Le `noqa` est inévitable et documenté. RAS.
- **L50** `os.environ["PYTHONHASHSEED"] = str(seed)` : Conforme tâche. RAS.
- **L52** `logger.info(...)` : Log INFO après fixation des seeds. RAS.
- **L55–58** `try: import torch / except ImportError:` : Import optionnel correct. Log INFO « PyTorch is not available ». Le `except ImportError` est spécifique (pas large). RAS.
- **L61–63** `torch.manual_seed(seed)`, `torch.cuda.manual_seed_all(seed)` : Conforme spec §16.1 et tâche. RAS.
- **L66–67** `if not deterministic_torch: return` : Early return propre. RAS.
- **L69–76** Fallback `warn_only=True` : Le `except RuntimeError` est spécifique. Le fallback est documenté dans la docstring, la tâche et le plan comme exception au strict-no-fallback. Le warning est loggé au niveau WARNING avec message explicite. RAS.

RAS après lecture complète du diff (76 lignes).

#### `ai_trading/config.py` (1 ligne modifiée)

- **L304** `global_seed: int = Field(ge=1)` : Anciennement `ge=0`. Maintenant cohérent avec `seed.py` L43 (`seed < 1` → ValueError). La tâche spécifie « strictly positive (>= 1) ». RAS.

#### `tests/test_seed.py` (288 lignes — lecture complète du diff)

- **L1–12** : Docstring avec `#048`, mapping AC1–AC8. RAS.
- **TestSeedManagerImport** (L25–36) : Import + callable check. RAS.
- **TestSetGlobalSeedBasic** (L39–80) : Tests `random.random()`, `np.random.rand()`, `PYTHONHASHSEED` — double appel même seed → séquences identiques. Comparaisons correctes (`==` pour random, `np.testing.assert_array_equal` pour numpy). RAS.
- **TestReproducibility** (L83–116) : Couvre AC6. Vérifie aussi que seeds différentes → séquences différentes. RAS.
- **TestValidation** (L119–170) : seed=-1 (ValueError), seed=0 (ValueError), seed=float (TypeError), seed=None (TypeError), seed=string (TypeError), seed=bool (TypeError), seed=2³¹−1 (accepté). Boundary coverage complète. RAS.
- **TestPyTorchOptional** (L173–202) : `mock.patch.dict(sys.modules, {"torch": None})` simule l'absence de PyTorch. Vérifie : pas de crash, log INFO, `deterministic_torch=True` sans crash. RAS.
- **TestPyTorchDeterministic** (L205–268) : MagicMock pour torch. Vérifie `manual_seed(42)`, `cuda.manual_seed_all(42)`, `use_deterministic_algorithms(True)`. Test fallback `warn_only=True` avec `side_effect=[RuntimeError, None]` — vérifie les 2 appels et le WARNING loggé. `deterministic_torch=False` → `use_deterministic_algorithms` non appelé. RAS.
- **TestEdgeCases** (L271–288) : seed=1 (min valid), appels consécutifs réinitialisant le state. RAS.

RAS après lecture complète du diff (288 lignes).

#### `tests/test_config_validation.py` (5 lignes ajoutées)

- **L273–276** `test_global_seed_zero_raises` : Teste que `global_seed=0` est rejeté par la validation Pydantic (`Field(ge=1)`). Utilise `_mutate` et les fixtures partagées `default_yaml_data`, `tmp_yaml` de `conftest.py`. RAS.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_seed.py` — conforme au plan (`implementation.md` L1042) |
| ID tâche dans docstring | ✅ | `(#048)` en L1 |
| Couverture des critères AC | ✅ | AC1→TestSeedManagerImport, AC2→TestSetGlobalSeedBasic, AC3→TestPyTorchDeterministic, AC4→TestPyTorchOptional, AC5→test_deterministic_fallback_warn_only, AC6→TestReproducibility, AC7→TestValidation, AC8→TestEdgeCases |
| Cas nominaux + erreurs + bords | ✅ | Nominaux (random/numpy/PYTHONHASHSEED/torch), erreurs (TypeError×4, ValueError×2), bords (seed=1, seed=2³¹−1, appels consécutifs) |
| Boundary fuzzing seed | ✅ | seed=0 (invalid boundary), seed=1 (min valid), seed=-1 (négatif), seed=2³¹−1 (large), seed=True (bool subclass), seed=None, seed=float, seed=string |
| Déterministes | ✅ | Seeds fixes (42, 99, 123) dans tous les tests |
| Pas de dépendance réseau | ✅ | Données synthétiques uniquement |
| Portabilité chemins | ✅ | Scan B1 #9 : 0 `/tmp` |
| Tests registre réalistes | N/A | Module non concerné |
| Contrat ABC complet | N/A | Module non concerné |
| Tests désactivés | ✅ | 0 `@pytest.mark.skip` ou `xfail` |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 #1, #2 : 0 fallback silencieux, 0 except large. Le seul `except RuntimeError` est l'exception documentée pour le fallback CUDA. |
| §R10 Defensive indexing | N/A | Pas d'indexation array |
| §R2 Config-driven | ✅ | Module reçoit `seed` et `deterministic_torch` en argument. Pas de valeur hardcodée. Config `global_seed: 42` dans `default.yaml` L214. |
| §R3 Anti-fuite | N/A | Module utilitaire, pas de données temporelles |
| §R4 Reproductibilité | ✅ | Scan B1 #7 : `random.seed()` et `np.random.seed()` sont le rôle du module. Pas de legacy API hors du seed manager. |
| §R5 Float conventions | N/A | Pas de tenseurs ni métriques |
| §R6 Anti-patterns Python | ✅ | Scans B1 #12–18 : 0 mutable defaults, 0 open(), 0 bool identité, 0 dict collision. `isinstance(seed, bool)` avant `isinstance(seed, int)` correct. Pas de NaN/inf à valider (int). |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `set_global_seed`, `deterministic_torch`, `logger` |
| Pas de code mort/debug | ✅ | Scan B1 #5 (print=0), #8 (TODO=0) |
| Imports propres / relatifs | ✅ | stdlib → third-party → local. Pas d'imports inutilisés. |
| `noqa` justifiés | ✅ | `NPY002` (legacy API requise pour global state), `F401` (import existence check) — les deux sont inévitables |
| DRY | ✅ | Aucune duplication |
| `__init__.py` à jour | ✅ | `ai_trading/utils/__init__.py` docstring présente. Pas d'import side-effect nécessaire. |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Commentaire |
|---|---|---|
| Spécification §16.1 | ✅ | Seeds fixés pour : numpy/random (L48–49), PyTorch (L62–63), PYTHONHASHSEED (L50). XGBoost `random_state` explicitement délégué au modèle (conforme spec et tâche). |
| Plan WS-12.1 | ✅ | Fonction `set_global_seed(seed, deterministic_torch)` conforme. Fallback CUDA documenté. Import optionnel PyTorch. |
| Formules doc vs code | N/A | Pas de formule mathématique |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `set_global_seed(seed: int, deterministic_torch: bool) -> None` — compatible avec l'orchestrateur futur (WS-12.2) |
| Config model vs validation | ✅ | `config.py` `Field(ge=1)` ↔ `seed.py` `seed < 1` — **cohérent** (corrigé depuis v1) |
| Clés de configuration | ✅ | `reproducibility.global_seed` dans `default.yaml` L214, `ReproducibilityConfig.global_seed` dans `config.py` L304 |
| Imports croisés | ✅ | `seed.py` n'importe aucun module du projet — 0 risque de dépendance circulaire |
| Test config_validation ajouté | ✅ | `test_global_seed_zero_raises` couvre le boundary `seed=0` côté Pydantic |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts | N/A | Module utilitaire (pas de concept financier) |
| Nommage métier cohérent | ✅ | `global_seed`, `deterministic_torch` — termes clairs et standards |
| Séparation des responsabilités | ✅ | Module dédié à la fixation des seeds — responsabilité unique |

---

## Remarques

Aucune remarque. Tous les items v1 sont corrigés.

---

## Résumé

Les 3 items identifiés en review v1 (WARNING incohérence `ge=0`/`>= 1`, MINEUR checklist incomplète, MINEUR nom de fichier test) sont tous corrigés dans le commit FIX `31968b8`. Le code est propre, les tests couvrent l'intégralité des critères d'acceptation avec boundary fuzzing complet, et la cohérence intermodule est rétablie. Aucun nouvel item identifié après scan GREP complet et lecture ligne-par-ligne de tous les diffs.
