# Revue PR — [WS-13] #055 — Configuration full-scale BTCUSDT

Branche : `task/055-config-fullscale-btc`
Tâche : `docs/tasks/M6/055__ws13_config_fullscale_btc.md`
Date : 2026-03-03

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

La branche crée `configs/fullscale_btc.yaml` (copie de `default.yaml` avec `dataset.start` et `strategy.name` ajustés) et des tests exhaustifs dans `tests/test_fullscale_config.py`. Le processus TDD (RED → GREEN) est correctement suivi, tous les tests passent (1621 passed), ruff est clean. Deux items mineurs identifiés empêchent le verdict CLEAN.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/055-config-fullscale-btc` | ✅ | `git branch --show-current` → `task/055-config-fullscale-btc` |
| Commit RED présent | ✅ | `54ce85f [WS-13] #055 RED: tests config fullscale_btc.yaml` |
| Commit GREEN présent | ✅ | `b32ec8d [WS-13] #055 GREEN: config fullscale_btc.yaml` |
| Commit RED = tests uniquement | ✅ | `git show --stat 54ce85f` → `tests/test_fullscale_config.py` (1 file, 300 insertions) |
| Commit GREEN = implem + tâche | ✅ | `git show --stat b32ec8d` → `configs/fullscale_btc.yaml` + `docs/tasks/M6/055__ws13_config_fullscale_btc.md` (2 files) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1..HEAD` → exactement 2 commits (RED + GREEN) |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (9/9) |
| Checklist cochée | ✅ (8/9 — seul « PR ouverte » non coché, attendu) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1621 passed**, 0 failed (23.37s) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| Fallbacks silencieux (§R1) | `grep 'or []\|or {}\|or ""\|or 0\| if .* else '` | 0 occurrences (grep exécuté) |
| Except trop large (§R1) | `grep 'except:$\|except Exception:'` | 0 occurrences (grep exécuté) |
| Print résiduel (§R7) | `grep 'print('` | 0 occurrences (grep exécuté) |
| Shift négatif (§R3) | `grep '.shift(-'` | 0 occurrences (grep exécuté) |
| Legacy random API (§R4) | `grep 'np.random.seed\|...'` | 0 occurrences (grep exécuté) |
| TODO/FIXME orphelins (§R7) | `grep 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences (grep exécuté) |
| Chemins hardcodés (§R7) | `grep '/tmp\|/var/tmp\|C:\\'` | 0 occurrences (grep exécuté) |
| noqa (§R7) | `grep 'noqa'` | 0 occurrences (grep exécuté) |
| Imports absolus __init__ (§R7) | N/A | Aucun `__init__.py` modifié |
| Registration manuelle (§R7) | `grep 'register_model\|register_feature'` | 0 occurrences (grep exécuté) |
| Mutable defaults (§R6) | `grep 'def.*=[]\|def.*={}'` | 0 occurrences (grep exécuté) |
| is True/False (§R6) | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences (grep exécuté) |
| Fixtures dupliquées (§R7) | `grep 'load_config.*configs/'` | 1 match L267 : `load_config("configs/nonexistent_btc.yaml")` — faux positif (test d'erreur : fichier inexistant → `FileNotFoundError`, le chemin relatif n'a pas d'impact) |

### Annotations par fichier (B2)

#### `configs/fullscale_btc.yaml`

- Comparaison structurelle avec `default.yaml` via script Python : seules 2 valeurs diffèrent (`dataset.start: "2017-08-17"`, `strategy.name: "dummy"`). Toutes les autres sections sont strictement identiques octet par octet (hors commentaires d'en-tête).
- Toutes les valeurs correspondent aux attentes de la tâche (§ Évolutions proposées).
- Les commentaires sont pertinents et cohérents avec la spec.
- RAS après lecture complète du diff (224 lignes).

#### `tests/test_fullscale_config.py`

- **L93** `72,` dans le calcul de `feature_min` :
  Sévérité : **MINEUR**
  Observation : Magic number `72` en dur. Cette valeur est redondante avec `max(cfg.features.params.vol_windows)` (qui vaut déjà 72 pour la config actuelle). Si `vol_windows` venait à changer dans `fullscale_btc.yaml`, le hardcoded `72` masquerait la divergence en dominant le `max()`.
  Suggestion : Supprimer le `72` littéral. `max(cfg.features.params.vol_windows)` couvre déjà cette contrainte.

- **L19-20** `PROJECT_ROOT` et `DEFAULT_PATH` définis localement :
  Sévérité : **MINEUR**
  Observation : `tests/conftest.py` fournit les fixtures `default_config_path`, `default_config` et `default_yaml_data` qui couvrent le même besoin pour `default.yaml`. Le test pourrait réutiliser `default_config` dans la fixture `configs` (L141) et `default_yaml_data` dans `TestFullscaleRawYamlDiff` (L232) au lieu de redéfinir `DEFAULT_PATH` et `_load_raw_yaml()`. Note : `PROJECT_ROOT` est aussi redéfini dans 5 autres fichiers de test du repo — c'est un pattern existant, mais cette PR avait l'opportunité de ne pas le reproduire.
  Suggestion : Remplacer la fixture `configs` par injection de `default_config` depuis conftest. Utiliser `default_yaml_data` au lieu de `_load_raw_yaml(DEFAULT_PATH)` dans `TestFullscaleRawYamlDiff`.

- Le reste du fichier (300 lignes) est propre : structure en classes thématiques, docstrings avec `#055`, `tmp_path` pour les fichiers temporaires, aucun import inutilisé. RAS.

#### `docs/tasks/M6/055__ws13_config_fullscale_btc.md`

- Statut DONE, critères cochés, checklist cohérente. RAS.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères | ✅ | AC1 → `test_file_exists` ; AC2 → `test_load_config_succeeds` ; AC3 → `TestFullscaleStrictValidation` (4 tests) ; AC4 → `test_dataset_start`, `test_dataset_end` ; AC5 → `test_strategy_name` ; AC6 → `TestFullscaleUnchangedParams` (15 tests) ; AC7 → `TestFullscaleErrorCases` (3 tests) ; AC8 → 1621 passed ; AC9 → ruff clean |
| Cas nominaux + erreurs + bords | ✅ | Nominal : 5 classes (exists, loads, validation, overrides, unchanged). Erreur : `TestFullscaleErrorCases` (missing file, corrupted, invalid strategy, warmup violation). Bord : `TestFullscaleRawYamlDiff` (raw YAML comparison). |
| Boundary fuzzing | ✅/N/A | Pas de paramètre numérique d'entrée à fuzzer (les tests vérifient une config statique). Les cas d'erreur testent warmup < L, strategy invalide, section manquante. |
| Déterministes | ✅ | Aucun aléatoire dans les tests (lecture de fichiers YAML uniquement). |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé. `tmp_path` utilisé pour les fichiers temporaires (L262, L273, L284). |
| Tests registre réalistes | N/A | Pas de registre testé. |
| Contrat ABC complet | N/A | Pas d'ABC testé. |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| Strict code (no fallbacks) (§R1) | ✅ | Scan B1 : 0 fallbacks, 0 except large. Aucun code source `ai_trading/` modifié. |
| Defensive indexing (§R10) | N/A | Aucun indexing dans les fichiers modifiés. |
| Config-driven (§R2) | ✅ | Le fichier YAML reprend tous les paramètres de `default.yaml`. Aucun hardcoding dans le code source. |
| Anti-fuite (§R3) | N/A | Pas de traitement de données dans cette tâche (config uniquement). |
| Reproductibilité (§R4) | ✅ | `reproducibility.global_seed: 42` et `deterministic_torch: true` présents dans fullscale. Scan B1 : 0 legacy random. |
| Float conventions (§R5) | N/A | Aucun tenseur/métrique manipulé. |
| Anti-patterns Python (§R6) | ✅ | Scan B1 : 0 mutable defaults, 0 `is True/False`. `open()` dans `_load_raw_yaml` utilise context manager `with`. |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage et style | ✅ | snake_case, classes CamelCase, conforme. |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO/FIXME. |
| Imports propres / relatifs | ✅ | 4 imports (Path, pytest, yaml, ai_trading.config). Tous utilisés, pas d'import `*`. |
| DRY | ⚠️ | Voir MINEUR #2 : `DEFAULT_PATH` / `_load_raw_yaml` redondants avec conftest. |

### Conformité spec v1.0 (B6)

| Critère | Verdict |
|---|---|
| Spécification (§3, §4.1) | ✅ — `dataset.start = "2017-08-17"` correspond au listing BTC Binance. |
| Plan d'implémentation (WS-13.1) | ✅ — Fichier YAML versionné conforme au plan. |
| Formules doc vs code | N/A — Pas de formule dans cette tâche. |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Clés de configuration | ✅ | Toutes les clés de `fullscale_btc.yaml` existent dans le modèle Pydantic (`load_config` succède). Vérifié par `test_load_config_succeeds`. |
| Imports croisés | ✅ | Seuls imports : `PipelineConfig`, `load_config` depuis `ai_trading.config` — existent dans `Max6000i1`. |
| Autres critères | N/A | Pas de nouvelle fonction, classe ou signature introduite. |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | Paramètres BTC réalistes (start 2017-08-17, H=4 bars, fee 5bps). |
| Nommage métier cohérent | ✅ | Noms identiques à `default.yaml`. |
| Invariants de domaine | ✅ | `start < end`, `embargo >= H`, `min_warmup >= L` — testés explicitement. |

---

## Remarques

1. **[MINEUR]** Magic number `72` dans le calcul de `feature_min`.
   - Fichier : `tests/test_fullscale_config.py`
   - Ligne : 93
   - Suggestion : Supprimer le littéral `72` du `max()`. `max(cfg.features.params.vol_windows)` couvre déjà cette valeur. Le `72` hardcodé est redondant et pourrait masquer un drift si `vol_windows` changeait.

2. **[MINEUR]** Duplication de fixtures conftest (`DEFAULT_PATH`, `_load_raw_yaml`).
   - Fichier : `tests/test_fullscale_config.py`
   - Lignes : 20, 31-33, 141-144, 233
   - Suggestion : Réutiliser les fixtures partagées `default_config` et `default_yaml_data` de `tests/conftest.py` au lieu de redéfinir `DEFAULT_PATH` et `_load_raw_yaml()` localement. Cela aligne le fichier avec la convention de factorisation existante.

## Actions requises

1. Supprimer le littéral `72` à la ligne 93 de `tests/test_fullscale_config.py`.
2. Remplacer `DEFAULT_PATH` / `_load_raw_yaml(DEFAULT_PATH)` par les fixtures conftest (`default_config`, `default_yaml_data`).
