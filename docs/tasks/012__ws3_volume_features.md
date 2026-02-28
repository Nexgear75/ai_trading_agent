# Tâche — Features de volume (logvol, dlogvol)

Statut : TODO
Ordre : 012
Workstream : WS-3
Milestone : M2
Gate lié : G-Features

## Contexte
Les features de volume capturent l'activité de trading. Le log-volume lisse les valeurs extrêmes et le différentiel de log-volume détecte les changements brusques d'activité.

Références :
- Plan : `docs/plan/implementation.md` (WS-3.5)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§6.2)
- Config : `configs/default.yaml` (section `features.params.logvol_epsilon`)
- Code : `ai_trading/features/volume.py` (à créer)

Dépendances :
- Tâche 007 — Registre de features et BaseFeature (doit être DONE)

## Objectif
Implémenter les deux features de volume :
1. `logvol(t) = log(V_t + ε)` avec `ε = 1e-8`.
2. `dlogvol(t) = logvol(t) - logvol(t-1)`.

## Règles attendues
- **Config-driven** : `logvol_epsilon` lu depuis `config.features.params`.
- **Strict code** : NaN explicite pour `dlogvol` à t=0 (pas de remplissage).
- **Anti-fuite** : chaque feature à t ne dépend que de données ≤ t.

## Évolutions proposées
- Créer `ai_trading/features/volume.py` avec 2 classes : `LogVolume` et `DLogVolume`.
- `LogVolume` décorée `@register_feature("logvol")`, `required_params = ["logvol_epsilon"]`.
- `DLogVolume` décorée `@register_feature("dlogvol")`, `required_params = ["logvol_epsilon"]`.
- `logvol.min_periods` retourne 1 (disponible dès la première bougie).
- `dlogvol.min_periods` retourne 2 (nécessite deux bougies).
- `DLogVolume.compute()` calcule `logvol` en interne puis différencie (indépendance du registre).

## Critères d'acceptation
- [ ] 2 classes enregistrées : `logvol`, `dlogvol` dans `FEATURE_REGISTRY`.
- [ ] Volume nul → `logvol ≈ log(ε)` ≈ -18.42 (avec ε=1e-8).
- [ ] `dlogvol` NaN à t=0.
- [ ] `logvol_epsilon` lu depuis params (pas hardcodé).
- [ ] Causalité vérifiée : modifier `volume[t > T]` ne modifie pas les features `[t <= T]`.
- [ ] Tests numériques avec valeurs calculées à la main.
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords.
- [ ] Suite de tests verte après implémentation.
- [ ] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/012-volume-features` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/012-volume-features` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-3] #012 RED: tests features volume`.
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-3] #012 GREEN: features volume`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-3] #012 — Features de volume`.
