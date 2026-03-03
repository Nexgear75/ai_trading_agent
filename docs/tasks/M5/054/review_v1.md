# Revue PR — [WS-12] #054 — Gate M5 (Production Readiness)

Branche : `task/054-gate-m5`
Tâche : `docs/tasks/M5/054__ws12_gate_m5.md`
Date : 2026-03-03

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

La branche implémente 24 tests couvrant les 3 critères du gate M5 (reproductibilité, conformité artefacts, exécution) plus 6 tests unitaires pour les helpers de comparaison. Tous les tests passent (24/24), ruff est clean (0 erreur), et la structure TDD (RED→GREEN) est conforme. Deux items WARNING et deux items MINEUR identifiés empêchent le verdict CLEAN.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/054-gate-m5` | ✅ | `git branch --show-current` → `task/054-gate-m5` |
| Commit RED présent | ✅ | `0846ec0` — `[WS-12] #054 RED: tests gate M5` |
| Commit GREEN présent | ✅ | `bf0b2e7` — `[WS-12] #054 GREEN: gate M5` |
| RED contient uniquement des tests | ✅ | `git show --stat 0846ec0` → `tests/test_gate_m5.py | 610 +++` (1 fichier) |
| GREEN contient implémentation + tâche | ✅ | `git show --stat bf0b2e7` → `docs/tasks/M5/054__ws12_gate_m5.md | 36 +++---` (1 fichier) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → 2 commits exactement |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (9/9) |
| Checklist cochée | ✅ (8/9 — la PR n'est pas encore ouverte, `[ ]` sur ce point attendu) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1579 passed**, 0 failed ✅ |
| `ruff check ai_trading/ tests/` | **All checks passed** ✅ |

Phase A : **PASS** → Phase B engagée.

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 — Fallbacks silencieux | `grep 'or []\|or {}...'` | 1 match L217 : `f"{prefix}.{key}" if prefix else key` → **faux positif** (ternaire de formatage string, pas un fallback) |
| §R1 — Except trop large | `grep 'except:$\|except Exception:'` | 0 occurrences (grep exécuté) |
| §R7 — Print résiduel | `grep 'print('` | 0 occurrences (grep exécuté) |
| §R3 — Shift négatif | `grep '.shift(-'` | 0 occurrences (grep exécuté) |
| §R4 — Legacy random API | `grep 'np.random.seed...'` | 0 occurrences (grep exécuté) |
| §R7 — TODO/FIXME | `grep 'TODO\|FIXME...'` | 0 occurrences (grep exécuté) |
| §R7 — Chemins hardcodés | `grep '/tmp\|C:\\'` | 0 occurrences (grep exécuté) |
| §R7 — Noqa | `grep 'noqa'` | 0 occurrences (grep exécuté) |
| §R7 — Registration manuelle | `grep 'register_model\|register_feature'` | 0 occurrences (grep exécuté) |
| §R6 — Mutable defaults | `grep 'def.*=[]\|def.*={}'` | 0 occurrences (grep exécuté) |
| §R6 — open() / read_text() | `grep '.read_text\|open('` | 15 matches → tous `Path.read_text()` pour lire JSON/YAML dans des tests, acceptable |
| §R6 — Bool identity | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences (grep exécuté) |
| §R9 — Boucles Python range | `grep 'for .* in range(.*):' ` | 0 occurrences (grep exécuté) |
| §R6 — isfinite checks | `grep 'isfinite'` | 1 match L224 : `math.isfinite(val)` dans `_extract_numeric_fields` — correct |
| §R7 — Fixtures dupliquées | `grep 'load_config.*configs/'` | 0 occurrences (grep exécuté) |
| §R7 — Imports absolus init | N/A | Pas de `__init__.py` modifié |

### Annotations par fichier (B2)

#### `tests/test_gate_m5.py` (610 lignes)

- **L26-29** `def _write_parquet(...)`: fonction identique à `test_integration.py:24` et `test_runner.py:61`. Duplication triple.
  Sévérité : MINEUR (DRY — §R7)
  Suggestion : extraire dans `conftest.py` comme fixture ou helper partagé.

- **L33-200** `def _make_config(...)`: quasi-identique à `_make_integration_config` dans `test_integration.py:31-197` (seule différence : paramètre `seed` ajouté). 170 lignes de config dupliquées. Risque de drift si la config évolue.
  Sévérité : MINEUR (DRY — §R7)
  Suggestion : factoriser un helper commun dans `conftest.py` avec le paramètre `seed` optionnel.

- **L217** `full_key = f"{prefix}.{key}" if prefix else key`: faux positif §R1 (ternaire de formatage, pas un fallback silencieux).
  Sévérité : RAS

- **L220-224** `_extract_numeric_fields` : filtre correctement NaN, inf, bool, None. `math.isfinite(val)` présent **avant** utilisation. Conforme §R6.
  Sévérité : RAS

- **L230-264** `_compare_metrics_dicts` : logique de tolérance `atol OR rtol` correcte. Le guard `abs(v1) > 0` évite la division par zéro. La comparaison est asymétrique (rtol relatif à v1 uniquement), ce qui est acceptable pour le use case same-platform.
  Sévérité : RAS

- **L334** `key_fields = ["n_trades", "net_pnl", "max_drawdown"]` : le plan (implementation.md L112) spécifie 5 champs numériques clés par fold : `theta`, `n_trades`, `net_pnl`, `sharpe`, `max_drawdown`. Le test `test_reproducibility_key_fields_exact` ne vérifie que 3/5 champs à `atol=1e-7`. Les champs `theta` (dans `fold["threshold"]["theta"]`) et `sharpe` (dans `fold["trading"]["sharpe"]`) sont absents de la comparaison exacte. **Note** : ces champs sont couverts au niveau `rtol=1%` par `test_reproducibility_same_seed_same_config` via `_compare_metrics_dicts`, donc le critère plan (95% à 1%) est satisfait. Mais la vérification exacte same-platform est incomplète.
  Sévérité : WARNING
  Suggestion : ajouter `"sharpe"` à `key_fields` et ajouter une comparaison séparée pour `theta` via `f1["threshold"]["theta"]` / `f2["threshold"]["theta"]`.

- **L340-341** `if v1 is not None and v2 is not None:` : le guard silencieux skip les champs None sans vérifier que les deux runs ont la même None-ness. Si run1 produit `theta=0.5` et run2 `theta=None`, le test ne détecterait pas la divergence. Même pattern à L369-371 pour les aggregate means.
  Sévérité : WARNING
  Suggestion : ajouter `assert (v1 is None) == (v2 is None), f"Fold {i} {field}: one is None"` avant le guard.

- **L336** `strict=True` dans `zip()` : conforme Python 3.10+, bonne pratique.
  Sévérité : RAS

- **L382-490** `TestGateM5ArtefactsConformity` : setup fixture avec `autouse=True` exécute un pipeline complet une fois pour la classe. Tests de schéma JSON, arborescence §15.1, equity curves, predictions, metrics structure — 11 tests couvrant le critère 2. Complet et conforme.
  Sévérité : RAS (après lecture complète des 110 lignes)

- **L497-565** `TestGateM5Execution` : 4 tests vérifiant DummyModel et no_trade completion, θ bypass, et zero PnL. Utilise `pytest.approx(0.0, abs=1e-12)` pour la comparaison float. Conforme.
  Sévérité : RAS

- **L572-610** `TestMetricsComparison` : 6 tests unitaires pour `_compare_metrics_dicts` et `_extract_numeric_fields`. Bon coverage des edge cases (NaN, inf, bool, nested dicts, within/beyond tolerance).
  Sévérité : RAS

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_gate_m5.py`, ID `#054` dans toutes les docstrings |
| Couverture des critères d'acceptation | ✅ | Critère 1 → 3 tests (reproducibility), Critère 2 → 11 tests (artefacts), Critère 3 → 4 tests (execution), + 6 unit tests helpers |
| Cas nominaux + erreurs + bords | ✅ | Nominaux: pipeline DummyModel/no_trade. Bords: NaN, inf, bool dans extraction. Pas de tests d'erreur spécifiques mais le scope est un gate (validation, pas implémentation) |
| Boundary fuzzing | N/A | Tests de gate validant output du pipeline, pas d'entrées numériques directes à fuzzer (sauf helper testé: tolerance 0.5%/10%) |
| Déterministes | ✅ | Seed fixée `42` via config + `synthetic_ohlcv` fixture (seed 42). 2 runs identiques par design |
| Données synthétiques | ✅ | Fixture `synthetic_ohlcv` (conftest.py L301) — GBM 500 candles, no network |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé. Tous les chemins via `tmp_path` pytest fixture |
| Tests registre réalistes | N/A | Pas de test de registre dans ce fichier |
| Contrat ABC complet | N/A | Pas d'ABC dans le scope |
| Tests désactivés | ✅ | 0 `@pytest.mark.skip` ou `xfail` |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 — Strict code (no fallbacks) | ✅ | Scan B1 : 1 match faux positif (ternaire L217). 0 except |
| §R10 — Defensive indexing | ✅ | Pas d'indexing risqué. Les accès `fold["trading"][field]` sont sur des données JSON parsées valides par structure du pipeline |
| §R2 — Config-driven | ✅ | Tous les paramètres dans le dict YAML construit par `_make_config`. Pas de hardcoding significatif (sauf seed=42 passé en paramètre) |
| §R3 — Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. Tests de gate n'introduisent pas de look-ahead |
| §R4 — Reproductibilité | ✅ | Scan B1 : 0 legacy random. Seeds fixées. 2 runs identiques |
| §R5 — Float conventions | ✅ | Comparaisons float via `abs(v1-v2) <= atol`, `pytest.approx`. Pas de tenseurs float32 dans les tests |
| §R6 — Anti-patterns Python | ✅ | 0 mutable defaults, 0 bool identity, `math.isfinite` présent pour NaN/inf check. Tous `Path.read_text()` (pas d'open brut) |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Conforme partout |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO |
| Imports propres | ✅ | Imports locaux dans les tests (valid pattern for lazy loading), pas d'import * |
| DRY | ⚠️ | `_write_parquet` dupliquée 3× (test_gate_m5, test_integration, test_runner). `_make_config` quasi-identique à `_make_integration_config`. Voir MINEUR 1 et 2 |

### Conformité spec v1.0 (B6)

| Critère | Verdict |
|---|---|
| Spécification (§15, §16) | ✅ — Arborescence §15.1 vérifiée (manifest, metrics, config_snapshot, pipeline.log, folds, equity curves, predictions) |
| Plan d'implémentation (Gate M5) | ⚠️ — Critère 1 satisfait à 95% (test large), mais key_fields exact test incomplet (3/5 champs). Voir WARNING 1 |
| Formules doc vs code | ✅ — Tolérance 1% et atol=1e-7 conformes à la tâche |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `run_pipeline(config)` retourne `Path` — conforme |
| Clés de configuration | ✅ | Config dict construit manuellement est identique à test_integration.py qui fonctionne |
| Imports croisés | ✅ | `load_config`, `run_pipeline`, `validate_manifest`, `validate_metrics` — tous existent dans la branche |
| Conventions numériques | ✅ | float64 pour métriques (json.loads retourne float64 Python) |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts | ✅ | Gate M5 vérifie reproductibilité, conformité artefacts, exécution — concepts corrects |
| Nommage métier | ✅ | `net_pnl`, `max_drawdown`, `sharpe`, `equity_curve` — noms standards |
| Invariants de domaine | ✅ | `n_trades == 0` et `net_pnl == 0` pour no_trade baseline — invariant correct |

---

## Remarques

1. **[WARNING]** Per-fold key fields incomplets dans `test_reproducibility_key_fields_exact`.
   - Fichier : `tests/test_gate_m5.py`
   - Ligne(s) : 334
   - Description : `key_fields = ["n_trades", "net_pnl", "max_drawdown"]` ne couvre que 3 des 5 champs numériques clés par fold définis dans le plan (implementation.md L112). `theta` (`fold["threshold"]["theta"]`) et `sharpe` (`fold["trading"]["sharpe"]`) manquent de la vérification exacte `atol=1e-7`. Ils sont couverts au niveau `rtol=1%` par le test large, mais la vérification exacte same-platform est incomplète.
   - Suggestion : ajouter `"sharpe"` à `key_fields` pour le path `fold["trading"]`, et ajouter une comparaison séparée pour `theta` via `f1["threshold"]["theta"]` / `f2["threshold"]["theta"]` avec le même `atol=1e-7`.

2. **[WARNING]** Guard `if v1 is not None and v2 is not None` silencieux.
   - Fichier : `tests/test_gate_m5.py`
   - Ligne(s) : 340-341, 369-371
   - Description : Si run1 produit une valeur non-None et run2 produit None (ou inversement) pour un champ, le test skip silencieusement la comparaison au lieu de détecter la divergence. Pour un test de reproductibilité, une divergence de None-ness est elle-même un échec de reproductibilité.
   - Suggestion : ajouter `assert (v1 is None) == (v2 is None), f"Fold {i} {field}: None mismatch {v1} vs {v2}"` avant le guard.

3. **[MINEUR]** DRY — `_write_parquet` dupliquée 3 fois.
   - Fichier : `tests/test_gate_m5.py` (L26), `tests/test_integration.py` (L24), `tests/test_runner.py` (L61)
   - Description : Fonction helper identique dans 3 fichiers de test. Risque de drift si le format parquet change.
   - Suggestion : extraire dans `tests/conftest.py` comme helper partagé.

4. **[MINEUR]** DRY — `_make_config` quasi-identique à `_make_integration_config`.
   - Fichier : `tests/test_gate_m5.py` (L33-200), `tests/test_integration.py` (L31-197)
   - Description : ~170 lignes de config YAML dupliquées. Seule différence : paramètre `seed` (hardcodé à 42 dans integration, paramétré dans gate M5).
   - Suggestion : factoriser dans `conftest.py` un helper commun `_make_pipeline_config(..., seed=42)` réutilisé par les deux fichiers.

## Résumé

Branche conforme TDD (RED→GREEN), 24/24 tests passent, ruff clean, 1579 tests total GREEN. Deux warnings (key fields per-fold incomplets, guard None silencieux) et deux mineurs (DRY helpers). Les warnings nécessitent correction pour assurer la complétude de la vérification de reproductibilité conformément au plan.

```
RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 2
- Mineurs : 2
- Rapport : docs/tasks/M5/054/review_v1.md
```
