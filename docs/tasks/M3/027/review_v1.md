# Review v1 — task/027-cost-model

**Branche** : `task/027-cost-model`
**Tâche** : `docs/tasks/M3/027__ws8_cost_model.md`
**Date** : 2025-03-02
**Reviewer** : Copilot (Claude Opus 4.6)
**Verdict** : **CLEAN**

---

## Phase A — Compliance rapide

### A1. Périmètre

3 fichiers modifiés :
| Fichier | Type |
|---|---|
| `ai_trading/backtest/costs.py` | nouveau — implémentation |
| `tests/test_cost_model.py` | nouveau — tests |
| `docs/tasks/M3/027__ws8_cost_model.md` | mis à jour — statut DONE |

### A2. Structure branche & commits

- [x] Branche `task/027-cost-model` depuis `Max6000i1`.
- [x] Commit RED : `a16e0cc [WS-8] #027 RED: tests modèle de coûts de transaction` — contient uniquement `tests/test_cost_model.py` (212 insertions).
- [x] Commit GREEN : `1296ac5 [WS-8] #027 GREEN: modèle de coûts de transaction` — contient `ai_trading/backtest/costs.py` (81 lignes), `docs/tasks/M3/027__ws8_cost_model.md` (mise à jour statut), `tests/test_cost_model.py` (1 suppression mineure).
- [x] Pas de commits parasites entre RED et GREEN.

### A3. Tâche associée

- [x] Statut : DONE
- [x] Critères d'acceptation : tous cochés `[x]` (11/11)
- [x] Checklist : tous cochés `[x]` sauf PR (attendu — pas encore ouverte)

### A4. Suite de validation

- [x] `pytest` : **764 passed** en 7.05s — 0 échec
- [x] `ruff check ai_trading/ tests/` : **All checks passed!**

---

## Phase B — Code review adversariale

### B1. Scan automatisé

| Check | Résultat |
|---|---|
| Fallbacks silencieux (`or []`, `or {}`, `if x else`) | ✅ clean |
| Except trop large | ✅ clean |
| Print résiduel | ✅ clean |
| Shift négatif | ✅ clean |
| Legacy random API | ✅ clean |
| TODO / FIXME / HACK | ✅ clean |
| Chemins hardcodés | ✅ clean |
| Imports absolus `__init__.py` | ✅ clean |
| Registration manuelle tests | ✅ clean |
| Mutable defaults | ✅ clean |
| `open()` sans context manager | ✅ clean |

### B2. Revue ligne par ligne

#### `ai_trading/backtest/costs.py` (81 lignes)

**Structure** : un module à fonction unique `apply_cost_model()`. Pas de dépendances externes (pur Python). Docstring complète avec paramètres, retour et exceptions.

**Validation des entrées** :
- `fee_rate_per_side < 0` → `ValueError` ✅
- `slippage_rate_per_side < 0` → `ValueError` ✅
- Clé `entry_price` manquante → `ValueError` ✅
- Clé `exit_price` manquante → `ValueError` ✅
- `entry_price <= 0` → `ValueError` (évite division par zéro) ✅

**Formules** (vérifiées contre spec §12.3) :
- `p_entry_eff = p_entry × (1 + s)` ✅ exact
- `p_exit_eff = p_exit × (1 - s)` ✅ exact
- `fee_factor_sq = (1 - f)²` pré-calculé hors boucle ✅ optimisation correcte
- `m_net = fee_factor_sq × (p_exit_eff / p_entry_eff)` ✅ exact
- `r_net = m_net - 1` ✅ exact

**Immutabilité** : les trades d'entrée ne sont pas mutés (`{**trade, ...}` crée un nouveau dict). ✅

**Float convention** : calculs en float Python natif (float64). ✅ conforme.

**Retour** : nouvelle liste de dicts avec clés ajoutées `entry_price_eff`, `exit_price_eff`, `m_net`, `r_net`. Les clés originales sont préservées. ✅

**Aucun fallback** : pas de valeur par défaut, pas de `or`, pas de `try/except`. Strict. ✅

### B3. Revue des tests

#### `tests/test_cost_model.py` (211 lignes, 16 tests)

**Naming** : `test_cost_model.py` ✅ convention respectée.

**Couverture des critères d'acceptation** :

| AC | Test(s) | Verdict |
|---|---|---|
| AC1 — M_net formula | `test_m_net_formula` | ✅ |
| AC2 — p_entry_eff, p_exit_eff | `test_entry_price_eff`, `test_exit_price_eff` | ✅ |
| AC3 — r_net = M_net - 1 | `test_r_net_formula` | ✅ |
| AC4 — Numerical hand calc | `test_numerical_hand_calculation` | ✅ |
| AC5 — Symmetric slippage | `test_symmetric_slippage` | ✅ |
| AC6 — Config-driven | Tests passent fee/slippage en paramètre, pas hardcodé | ✅ |
| AC7 — p_entry == p_exit → r_net < 0 | `test_equal_entry_exit_negative_r_net` | ✅ |
| AC8 — f=0, s=0 → raw return | `test_zero_costs_raw_return` | ✅ |
| AC9 — Nominal + erreurs + bords | 3 classes : Formula, Edge, Validation | ✅ |

**Cas couverts** :
- Nominaux : 6 tests de formules ✅
- Bords : empty list, multiple trades, equal prices, losing trade, original keys preserved ✅
- Erreurs : fee < 0, slippage < 0, missing entry_price, missing exit_price, entry_price = 0, entry_price < 0 ✅
- Déterminisme : aucun aléa, données synthétiques ✅
- Pas de réseau, pas de chemins hardcodés ✅

### B4. Règles non négociables

- [x] **Strict code** : validation explicite + raise, aucun fallback, aucun except.
- [x] **Config-driven** : `fee_rate_per_side` et `slippage_rate_per_side` passés en paramètres (lus depuis `CostsConfig` en amont). `configs/default.yaml` contient les valeurs (`0.0005`, `0.00025`).
- [x] **Anti-fuite** : N/A pour le cost model (pas de données temporelles).
- [x] **Float conventions** : float64 (Python natif) pour tous les calculs de retour. ✅
- [x] **Pas de mutable defaults** : aucun `def f(x=[])`.
- [x] **Pas de `.values` misuse** : pas de pandas dans ce module.
- [x] **Pas de `float ==`** : tests utilisent `pytest.approx(rel=1e-12)`.

### B5. Qualité du code

- [x] snake_case partout.
- [x] Pas de code mort, pas de `print()`, pas de TODO.
- [x] Imports propres : uniquement `from __future__ import annotations`.
- [x] DRY : aucune duplication. `fee_factor_sq` pré-calculé une seule fois.

### B6. Cohérence avec la spec §12.3

Formule spec :
$$M_{net} = (1 - f)^2 \cdot \frac{Close_{t+H} \cdot (1 - s)}{Open_{t+1} \cdot (1 + s)}$$

Implémentation :
```python
fee_factor_sq = (1 - fee_rate_per_side) ** 2
p_entry_eff = p_entry * (1 + slippage_rate_per_side)
p_exit_eff = p_exit * (1 - slippage_rate_per_side)
m_net = fee_factor_sq * (p_exit_eff / p_entry_eff)
r_net = m_net - 1
```

**Correspondance exacte** : la formule est décomposée en étapes lisibles mais mathématiquement identique. ✅

### B7. Cohérence intermodule

- **Avec `execute_trades()`** : les dicts produits par `engine.py` contiennent `signal_time`, `entry_time`, `exit_time`, `entry_price`, `exit_price`. Le cost model requiert `entry_price` et `exit_price`, et préserve toutes les clés. ✅ Compatible.
- **Avec `CostsConfig`** : paramètres `fee_rate_per_side` et `slippage_rate_per_side` correspondent aux champs du modèle Pydantic. ✅
- **Avec `configs/default.yaml`** : clés `costs.fee_rate_per_side` et `costs.slippage_rate_per_side` présentes. ✅

---

## Remarques

Aucune remarque. Le code est conforme, les tests sont complets, la spec est respectée.

---

## Résumé

Implémentation exemplaire du modèle de coûts de transaction (tâche #027). Le module `costs.py` est minimal (81 lignes), strict (validation explicite sans fallback), et conforme à la spec §12.3 (4 formules vérifiées). Les 16 tests couvrent l'intégralité des critères d'acceptation avec des cas nominaux, bords et erreurs. Aucun problème détecté.

**Verdict : CLEAN** — 0 bloquant, 0 warning, 0 mineur.
