# Revue PR — [WS-D-1] #076 — Utilitaires formatage et couleurs

Branche : `task/076-wsd1-utils-formatting`
Tâche : `docs/tasks/MD-1/076__wsd1_utils_formatting.md`
Date : 2026-03-05

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Implémentation solide des fonctions de formatage (`format_pct`, `format_float`, `format_int`, `format_timestamp`, `format_mean_std`, `format_sharpe_per_trade`), de la palette §9.2 et des fonctions de seuils colorés §6.2. 68 tests passent, ruff clean. Cependant, `format_mean_std` ne supporte pas la précision 1 décimale requise par §9.3 pour `hit_rate` (WARNING), et `fmt_type` n'est pas validé (MINEUR). Quelques lacunes de boundary testing et checklist incomplète.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/NNN-short-slug` | ✅ | `task/076-wsd1-utils-formatting` |
| Commit RED présent | ✅ | `4b21283` — `[WS-D-1] #076 RED: tests utilitaires formatage et couleurs` |
| Commit RED = tests uniquement | ✅ | `git show --stat 4b21283` → 1 fichier : `tests/test_dashboard_utils.py` (450 insertions) |
| Commit GREEN présent | ✅ | `34dd92a` — `[WS-D-1] #076 GREEN: utilitaires formatage et couleurs` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 34dd92a` → 3 fichiers : `scripts/dashboard/utils.py` (+151), `tests/test_dashboard_utils.py` (+2/-6 cleanup imports), `docs/tasks/MD-1/076__wsd1_utils_formatting.md` (+64) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → exactement 2 commits (RED puis GREEN) |

### Tâche

| Critère | Verdict | Commentaire |
|---|---|---|
| Statut DONE | ✅ | Ligne 3 : `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (9/9) | Tous `[x]` |
| Checklist cochée | ⚠️ (7/9) | Items « Commit GREEN » et « Pull Request » non cochés `[ ]`. Le commit GREEN existe (34dd92a) — l'item devrait être coché. L'item PR est attendu non coché à ce stade. |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/test_dashboard_utils.py -v --tb=short` | **68 passed**, 0 failed |
| `pytest tests/ -v --tb=short` (suite complète) | **1931 passed**, 27 deselected, 0 failed |
| `ruff check scripts/dashboard/utils.py tests/test_dashboard_utils.py` | **All checks passed** |

Phase A : **PASS** — poursuite en Phase B.

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat | Analyse |
|---|---|---|---|
| §R1 — Fallbacks silencieux | `grep ' or []\| or {}...\| if .* else '` | 4 matches (L81, L98, L138, L153) | **Faux positifs** — ternaires de logique conditionnelle (format pct vs float, color choices), pas des fallbacks masquant des erreurs |
| §R1 — Except trop large | `grep 'except:$\|except Exception:'` | 0 occurrences (grep exécuté) | ✅ |
| §R7 — Print résiduel | `grep 'print('` | 0 occurrences (grep exécuté) | ✅ |
| §R3 — Shift négatif | `grep '.shift(-'` | 0 occurrences (grep exécuté) | ✅ N/A (pas de pandas) |
| §R4 — Legacy random API | `grep 'np.random.seed...'` | 0 occurrences (grep exécuté) | ✅ N/A (pas de random) |
| §R7 — TODO/FIXME | `grep 'TODO\|FIXME'` | 0 occurrences (grep exécuté) | ✅ |
| §R7 — Chemins hardcodés tests | `grep '/tmp\|C:\\'` | 0 occurrences (grep exécuté) | ✅ |
| §R7 — Imports absolus `__init__` | `grep 'from ai_trading\.'` | 0 occurrences (aucun `__init__.py` modifié) | ✅ N/A |
| §R7 — Registration manuelle tests | `grep 'register_model\|register_feature'` | 0 occurrences (grep exécuté) | ✅ N/A |
| §R6 — Mutable defaults | `grep 'def.*=[]\|def.*={}'` | 0 occurrences (grep exécuté) | ✅ |
| §R6 — `open()` sans context manager | `grep '.read_text\|open('` | 0 occurrences (grep exécuté) | ✅ N/A (pas d'I/O fichier) |
| §R6 — Bool identity | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences (grep exécuté) | ✅ |
| §R6 — Dict collision | `grep '\[.*\] = .*'` | 0 occurrences (grep exécuté) | ✅ |
| §R9 — Boucle Python numpy | `grep 'for .* in range(.*):' ` | 0 occurrences (grep exécuté) | ✅ N/A |
| §R6 — `isfinite` check | `grep 'isfinite'` | 0 occurrences (grep exécuté) | Acceptable — les fonctions traitent `None` explicitement et ne reçoivent pas d'input utilisateur brut (les valeurs viennent de `metrics.json` déjà validé) |
| §R9 — numpy répétitions | `grep 'np.[a-z]*(.*for .* in '` | 0 occurrences (grep exécuté) | ✅ N/A |
| §R7 — noqa | `grep 'noqa'` | 0 occurrences (grep exécuté) | ✅ |
| §R7 — per-file-ignores | `grep 'per-file-ignores' pyproject.toml` | Aucune entrée pour `scripts/` ou `test_dashboard_utils` | ✅ |
| §R7 — Fixtures dupliquées | `grep 'load_config.*configs/'` | 0 occurrences (grep exécuté) | ✅ N/A |

### Annotations par fichier (B2)

#### `scripts/dashboard/utils.py` (151 lignes ajoutées)

- **L66-81** `format_mean_std` — Le paramètre `fmt_type` accepte `"pct"` ou `"float"` mais aucune validation n'est effectuée. Un `fmt_type` invalide (e.g. `"percentage"`, typo) tombe silencieusement dans la branche `else` (format float) sans erreur. §R1 exige une validation explicite aux frontières.
  - Sévérité : **MINEUR**
  - Suggestion : ajouter `if fmt_type not in ("pct", "float"): raise ValueError(f"Unknown fmt_type: {fmt_type!r}")` après le guard `None`.

- **L81** `result = f"{mean:.2%} ± {std:.2%}" if fmt_type == "pct" else f"{mean:.2f} ± {std:.2f}"` — La précision est hardcodée à `.2%` / `.2f`. Or, §6.2 spécifie que Hit Rate utilise « Pourcentage, **1 décimale** » et §9.3 confirme explicitement « `:.1%` pour `hit_rate` ». La fonction ne permet pas de passer un paramètre `decimals` pour la précision, ce qui empêchera les pages dashboard de formater hit_rate conformément à la spec sans contournement (duplication de logique).
  - Sévérité : **WARNING**
  - Suggestion : ajouter un paramètre `decimals: int = 2` et utiliser `f"{mean:.{decimals}%} ± {std:.{decimals}%}"` / `f"{mean:.{decimals}f} ± {std:.{decimals}f}"`.

- **L17-23** Palette §9.2 — Les 6 constantes sont conformes aux hex de la spec. Pas de 7ème constante pour le fond graphiques (`#ffffff`) — cohérent avec l'objectif « 6 constantes » de la tâche et le fait que le fond est géré par Plotly/Streamlit.
  - Sévérité : **RAS**

- **L30-62** Fonctions `format_pct`, `format_float`, `format_int`, `format_timestamp` — Implémentation correcte, gestion `None → —` systématique, `format_pct` utilise `{value:.{decimals}%}` (pas de multiplication manuelle par 100, conforme à §9.3).
  - Sévérité : **RAS**

- **L90-138** Fonctions de seuils colorés (`pnl_color`, `sharpe_color`, `mdd_color`, `hit_rate_color`, `profit_factor_color`) — Seuils conformes à §6.2, MDD utilise les ratios corrects (`0.10`, `0.25`), None → `COLOR_NEUTRAL`.
  - Sévérité : **RAS**

- **L144-156** `format_sharpe_per_trade` — `|value| > 1000` → scientifique, `n_trades ≤ 2` → ⚠️. Conforme à §6.4.
  - Sévérité : **RAS**

#### `tests/test_dashboard_utils.py` (448 lignes)

- **Général** — 68 tests bien structurés en 12 classes, couvrant valeurs normales, `None`, zéro, négatif, bornes exactes. ID tâche `#076` dans les docstrings. Imports locaux dans chaque test (acceptable pour isolation).
  - Sévérité : **RAS**

- **TestFormatSharpePerTrade** — Pas de test pour `n_trades=3` (première valeur au-dessus du seuil ⚠️). Le boundary testing couvre `n_trades=1`, `n_trades=2` (avec ⚠️), et `n_trades=50` (sans ⚠️), mais la transition exacte `2→3` n'est pas testée.
  - Sévérité : **MINEUR**
  - Suggestion : ajouter `test_no_warning_three_trades` vérifiant `format_sharpe_per_trade(0.05, n_trades=3) == "0.05"`.

- **TestFormatSharpePerTrade** — Pas de test pour `n_trades=0` (edge case : 0 trades, devrait aussi afficher ⚠️).
  - Sévérité : **MINEUR**
  - Suggestion : ajouter `test_warning_zero_trades` vérifiant `format_sharpe_per_trade(0.0, n_trades=0) == "0.00 ⚠️"`.

- **Diff RED→GREEN** — Le commit GREEN ne modifie que les imports (`datetime, timezone` → `UTC, datetime`, suppression de `import pytest` inutilisé). Aucune logique de test modifiée. Acceptable.
  - Sévérité : **RAS**

#### `docs/tasks/MD-1/076__wsd1_utils_formatting.md`

- La checklist « Commit GREEN » est `[ ]` alors que le commit `34dd92a` existe. Incohérence cosmétique.
  - Sévérité : **MINEUR**
  - Suggestion : cocher `[x]` pour l'item « Commit GREEN ».

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères d'acceptation | ✅ | 9 critères → 12 classes de tests couvrant palette, format_pct, format_float, format_int, format_timestamp, format_mean_std, 5 color functions, format_sharpe_per_trade |
| Cas nominaux + erreurs + bords | ✅ | None, zéro, négatif, valeurs extrêmes testés pour chaque fonction |
| Boundary fuzzing | ⚠️ | Manque `n_trades=3` (transition ⚠️) et `n_trades=0` (edge case) pour `format_sharpe_per_trade` |
| Déterministes | ✅ | Pas d'aléatoire — formatage pur |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé |
| Tests registre réalistes | N/A | Pas de registre concerné |
| Contrat ABC complet | N/A | Pas d'ABC |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 — Strict code (no fallbacks) | ⚠️ | `fmt_type` non validé dans `format_mean_std` (MINEUR). Scan B1 : 4 ternaires = faux positifs |
| §R10 — Defensive indexing | ✅ | Pas d'indexation/slicing dans le code |
| §R2 — Config-driven | ✅ | Constantes couleurs dans `utils.py` (conforme à la tâche : « les couleurs sont définies comme constantes dans utils.py ») |
| §R3 — Anti-fuite | ✅ | N/A — pas de données temporelles |
| §R4 — Reproductibilité | ✅ | N/A — pas d'aléatoire. Scan B1 : 0 legacy random |
| §R5 — Float conventions | ✅ | N/A — formatage d'affichage uniquement |
| §R6 — Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 `open()` sans `with`, 0 bool identity |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Toutes fonctions et constantes en snake_case/UPPER_CASE |
| Pas de code mort/debug | ✅ | Scan B1 : 0 `print()`, 0 TODO/FIXME |
| Imports propres | ✅ | `from __future__ import annotations` + `from datetime import datetime`. Scan B1 : 0 noqa |
| DRY | ✅ | `_NULL_DISPLAY` centralisé, pas de duplication |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Commentaire |
|---|---|---|
| §9.2 Palette | ✅ | 6 constantes avec hex exacts de la spec |
| §9.3 Formatage | ⚠️ | `format_pct`, `format_float`, `format_int`, `format_timestamp` conformes. `format_mean_std` conforme pour le cas général (`.2%`, `.2f`) mais **ne supporte pas `.1%` pour hit_rate** comme exigé par §9.3 |
| §6.2 Seuils colorés | ✅ | 5 fonctions avec bornes exactes de la spec (ratios, pas pourcentages) |
| §6.4 Sharpe/trade | ✅ | Scientific > 1000, ⚠️ ≤ 2 trades |
| Plan d'implémentation | ✅ | Conforme WS-D-1.4 |
| Formules doc vs code | ✅ | Aucun off-by-one détecté |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | Toutes les fonctions retournent `str`, types d'entrée cohérents |
| Imports croisés | ✅ | Aucun import d'autres modules du projet — module autonome |
| DRY inter-modules | ✅ | Pas de duplication avec d'autres modules |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | Seuils Sharpe, MDD, Hit Rate, PF conformes aux conventions financières |
| Nommage métier cohérent | ✅ | `pnl_color`, `sharpe_color`, `mdd_color` — noms explicites |
| Séparation des responsabilités | ✅ | Module dédié au formatage/affichage, pas de calcul métier |
| Cohérence des unités/échelles | ✅ | Valeurs en ratios décimaux (0.10 = 10%), conversion automatique par Python `%.format` |

---

## Remarques

1. **[WARNING]** `format_mean_std` ne supporte pas la précision variable requise par §9.3.
   - Fichier : `scripts/dashboard/utils.py`
   - Ligne(s) : 81
   - §9.3 dit explicitement « `:.1%` pour `hit_rate` ». La function hardcode `.2%` pour tout `fmt_type="pct"`.
   - Suggestion : ajouter paramètre `decimals: int = 2` et utiliser `f"{mean:.{decimals}%} ± {std:.{decimals}%}"`.

2. **[MINEUR]** `format_mean_std` — `fmt_type` non validé.
   - Fichier : `scripts/dashboard/utils.py`
   - Ligne(s) : 66-81
   - Un `fmt_type` invalide tombe silencieusement dans le format float.
   - Suggestion : `if fmt_type not in ("pct", "float"): raise ValueError(...)`.

3. **[MINEUR]** Boundary test manquant : `n_trades=3` dans `format_sharpe_per_trade`.
   - Fichier : `tests/test_dashboard_utils.py`
   - Ligne(s) : classe `TestFormatSharpePerTrade`
   - Suggestion : ajouter test `n_trades=3` → pas de ⚠️.

4. **[MINEUR]** Edge case test manquant : `n_trades=0` dans `format_sharpe_per_trade`.
   - Fichier : `tests/test_dashboard_utils.py`
   - Ligne(s) : classe `TestFormatSharpePerTrade`
   - Suggestion : ajouter test `n_trades=0` → ⚠️.

5. **[MINEUR]** Checklist tâche : item « Commit GREEN » non coché `[ ]` alors que le commit `34dd92a` existe.
   - Fichier : `docs/tasks/MD-1/076__wsd1_utils_formatting.md`
   - Suggestion : cocher `[x]`.

---

## Actions requises

1. Ajouter un paramètre `decimals` à `format_mean_std` pour supporter `.1%` (hit_rate §9.3).
2. Valider `fmt_type` dans `format_mean_std` avec `raise ValueError`.
3. Ajouter tests boundary `n_trades=3` et `n_trades=0` pour `format_sharpe_per_trade`.
4. Cocher la checklist « Commit GREEN » dans la tâche.
