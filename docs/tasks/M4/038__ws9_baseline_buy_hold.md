# Tâche — Baseline buy & hold

Statut : DONE
Ordre : 038
Workstream : WS-9
Milestone : M4
Gate lié : M4

## Contexte
La baseline buy & hold achète au début de la période test et vend à la fin. Elle sert de comparaison contextuelle (position continue vs décisions discrètes Go/No-Go). Son comportement repose sur `execution_mode = "single_trade"`, déjà supporté par le moteur de backtest (WS-8.1).

Références :
- Plan : `docs/plan/implementation.md` (WS-9.2)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§12.5, §13.2)
- Code : `ai_trading/baselines/buy_hold.py` (à créer)

Dépendances :
- Tâche 036 — Validation du gate G-Backtest (doit être DONE)

## Objectif
Implémenter la classe `BuyHoldBaseline(BaseModel)` enregistrée dans le `MODEL_REGISTRY` via `@register_model("buy_hold")`, avec `execution_mode = "single_trade"`.

## Règles attendues
- **Architecture** : hérite de `BaseModel`, `output_type = "signal"`, `execution_mode = "single_trade"`.
- **`fit()`** : no-op.
- **`predict()`** : retourne un vecteur de uns `np.ones(N, dtype=np.float32)` — signal Go permanent.
- **Intégration backtest** : l'orchestrateur transmet `execution_mode = "single_trade"` au moteur. Un seul trade : entrée à `Open[first_test_timestamp]` (sans décalage t→t+1), sortie à `Close[last_test_timestamp]`.
- **Coûts** : `f` et `s` appliqués une fois à l'entrée et une fois à la sortie.
- **Résultat** : `n_trades = 1`, `net_return = (1-f)^2 * Close_end*(1-s) / (Open_start*(1+s)) - 1`.
- **Equity** : constante pendant la durée du trade, mise à jour à la dernière bougie.
- **Divergence signaux/trades attendue** : `preds_test.csv` contient des signaux `1` sur toute la période alors qu'un seul trade est exécuté — documenté et conforme.

## Évolutions proposées
- Créer `ai_trading/baselines/buy_hold.py` avec la classe `BuyHoldBaseline`.
- Mettre à jour `ai_trading/baselines/__init__.py` pour importer et exposer la classe.
- Créer `tests/test_baseline_buy_hold.py`.

## Critères d'acceptation
- [x] `BuyHoldBaseline` hérite de `BaseModel` et est enregistrée `@register_model("buy_hold")`.
- [x] `output_type == "signal"`, `execution_mode == "single_trade"`.
- [x] `fit()` est un no-op.
- [x] `predict(X)` retourne `np.ones(N, dtype=np.float32)`.
- [x] Soumis au backtest en mode `single_trade` → `n_trades = 1`.
- [x] `net_return` cohérent avec `(1-f)^2 * Close_end*(1-s) / (Open_start*(1+s)) - 1`.
- [x] `exposure_time_frac = 1.0` exactement (Note I-08).
- [x] `"buy_hold"` est résolvable via `get_model_class("buy_hold")`.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/038-baseline-buy-hold` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/038-baseline-buy-hold` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-9] #038 RED: tests for BuyHoldBaseline`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-9] #038 GREEN: BuyHoldBaseline with single_trade mode, permanent Go signal, backtest integration`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-9] #038 — Baseline buy & hold`.
