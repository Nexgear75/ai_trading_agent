# Tâche — Feature RSI avec lissage de Wilder (rsi_14)

Statut : TODO
Ordre : 010
Workstream : WS-3
Milestone : M2
Gate lié : G-Features

## Contexte
Le RSI (Relative Strength Index) est un indicateur de momentum borné [0, 100]. Le MVP utilise un RSI à 14 périodes avec le lissage exponentiel de Wilder et un epsilon pour éviter les divisions par zéro.

Références :
- Plan : `docs/plan/implementation.md` (WS-3.3)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§6.3)
- Config : `configs/default.yaml` (section `features.params.rsi_period`, `features.params.rsi_epsilon`)
- Code : `ai_trading/features/rsi.py` (à créer)

Dépendances :
- Tâche 007 — Registre de features et BaseFeature (doit être DONE)

## Objectif
Implémenter la feature `rsi_14` avec lissage de Wilder :
1. Calculer les gains (G) et pertes (L) : `G_t = max(0, C_t - C_{t-1})`, `L_t = max(0, C_{t-1} - C_t)`.
2. Initialisation SMA : `AG_n = mean(G[1..n])`, `AL_n = mean(L[1..n])`.
3. Lissage Wilder : `AG_t = ((n-1) * AG_{t-1} + G_t) / n`, idem pour AL.
4. `RS_t = AG_t / (AL_t + ε)`, `RSI_t = 100 - 100 / (1 + RS_t)`.

## Règles attendues
- **Config-driven** : `rsi_period` et `rsi_epsilon` lus depuis `config.features.params`.
- **Strict code** : les cas limites sont gérés explicitement (pas de fallback silencieux) :
  - `AL ≈ 0 et AG > 0` → RSI = 100
  - `AG ≈ 0 et AL > 0` → RSI = 0
  - `AG ≈ 0 et AL ≈ 0` → RSI = 50
- **Anti-fuite** : le RSI à t ne dépend que de données ≤ t.

## Évolutions proposées
- Créer `ai_trading/features/rsi.py` avec une classe `RSI14` décorée `@register_feature("rsi_14")`.
- `required_params = ["rsi_period", "rsi_epsilon"]`.
- `min_periods` retourne `rsi_period + 1` (n gains/pertes nécessitent n+1 clôtures).
- Implémentation vectorisée avec boucle de lissage Wilder (inévitable pour le lissage récursif).

## Critères d'acceptation
- [ ] Classe enregistrée : `rsi_14` dans `FEATURE_REGISTRY`.
- [ ] Tests numériques sur séries connues avec valeurs calculées à la main.
- [ ] Résultat ∈ [0, 100] pour toute entrée valide.
- [ ] Cas limites couverts : série monotone croissante (RSI → 100), monotone décroissante (RSI → 0), constante (RSI = 50).
- [ ] `rsi_period` et `rsi_epsilon` lus depuis params (pas hardcodés).
- [ ] NaN aux positions t < rsi_period.
- [ ] Causalité vérifiée : modifier `close[t > T]` ne modifie pas `rsi_14[t <= T]`.
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords.
- [ ] Suite de tests verte après implémentation.
- [ ] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/010-rsi` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/010-rsi` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-3] #010 RED: tests RSI Wilder`.
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-3] #010 GREEN: RSI Wilder`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-3] #010 — Feature RSI avec lissage de Wilder`.
