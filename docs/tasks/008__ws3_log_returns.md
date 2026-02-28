# Tâche — Features log-returns (logret_1, logret_2, logret_4)

Statut : TODO
Ordre : 008
Workstream : WS-3
Milestone : M2
Gate lié : G-Features

## Contexte
Les log-returns sont les features de base du pipeline. Trois variantes sont requises : `logret_1`, `logret_2`, `logret_4`, correspondant aux rendements logarithmiques sur 1, 2 et 4 bougies respectivement.

Références :
- Plan : `docs/plan/implementation.md` (WS-3.1)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§6.2)
- Code : `ai_trading/features/log_returns.py` (à créer)

Dépendances :
- Tâche 007 — Registre de features et BaseFeature (doit être DONE)

## Objectif
Implémenter les trois features log-return en tant que classes `BaseFeature` enregistrées dans le registre via `@register_feature` :
- `logret_1(t) = log(C_t / C_{t-1})`
- `logret_2(t) = log(C_t / C_{t-2})`
- `logret_4(t) = log(C_t / C_{t-4})`

## Règles attendues
- **Anti-fuite** : chaque feature à t ne dépend que de données ≤ t (causalité stricte).
- **Config-driven** : aucun paramètre hardcodé (les périodes k ∈ {1, 2, 4} sont implicites dans le nom de la feature, conformément à la spec §6.2).
- **Strict code** : NaN explicite aux positions t < k (pas de remplissage par 0 ou forward-fill).

## Évolutions proposées
- Créer `ai_trading/features/log_returns.py` avec 3 classes : `LogReturn1`, `LogReturn2`, `LogReturn4`.
- Chaque classe hérite de `BaseFeature` et est décorée `@register_feature("logret_1")`, etc.
- `compute(ohlcv, params)` utilise la colonne `close` du DataFrame OHLCV.
- `min_periods` retourne k (1, 2, ou 4 respectivement).
- `required_params` est une liste vide (pas de paramètre configurable).

## Critères d'acceptation
- [ ] 3 classes enregistrées : `logret_1`, `logret_2`, `logret_4` dans `FEATURE_REGISTRY`.
- [ ] Valeurs numériques correctes sur données synthétiques calculées à la main.
- [ ] NaN aux positions t < k pour chaque variante.
- [ ] Causalité vérifiée : modifier `close[t > T]` ne modifie pas `logret_k[t <= T]`.
- [ ] Résultat ≈ `np.log(close / close.shift(k))` (tolérance `atol=1e-12`).
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords.
- [ ] Suite de tests verte après implémentation.
- [ ] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/008-log-returns` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/008-log-returns` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-3] #008 RED: tests log-returns features`.
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-3] #008 GREEN: log-returns features`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-3] #008 — Features log-returns`.
