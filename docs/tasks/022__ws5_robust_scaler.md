# Tâche — Robust scaler (option)

Statut : DONE
Ordre : 022
Workstream : WS-5
Milestone : M2
Gate lié : G-Split

## Contexte
Le robust scaler est une alternative au standard scaler, plus résistante aux outliers. Il centre par la médiane et met à l'échelle par l'IQR, avec clipping/winsorization aux quantiles configurés. Activé par `config.scaling.method = robust`.

Références :
- Plan : `docs/plan/implementation.md` (WS-5.2)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§9.2)
- Config : `configs/default.yaml` (section `scaling.method`, `scaling.robust_quantile_low`, `scaling.robust_quantile_high`, `scaling.epsilon`)
- Code : `ai_trading/data/scaler.py` (à étendre)

Dépendances :
- Tâche 021 — Standard scaler (doit être DONE)

## Objectif
Implémenter le robust scaler avec la même interface que le standard scaler :
1. `fit(X_train)` : estimer médiane et IQR par feature j (reshape `(N, L, F)` → `(N*L, F)`). Calculer les quantiles de clipping.
2. `transform(X)` : centrer par médiane, diviser par `(IQR + ε)`, clipper aux quantiles.
3. Fit uniquement sur train.

## Règles attendues
- **Anti-fuite** : `fit()` uniquement sur X_train (même règle que standard scaler).
- **Config-driven** : `robust_quantile_low`, `robust_quantile_high`, `epsilon` lus depuis la config.
- **Strict code** : NaN dans X_train → `ValueError`.
- **Même interface** que le standard scaler (interchangeable dans le pipeline).

## Évolutions proposées
- Ajouter `RobustScaler` dans `ai_trading/data/scaler.py`, même interface que `StandardScaler`.
- `fit()` calcule médiane, Q1 (quantile_low), Q3 (quantile_high), IQR = Q3 - Q1 par feature.
- `transform()` : `(x - median) / (IQR + ε)`, puis clipping aux bornes `[quantile_low_value, quantile_high_value]`.
- `save()`/`load()` : sérialisation des paramètres (median, IQR, quantiles).
- Factory ou sélection par config : `create_scaler(config) -> StandardScaler | RobustScaler`.

## Critères d'acceptation
- [x] Stats estimées uniquement sur X_train (test non vu).
- [x] Outliers extrêmes clippés aux quantiles configurés.
- [x] `robust_quantile_low` et `robust_quantile_high` lus depuis la config.
- [x] NaN dans X_train → `ValueError`.
- [x] Même interface que `StandardScaler` : `fit()`, `transform()`, `fit_transform()`, `save()`, `load()`.
- [x] Factory `create_scaler(config)` retourne le bon scaler selon `config.scaling.method`.
- [x] `scaling.method` inconnu → `ValueError`.
- [x] Paramètres sérialisables (save/load).
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/022-robust-scaler` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/022-robust-scaler` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-5] #022 RED: tests robust scaler`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-5] #022 GREEN: robust scaler`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-5] #022 — Robust scaler`.
