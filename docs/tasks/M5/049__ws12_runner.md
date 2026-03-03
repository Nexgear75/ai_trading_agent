# Tâche — Orchestrateur de run (runner)

Statut : TODO
Ordre : 049
Workstream : WS-12
Milestone : M5
Gate lié : M5

## Contexte
L'orchestrateur est le cœur du pipeline. Il enchaîne toutes les étapes du run de bout en bout : chargement config, seed, vérification données, features, dataset, création run_dir, boucle par fold (split → train → predict → calibrer θ → backtest → métriques), agrégation inter-fold, écriture artefacts. Il est responsable du bypass θ pour les baselines/RL et de la dérivation automatique de `strategy.framework`.

Références :
- Plan : `docs/plan/implementation.md` (WS-12.2)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§3 dataflow, §14.4, ensemble du pipeline)
- Code : `ai_trading/pipeline/runner.py`

Dépendances :
- Tous les WS précédents (WS-1 à WS-11, WS-12.1)
- Tâche 044 — Run dir (doit être DONE)
- Tâche 045 — Manifest builder (doit être DONE)
- Tâche 046 — Metrics builder (doit être DONE)
- Tâche 047 — JSON schema validation (doit être DONE)
- Tâche 048 — Seed manager (doit être DONE)

## Objectif
Implémenter le module `ai_trading/pipeline/runner.py` qui orchestre le pipeline complet :

1. Charger la config (avec overrides CLI).
2. Vérifier la cohérence des registres : `assert set(MODEL_REGISTRY) <= set(VALID_STRATEGIES)`.
3. Fixer la seed globale via seed manager.
4. Vérifier l'existence des données brutes (erreur si absentes) + exécuter QA.
5. Calculer les features.
6. Construire le dataset.
7. Créer le `run_dir` via WS-11.1.
8. Brancher le logging phase 2 (FileHandler vers `run_dir/pipeline.log`).
9. Pour chaque fold :
   - Split (train/val/test).
   - Déléguer au trainer (scale → fit → predict val → predict test → save).
   - Si `output_type == "regression"` : calibrer θ sur val. Si `output_type == "signal"` : bypass θ (forcer `method = "none"`, `theta = null`, loggé INFO).
   - Appliquer θ aux prédictions test (ou signaux directs pour `output_type == "signal"`).
   - Écrire `preds_val.csv` et `preds_test.csv` si `save_predictions = true`.
   - Backtest (avec `execution_mode` du modèle).
   - Calculer les métriques.
10. Agréger inter-fold avec vérification §14.4.
11. Écrire artefacts (manifest, metrics, config_snapshot, equity_curve stitché si `save_equity_curve = true`).
12. Valider les JSON via WS-11.4.

## Règles attendues
- Config-driven : aucun paramètre hardcodé. Toute décision est pilotée par la config.
- Strict code : erreur explicite si données brutes absentes, si registre incohérent, si un fold échoue.
- Anti-fuite : le paramètre `ohlcv` passé aux modèles et baselines est le DataFrame complet `[dataset.start, dataset.end[` (nécessaire pour SMA et RL).
- Le bypass θ pour `output_type == "signal"` est **explicitement loggé** au niveau INFO.
- La dérivation de `strategy.framework` utilise un mapping interne (`STRATEGY_FRAMEWORK_MAP`), jamais lu depuis la config YAML.
- La génération conditionnelle des artefacts respecte les flags `config.artifacts.save_*`.
- `manifest.json`, `metrics.json` et `config_snapshot.yaml` sont toujours générés (inconditionnels).

## Évolutions proposées
- Fonction `run_pipeline(config) -> Path` qui exécute le pipeline complet et retourne le chemin du `run_dir`.
- Mapping `STRATEGY_FRAMEWORK_MAP` pour la dérivation automatique de `strategy.framework`.
- Constante `VALID_STRATEGIES` listant toutes les stratégies valides.

## Critères d'acceptation
- [ ] Le module `ai_trading/pipeline/runner.py` existe et est importable.
- [ ] Run complet avec DummyModel → arborescence correcte, JSON valides, métriques non nulles.
- [ ] Run complet avec baseline no_trade → bypass θ, net_pnl=0, n_trades=0.
- [ ] Les warnings §14.4 sont émis si les seuils sont dépassés.
- [ ] Le bypass θ pour `output_type == "signal"` est loggé au niveau INFO.
- [ ] `strategy.framework` est dérivé automatiquement et correct pour chaque stratégie MVP.
- [ ] Le `config_snapshot.yaml` est toujours écrit (inconditionnel).
- [ ] La validation JSON Schema est exécutée en fin de run.
- [ ] Les artefacts conditionnels (`preds_*.csv`, `equity_curve.csv`, modèle) respectent les flags `save_*`.
- [ ] Test de causalité généralisé : modifier les prix OHLCV futurs → signaux passés identiques.
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords.
- [ ] Suite de tests verte après implémentation.
- [ ] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/049-runner` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/049-runner` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-12] #049 RED: tests orchestrateur runner`.
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-12] #049 GREEN: orchestrateur runner`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-12] #049 — Orchestrateur de run (runner)`.
