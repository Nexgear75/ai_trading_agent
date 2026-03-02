# Tâche — Baseline no-trade

Statut : DONE
Ordre : 037
Workstream : WS-9
Milestone : M4
Gate lié : M4

## Contexte
La baseline no-trade est la borne inférieure de performance : aucun trade n'est ouvert, l'équité reste constante à 1.0. Elle sert de référence pour la comparaison Go/No-Go (comparaison « pomme-à-pomme » avec les modèles de prédiction).

Références :
- Plan : `docs/plan/implementation.md` (WS-9.1)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§13.1)
- Code : `ai_trading/baselines/no_trade.py` (à créer)

Dépendances :
- Tâche 036 — Validation du gate G-Backtest (doit être DONE)

## Objectif
Implémenter la classe `NoTradeBaseline(BaseModel)` enregistrée dans le `MODEL_REGISTRY` via `@register_model("no_trade")`.

## Règles attendues
- **Architecture** : hérite de `BaseModel` (WS-6.1), `output_type = "signal"`, `execution_mode = "standard"`.
- **`fit()`** : no-op (pas d'entraînement).
- **`predict()`** : retourne un vecteur de zéros `np.zeros(N, dtype=np.float32)` — aucun signal Go.
- **Résultats attendus** : 0 trades, équité constante `E_t = 1.0`, `net_pnl = 0`, `n_trades = 0`, `MDD = 0`.
- **Enregistrement** : `@register_model("no_trade")` pour inclusion dans `MODEL_REGISTRY`.
- **Strict code** : pas de fallback, pas de valeurs par défaut implicites.

## Évolutions proposées
- Créer `ai_trading/baselines/no_trade.py` avec la classe `NoTradeBaseline`.
- Mettre à jour `ai_trading/baselines/__init__.py` pour importer et exposer la classe.
- Créer `tests/test_baseline_no_trade.py`.

## Critères d'acceptation
- [x] `NoTradeBaseline` hérite de `BaseModel` et est enregistrée `@register_model("no_trade")`.
- [x] `output_type == "signal"`, `execution_mode == "standard"`.
- [x] `fit()` est un no-op (ne modifie aucun état).
- [x] `predict(X)` retourne `np.zeros(N, dtype=np.float32)`.
- [x] Soumis au backtest commun → 0 trades, equity constante à 1.0.
- [x] Métriques attendues : `net_pnl = 0`, `n_trades = 0`, `MDD = 0`.
- [x] `"no_trade"` est résolvable via `get_model_class("no_trade")`.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/037-baseline-no-trade` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/037-baseline-no-trade` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-9] #037 RED: <résumé>` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-9] #037 GREEN: <résumé>`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-9] #037 — Baseline no-trade`.
