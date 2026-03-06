# Revue PR — [WS-11] #046 — Metrics builder

**Branche** : `task/046-metrics-builder`
**Tâche** : `docs/tasks/M5/046__ws11_metrics_builder.md`
**Date** : 2026-03-03
**Itération** : v1

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Le module `metrics_builder.py` est bien structuré, API claire, tests complets (42 tests, 9 classes de tests, couverture des AC). Trois warnings significatifs identifiés : (1) `json.dumps` sans `allow_nan=False` permet la production de JSON invalide si des NaN/inf arrivent depuis l'amont, (2) les fonctions `_normalize_prediction`/`_normalize_trading` omettent silencieusement les clés requises par le schéma sans erreur, (3) `write_fold_metrics` n'applique pas de normalisation, créant un risque de divergence avec le fichier global. Deux items mineurs additionnels.

---

## Phase A — Compliance

### A1. Périmètre

Fichiers modifiés vs `Max6000i1` :

| Catégorie | Fichiers |
|---|---|
| Source (`ai_trading/`) | `ai_trading/artifacts/__init__.py`, `ai_trading/artifacts/metrics_builder.py` |
| Tests (`tests/`) | `tests/test_metrics_builder.py` |
| Docs | `docs/tasks/M5/046__ws11_metrics_builder.md` |
| Autres | `README.md` |

### A2. Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/046-metrics-builder` | ✅ | `git branch --show-current` → `task/046-metrics-builder` |
| Commit RED présent | ✅ | `11e6476` — `[WS-11] #046 RED: tests metrics builder` |
| Commit GREEN présent | ✅ | `0ec7e67` — `[WS-11] #046 GREEN: metrics builder` |
| Commit RED = tests uniquement | ✅ | `git show --stat 11e6476` → `tests/test_metrics_builder.py` (775 insertions) |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 0ec7e67` → `ai_trading/artifacts/__init__.py`, `ai_trading/artifacts/metrics_builder.py`, `docs/tasks/M5/046__ws11_metrics_builder.md` |
| Pas de commits parasites entre RED et GREEN | ✅ | Aucun commit entre `11e6476` (RED) et `0ec7e67` (GREEN) |
| Commit hors TDD sur la branche | ⚠️ | `bed7d31 maj README pipeline` — commit avant RED, modifie `README.md` (voir remarque 4) |

### A3. Tâche associée

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (9/9) |
| Checklist cochée | ✅ (8/9 — seul « PR ouverte » non coché, attendu) |

**Vérification des critères d'acceptation :**

| AC | Description | Preuve code/test |
|---|---|---|
| AC-1 | Module importable | `from ai_trading.artifacts.metrics_builder import build_metrics` — L14 du test + `__init__.py` exporte les 3 fonctions |
| AC-2 | JSON valide contre schéma | `TestSchemaValidation` (7 tests) utilise `jsonschema.validate()` |
| AC-3 | `metrics_fold.json` cohérent | `TestFoldMetricsCoherence` (3 tests) — assert `fold_loaded == fold_entry` |
| AC-4 | `n_samples_*` présents | `TestNSamplesFields` (3 tests), vérifiés dans `_REQUIRED_FOLD_KEYS` L24 |
| AC-5 | Métriques float64 | `TestFloat64Metrics` (5 tests), `_ensure_float()` L59-62, `_ensure_int()` L65-67 |
| AC-6 | Test intégration | `TestIntegration` (2 tests) — build → write → reload → validate |
| AC-7 | Erreurs + bords | `TestStrictValidation` (8 tests) — empty run_id, empty folds, missing keys, duplicates |
| AC-8 | Suite verte | ✅ 42 passed |
| AC-9 | ruff clean | ✅ `All checks passed!` |

### A4. CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1326 passed**, 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed!** |

✅ Phase A passée.

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux | `grep -n ' or \[\]\| or {}\| or ""\| or 0\b\| if .* else '` | 0 occurrences (grep exécuté) |
| §R1 Except trop large | `grep -n 'except:$\|except Exception:'` | 0 occurrences (grep exécuté) |
| §R7 Suppressions lint (noqa) | `grep -n 'noqa'` | 0 occurrences (grep exécuté) |
| §R7 per-file-ignores | `grep -n 'per-file-ignores' pyproject.toml` | Existe L51, non modifié par cette PR |
| §R7 Print résiduel | `grep -n 'print('` | 0 occurrences (grep exécuté) |
| §R3 Shift négatif | `grep -n '\.shift(-'` | 0 occurrences (grep exécuté) |
| §R4 Legacy random API | `grep -n 'np\.random\.seed\|...'` | 0 occurrences (grep exécuté) |
| §R7 TODO/FIXME | `grep -n 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences (grep exécuté) |
| §R7 Chemins hardcodés OS | `grep -n '/tmp\|/var/tmp\|C:\\'` (tests) | 0 occurrences (grep exécuté) |
| §R7 Imports absolus `__init__` | `grep -n 'from ai_trading\.'` (`__init__.py`) | 0 occurrences (grep exécuté) — imports relatifs ✅ |
| §R7 Registration manuelle tests | `grep -n 'register_model\|register_feature'` (tests) | 0 occurrences (grep exécuté) |
| §R6 Mutable defaults | `grep -n 'def .*=\[\]\|def .*={}'` | 0 occurrences (grep exécuté) |
| §R6 open() sans context manager | `grep -n '\.read_text\|open('` (src) | 0 occurrences — `write_text()` utilisé (raccourci Path) ✅ |
| §R6 Comparaison booléenne identité | `grep -n 'is np\.bool_\|is True\|is False'` | 0 occurrences (grep exécuté) |
| §R6 Dict collision silencieuse | `grep -n '\[.*\] = .*'` | 7 matches — analysés : clés issues de tuples constantes (`_PREDICTION_FLOAT_KEYS`, `_TRADING_FLOAT_KEYS`, `_TRADING_INT_KEYS`), pas de collision possible. **Faux positifs.** |
| §R9 Boucle Python sur numpy | `grep -n 'for .* in range(.*):' ` | 0 occurrences (grep exécuté) |
| §R6 isfinite check | `grep -n 'isfinite\|math.isfinite\|np.isfinite'` | 0 occurrences — voir remarque 1 |
| §R9 Appels numpy répétés | `grep -n 'np\.[a-z]*(.*for .* in '` | 0 occurrences (grep exécuté) |
| §R7 Fixtures dupliquées | `grep -n 'load_config.*configs/'` (tests) | 0 occurrences (grep exécuté) |
| §R7 Tests désactivés | `grep -n 'skip\|xfail'` (tests) | 0 occurrences (grep exécuté) |
| NaN safety JSON | `grep -n 'allow_nan'` | 0 occurrences — voir remarque 1 |

### B2. Annotations par fichier

#### `ai_trading/artifacts/metrics_builder.py` (251 lignes)

- **L229, L249** — `json.dumps(metrics_data, indent=2, ensure_ascii=False)` : `json.dumps` est appelé **sans `allow_nan=False`**. En Python, `json.dumps(float('nan'))` produit `NaN` qui n'est **pas du JSON valide** (RFC 8259). Si un module amont produit une métrique NaN ou inf (calcul dégénéré, division par zéro non interceptée), le fichier produit sera invalide et non parsable par des consommateurs JSON stricts.
  Sévérité : **WARNING**
  Suggestion : Ajouter `allow_nan=False` aux deux appels `json.dumps` pour fail-fast.

- **L71-76** — `_normalize_prediction` : la fonction ne copie que les clés **présentes** dans `prediction` (`if key in prediction`). Le schéma JSON exige `mae`, `rmse`, `directional_accuracy` comme required. Si l'une de ces clés est absente de l'entrée, elle est silencieusement omise — aucune erreur n'est levée. La sortie de `build_metrics` sera alors non conforme au schéma sans que le module ne le signale.
  Sévérité : **WARNING**
  Suggestion : Valider la présence des clés required du schéma dans `_normalize_prediction` et `_normalize_trading` (lever `KeyError` si absentes). Même pattern que `_normalize_fold` qui valide `_REQUIRED_FOLD_KEYS`.

- **L79-87** — `_normalize_trading` : même logique que ci-dessus. Les clés required par le schéma (`net_pnl`, `net_return`, `max_drawdown`, `profit_factor`, `n_trades`) ne sont pas validées — omission silencieuse si absentes.
  Sévérité : **WARNING** (même item que ci-dessus, regroupé)

- **L237-251** — `write_fold_metrics` : cette fonction écrit `fold_data` tel quel, **sans normalisation**. Or `build_metrics` applique `_normalize_fold` (conversion int/float, reordonnancement des clés). Si le caller passe des données brutes (non normalisées) à `write_fold_metrics`, le fichier `metrics_fold.json` peut diverger du fold correspondant dans `metrics.json`. Le contrat AC-3 (cohérence fold ↔ global) n'est garanti que si le caller passe des données déjà normalisées.
  Sévérité : **WARNING**
  Suggestion : Soit appliquer `_normalize_fold` dans `write_fold_metrics`, soit documenter clairement que le caller doit passer la sortie de `build_metrics["folds"][i]`.

- **L59-62** — `_ensure_float` : pas de check `math.isfinite`. NaN/inf passent silencieusement. Lié au warning JSON ci-dessus.
  Sévérité : Couvert par le WARNING L229/L249.

- **L90-95** — `_normalize_aggregate_block` : accès direct à `block["mean"]` et `block["std"]` → KeyError si absent. ✅ Strict.

- **L103-118** — `_normalize_fold` : validation `_REQUIRED_FOLD_KEYS` → KeyError si absent. ✅ Strict.

- **L161-168** — Validation `strategy_info` et `aggregate_data` : accès direct `strategy_info["strategy_type"]` → KeyError si absent. ✅ Strict.

- **L221-231** — `write_metrics` : `run_dir.mkdir(parents=True, exist_ok=True)` avant écriture. ✅ Path creation correcte.

- **L242-251** — `write_fold_metrics` : `fold_dir.mkdir(parents=True, exist_ok=True)` avant écriture. ✅ Path creation correcte.

- **L175-186** — Détection des `fold_id` dupliqués via list + `if fid in fold_ids`. Complexité O(n²), mais n est le nombre de folds (typiquement 3-5). Acceptable. RAS.

#### `ai_trading/artifacts/__init__.py` (31 lignes)

- Imports relatifs (`from .metrics_builder import ...`). ✅ Conforme §R7.
- `__all__` mis à jour avec les 3 nouvelles fonctions. ✅
- RAS après lecture complète du diff (8 lignes ajoutées).

#### `tests/test_metrics_builder.py` (775 lignes, 42 tests)

- **L24-29** — `SCHEMA_PATH` construit via `Path(__file__).resolve().parent.parent / "docs" / ...` : chemin absolu résolu au runtime, portable. ✅ Pas de chemin hardcodé.

- **L296-331** — `test_fold_metrics_coherent_with_global` : le test écrit `fold_data` **brut** via `write_fold_metrics` puis compare avec la version **normalisée** du global. Le test passe parce que les données de test `_minimal_fold_data` sont déjà du bon type (Python int/float natifs). Si des types numpy étaient utilisés, le test passerait quand même après JSON round-trip, mais en production la divergence pourrait exister en mémoire. Lié au WARNING `write_fold_metrics` ci-dessus.
  Sévérité : Couvert par le WARNING sur `write_fold_metrics`.

- Tests d'erreur couverts : `empty_run_id`, `empty_folds`, `missing_strategy_type`, `missing_strategy_name`, `missing_fold_field`, `missing_aggregate_prediction`, `missing_aggregate_trading`, `duplicate_fold_ids`. ✅ Bon panel d'erreurs.

- Tests de bord couverts : 0 trades (all nullable as None), threshold method "none", 1 fold, multi-folds (3), baseline strategy. ✅

- Test manquant : pas de test pour une clé required de prediction/trading manquante à l'intérieur d'un fold (ex : `prediction` sans `mae`). Ceci est lié au WARNING sur `_normalize_prediction` qui ne valide pas les sous-clés. Si la validation était ajoutée, un test correspondant serait nécessaire.
  Sévérité : Couvert par le WARNING ci-dessus.

- `#046` dans docstrings des classes de test. ✅
- Pas de `skip`/`xfail`. ✅
- Données synthétiques uniquement. ✅
- `tmp_path` fixture pour tous les tests I/O. ✅
- Pas de seed nécessaire (déterministe par construction). ✅

### B3. Tests — résumé

| Critère | Verdict |
|---|---|
| Convention nommage `test_metrics_builder.py` | ✅ |
| `#046` dans docstrings | ✅ |
| Couverture des AC | ✅ (9 AC couverts par 9 classes de tests) |
| Cas nominaux | ✅ |
| Cas d'erreur | ✅ (8 tests d'erreur) |
| Cas de bords | ✅ (0 trades, 1 fold, null threshold) |
| Pas de `skip`/`xfail` | ✅ |
| Déterministes | ✅ |
| Données synthétiques | ✅ |
| Portabilité chemins (`tmp_path`) | ✅ |

### B4. Audit — Règles non négociables

#### B4a. Strict code (§R1)
- Pas de fallback silencieux (grep: 0 occurrences). ✅
- Pas d'except trop large (grep: 0 occurrences). ✅
- Validation explicite des clés fold/strategy/aggregate. ✅
- ⚠️ Sous-clés prediction/trading non validées (voir WARNING remarque 2).

#### B4b. Config-driven (§R2)
- Le module ne lit aucune config — il reçoit des dicts en entrée. ✅ N/A.

#### B4c. Anti-fuite (§R3)
- Module d'artefacts/sérialisation. Pas d'accès aux données temporelles. ✅ N/A.
- Pas de `.shift(-` (grep: 0 occurrences). ✅

#### B4d. Reproductibilité (§R4)
- Pas de random (grep: 0 occurrences). ✅ N/A.

#### B4e. Float conventions (§R5)
- Métriques converties en Python float (float64) via `_ensure_float`. ✅
- Entiers (`fold_id`, `n_samples_*`, `n_trades`) en Python int via `_ensure_int`. ✅

#### B4f. Anti-patterns (§R6)
- Pas de mutable defaults (grep: 0 occurrences). ✅
- Path creation OK (`mkdir(parents=True, exist_ok=True)`). ✅
- Pas de `open()` nu — `Path.write_text()` utilisé. ✅
- Pas de comparaison float `==` (pas de floats comparés). ✅
- Pas de NaN/isfinite check — voir WARNING remarque 1. ⚠️

### B5. Qualité du code (§R7)

| Critère | Verdict |
|---|---|
| snake_case | ✅ |
| Pas de code mort / TODO | ✅ (grep: 0 occurrences) |
| Pas de print() | ✅ (grep: 0 occurrences) |
| Imports propres | ✅ (stdlib `json`, `logging`, `Path` ; pas d'import inutilisé) |
| `__init__.py` relatif + `__all__` | ✅ |
| Pas de noqa | ✅ |
| Pas de fichiers générés | ✅ |

### B5-bis. Bonnes pratiques métier (§R9)
- Module de sérialisation d'artefacts — pas de calcul financier direct. N/A.

### B6. Cohérence avec les specs

| Critère | Verdict |
|---|---|
| Conforme à `metrics.schema.json` | ✅ — structure de sortie conforme (prouvé par `jsonschema.validate()` dans les tests) |
| `run_id`, `strategy`, `folds`, `aggregate` | ✅ — 4 clés top-level |
| `folds` contient les 8 champs required par fold | ✅ — `_REQUIRED_FOLD_KEYS` |
| `metrics_fold.json` par fold | ✅ — `write_fold_metrics` |
| Formules spec respectées | N/A — module de sérialisation, pas de formules |

### B7. Cohérence intermodule (§R8)

| Critère | Verdict |
|---|---|
| `__init__.py` exporte les nouvelles fonctions | ✅ |
| Pas d'imports croisés sur du code non-mergé | ✅ — seuls `json`, `logging`, `Path` importés |
| Signatures keyword-only, pas de default fallback | ✅ |
| Pas de conflit avec modules existants (`manifest.py`, `run_dir.py`) | ✅ |

---

## Remarques

1. **[WARNING]** `json.dumps` sans `allow_nan=False` — production de JSON invalide possible
   - Fichier : `ai_trading/artifacts/metrics_builder.py`
   - Ligne(s) : 229, 249
   - Description : `json.dumps(metrics_data, indent=2, ensure_ascii=False)` est appelé sans `allow_nan=False`. En Python, `json.dumps(float('nan'))` produit `NaN` qui n'est pas du JSON valide (RFC 8259). Si une métrique amont est NaN/inf, le fichier produit sera invalide.
   - Suggestion : Ajouter `allow_nan=False` aux deux appels `json.dumps` dans `write_metrics` et `write_fold_metrics`. Cela fera lever `ValueError` en cas de NaN/inf, conformément au principe strict code.

2. **[WARNING]** `_normalize_prediction` et `_normalize_trading` omettent silencieusement les clés required du schéma
   - Fichier : `ai_trading/artifacts/metrics_builder.py`
   - Ligne(s) : 71-87
   - Description : Les fonctions ne copient que les clés présentes dans l'entrée (`if key in prediction`). Les clés required par le schéma (`mae`, `rmse`, `directional_accuracy` pour prediction ; `net_pnl`, `net_return`, `max_drawdown`, `profit_factor`, `n_trades` pour trading) ne sont pas validées. Un fold avec `prediction: {}` passe sans erreur et produit une sortie non conforme au schéma.
   - Suggestion : Ajouter des tuples `_REQUIRED_PREDICTION_KEYS` et `_REQUIRED_TRADING_KEYS` et valider leur présence (lever `KeyError`), comme fait pour `_REQUIRED_FOLD_KEYS`. Ajouter un test pour vérifier qu'une prédiction incomplète lève une erreur.

3. **[WARNING]** `write_fold_metrics` n'applique pas la normalisation — risque de divergence avec le global
   - Fichier : `ai_trading/artifacts/metrics_builder.py`
   - Ligne(s) : 237-251
   - Description : `write_fold_metrics` écrit `fold_data` tel quel, alors que `build_metrics` normalise chaque fold via `_normalize_fold` (conversion int/float). Le contrat AC-3 « cohérent avec l'entrée correspondante dans `metrics.json` » n'est garanti que si le caller passe des données déjà normalisées. Le test `test_fold_metrics_coherent_with_global` passe par coïncidence (données de test déjà du bon type).
   - Suggestion : Soit appliquer `_normalize_fold` dans `write_fold_metrics`, soit documenter clairement dans la docstring que le caller doit passer `build_metrics(...)["folds"][i]`. Ajuster le test de cohérence pour utiliser des données non triviales (ex : numpy int64) afin de prouver la robustesse.

4. **[MINEUR]** Commit non-TDD sur la branche tâche
   - Description : Le commit `bed7d31 maj README pipeline` modifie `README.md` (297 insertions, 63 suppressions) sur la branche `task/046-metrics-builder`. Bien que placé avant le RED commit (pas entre RED et GREEN), il ajoute du bruit hors périmètre de la tâche dans la PR.
   - Suggestion : Soit rebaser/squasher ce commit sur `Max6000i1` indépendamment, soit l'exclure de la PR.

5. **[MINEUR]** Pas de test de sous-clé prediction/trading manquante
   - Fichier : `tests/test_metrics_builder.py`
   - Description : `TestStrictValidation` teste les clés manquantes au niveau fold (`prediction` absente) et au niveau top-level (`aggregate.trading` absent), mais ne teste pas une sous-clé manquante inside prediction (ex : `prediction` sans `mae`). Ce test serait nécessaire si la validation des sous-clés est ajoutée (remarque 2).
   - Suggestion : Ajouter un test `test_missing_prediction_required_key_raises` après correction de la remarque 2.

---

## Résumé

| Sévérité | Count |
|---|---|
| BLOQUANT | 0 |
| WARNING | 3 |
| MINEUR | 2 |

Le code est bien structuré et fonctionnel. Les 3 warnings portent sur la robustesse de la sérialisation JSON (NaN safety), la validation incomplète des sous-structures, et un risque de divergence fold/global. Aucun bloquant, mais les warnings méritent correction avant merge pour respecter le principe strict code.
