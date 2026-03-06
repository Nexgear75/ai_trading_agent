# Revue PR — [WS-D-3] #081 — Page 2 : equity curve stitchée et métriques par fold

Branche : `task/081-wsd3-equity-fold-metrics`
Tâche : `docs/tasks/MD-2/081__wsd3_equity_fold_metrics.md`
Date : 2026-03-06

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

La tâche implémente correctement la section equity curve et le tableau des métriques par fold dans `2_run_detail.py`, avec logique métier bien isolée dans `run_detail_logic.py`. 32 tests passent, le code est propre (ruff ok, pas de TODO, imports corrects). Cependant, `normalize_equity()` est du code mort (définie, testée en 6 tests, mais jamais appelée), ce qui constitue un WARNING. Plusieurs patterns de fallback dans la couche de présentation sont classés MINEUR.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche | ✅ | `task/081-wsd3-equity-fold-metrics` |
| Commit RED présent | ✅ | `58db860 [WS-D-3] #081 RED: tests equity curve normalisation et métriques par fold` |
| Commit GREEN présent | ✅ | `dffd6af [WS-D-3] #081 GREEN: equity curve stitchée et métriques par fold` |
| RED = tests uniquement | ✅ | `git show --stat 58db860` → 1 fichier : `tests/test_dashboard_equity_fold.py` (500 insertions) |
| GREEN = impl + tâche | ✅ | `git show --stat dffd6af` → 4 fichiers : `run_detail_logic.py`, `2_run_detail.py`, `test_dashboard_equity_fold.py`, tâche MD |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1..HEAD` → exactement 2 commits (RED puis GREEN) |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (12/12) |
| Checklist cochée | ❌ (7/9 — items "Commit GREEN" et "PR ouverte" non cochés) |

> L'item "Commit GREEN" est non coché dans le fichier de tâche alors que le commit `dffd6af` existe. MINEUR.

### CI

| Check | Résultat |
|---|---|
| `pytest tests/test_dashboard_equity_fold.py -v` | **32 passed**, 0 failed |
| `pytest tests/ -v` (suite complète) | **2093 passed**, 0 failed, 27 deselected |
| `ruff check` (fichiers modifiés) | **All checks passed** |

→ Phase A : **PASS**. Passage en Phase B.

---

## Phase B — Code Review

### B1 — Résultats du scan automatisé (GREP)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks `or []` / `or {}` / `or 0` | `grep -n 'or \[\]\|or {}\|or 0\b'` | 0 occurrences (grep exécuté) |
| §R1 Except trop large | `grep -n 'except:$\|except Exception:'` | 0 occurrences (grep exécuté) |
| §R7 Suppressions lint (noqa) | `grep -n 'noqa'` | 0 occurrences (grep exécuté) |
| §R7 Print résiduel | `grep -n 'print('` | 0 occurrences (grep exécuté) |
| §R3 Shift négatif | `grep -n '\.shift(-'` | 0 occurrences (grep exécuté) |
| §R4 Legacy random API | `grep -n 'np.random.seed\|random.seed'` | 0 occurrences (grep exécuté) |
| §R7 TODO/FIXME orphelins | `grep -n 'TODO\|FIXME'` | 0 occurrences (grep exécuté) |
| §R7 Chemins hardcodés (tests) | `grep -n '/tmp\|/var/tmp'` | 0 occurrences (grep exécuté) |
| §R7 Imports absolus `__init__` | N/A | Aucun `__init__.py` modifié |
| §R7 Registration manuelle tests | `grep -n 'register_model\|register_feature'` | 0 occurrences (grep exécuté) |
| §R6 Mutable defaults | `grep -n 'def.*=\[\]\|def.*={}'` | 0 occurrences (grep exécuté) |
| §R6 open() sans context manager | `grep -n 'open('` | 0 occurrences (grep exécuté) |
| §R6 Bool identity | `grep -n 'is True\|is False'` | 0 occurrences (grep exécuté) |
| §R9 for range (vectorisation) | `grep -n 'for .* in range'` | 0 occurrences (grep exécuté) |
| §R6 isfinite | `grep -n 'isfinite'` | 0 occurrences (N/A — pas de validation de bornes numériques côté dashboard) |
| §R7 Fixtures dupliquées | `grep -n 'load_config.*configs/'` | 0 occurrences (grep exécuté) |
| §R6 `.get()` avec defaults | `grep -n '\.get(' run_detail_logic.py` | Matches L344, L345, L353, L390 — analysés ci-dessous |
| §R1 Ternary fallbacks | `grep -n 'if .* else '` | Matches L360, L367, L394 — analysés ci-dessous |

### B2 — Annotations par fichier

#### `scripts/dashboard/pages/run_detail_logic.py` (137 lignes de diff ajoutées)

- **L270-293** `def normalize_equity(equity: pd.Series) -> pd.Series:` — Fonction publique définie, testée par 6 tests, mais **jamais importée ni appelée** dans `2_run_detail.py` ni ailleurs dans le codebase. `chart_equity_curve()` dans `charts.py:50-53` effectue sa propre normalisation identique (`df["equity"] / eq_start`). La page Streamlit duplique le check `<= 0` en inline (L108-113 de `2_run_detail.py`). Cette fonction est du **code mort**.
  Sévérité : **WARNING**
  Suggestion : Soit supprimer `normalize_equity` et ses 6 tests, soit l'intégrer dans le flux (importer dans `2_run_detail.py` et l'utiliser à la place du check inline + la normalisation interne de `chart_equity_curve`).

- **L344** `trading = fold.get("trading", {})` — Fallback silencieux avec dict vide si `trading` est absent du fold. En couche de présentation, le comportement attendu est d'afficher "—" pour toutes les métriques trading manquantes. Le pattern est testé (`test_null_trading_values_em_dash`).
  Sévérité : **MINEUR**
  Suggestion : Utiliser `fold["trading"]` si le contrat impose la présence, ou documenter la raison du fallback dans un commentaire.

- **L345** `prediction = fold.get("prediction", {})` — Même pattern que L344 pour les métriques de prédiction.
  Sévérité : **MINEUR**

- **L353** `"Method": threshold.get("method", _NULL_DISPLAY)` — Fallback avec "—" si `method` absent de `threshold`. Le dict `threshold` est accédé strictement à L343 (`fold["threshold"]`), donc le threshold existe. Mais si `method` est absent du sous-dict, "—" est affiché silencieusement.
  Sévérité : **MINEUR**
  Suggestion : Utiliser `threshold["method"]` puisque `method` est un champ requis du schéma threshold.

- **L360** `str(n_trades) if n_trades is not None else _NULL_DISPLAY` — Pattern ternaire pour afficher "—" quand `n_trades` est null. Conforme à §9.3.
  Sévérité : RAS (comportement de présentation documenté §9.3).

- **L367** `n_trades if n_trades is not None else 0` — Quand `n_trades` est null, passe 0 à `format_sharpe_per_trade`, ce qui déclenche ⚠️. Si `sharpe_pt` est aussi null, `format_sharpe_per_trade` retourne "—" avant de vérifier n_trades. Logique correcte.
  Sévérité : **MINEUR** (fallback mais comportement testé).

- **L390** `trading = fold.get("trading", {})` — Même pattern qu'en L344, dans `build_pnl_bar_data`.
  Sévérité : **MINEUR**

- **L394** `pnl if pnl is not None else 0.0` — Null PnL → 0 pour bar chart. Testé (`test_null_pnl_uses_zero`).
  Sévérité : **MINEUR**

#### `scripts/dashboard/pages/2_run_detail.py` (53 lignes de diff ajoutées)

- **L104** `equity_df = load_equity_curve(run_dir)` — Conforme au plan (réutilise `load_equity_curve`). ✅

- **L106-113** Check inline `first_equity <= 0` + `st.error()` — Duplique la validation de `normalize_equity` et `chart_equity_curve`. Mais fournit un message utilisateur propre avant crash potentiel. Acceptable pour la couche Streamlit.
  Sévérité : RAS.

- **L115-121** Appel `chart_equity_curve(equity_df, fold_boundaries=True, drawdown=True, in_trade_zones=True)` — Conforme à la tâche et §6.3. ✅

- **L130** `fold_table = build_fold_metrics_table(metrics)` — Appel correct. ✅

- **L132-133** `st.dataframe(fold_table, use_container_width=True, hide_index=True)` — Affichage propre. ✅

- **L135-138** PnL bar chart conditionnel. Conforme §6.4. ✅

- **L140** `st.info("Aucune donnée de fold disponible.")` — Message informatif si table vide. ✅

- **Note** : `normalize_equity` n'est pas importé dans ce fichier (voir WARNING ci-dessus).

#### `tests/test_dashboard_equity_fold.py` (499 lignes ajoutées)

- **Structure** : 4 classes de test, 32 tests. Docstrings avec `#081`. Données synthétiques. ✅
- **Couverture** : tous les critères d'acceptation couverts par au moins un test. ✅
- **Boundary testing** : `n_trades=0` (non testé directement mais couvert par n_trades=None → 0), `n_trades=1` (testé L465), `n_trades=2` (testé L235), `n_trades=3` (testé L472). ⚠️ `n_trades=0` explicite manquant.
- **6 tests pour `normalize_equity`** : valides techniquement mais testent du code mort (WARNING lié).
- Pas de `@pytest.mark.skip` ni `xfail`. ✅
- Pas de dépendance réseau. ✅
- Pas de chemin hardcodé `/tmp`. ✅
- Imports locaux à chaque méthode (style acceptable, évite dépendance au scope module). ✅

### B3 — Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_dashboard_equity_fold.py`, ID `#081` en docstrings |
| Couverture critères | ✅ | 12 critères → 32 tests (mapping vérifié) |
| Cas nominaux + erreurs + bords | ✅ | Nominal, equity[0]≤0, null values, empty folds, n_trades boundaries |
| Boundary fuzzing | ✅ | n_trades=1, 2, 3; single element equity; empty folds |
| Déterministes | ✅ | Données synthétiques, pas d'aléatoire |
| Portabilité chemins | ✅ | Scan B1: 0 `/tmp` |
| Tests registre réalistes | N/A | Pas de registre dans cette tâche |
| Contrat ABC complet | N/A | Pas d'ABC |

### B4 — Code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ⚠️ | 5 `.get(key, default)` + 3 ternaires dans code de présentation. Analysés B2, classés MINEUR. |
| §R10 Defensive indexing | ✅ | `equity.iloc[0]` seul accès indexé, validé par check `<= 0`. |
| §R2 Config-driven | ✅ | Pas de valeur hardcodée. θ lu depuis `metrics.json` → `fold.threshold.theta`. |
| §R3 Anti-fuite | ✅ | Scan B1: 0 `.shift(-`. Données lues, jamais recalculées. |
| §R4 Reproductibilité | ✅ | Scan B1: 0 legacy random. Pas d'aléatoire dans ce module. |
| §R5 Float conventions | N/A | Couche de présentation, pas de tenseurs/métriques calculées. |
| §R6 Anti-patterns Python | ✅ | Scan B1: 0 mutable defaults, 0 open(), 0 bool identity. |

### B5 — Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `normalize_equity`, `build_fold_metrics_table`, `build_pnl_bar_data`, `_fmt_theta`, `_fmt_quantile` |
| Pas de code mort/debug | ❌ | `normalize_equity` est définie/testée mais jamais appelée (WARNING #1) |
| Imports propres / relatifs | ✅ | Scan B1: 0 imports absolus `__init__`, imports ordonnés |
| DRY | ✅ | Réutilise `format_pct`, `format_float`, `format_sharpe_per_trade`, `_NULL_DISPLAY` de `utils.py` |
| `.gitignore` | ✅ | Pas de fichiers générés inclus |

### B5-bis — Bonnes pratiques métier

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | Equity normalisée à 1.0, PnL %, drawdown, Sharpe — utilisation correcte |
| Nommage métier cohérent | ✅ | `equity`, `net_pnl`, `sharpe`, `mdd`, `hit_rate` |
| Séparation des responsabilités | ✅ | Logique dans `run_detail_logic.py`, rendu dans `2_run_detail.py`, graphiques dans `charts.py` |
| Invariants de domaine | ✅ | `equity[0] > 0` validé avant normalisation |
| Cohérence des unités/échelles | ✅ | Ratios affichés en %, Sharpe en float |
| Patterns de calcul financier | N/A | Pas de calcul, lecture seule |

### B6 — Conformité spec v1.0

| Critère | Verdict |
|---|---|
| §6.3 Courbe d'équité stitchée | ✅ — Normalisée à 1.0, fold boundaries, drawdown, in_trade zones |
| §6.4 Métriques par fold | ✅ — 14 colonnes (12 spec + Method + Quantile comme recommandé) |
| §6.4 θ via threshold object | ✅ — `fold["threshold"]` accédé, method/theta/quantile extraits |
| §6.4 method="none" → "—" | ✅ — `_fmt_theta()` retourne `_NULL_DISPLAY` |
| §6.4 ⚠️ n_trades ≤ 2 | ✅ — Délégué à `format_sharpe_per_trade()` |
| §6.4 null → "—" | ✅ — Via `format_pct`, `format_float`, `_NULL_DISPLAY` |
| §6.4 Bar chart PnL | ✅ — `build_pnl_bar_data()` + `chart_pnl_bar()` |
| §4.2 Dégradation equity absente | ✅ — `st.info(...)` si `load_equity_curve` retourne None |
| Formules doc vs code | ✅ — Pas de divergence |

### B7 — Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `chart_equity_curve(df, fold_boundaries, drawdown, in_trade_zones)` et `chart_pnl_bar(list[dict])` conformes |
| Noms de colonnes DataFrame | ✅ | `equity`, `in_trade`, `fold`, `time_utc` — cohérents avec `data_loader.py` |
| Clés de configuration | N/A | Pas de lecture config directe |
| Structures de données partagées | ✅ | Dict `{fold, net_pnl}` conforme à `chart_pnl_bar` |
| Conventions numériques | ✅ | Pas de dtype imposé côté dashboard |
| Imports croisés | ✅ | `charts.py`, `data_loader.py`, `utils.py` — tous présents sur `Max6000i1` |
| Forwarding kwargs | N/A | Pas de pattern wrapper avec kwargs |

---

## Remarques

1. **[WARNING]** `normalize_equity()` est du code mort.
   - Fichier : `scripts/dashboard/pages/run_detail_logic.py`
   - Ligne(s) : 270-293
   - La fonction est définie et testée par 6 tests (`TestNormalizeEquity`) mais n'est jamais importée ni appelée dans `2_run_detail.py` ou ailleurs. `chart_equity_curve()` dans `charts.py:50-53` effectue sa propre normalisation identique. La page Streamlit fait un check inline `first_equity <= 0` (L108-113) sans appeler `normalize_equity`.
   - Suggestion : Supprimer `normalize_equity` et ses 6 tests, ou l'intégrer dans le flux (appeler depuis `2_run_detail.py` et/ou `chart_equity_curve`).

2. **[MINEUR]** `.get("trading", {})` et `.get("prediction", {})` — fallbacks silencieux.
   - Fichier : `scripts/dashboard/pages/run_detail_logic.py`
   - Ligne(s) : 344, 345, 390
   - Fournit un dict vide si la clé est absente, masquant potentiellement une structure incomplète.
   - Suggestion : Utiliser `fold["trading"]` / `fold["prediction"]` si ces clés sont contractuellement requises dans `metrics.json`, ou ajouter un commentaire justifiant le fallback.

3. **[MINEUR]** `threshold.get("method", _NULL_DISPLAY)` — fallback pour clé requise.
   - Fichier : `scripts/dashboard/pages/run_detail_logic.py`
   - Ligne(s) : 353
   - `method` est un champ requis de l'objet `threshold`. Le fallback masque une structure invalide.
   - Suggestion : `threshold["method"]`.

4. **[MINEUR]** `pnl if pnl is not None else 0.0` — fallback dans `build_pnl_bar_data`.
   - Fichier : `scripts/dashboard/pages/run_detail_logic.py`
   - Ligne(s) : 394
   - Null PnL converti silencieusement en 0 pour le bar chart. Testé et intentionnel, mais techniquement un fallback §R1.
   - Suggestion : Acceptable en l'état pour la couche de présentation. Optionnellement, exclure les folds sans PnL du bar chart au lieu de forcer 0.

5. **[MINEUR]** Checklist de tâche incomplète.
   - Fichier : `docs/tasks/MD-2/081__wsd3_equity_fold_metrics.md`
   - Ligne(s) : 68-69
   - Items "Commit GREEN" et "Pull Request ouverte" non cochés `[x]` malgré l'existence du commit GREEN `dffd6af`.
   - Suggestion : Cocher l'item Commit GREEN. L'item PR sera coché à l'ouverture effective.

---

## Résumé

Le code est fonctionnellement correct, bien structuré et conformé à la spec. La séparation logique/rendu est bonne, les tests sont complets (32 tests, bons boundaries). Le point notable est la fonction `normalize_equity` qui est du code mort (définie/testée mais jamais appelée), constituant un WARNING. Les 4 items MINEUR concernent des fallbacks dans la couche de présentation et la checklist incomplète.

---

RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 1
- Mineurs : 4
- Rapport : `docs/tasks/MD-2/081/review_v1.md`
