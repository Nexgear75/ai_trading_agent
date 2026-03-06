# PR Review — [WS-6] #028 Fold Trainer (orchestration fit/predict par fold)

**Branche** : `task/028-fold-trainer`
**Date** : 2 mars 2026
**Itération** : v1
**Verdict** : CLEAN

## Grille d'audit

### Structure branche & commits
- [x] Branche `task/028-fold-trainer` depuis `Max6000i1`.
- [x] Commit RED : `[WS-6] #028 RED: tests fold trainer scale/fit/predict/save` (tests uniquement).
- [x] Commit GREEN : `[WS-6] #028 GREEN: fold trainer orchestration scale/fit/predict/save` (implémentation + tâche).
- [ ] Pas de commits parasites entre RED et GREEN.

> **Note** : Un commit `873ec0b amélioration skill` modifiant `.github/skills/implementing-task/SKILL.md` est présent sur la branche, mais **avant** le commit RED, pas entre RED et GREEN. Impact nul sur le code de la tâche.

### Tâche associée
- [x] `docs/tasks/M3/028__ws6_fold_trainer.md` : statut DONE.
- [x] Critères d'acceptation cochés `[x]` (11/11).
- [ ] Checklist cochée `[x]`.

> **Note** : Les 2 derniers items de la checklist (commit GREEN, PR ouverte) ne sont pas cochés. Mineur — ces items sont post-implémentation et la PR vient d'être créée.

### Tests
- [x] Convention de nommage (`test_fold_trainer.py`).
- [x] Couverture des critères d'acceptation (11/11 couverts par 21 tests).
- [x] Cas nominaux + erreurs + bords.
- [x] `pytest` GREEN, 0 échec (789 passed).
- [x] `ruff check ai_trading/ tests/` clean.
- [x] Données synthétiques (pas réseau).
- [x] Tests déterministes (seeds fixées : `default_rng(42)`, `default_rng(99)`, `default_rng(55)`).

### Strict code (no fallbacks)
- [x] Aucun `or default`, `value if value else default`.
- [x] Aucun `except` trop large.
- [x] Validation explicite + `raise` : erreurs propagées directement (tests `test_model_fit_error_propagates`, `test_scaler_error_propagates`).

### Config-driven
- [x] Paramètres dans `configs/default.yaml`, pas hardcodés.
- [x] `create_scaler(self._config.scaling)` — méthode de scaling lue depuis config.
- [x] `early_stopping_patience` lu depuis `config.training.early_stopping_patience` et transmis via l'objet config.

### Anti-fuite (look-ahead)
- [x] Scaler fit sur train uniquement (`scaler.fit(X_train)`).
- [x] Test mock vérifiant `fit()` appelé une seule fois avec `X_train` uniquement.
- [x] Test perturbation anti-fuite : `X_test` modifié → `y_hat_val` inchangé.
- [x] `transform()` appliqué aux 3 splits (train, val, test) — vérifié par mock.

### Reproductibilité
- [x] Seeds fixées et tracées dans les tests.
- [N/A] Hashes SHA-256 (pas applicable pour ce module).

### Float conventions
- [x] Float32 pour X_train, y_train, X_val, y_val, X_test (fixtures `astype(np.float32)`).
- [x] `y_hat_val` et `y_hat_test` vérifiés `dtype == np.float32`.

### Qualité
- [x] snake_case.
- [x] Pas de `print()`, code mort, `TODO` orphelin.
- [x] Imports propres (grep clean).
- [x] DRY : pas de duplication de logique.

## Cohérence inter-modules

| Interface | Conformité | Détail |
|---|---|---|
| `BaseModel.fit()` signature | ✅ | 9 kwargs identiques (X_train, y_train, X_val, y_val, config, run_dir, meta_train, meta_val, ohlcv) |
| `BaseModel.predict(X=...)` | ✅ | Appel par keyword, signature compatible |
| `BaseModel.save(path)` | ✅ | `model.save(run_dir / "model")` conforme |
| `create_scaler(ScalingConfig)` | ✅ | `create_scaler(self._config.scaling)` — type correct |
| Retour structuré | ✅ | `{y_hat_val, y_hat_test, artifacts, scaler}` conforme à la tâche |

## Analyse détaillée du code

### `ai_trading/training/trainer.py` (117 lignes)

Code minimal et focalisé. Responsabilité unique : orchestration scale → fit → predict → save. Aucune logique métier dans le trainer.

**Points positifs** :
- Séparation des responsabilités claire — le trainer ne contient pas de boucle epoch.
- Pas de CSV export (correctement délégué à l'orchestrateur WS-12.2).
- Pas de fallback, pas d'exception catching — erreurs propagées proprement.
- Docstrings complètes avec types et shapes.

### `tests/test_fold_trainer.py` (682 lignes)

21 tests organisés en 6 classes thématiques :
- `TestFoldTrainerNominal` (6 tests) : workflow complet, shapes, save, scaler retourné
- `TestFoldTrainerScaling` (3 tests) : anti-fuite fit train only, transform 3 splits, perturbation
- `TestFoldTrainerModelFit` (3 tests) : données scalées, meta/ohlcv, config/run_dir
- `TestFoldTrainerPatience` (2 tests) : config-driven patience
- `TestFoldTrainerPredict` (2 tests) : predict reçoit données scalées val et test
- `TestFoldTrainerEdgeCases` (5 tests) : single sample, artifacts, erreur model, erreur scaler, n_features différent

**Couverture qualitativement bonne** : nominaux, erreurs, bords, anti-fuite.

### `pyproject.toml`

Ajout `N803`/`N806` pour trainer.py et test_fold_trainer.py — justifié par les variables numpy en majuscules (`X_train`, `X_val`, etc.), cohérent avec les ignores existants sur base.py et dummy.py.

## Remarques

1. [MINEUR] Le commit `873ec0b` (amélioration skill) est présent sur la branche mais ne devrait pas l'être. Il ne fait pas partie de la tâche #028. Idéalement, il aurait dû être commité sur `Max6000i1` directement ou sur une branche séparée.
   - Fichier : `.github/skills/implementing-task/SKILL.md`
   - Suggestion : Rebase interactif pour retirer ce commit de la branche, ou l'accepter tel quel puisqu'il n'affecte aucun code fonctionnel.

2. [MINEUR] Checklist de fin de tâche (`028__ws6_fold_trainer.md`) : les 2 derniers items ne sont pas cochés.
   - Fichier : `docs/tasks/M3/028__ws6_fold_trainer.md`
   - Lignes : 89-90
   - Suggestion : Cocher après merge de la PR.

## Résumé

Implémentation propre et minimale du fold trainer. Le code respecte strictement les principes anti-fuite (scaler fit train only), strict code (pas de fallback), et config-driven. Les 21 tests couvrent exhaustivement les critères d'acceptation avec cas nominaux, erreurs et bords. Aucun bloquant identifié.
