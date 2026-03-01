# Tâche — Calcul de la cible y_t (label)

Statut : DONE
Ordre : 015
Workstream : WS-4
Milestone : M2
Gate lié : G-Split

## Contexte
Le pipeline est une tâche de régression : prédire un log-return futur à horizon H. Deux variantes de label sont supportées selon la config. Le label dépend de prix futurs (`O_{t+1}`, `C_{t+H}`) et ne doit jamais fuiter dans les features.

Références :
- Plan : `docs/plan/implementation.md` (WS-4.1)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§5.1, §5.2, §5.3)
- Config : `configs/default.yaml` (section `label.horizon_H_bars`, `label.target_type`)
- Code : `ai_trading/data/dataset.py` (à créer, ou module dédié `ai_trading/data/labels.py`)

Dépendances :
- Tâche 014 — Warmup et validation de causalité (doit être DONE)

## Objectif
Implémenter les deux variantes de label :
1. `log_return_trade` : `y_t = log(Close[t+H] / Open[t+1])` (label par défaut).
2. `log_return_close_to_close` : `y_t = log(Close[t+H] / Close[t])`.

Le choix est piloté par `config.label.target_type`. Les samples dont `t+1` ou `t+H` est un trou sont invalidés.

## Règles attendues
- **Config-driven** : `horizon_H_bars` et `target_type` lus depuis `config.label`.
- **Strict code** : `target_type` inconnu → `ValueError` explicite. Pas de fallback vers un type par défaut.
- **Anti-fuite** : le label `y_t` dépend de prix futurs — ces prix ne doivent jamais apparaître dans les features à t.
- **Strict code** : si `Open[t+1]` ou `Close[t+H]` est manquant (trou), le sample est masqué — pas de NaN silencieux.

## Évolutions proposées
- Créer une fonction `compute_labels(ohlcv, config, valid_mask) -> (y, label_mask)` :
  - `y` : array de shape `(N_total,)` contenant les labels (NaN pour les positions invalides).
  - `label_mask` : booléen `(N_total,)` — `True` si le label est calculable (pas de trou dans `[t+1, t+H]`).
  - Le masque final de validité des samples sera : `final_mask & label_mask`.
- Supporter les deux `target_type` via un branchement explicite.

## Critères d'acceptation
- [x] Valeurs numériques correctes pour `log_return_trade` sur données synthétiques.
- [x] Valeurs numériques correctes pour `log_return_close_to_close` sur données synthétiques.
- [x] Changement de `target_type` → valeurs différentes sur les mêmes données.
- [x] Sample invalidé si trou à `t+1` ou `t+H`.
- [x] `target_type` inconnu → `ValueError`.
- [x] `horizon_H_bars` et `target_type` lus depuis la config (pas hardcodés).
- [x] Anti-fuite (label) : masquer les prix `t > t+H` → `y_t` identique.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/015-label-target` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/015-label-target` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-4] #015 RED: tests calcul label y_t`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-4] #015 GREEN: calcul label y_t`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-4] #015 — Calcul de la cible y_t`.
