# Tâche — Validation des métriques sur données réelles BTCUSDT

Statut : TODO
Ordre : 057
Workstream : WS-13
Milestone : M6
Gate lié : M6

## Contexte
Après l'exécution du pipeline grandeur nature (tâche 056), il faut valider que les métriques produites sur ~73 000 bougies réelles sont numériquement cohérentes. Les tests sur données synthétiques (500 bougies) ne garantissent pas la robustesse sur un volume réaliste. Ce test complémentaire vérifie l'absence de NaN/Inf et le respect des plages attendues pour chaque métrique de trading et de prédiction.

Références :
- Plan : `docs/plan/implementation.md` (WS-13.3)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§13, §14)
- Code : `ai_trading/metrics/trading.py`, `ai_trading/metrics/prediction.py`, `ai_trading/metrics/aggregation.py`

Dépendances :
- Tâche 056 — Test fullscale make run-all (doit être DONE)

## Objectif
Ajouter dans `tests/test_fullscale_btc.py` un ou plusieurs tests marqués `@pytest.mark.fullscale` qui valident la cohérence numérique des métriques produites par le run grandeur nature sur données réelles BTCUSDT.

## Règles attendues
- Accès réseau réel obligatoire : pas de fixtures synthétiques.
- Les tests réutilisent le run directory produit par le test de la tâche 056 (ou s'exécutent après le run complet).
- Aucune valeur numérique attendue hardcodée (on vérifie des plages et l'absence de NaN/Inf, pas des valeurs exactes).

## Évolutions proposées
- Ajouter dans `tests/test_fullscale_btc.py` un test `test_fullscale_metrics_coherence` (marqué `@pytest.mark.fullscale`) qui, pour chaque fold du run :
  1. Vérifie que `net_pnl` est un float fini (pas NaN, pas Inf).
  2. Vérifie que `max_drawdown` ∈ [0, 1].
  3. Vérifie que `n_trades >= 0`.
  4. Vérifie que `sharpe` est un float fini.
  5. Vérifie que `hit_rate` ∈ [0, 1] si `n_trades > 0`.
- Valider l'agrégation inter-fold :
  6. Le bloc `aggregated` contient `mean` et `std` pour chaque métrique de trading.
  7. Les valeurs `mean` et `std` sont des floats finis.

## Critères d'acceptation
- [ ] Test `test_fullscale_metrics_coherence` existe dans `tests/test_fullscale_btc.py`, marqué `@pytest.mark.fullscale`.
- [ ] Pour chaque fold : `net_pnl` est un float fini.
- [ ] Pour chaque fold : `max_drawdown` ∈ [0, 1].
- [ ] Pour chaque fold : `n_trades >= 0`.
- [ ] Pour chaque fold : `sharpe` est un float fini.
- [ ] Pour chaque fold : `hit_rate` ∈ [0, 1] si `n_trades > 0`.
- [ ] Agrégation inter-fold contient `mean` et `std` pour chaque métrique de trading.
- [ ] Toutes les valeurs agrégées sont des floats finis.
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords.
- [ ] Suite de tests standard verte après implémentation.
- [ ] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/057-fullscale-metrics-validation` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/057-fullscale-metrics-validation` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-13] #057 RED: tests validation métriques fullscale`.
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-13] #057 GREEN: validation métriques fullscale BTCUSDT`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-13] #057 — Validation métriques fullscale BTCUSDT`.
