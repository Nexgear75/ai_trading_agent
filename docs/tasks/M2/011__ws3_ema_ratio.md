# Tâche — Feature EMA ratio (ema_ratio_12_26)

Statut : DONE
Ordre : 011
Workstream : WS-3
Milestone : M2
Gate lié : G-Features

## Contexte
L'EMA ratio mesure la divergence relative entre une EMA rapide (12 périodes) et une EMA lente (26 périodes) des clôtures. C'est un indicateur de tendance.

Références :
- Plan : `docs/plan/implementation.md` (WS-3.4)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§6.4)
- Config : `configs/default.yaml` (section `features.params.ema_fast`, `features.params.ema_slow`)
- Code : `ai_trading/features/ema.py` (à créer)

Dépendances :
- Tâche 007 — Registre de features et BaseFeature (doit être DONE)

## Objectif
Implémenter la feature `ema_ratio_12_26` :
1. `EMA_n(t) = α_n * C_t + (1 - α_n) * EMA_n(t-1)` avec `α_n = 2 / (n + 1)`.
2. Initialisation : `EMA_n(n-1) = SMA(C[0..n-1])` (moyenne simple des n premières clôtures).
3. Feature : `ema_ratio_12_26(t) = EMA_12(t) / EMA_26(t) - 1`.

## Règles attendues
- **Config-driven** : `ema_fast` et `ema_slow` lus depuis `config.features.params`.
- **Strict code** : pas de fallback si les paramètres sont absents. Erreur explicite.
- **Anti-fuite** : l'EMA à t ne dépend que de données ≤ t.
- **Propriété de convergence** : sur une série constante, `EMA_fast = EMA_slow = constante` → ratio = 0.

## Évolutions proposées
- Créer `ai_trading/features/ema.py` avec une classe `EmaRatio1226` décorée `@register_feature("ema_ratio_12_26")`.
- `required_params = ["ema_fast", "ema_slow"]`.
- `min_periods` retourne `ema_slow - 1` (25) car l'EMA lente produit sa première valeur à l'index `ema_slow - 1`.
- L'EMA est calculée via `pd.Series.ewm(span=n, adjust=False)` ou implémentation manuelle avec initialisation SMA.

## Critères d'acceptation
- [x] Classe enregistrée : `ema_ratio_12_26` dans `FEATURE_REGISTRY`.
- [x] Tests numériques avec valeurs calculées à la main.
- [x] Convergence vérifiée : série constante → ratio = 0 (tolérance `atol=1e-10`).
- [x] `ema_fast` et `ema_slow` lus depuis params (pas hardcodés).
- [x] NaN aux positions t < ema_slow - 1 (premier non-NaN à l'index `ema_slow - 1`).
- [x] Causalité vérifiée : modifier `close[t > T]` ne modifie pas `ema_ratio[t <= T]`.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/011-ema-ratio` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/011-ema-ratio` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-3] #011 RED: tests EMA ratio`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-3] #011 GREEN: EMA ratio`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-3] #011 — Feature EMA ratio`.
