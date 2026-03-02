# Tâche — Bypass calibration θ pour RL et baselines

Statut : TODO
Ordre : 033
Workstream : WS-7
Milestone : M3
Gate lié : G-Doc

## Contexte
Les modèles qui déclarent `output_type == "signal"` (RL-PPO, baselines no-trade, buy & hold, SMA) produisent directement des signaux binaires Go/No-Go. Ils ne passent pas par la calibration θ. Le pipeline doit détecter automatiquement `output_type` et court-circuiter la calibration, sans branchement sur `strategy.name`.

Références :
- Plan : `docs/plan/implementation.md` (WS-7.4)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§11.4, §11.5)
- Code : `ai_trading/calibration/threshold.py` (extension du module existant)

Dépendances :
- Tâche 031 — WS-7 theta optimization (doit être DONE) — le bypass s'intègre dans le flux de calibration
- Tâche 024 — WS-6 BaseModel ABC (doit être DONE) — pour `output_type`

## Objectif
Implémenter la logique de bypass de la calibration θ quand `model.output_type == "signal"`, retournant les métadonnées appropriées (`method = "none"`, `theta = null`).

## Règles attendues
- **Pattern plug-in** : le bypass est basé sur `model.output_type`, jamais sur `strategy.name` (pas de branchement conditionnel sur le nom du modèle).
- **Strict code** : pour `output_type == "signal"`, les prédictions binaires (0/1) sont utilisées directement comme signaux, sans transformation.
- **Conformité spec** : §11.5 pour RL (`theta = null`, métriques prédiction = null), §11.4 pour baselines.

## Évolutions proposées

### 1. Logique de bypass dans le flux de calibration
- Si `model.output_type == "regression"` : exécuter la calibration complète (WS-7.1 → WS-7.2 → WS-7.3)
- Si `model.output_type == "signal"` : bypass total
  - Pas de calcul de quantiles
  - Pas de backtest de calibration
  - Les prédictions `y_hat` sont déjà des signaux binaires (0/1) → utilisées directement

### 2. Retour structuré pour le cas bypass
- `method = "none"`
- `theta = None` (null en JSON)
- `quantile = None`
- Pas de métriques de calibration

### 3. Cas spécifiques
- **RL (PPO)** : `output_type == "signal"`, actions binaires directes, `threshold.method = "none"`, `theta = null`
- **Baselines** (no-trade, buy & hold, SMA) : `output_type == "signal"`, signaux directs, pas de θ
- **SMA exception** : la SMA est explicitement paramétrée via `config.baselines.sma`, mais ne passe PAS par la calibration θ

## Critères d'acceptation
- [ ] `output_type == "signal"` → calibration θ totalement bypassée (pas de quantiles, pas de backtest calibration)
- [ ] `output_type == "regression"` → calibration normale (pas de régression)
- [ ] Retour de calibration pour bypass : `method = "none"`, `theta = None`
- [ ] Les signaux binaires (0/1) sont passés directement au backtest sans transformation
- [ ] Aucun branchement sur `strategy.name` — uniquement sur `output_type`
- [ ] Test avec un modèle factice `output_type = "signal"` : calibration bypassée, signaux utilisés directement
- [ ] Test avec DummyModel (`output_type = "regression"`) : calibration normale exécutée
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords
- [ ] Suite de tests verte après implémentation
- [ ] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/033-theta-bypass` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/033-theta-bypass` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-7] #033 RED: tests bypass calibration θ pour signal models` (fichiers de tests uniquement).
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-7] #033 GREEN: bypass calibration θ pour RL et baselines`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-7] #033 — Bypass calibration θ pour RL et baselines`.
