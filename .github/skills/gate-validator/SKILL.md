---
name: gate-validator
description: Valide les gates du plan AI Trading Pipeline (M1..M5, G-Features, G-Split, G-Backtest, G-Doc, G-Leak, G-Perf) en vérifiant artefacts, tests, reproductibilité et conformité spec. À utiliser pour auditer un gate avant revue de milestone.
argument-hint: "[gate: M1|M2|M3|M4|M5|G-Features|G-Split|G-Backtest|G-Doc|G-Perf|all] [mode: check|report]"
---

# Agent Skill — Gate Validator (AI Trading Pipeline)

## Objectif
Auditer un ou plusieurs gates du plan d'implémentation AI Trading Pipeline et produire un verdict structuré (GO / NO-GO / GO AVEC RÉSERVES) avec preuves.

## Contexte repo

- **Plan (source des gates)** : `docs/plan/implementation.md`
- **Spécification** : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md`
- **Tâches** : `docs/tasks/`
- **Code source** : `ai_trading/`
- **Tests** : `tests/`
- **Configs** : `configs/default.yaml`
- **Artefacts attendus** : `runs/`

## Rôle de l'agent

Tu dois :
- vérifier que les preuves concrètes (artefacts, tests, configs, logs) existent dans le repo ;
- confronter chaque critère du gate aux fichiers réellement présents ;
- produire un rapport de conformité factuel (pas d'hypothèses) ;
- ne jamais déclarer un gate GO sans preuve vérifiable.

## Registre des gates

### Gates intra-milestone

#### G-Features — Features causales et complètes (après WS-3.7, avant WS-4.1)

| # | Critère | Seuil | Preuve attendue |
|---|---|---|---|
| F.1 | Features enregistrées dans `FEATURE_REGISTRY` | 9 features | `from ai_trading.features import FEATURE_REGISTRY; assert len(FEATURE_REGISTRY) == 9` |
| F.2 | NaN hors zone warmup | 0 NaN | Test sur dataset synthétique >= 500 bougies |
| F.3 | Audit de causalité | Modifier prix `t > T` → features identiques `t <= T` (atol=0) | Test de perturbation dans `tests/test_features.py` |
| F.4 | `feature_version` tracée | Tracée pour chaque feature | Vérification dans config/code |
| F.5 | Couverture tests WS-3.* | >= 90% | `pytest --cov=ai_trading.features --cov-fail-under=90` |

#### G-Split — Splits causaux et disjoints (après WS-4.6, avant WS-5.1)

| # | Critère | Seuil | Preuve attendue |
|---|---|---|---|
| S.1 | Disjonction temporelle train/val/test par fold | 100% | Test vérifiant aucun timestamp partagé |
| S.2 | Purge E2E | `max(t + H × Δ for t in train_val) < test_start` par fold | Test dans `tests/test_splitter.py` |
| S.3 | Folds valides après troncation | >= 1 | Test avec données suffisantes |
| S.4 | Reproductibilité X_seq | Bit-à-bit (atol=1e-7) | Test de reproductibilité |
| S.5 | NaN dans X_seq et y | 0% | Assertion dans tests |
| S.6 | Anti-fuite scaler | `set(indices_train) ∩ set(indices_val ∪ indices_test) == ∅` | Test dans `tests/test_scaler.py` |

#### G-Backtest — Moteur déterministe et correct (après WS-8.4, avant WS-9.1)

| # | Critère | Seuil | Preuve attendue |
|---|---|---|---|
| B.1 | Déterminisme | 2 runs → `trades.csv` SHA-256 identiques, equity atol=1e-10 | Test dans `tests/test_backtest.py` |
| B.2 | Cohérence equity-trades | `E_final == E_0 * Π(1 + w * r_net_i)` (atol=1e-8) | Test numérique |
| B.3 | Mode one_at_a_time | Aucun trade chevauché (signaux denses) | Test avec signaux Go consécutifs |
| B.4 | Modèle de coûts | Résultat identique au calcul main sur >= 3 cas | Tests numériques |
| B.5 | `trades.csv` parseable | Colonnes conformes | Test de parsing |
| B.6 | Anti-fuite backtest | Signaux à t indépendants des prix t' > t | Test de perturbation |

#### G-Doc — Contrat plug-in complet (après WS-7.4, avant gate M3)

| # | Critère | Seuil | Preuve attendue |
|---|---|---|---|
| D.1 | `output_type` déclaré et correct | >= 4 stratégies | Test : DummyModel → "regression", NoTrade → "signal", etc. |
| D.2 | `execution_mode` correct | Default "standard", BuyHold → "single_trade" | Test d'attributs |
| D.3 | Cohérence registres | `set(VALID_STRATEGIES) == set(MODEL_REGISTRY)` | Assertion dans test |
| D.4 | Docstrings conformes | Contrat BaseModel documenté | Inspection |
| D.5 | Bypass θ fonctionnel | `output_type == "signal"` → skip calibration | Test sur données synthétiques |
| D.6 | Anti-fuite calibration | θ indépendant de y_hat_test | Test de perturbation |

### Gates de milestone

#### M1 — Configuration et données sources

| # | Critère | Seuil | Preuve attendue |
|---|---|---|---|
| M1.1 | Validation config | 0 erreur | Log chargement config, tests `test_config.py` |
| M1.2 | QA données | 0 erreur bloquante | Rapport QA, tests `test_qa.py` |
| M1.3 | Couverture tests WS-1/WS-2 | >= 95% | `pytest --cov=ai_trading.config --cov=ai_trading.data --cov-fail-under=95` |
| M1.4 | Hash SHA-256 données | Tracé | Hash dans manifest ou logs |

#### M2 — Pipeline data/feature causale

| # | Critère | Seuil | Preuve attendue |
|---|---|---|---|
| M2.1 | G-Features GO | Tous critères F.1-F.5 | Rapport G-Features |
| M2.2 | G-Split GO | Tous critères S.1-S.6 | Rapport G-Split |
| M2.3 | Reproductibilité X_seq | Bit-à-bit (atol=1e-7) même seed | Test de reproductibilité |
| M2.4 | NaN hors warmup | 0% | Tests d'assertion |

#### M3 — Framework d'entraînement

| # | Critère | Seuil | Preuve attendue |
|---|---|---|---|
| M3.1 | G-Doc GO | Tous critères D.1-D.6 | Rapport G-Doc |
| M3.2 | fit/predict OK | >= 3 stratégies (dummy + 2 baselines) | Tests `test_trainer.py` |
| M3.3 | Calibration θ exécutable | 100% des folds valides avec DummyModel | Test de calibration |
| M3.4 | Bypass θ | Fonctionnel pour `output_type == "signal"` | Test de bypass |
| M3.5 | Stabilité multi-seeds | 0 crash sur seeds 42, 43, 44 | Tests multi-seed |

#### M4 — Evaluation trading

| # | Critère | Seuil | Preuve attendue |
|---|---|---|---|
| M4.1 | G-Backtest GO | Tous critères B.1-B.6 | Rapport G-Backtest |
| M4.2 | Déterminisme backtest | Delta Sharpe <= 0.02, Delta MDD <= 0.5pp | Test 2 runs même seed |
| M4.3 | Pipeline sans crash | DummyModel + 3 baselines | Tests d'intégration |
| M4.4 | Métriques cohérentes | no_trade → pnl=0, buy_hold → n_trades=1 | Tests `test_baselines.py` |
| M4.5 | Couverture WS-8/WS-9/WS-10 | >= 95% | pytest --cov-fail-under=95 |

#### M5 — Readiness de livraison

| # | Critère | Seuil | Preuve attendue |
|---|---|---|---|
| M5.1 | Reproductibilité e2e | >= 95% champs numériques dans tolérance <= 1% | Test cross-run même seed |
| M5.2 | Conformité artefacts | 100% JSON Schema validation | `jsonschema.validate()` sur manifest + metrics |
| M5.3 | Exécution complète | `make run-all` + CI verte | CI logs, output de make |

### Gate transversal

#### G-Leak — Anti-fuite continue

Vérifié implicitement dans chaque gate. Points de contrôle :
- Features : test perturbation prix futurs → features identiques
- Labels : `y_t` n'utilise que `Open[t+1]` et `Close[t+H]`
- Splits : aucun timestamp test dans train/val
- Scaling : scaler.fit() sur train uniquement
- Calibration : θ calibré sur val, jamais sur test
- Backtest : signaux à t indépendants des prix futurs
- SMA : backward-looking uniquement

#### G-Perf — Performance (post-MVP, non bloquant)

| # | Critère | Seuil | Priorité |
|---|---|---|---|
| P.1 | Pipeline complet | <= 120s (CPU, 2000 bougies, 3 folds) | Post-MVP |
| P.2 | Feature pipeline | <= 5s (2000 bougies, 9 features) | Post-MVP |
| P.3 | Pic mémoire | <= 2 GB | Post-MVP |
| P.4 | Scalabilité | Doubler N → temps <= 2.5x | Post-MVP |

## Workflow de validation

1. **Identifier le gate demandé** (ou `all` pour audit complet).
2. **Vérifier les prérequis** : gates intra-milestone avant gate de milestone.
3. **Parcourir le registre** : pour chaque critère, vérifier preuve.
4. **Exécuter les tests** (mode `check`) ou vérifier présence fichiers (mode `report`).
5. **Vérifier G-Leak** : l'anti-fuite est implicite dans chaque gate.
6. **Produire le verdict** par critère.

## Format du rapport de sortie

```markdown
# Rapport de validation — Gate [ID]

Date : [YYYY-MM-DD]
Milestone : [M1..M5]
Verdict global : [GO | NO-GO | GO AVEC RÉSERVES]

## Détail par critère

| # | Critère | Verdict | Preuve / Remarque |
|---|---|---|---|
| X.1 | … | GO | `chemin/vers/preuve` |
| X.2 | … | NO-GO | Absent : [ce qui manque] |

## Vérification anti-fuite (G-Leak)
| Étape | Statut | Commentaire |
|---|---|---|
| Features | ✅/❌ | |
| Splits | ✅/❌ | |
| Scaling | ✅/❌ | |

## Actions requises (si NO-GO)
1. [Action corrective 1]
2. [Action corrective 2]
```

## Ordre d'exécution des gates

```
M1 → G-Features → G-Split → M2 → G-Doc → M3 → G-Backtest → M4 → M5
```

Les gates intra-milestone sont bloquants pour les WS en aval. Le gate de milestone ne peut être GO que si tous ses gates intra-milestone sont GO.

## Principes

- **Factuel** : ne pas inférer de conformité sans preuve tangible.
- **Traçable** : chaque verdict cite le chemin du fichier ou le nom du test.
- **Incrémental** : un gate peut être audité plusieurs fois ; seul le dernier rapport fait foi.
- **Anti-fuite intégré** : G-Leak est vérifié dans chaque gate, pas séparément.

## Limites
- Ce skill ne crée pas les artefacts manquants ; il se limite à diagnostiquer.
- Pour créer les tâches de remédiation, utiliser le skill `task-creator`.
