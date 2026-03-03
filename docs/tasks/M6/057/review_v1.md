# Revue PR — [WS-13] #057 — Validation métriques fullscale BTCUSDT

Branche : `task/057-fullscale-metrics-validation`
Tâche : `docs/tasks/M6/057__ws13_fullscale_metrics_validation.md`
Date : 2026-03-03

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

La branche ajoute un test `test_fullscale_metrics_coherence` dans `tests/test_fullscale_btc.py` validant la cohérence numérique des métriques produites par le run grandeur nature BTCUSDT. Le code est propre, bien structuré, et suit les conventions. Un item MINEUR est identifié : les critères d'acceptation #5 et #8 affirment « float fini » de manière inconditionnelle, mais l'implémentation autorise `None` (correct selon le JSON schema `metrics.schema.json`). Les critères doivent être ajustés.

---

## Phase A — Compliance

### A1. Périmètre

- Branche source : `task/057-fullscale-metrics-validation`
- Tâche : `docs/tasks/M6/057__ws13_fullscale_metrics_validation.md`
- Fichiers modifiés (2) :
  - `tests/test_fullscale_btc.py` (111 insertions dans RED, 0 dans GREEN)
  - `docs/tasks/M6/057__ws13_fullscale_metrics_validation.md` (20 ins / 20 del dans GREEN)
- 0 fichiers source `ai_trading/`, 1 fichier test, 1 fichier doc

### A2. Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/057-*` | ✅ | `git branch --show-current` → `task/057-fullscale-metrics-validation` |
| Commit RED présent | ✅ | `f65932b [WS-13] #057 RED: tests validation métriques fullscale` |
| Commit GREEN présent | ✅ | `7074b36 [WS-13] #057 GREEN: validation métriques fullscale BTCUSDT` |
| RED = tests uniquement | ✅ | `git show --stat f65932b` → `tests/test_fullscale_btc.py | 111 +++` (1 file) |
| GREEN = implémentation + tâche | ✅ | `git show --stat 7074b36` → `057__ws13_fullscale_metrics_validation.md | 40 +--` (task update only — acceptable car tâche test-only : les tests ARE l'implémentation) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → 2 commits exactement |

### A3. Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (11/11 `[x]`) |
| Checklist cochée | ✅ (8/9 `[x]`, le 9e = « PR ouverte » attendu post-review) |

Vérification critère par critère :

| # | Critère | Ligne(s) preuve | Verdict |
|---|---|---|---|
| 1 | Test `test_fullscale_metrics_coherence` existe, marqué `@pytest.mark.fullscale` | L61 (classe `@pytest.mark.fullscale`), L215 (méthode) | ✅ |
| 2 | net_pnl est un float fini | L237-243 (`isinstance` + `math.isfinite`) | ✅ |
| 3 | max_drawdown ∈ [0, 1] | L246-251 (`isinstance` + `0.0 <= mdd <= 1.0`) | ✅ |
| 4 | n_trades >= 0 | L254-259 (`isinstance(n_trades, int)` + `>= 0`) | ✅ |
| 5 | sharpe est un float fini | L262-271 — vérifié SEULEMENT si `not None` | ⚠️ voir MINEUR #1 |
| 6 | hit_rate ∈ [0, 1] si n_trades > 0 | L274-282 — vérifié si `not None and n_trades > 0` | ✅ (conforme au critère + schema null) |
| 7 | Agrégation contient mean et std | L287-290 (`assert "mean" in`, `assert "std" in`) | ✅ |
| 8 | Valeurs agrégées sont floats finis | L298-316 — vérifié SEULEMENT si `not None` | ⚠️ voir MINEUR #1 |
| 9 | Scénarios nominaux + erreurs + bords | Nominal : validation complète des métriques. Bords : `len(folds) >= 1`, `0.0 <= mdd <= 1.0`, `n_trades >= 0`, `0.0 <= hit_rate <= 1.0`, `math.isfinite`. | ✅ (couverture adaptée au contexte fullscale) |
| 10 | Suite standard verte | 1621 passed, 0 failed | ✅ |
| 11 | ruff clean | `All checks passed!` | ✅ |

### A4. CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` (hors fullscale) | **1621 passed**, 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** |

Phase A : **PASS** → poursuite en Phase B.

---

## Phase B — Code Review

### B1. Scan automatisé (GREP)

Fichier audité : `tests/test_fullscale_btc.py` (seul fichier `.py` modifié).

| Pattern recherché | Règle | Résultat |
|---|---|---|
| Fallbacks silencieux (`or []`, `or {}`, etc.) | §R1 | 0 occurrences ✅ |
| Except trop large | §R1 | 0 occurrences ✅ |
| `noqa` | §R7 | 1 match L67 : `global _run_dir  # noqa: PLW0603` — **pré-existant** (task #056), non introduit par cette PR. Justifié (module-level cache pattern). Faux positif. ✅ |
| `print(` résiduel | §R7 | 0 occurrences ✅ |
| `.shift(-` (look-ahead) | §R3 | 0 occurrences ✅ |
| Legacy random API | §R4 | 0 occurrences ✅ |
| `TODO\|FIXME\|HACK\|XXX` | §R7 | 0 occurrences ✅ |
| Chemins hardcodés `/tmp`, `C:\` | §R7 | 0 occurrences ✅ |
| Imports absolus `__init__.py` | §R7 | 0 occurrences (L24 `from ai_trading.artifacts.validation` est dans un fichier test, pas un `__init__.py`) ✅ |
| Registration manuelle tests | §R7 | 0 occurrences ✅ |
| Mutable defaults (`def.*=[]`) | §R6 | 0 occurrences ✅ |
| `is True\|is False\|is np.bool_` | §R6 | 0 occurrences ✅ |
| `open(` sans context manager | §R6 | L40 `with open(path, ...) as f:` — context manager utilisé. ✅ |
| `isfinite` (preuve d'usage) | §R6 | L243, L271, L305, L315 — `math.isfinite()` correctement utilisé. ✅ |
| `for .* in range(` (boucle Python) | §R9 | 0 occurrences ✅ |
| `per-file-ignores` dans pyproject.toml | §R7 | Aucune entrée pour `test_fullscale_btc.py`. ✅ |
| `load_config.*configs/` fixtures dupliquées | §R7 | 0 occurrences ✅ |

### B2. Annotations par fichier

#### `tests/test_fullscale_btc.py` (diff : 113 lignes, +1 import, +110 lignes de test)

- **L17** `import math` : ajout propre, nécessaire pour `math.isfinite()`. ✅

- **L211-215** : docstring du test contient `#057`, conforme à la convention (identifiant tâche dans docstring, pas dans nom de test). ✅

- **L224-225** : `folds = metrics["folds"]` — accès par clé directe. Le JSON schema requiert `"folds"` (`"required": ["folds"]`), et `test_metrics_json_valid_schema` (pré-existant) valide le schema en amont. Pas de risque de KeyError en contexte fullscale ordonné. ✅

- **L237-243** : validation `net_pnl` — type check (`isinstance(net_pnl, (int, float))`) + `math.isfinite()`. Pas de garde `None` → cohérent avec le schema (`"net_pnl": {"type": "number"}`, non-nullable). ✅

- **L246-251** : validation `max_drawdown` — `0.0 <= mdd <= 1.0`. Cohérent avec le schema (`"minimum": 0.0, "maximum": 1.0`). ✅

- **L254-259** : validation `n_trades` — `isinstance(n_trades, int)` + `>= 0`. Cohérent avec le schema (`"type": "integer", "minimum": 0`). ✅

- **L262-271** : validation `sharpe` — garde `if sharpe is not None:`. Le schema déclare `"type": ["number", "null"]` — donc `None` est légitime. Le test est correct, mais le critère d'acceptation #5 dit « sharpe est un float fini » sans mentionner null. Voir MINEUR #1.

- **L274-282** : validation `hit_rate` — garde `if hit_rate is not None and n_trades > 0:`. Le schema autorise null (`["number", "null"]`). Le critère d'acceptation #6 dit « hit_rate ∈ [0, 1] si n_trades > 0 » — le `if not None` est un ajout pragmatique. Le critère est imprécis mais le code est correct. ✅

- **L287-290** : vérification `mean` et `std` dans `aggregate.trading`. Conforme au schema (`"required": ["mean", "std"]`). ✅

- **L293-296** : vérification `mean_keys == std_keys`. Bon contrôle d'intégrité structurelle. ✅

- **L298-316** : validation des valeurs agrégées — garde `if val is not None:`. Le schema `aggregate_block` déclare `"additionalProperties": {"type": ["number", "null"]}`. Code correct. Voir MINEUR #1 pour la cohérence critère/code.

- **Observation globale** : la méthode `test_fullscale_metrics_coherence` dépend de `test_make_run_all_succeeds` via `_get_run_dir()`. L'ordre d'exécution est garanti (Python 3.7+ dict ordering → pytest collecte dans l'ordre de définition dans la classe). Si le run dir n'est pas disponible, `pytest.skip()` est appelé — comportement correct. ✅

Sévérité globale : RAS (hors MINEUR #1 sur la formulation des critères).

### B3. Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères | ✅ | Mapping AC 1-8 → L215-316, chaque critère a une assertion correspondante |
| Cas nominaux + erreurs + bords | ✅ | Nominal : validation complète. Bords : `len >= 1`, `[0,1]` ranges, `>= 0`, `isfinite`. Erreurs : assertions avec messages descriptifs |
| Boundary fuzzing | ✅ / N/A | Pas de paramètre numérique d'entrée (test d'intégration lisant des données réelles). Les bornes de domaine sont vérifiées (mdd ∈ [0,1], hit_rate ∈ [0,1], n_trades >= 0) |
| Déterministes | ✅ | Aucun aléatoire — lecture de fichiers JSON déterministe |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé. Chemins via `PROJECT_ROOT` (L26-30) |
| Tests registre réalistes | N/A | Pas de registre impliqué |
| Contrat ABC complet | N/A | Pas d'ABC impliqué |
| Données synthétiques | ✅ / N/A | Fullscale test par design : données réelles obligatoires (M6 policy) |
| Tests désactivés | ✅ | 0 `@pytest.mark.skip`, 0 `xfail` dans le diff |

### B4. Code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback. Pas d'`except` trop large. `if val is not None:` est un guard schema-driven, pas un fallback. |
| §R10 Defensive indexing | ✅ | Pas d'indexation numérique. Itération `for fold in folds` et `for key, val in .items()` — safe. |
| §R2 Config-driven | ✅ / N/A | Pas de paramètre hardcodé (test d'intégration, pas de code fonctionnel). |
| §R3 Anti-fuite | ✅ / N/A | Pas de feature engineering ni de données. Scan B1 : 0 `.shift(-`. |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random API. Test déterministe. |
| §R5 Float conventions | ✅ / N/A | Pas de tenseurs ni de calculs de métriques dans le test. Le test vérifie les valeurs produites. |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, `open()` avec context manager (L40), pas de `is True/False` numpy. `math.isfinite()` utilisé correctement (L243, L271, L305, L315). |

### B5. Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `test_fullscale_metrics_coherence`, `net_pnl`, `fold_id`, `agg_trading`, `mean_keys` |
| Pas de code mort/debug | ✅ | Scan B1 : 0 `print()`, 0 `TODO/FIXME` |
| Imports propres | ✅ | `import math` ajouté à la bonne position (stdlib). Pas d'import inutilisé. |
| DRY | ✅ | Pas de duplication. Les boucles de validation mean/std sont similaires mais opèrent sur des données différentes — pattern acceptable. |
| `.gitignore` | ✅ / N/A | Pas de fichier généré dans la PR. |

### B5-bis. Bonnes pratiques métier

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | Plages de validation cohérentes : drawdown ∈ [0,1], hit_rate ∈ [0,1], n_trades ≥ 0 |
| Nommage métier cohérent | ✅ | `net_pnl`, `max_drawdown`, `sharpe`, `hit_rate`, `n_trades` — noms standards |
| Séparation des responsabilités | ✅ | Test uniquement — pas de logique métier |
| Invariants de domaine | ✅ | Bornes vérifiées explicitement |
| Cohérence des unités/échelles | ✅ / N/A | Pas de calcul, validation de plages uniquement |

### B6. Cohérence avec les specs

| Critère | Verdict |
|---|---|
| Spécification §13, §14 | ✅ — Les métriques vérifiées (net_pnl, max_drawdown, sharpe, hit_rate, n_trades) sont conformes aux métriques définies dans la spec |
| Plan WS-13.3 | ✅ — La tâche 057 est bien dans le scope WS-13 |
| Formules doc vs code | ✅ — Pas de formule mathématique dans cette tâche (validation de plages, pas de calcul) |
| Pas d'exigence inventée | ✅ — Toutes les vérifications sont motivées par la tâche et le schema |

### B7. Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Clés de `metrics.json` | ✅ | `folds`, `fold_id`, `trading`, `net_pnl`, `max_drawdown`, `n_trades`, `sharpe`, `hit_rate`, `aggregate` — toutes cohérentes avec `metrics_builder.py` et `metrics.schema.json` |
| Structure `aggregate.trading.mean/std` | ✅ | Conforme au schema `aggregate_block` (`$defs`) |
| `_load_json()` / `_get_run_dir()` | ✅ | Réutilisation des helpers pré-existants dans le même fichier |
| Imports croisés | ✅ | `from ai_trading.artifacts.validation import ...` — existe dans `Max6000i1` |
| Nullabilité metrics | ✅ | Les gardes `if ... is not None:` correspondent au schema JSON (`["number", "null"]` pour sharpe, hit_rate, aggregate values) |

---

## Remarques

1. **[MINEUR]** Critères d'acceptation #5 et #8 : formulation imprécise vs implémentation.
   - Fichier : `docs/tasks/M6/057__ws13_fullscale_metrics_validation.md`
   - Critère #5 : « Pour chaque fold : `sharpe` est un float fini. »
   - Critère #8 : « Toutes les valeurs agrégées sont des floats finis. »
   - Code : `tests/test_fullscale_btc.py` L264 (`if sharpe is not None:`), L300 (`if val is not None:`), L310 (`if val is not None:`).
   - **Analyse** : le JSON schema `metrics.schema.json` déclare `sharpe`, `hit_rate` et les valeurs d'agrégation comme `["number", "null"]`. L'implémentation est donc correcte — elle autorise `None` conformément au schema. Cependant, les critères d'acceptation affirment « float fini » de manière inconditionnelle, créant une discordance entre le texte et le code. Si le pipeline produisait un `sharpe: null` sur un fold, le test passerait alors que le critère littéral ne serait pas satisfait.
   - **Suggestion** : modifier les critères d'acceptation pour refléter la nullabilité : « `sharpe` est un float fini ou null » et « Toutes les valeurs agrégées sont des floats finis (ou null pour les métriques optionnelles) ».

---

## Actions requises

1. Mettre à jour les critères d'acceptation #5 et #8 dans `docs/tasks/M6/057__ws13_fullscale_metrics_validation.md` pour mentionner explicitement la possibilité de valeurs null, en conformité avec le JSON schema.

---

## Résumé

Le code est propre, bien structuré, et conforme au schema `metrics.schema.json`. L'unique item est une imprécision rédactionnelle dans les critères d'acceptation de la tâche qui ne reflètent pas la nullabilité autorisée par le schema JSON. L'implémentation est correcte, seul le texte des critères nécessite un ajustement.
