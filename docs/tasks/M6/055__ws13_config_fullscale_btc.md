# Tâche — Configuration full-scale BTCUSDT

Statut : DONE
Ordre : 055
Workstream : WS-13
Milestone : M6
Gate lié : M6

## Contexte
Le pipeline doit être validé sur données réelles BTCUSDT en conditions grandeur nature. La première étape est de créer un fichier de configuration dédié `configs/fullscale_btc.yaml` qui cible la période complète du listing BTC sur Binance (2017-08-17 → 2026-01-01) avec la stratégie `dummy` pour valider le pipeline sans dépendance à un modèle ML/DL.

Références :
- Plan : `docs/plan/implementation.md` (WS-13.1)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§3, §4.1)
- Code : `ai_trading/config.py`

Dépendances :
- Tâche 002 — Config loader (doit être DONE)
- Tâche 003 — Config validation (doit être DONE)

## Objectif
Créer le fichier `configs/fullscale_btc.yaml` — configuration dédiée au test grandeur nature BTCUSDT. Ce fichier est versionné et ne doit **pas** être généré dynamiquement par les tests.

## Règles attendues
- Config-driven : le fichier doit être un YAML autonome parsable par le config loader existant (WS-1.2).
- Strict code : la validation stricte (WS-1.3) doit passer sans erreur sur ce fichier.
- Le fichier est une réplique de `configs/default.yaml` avec uniquement les paramètres ajustés pour un run réaliste complet.

## Évolutions proposées
- Créer `configs/fullscale_btc.yaml` avec les paramètres suivants modifiés par rapport à `default.yaml` :
  - `dataset.start` : `"2017-08-17"` (début du listing BTC sur Binance)
  - `dataset.end` : `"2026-01-01"`
  - `strategy.strategy_type` : `"model"`
  - `strategy.name` : `"dummy"` (validation pipeline sans modèle ML)
  - `window.L` : `128`
  - `window.min_warmup` : `200`
  - `splits.train_days` : `180`
  - `splits.test_days` : `30`
  - `splits.step_days` : `30`
  - Tous les autres paramètres (features, scaling, coûts, backtest, thresholding) identiques à `default.yaml`.
- Écrire un test vérifiant que le config loader parse `configs/fullscale_btc.yaml` sans erreur.

## Critères d'acceptation
- [x] `configs/fullscale_btc.yaml` existe et est versionné.
- [x] Le config loader parse le fichier sans erreur (`PipelineConfig.from_yaml("configs/fullscale_btc.yaml")`).
- [x] La validation stricte (WS-1.3) passe sans erreur sur ce fichier.
- [x] `dataset.start == "2017-08-17"` et `dataset.end == "2026-01-01"`.
- [x] `strategy.name == "dummy"`.
- [x] Les paramètres features, scaling, coûts, backtest et thresholding sont identiques à `default.yaml`.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/055-config-fullscale-btc` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/055-config-fullscale-btc` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-13] #055 RED: tests config fullscale_btc.yaml`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-13] #055 GREEN: config fullscale_btc.yaml`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-13] #055 — Configuration full-scale BTCUSDT`.
