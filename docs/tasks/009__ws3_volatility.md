# Tâche — Features de volatilité rolling (vol_24, vol_72)

Statut : TODO
Ordre : 009
Workstream : WS-3
Milestone : M2
Gate lié : G-Features

## Contexte
Les features de volatilité mesurent la dispersion des log-returns récents. Elles sont calculées comme l'écart-type population (ddof=0) des log-returns sur une fenêtre glissante causale.

Références :
- Plan : `docs/plan/implementation.md` (WS-3.2)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§6.5)
- Config : `configs/default.yaml` (section `features.params.vol_windows`, `features.params.volatility_ddof`)
- Code : `ai_trading/features/volatility.py` (à créer)

Dépendances :
- Tâche 007 — Registre de features et BaseFeature (doit être DONE)

## Objectif
Implémenter les deux features de volatilité :
- `vol_24(t) = std(logret_1(t-i), i ∈ [0, 23], ddof=0)` — fenêtre des 24 derniers log-returns `[t-23, t]`
- `vol_72(t) = std(logret_1(t-i), i ∈ [0, 71], ddof=0)` — fenêtre des 72 derniers log-returns `[t-71, t]`

## Règles attendues
- **Anti-fuite** : fenêtre strictement backward-looking, aucune donnée future.
- **Config-driven** : les fenêtres `vol_windows` et `volatility_ddof` sont lues depuis `config.features.params`.
- **Indépendance** : le module recalcule `logret_1 = log(C_t / C_{t-1})` en interne à partir des clôtures brutes, sans dépendre de la feature `logret_1` (choix architectural plan WS-3.6, point 2).
- **Strict code** : NaN aux positions où la fenêtre n'est pas complète (t < n). Pas de remplissage.

## Évolutions proposées
- Créer `ai_trading/features/volatility.py` avec 2 classes : `Volatility24`, `Volatility72`.
- Chaque classe hérite de `BaseFeature` et est décorée `@register_feature("vol_24")` / `@register_feature("vol_72")`.
- `required_params = ["vol_windows", "volatility_ddof"]`.
- `compute(ohlcv, params)` calcule `log(close / close.shift(1))` en interne puis applique `rolling(n).std(ddof=ddof)`.
- `min_periods` retourne n (24 ou 72) pour indiquer le warmup nécessaire.
- Un helper interne `_compute_logret_1(close)` peut être extrait dans `features/_helpers.py` si nécessaire.

## Critères d'acceptation
- [ ] 2 classes enregistrées : `vol_24`, `vol_72` dans `FEATURE_REGISTRY`.
- [ ] Résultat numérique identique à `np.std(..., ddof=0)` sur la fenêtre correspondante.
- [ ] Convention `ddof=0` (écart-type population) lue depuis la config.
- [ ] NaN aux positions t < n.
- [ ] Les fenêtres sont lues depuis `config.features.params.vol_windows` (pas hardcodées).
- [ ] Causalité vérifiée : modifier `close[t > T]` ne modifie pas `vol_n[t <= T]`.
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords.
- [ ] Suite de tests verte après implémentation.
- [ ] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/009-volatility` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/009-volatility` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-3] #009 RED: tests volatilité rolling`.
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-3] #009 GREEN: volatilité rolling`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-3] #009 — Features de volatilité rolling`.
