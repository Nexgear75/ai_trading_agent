# Tâche — Fallback θ (aucun quantile valide)

Statut : DONE
Ordre : 032
Workstream : WS-7
Milestone : M3
Gate lié : M3

## Contexte
Lorsqu'aucun θ candidat ne satisfait simultanément les contraintes `mdd <= mdd_cap` ET `n_trades >= min_trades`, le pipeline doit appliquer une logique de fallback définie dans l'Annexe E.2.2 de la spec. Le fold est conservé dans les résultats avec des métriques nulles plutôt que d'être supprimé.

Références :
- Plan : `docs/plan/implementation.md` (WS-7.3)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (Annexe E.2.2)
- Code : `ai_trading/calibration/threshold.py` (extension du module existant)

Dépendances :
- Tâche 031 — WS-7 theta optimization (doit être DONE)

## Objectif
Implémenter la logique de fallback θ conforme à l'Annexe E.2.2 : relaxation progressive des contraintes, θ = +∞ en dernier recours, et conservation du fold avec métriques nulles.

## Règles attendues
- **Strict code** : pas de fallback silencieux — un warning explicite est émis à chaque étape de relaxation.
- **Conformité spec** : suivre exactement la séquence définie dans E.2.2.
- **Traçabilité** : le fold est conservé dans les métriques même avec 0 trades.

## Évolutions proposées

### 1. Logique de fallback séquentielle
Intégrée à `calibrate_threshold()` (ou fonction dédiée) :

1. **Étape 1** : si aucun θ ne satisfait `mdd <= mdd_cap` ET `n_trades >= min_trades` :
   - Relâcher `min_trades` à 0
   - Retenir le θ qui satisfait `mdd <= mdd_cap` (le plus conservateur = quantile le plus haut)
   - Émettre un `WARNING` avec détails (contrainte relâchée, θ retenu)

2. **Étape 2** : si aucun θ ne respecte même `mdd <= mdd_cap` :
   - `θ = +∞` (no-trade pour ce fold)
   - Émettre un `WARNING` avec détails (aucun θ faisable)

3. **Conservation du fold** :
   - Le fold est conservé dans les résultats avec `n_trades = 0`, `net_pnl = 0`
   - Pas de suppression du fold des agrégations

## Critères d'acceptation
- [x] Cas nominal : relaxation `min_trades → 0` quand aucun θ ne satisfait les deux contraintes, mais certains satisfont `mdd <= mdd_cap`
- [x] Cas extrême : `θ = +∞` quand aucun θ ne satisfait `mdd <= mdd_cap`
- [x] Warning émis (vérifiable via `logging` ou capture) à chaque étape de relaxation
- [x] Le fold est conservé dans les résultats avec `n_trades = 0` et `net_pnl = 0`
- [x] La logique de fallback ne modifie PAS le comportement quand un θ faisable existe (pas de régression)
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/032-theta-fallback` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/032-theta-fallback` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-7] #032 RED: tests fallback θ` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-7] #032 GREEN: fallback θ aucun quantile valide`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-7] #032 — Fallback θ (aucun quantile valide)`.
