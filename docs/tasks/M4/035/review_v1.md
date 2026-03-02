# Revue PR — [WS-8] #035 — Journal de trades (trades.csv)

Branche : `task/035-trade-journal`
Tâche : `docs/tasks/M4/035__ws8_trade_journal.md`
Date : 2025-03-02

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

L'implémentation du journal de trades est propre, bien testée, et conforme à la spec §12.6. Les formules de coûts, le `gross_return`, le `net_return` et la cohérence avec l'équité finale sont correctement validés. Un seul point bloquant : l'écriture CSV ne garantit pas la création du répertoire parent du fichier de sortie (§R6 — Path creation). Deux points mineurs complètent le rapport.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/035-trade-journal` | ✅ | `git branch --show-current` → `task/035-trade-journal` |
| Commit RED présent | ✅ | `840a2e3` — `[WS-8] #035 RED: tests journal de trades CSV` |
| Commit GREEN présent | ✅ | `43930d4` — `[WS-8] #035 GREEN: export trade journal CSV` |
| Commit RED = tests uniquement | ✅ | `git show --stat 840a2e3` → 1 fichier: `tests/test_trade_journal.py` (454 insertions) |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 43930d4` → `ai_trading/backtest/journal.py` (141), `docs/tasks/M4/035__ws8_trade_journal.md` (63), `tests/test_trade_journal.py` (5 ajustements) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → exactement 2 commits (RED + GREEN) |

### Tâche

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` en tête du fichier de tâche |
| Critères d'acceptation cochés | ✅ (12/12) | Tous les 12 critères `[x]` |
| Checklist cochée | ⚠️ (7/9) | 2 items non cochés : Commit GREEN et Pull Request (voir MINEUR #1) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **958 passed**, 0 failed (6.61s) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

Phase A : **PASS** (CI green, structure TDD conforme)

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| Fallbacks silencieux (§R1) | `grep -n ' or \[\]...'` | 0 occurrences (grep exécuté) |
| Except trop large (§R1) | `grep -n 'except:\|except Exception:'` | 0 occurrences (grep exécuté) |
| Suppressions lint (§R7) | `grep -n 'noqa'` | 0 occurrences (grep exécuté) |
| Print résiduel (§R7) | `grep -n 'print('` | 0 occurrences (grep exécuté) |
| Shift négatif (§R3) | `grep -n '.shift(-'` | 0 occurrences (grep exécuté) |
| Legacy random API (§R4) | `grep -n 'np.random.seed...'` | 0 occurrences (grep exécuté) |
| TODO/FIXME orphelins (§R7) | `grep -n 'TODO\|FIXME'` | 0 occurrences (grep exécuté) |
| Chemins hardcodés (§R7) | `grep -n '/tmp\|/var/tmp'` tests | 0 occurrences (grep exécuté) |
| Imports absolus `__init__` (§R7) | `grep -n 'from ai_trading\.'` `__init__.py` | 0 occurrences (grep exécuté) |
| Registration manuelle tests (§R7) | `grep -n 'register_model\|register_feature'` | 0 occurrences (grep exécuté) — N/A module |
| Mutable defaults (§R6) | `grep -n 'def .*=\[\]\|def .*={}'` | 0 occurrences (grep exécuté) |
| `open()` sans context manager (§R6) | `grep -n 'open('` | 0 occurrences (grep exécuté) ; écriture via `df.to_csv()` (géré par pandas) |
| Bool identity (§R6) | `grep -n 'is True\|is False\|is np.bool_'` | 0 occurrences (grep exécuté) |
| `isfinite` présent (§R6) | `grep -c 'isfinite'` journal.py | 2 occurrences — validation `math.isfinite` pour `fee_rate_per_side` et `slippage_rate_per_side` |
| Boucle Python sur array (§R9) | `grep -n 'for .* in range'` | 0 occurrences (grep exécuté) — itération sur `list[dict]`, pas sur array numpy |
| Numpy comp vectorisable (§R9) | `grep -n 'np\.\[a-z\]*(.*for'` | 0 occurrences (grep exécuté) |
| Dict collision (§R6) | `grep -n 'dict.*\[.*\] ='` | 0 occurrences (grep exécuté) — rows construit par append |
| Fixtures dupliquées (§R7) | `grep -n 'load_config.*configs/'` tests | 0 occurrences (grep exécuté) — pas de config utilisée |

### Annotations par fichier (B2)

#### `ai_trading/backtest/journal.py` (141 lignes)

- **L104** `df.to_csv(path, index=False)` : **le répertoire parent de `path` n'est pas créé avant écriture**. Si le caller passe un chemin comme `run_dir / "backtest" / "trades.csv"` et que `run_dir / "backtest"` n'existe pas, `to_csv` lèvera `FileNotFoundError`. Le docstring dit « Destination CSV file path » mais ne documente pas explicitement que le parent doit pré-exister.
  Sévérité : **BLOQUANT** (§R6 — Path creation : « si un paramètre path est reçu et utilisé pour I/O, il doit être créé avant usage ou le contrat exige explicitement qu'il préexiste »)
  Suggestion : ajouter `path.parent.mkdir(parents=True, exist_ok=True)` avant `df.to_csv(path, index=False)`, ou documenter explicitement dans le docstring que le parent doit pré-exister.

- **L78–104** Boucle `for i, trade in enumerate(trades)` : itère sur une `list[dict]` Python pour construire les rows du DataFrame. C'est la bonne approche pour un nombre de trades typiquement petit (< 10K). Pas de problème de performance.
  Sévérité : RAS

- **L107–129** `_validate_rates` : utilise `math.isfinite()` avant les bornes `[0, 1)`. Correct — NaN et ±inf sont rejetés.
  Sévérité : RAS

- **L132–141** `_validate_trade` : valide la présence des clés requises et `entry_price > 0`. `exit_price > 0` n'est pas validé, mais la division `exit_price / entry_price` n'exige que `entry_price ≠ 0` (un `exit_price = 0` donnerait `gross_return = -1`, ce qui est mathématiquement valide comme perte totale). L'invariant `exit_price > 0` est garanti en amont par les données OHLCV.
  Sévérité : RAS

- **L17–28** `_REQUIRED_TRADE_KEYS` : frozenset contenant les 9 clés attendues. Cohérent avec la sortie de `apply_cost_model` (clés `entry_price_eff`, `exit_price_eff`, `r_net`) + clés ajoutées par le caller (`y_true`, `y_hat`) + clés originales de `execute_trades` (`entry_time`, `exit_time`, `entry_price`, `exit_price`).
  Sévérité : RAS

- **L30–44** `_COLUMN_ORDER` : les 14 colonnes dans l'ordre exact de §12.6. Vérifié par comparaison directe avec la spec.
  Sévérité : RAS

#### `tests/test_trade_journal.py` (455 lignes)

- RAS après lecture complète du diff. Tests bien structurés en classes thématiques (column order, fees, slippage, gross_return, net_return, equity coherence, y_hat, empty trades, multiple trades, missing keys, invalid rates, entry price validation). Couverture complète des critères d'acceptation. Utilisation systématique de `tmp_path` pour les chemins. `pytest.approx` pour les comparaisons float.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères d'acceptation | ✅ | AC1→TestColumnOrder, AC2→TestFeesPaid, AC3→TestSlippagePaid, AC4→TestGrossReturn, AC5→TestNetReturn, AC6→TestEquityCoherence, AC7→TestYHat, AC8→TestEmptyTrades, AC9/10→TestMultipleTradesCsv |
| Cas nominaux + erreurs + bords | ✅ | Nominaux (8 classes), Erreurs (TestMissingKeys, TestInvalidRates, TestEntryPriceValidation), Bords (TestEmptyTrades, fee=0, slippage=0, entry=exit) |
| Boundary fuzzing — taux | ✅ | fee=0 (TestFeesPaid.test_fees_paid_zero_fee_rate), fee<0 (raises), fee≥1 (raises), NaN (raises), inf (raises), slippage=0 (TestSlippagePaid.test_slippage_paid_zero_rate), slippage<0 (raises), slippage≥1 (raises), NaN (raises), inf (raises) |
| Boundary fuzzing — entry_price | ✅ | entry_price=0 (raises), entry_price<0 (raises) |
| Boundary fuzzing — missing keys | ✅ | Paramétrisé sur les 9 clés requises |
| Déterministes | ✅ | Pas d'aléatoire — données synthétiques déterministes |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé, tous les chemins via `tmp_path` |
| Tests registre réalistes | N/A | Pas de registre dans ce module |
| Contrat ABC complet | N/A | Pas d'ABC dans ce module |
| Pas de test `@skip`/`xfail` | ✅ | Vérifié par lecture du fichier |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| Strict code (§R1) | ✅ | Scan B1 : 0 fallback, 0 except. Validation explicite avec `raise ValueError` |
| Defensive indexing (§R10) | ✅ | Pas de slicing critique ; itération simple sur list[dict] |
| Config-driven (§R2) | ✅ | `f` et `s` passés en paramètres, lus depuis config par le caller. Config `costs.fee_rate_per_side` / `costs.slippage_rate_per_side` présents dans `configs/default.yaml` (L115-116) |
| Anti-fuite (§R3) | ✅ | Scan B1 : 0 `.shift(-`. Module d'export pur, aucun accès aux données temporelles |
| Reproductibilité (§R4) | ✅ | Scan B1 : 0 legacy random. Fonction déterministe sans aléatoire |
| Float conventions (§R5) | ✅ | Pas de tenseurs. DataFrame utilise float64 par défaut (correct pour métriques financières) |
| Anti-patterns Python (§R6) | ⚠️ | `path.parent.mkdir()` manquant (BLOQUANT #1). Reste OK : 0 mutable default, 0 `open()` direct, `isfinite` présent (2 occ.), 0 bool identity |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage et style | ✅ | snake_case cohérent, noms explicites (`_validate_rates`, `_validate_trade`, `_COLUMN_ORDER`) |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO/FIXME |
| Imports propres / relatifs | ✅ | `from __future__ import annotations`, `import math`, `from pathlib import Path`, `import pandas as pd` — ordre stdlib→third-party |
| DRY | ⚠️ | Validation des taux en [0, 1) avec isfinite dupliquée entre `journal.py` et `costs.py` (MINEUR #2) |
| `__init__.py` à jour | ✅ | `ai_trading/backtest/__init__.py` ne nécessite pas d'import du journal (pas de side-effect d'enregistrement) |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Preuve |
|---|---|---|
| Spécification §12.6 | ✅ | Colonnes identiques à §12.6 : `entry_time_utc, exit_time_utc, entry_price, exit_price, entry_price_eff, exit_price_eff, f, s, fees_paid, slippage_paid, y_true, y_hat, gross_return, net_return` |
| Plan d'implémentation WS-8.4 | ✅ | Module dédié `ai_trading/backtest/journal.py` conformément au plan |
| Formules doc vs code | ✅ | `fees_paid = f * (entry_price + exit_price)` ✓ (L97), `slippage_paid = s * (entry_price + exit_price)` ✓ (L98), `gross_return = (exit_price / entry_price) - 1` ✓ (L90), `net_return = r_net` (passthrough de apply_cost_model) ✓ (L101) |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `export_trade_journal(trades, path, f, s) → pd.DataFrame` — cohérent avec l'usage attendu |
| Noms de colonnes DataFrame | ✅ | Renommage `entry_time` → `entry_time_utc`, `exit_time` → `exit_time_utc` conforme à §12.6 |
| Clés de configuration | ✅ | `fee_rate_per_side`, `slippage_rate_per_side` → `configs/default.yaml` L115-116 |
| Structures de données partagées | ✅ | `_REQUIRED_TRADE_KEYS` cohérent avec sortie de `apply_cost_model` (costs.py) + `execute_trades` (engine.py) |
| Conventions numériques | ✅ | Float64 (pandas default) pour métriques. Pas de tenseur |
| Imports croisés | ✅ | Aucun import d'autres modules `ai_trading` — module autonome |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | `gross_return = (exit/entry) - 1` correct. `net_return` via multiplicatif M_net - 1 (passthrough). Décomposition coûts additive conforme à la tâche |
| Nommage métier cohérent | ✅ | `fees_paid`, `slippage_paid`, `gross_return`, `net_return` — standard |
| Séparation des responsabilités | ✅ | Module d'export pur, distinct de l'exécution (engine.py) et des coûts (costs.py) |
| Invariants de domaine | ✅ | `entry_price > 0` validé, taux dans `[0, 1)` validés |
| Cohérence des unités/échelles | ✅ | Returns arithmétiques, prix en quote currency |
| Patterns de calcul financier | ✅ | Pas de boucle numpy inutile. Calculs simples sur scalaires puis construction DataFrame |

---

## Remarques

1. **[BLOQUANT]** Path parent non créé avant écriture CSV
   - Fichier : `ai_trading/backtest/journal.py`
   - Ligne : 104
   - Description : `df.to_csv(path, index=False)` est appelé sans garantir que `path.parent` existe. Si le caller passe un chemin imbriqué (`run_dir / "backtest" / "trades.csv"`) dont le parent n'existe pas encore, un `FileNotFoundError` sera levé. Le docstring ne documente pas non plus que le parent doit pré-exister.
   - Règle : §R6 — Path creation (« si un paramètre path est reçu et utilisé pour I/O, il doit être créé avant usage ou le contrat exige explicitement qu'il préexiste »)
   - Suggestion : ajouter avant L104 :
     ```python
     path.parent.mkdir(parents=True, exist_ok=True)
     ```

2. **[MINEUR]** Checklist Commit GREEN non cochée
   - Fichier : `docs/tasks/M4/035__ws8_trade_journal.md`
   - Ligne : dernière section (checklist)
   - Description : L'item `[ ] **Commit GREEN**` n'est pas coché alors que le commit `43930d4` existe avec le message attendu `[WS-8] #035 GREEN: export trade journal CSV`. L'item Pull Request n'est pas coché non plus, ce qui est attendu (PR non encore créée).
   - Suggestion : cocher `[x]` l'item Commit GREEN dans la checklist.

3. **[MINEUR]** Duplication de la logique de validation des taux entre `costs.py` et `journal.py`
   - Fichier : `ai_trading/backtest/journal.py` L107-129 vs `ai_trading/backtest/costs.py` L44-50
   - Description : La validation `[0, 1)` pour `fee_rate_per_side` et `slippage_rate_per_side` est dupliquée dans les deux modules. De plus, `costs.py` ne valide PAS `isfinite` (pré-existant, hors scope de cette PR) tandis que `journal.py` le fait. Risque de drift futur si les règles de validation évoluent dans un seul des deux modules.
   - Suggestion : à terme, extraire une fonction utilitaire `_validate_rate(name, value)` dans un module partagé (ex : `ai_trading/backtest/_validation.py`) et l'utiliser dans les deux modules. Hors scope immédiat de cette PR.

## Résumé

Implémentation solide et bien testée (12 classes de tests, couverture complète des critères d'acceptation, boundary fuzzing sur les taux et prix). Un seul point bloquant : la création du répertoire parent avant écriture CSV (§R6). Deux points mineurs de maintenance (checklist, duplication validation). Après correction du bloquant, le code sera prêt pour merge.
