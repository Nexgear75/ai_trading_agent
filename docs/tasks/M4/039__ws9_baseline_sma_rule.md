# Tâche — Baseline SMA rule (Go/No-Go)

Statut : DONE
Ordre : 039
Workstream : WS-9
Milestone : M4
Gate lié : M4

## Contexte
La baseline SMA rule génère des signaux Go/No-Go basés sur le croisement de deux moyennes mobiles simples (SMA fast et SMA slow). Elle est soumise au backtest commun et sert de comparaison « pomme-à-pomme » avec les modèles de prédiction. Le contrat de causalité est strict : `rolling().mean()` est backward-looking par construction.

Références :
- Plan : `docs/plan/implementation.md` (WS-9.3)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§13.3, Annexe E.2.4)
- Code : `ai_trading/baselines/sma_rule.py`

Dépendances :
- Tâche 036 — Validation du gate G-Backtest (doit être DONE)

## Objectif
Implémenter la classe `SmaRuleBaseline(BaseModel)` enregistrée dans le `MODEL_REGISTRY` via `@register_model("sma_rule")`, avec calcul causal des SMA et génération des signaux Go/No-Go.

## Règles attendues
- **Architecture** : hérite de `BaseModel`, `output_type = "signal"`, `execution_mode = "standard"`.
- **`fit()`** : no-op.
- **`predict(X, meta=None, ohlcv=None)`** : utilise le paramètre `ohlcv` (DataFrame OHLCV complet) pour calculer `SMA_fast` et `SMA_slow` sur les clôtures via `pd.Series.rolling(window).mean()`.
- **Signal** : `Go (1)` si `SMA_fast(t) > SMA_slow(t)`, sinon `No-Go (0)`.
- **Alignement temporel** : utilise `meta['decision_time']` pour filtrer les signaux aux timestamps correspondant à `X`.
- **Causalité stricte** : `rolling()` est backward-looking. Ne jamais utiliser `apply()`, `shift(-k)`, ou toute opération look-ahead.
- **Premières décisions** : quand `SMA_slow` n'est pas définie → `No-Go`.
- **Config-driven** : `fast` et `slow` lus depuis `configs/default.yaml` (`baselines.sma.fast`, `baselines.sma.slow`). MVP : fast=20, slow=50.
- **Contrainte** : `fast < slow`.

## Évolutions proposées
- Créer `ai_trading/baselines/sma_rule.py` avec la classe `SmaRuleBaseline`.
- Mettre à jour `ai_trading/baselines/__init__.py` pour importer et exposer la classe.
- Créer `tests/test_baseline_sma_rule.py`.

## Critères d'acceptation
- [x] `SmaRuleBaseline` hérite de `BaseModel` et est enregistrée `@register_model("sma_rule")`.
- [x] `output_type == "signal"`, `execution_mode == "standard"`.
- [x] `fit()` est un no-op.
- [x] `predict()` calcule SMA via `pd.Series.rolling(window).mean()` sur `ohlcv["close"]`.
- [x] Signal correct sur séries synthétiques : tendance haussière → Go, baissière → No-Go.
- [x] Premières décisions (SMA_slow non définie) → No-Go.
- [x] Paramètres `fast` et `slow` lus depuis la config (`baselines.sma.fast`, `baselines.sma.slow`).
- [x] Validation `fast < slow` avec `raise` si non respecté.
- [x] **Test de causalité** : modifier les prix futurs (t > T) et vérifier que `predict()` retourne le même signal pour tout t ≤ T.
- [x] `"sma_rule"` est résolvable via `get_model_class("sma_rule")`.
- [x] Soumis au backtest commun → `n_trades >= 0`.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/039-baseline-sma-rule` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/039-baseline-sma-rule` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-9] #039 RED: tests for SmaRuleBaseline`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-9] #039 GREEN: <résumé>`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-9] #039 — Baseline SMA rule`.
