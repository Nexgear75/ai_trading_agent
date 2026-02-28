# Tâche — Feature pipeline (assemblage et orchestration)

Statut : TODO
Ordre : 013
Workstream : WS-3
Milestone : M2
Gate lié : G-Features

## Contexte
Les 9 features individuelles (tâches 008–012) sont implémentées et enregistrées dans le registre. Il faut maintenant créer le pipeline d'assemblage qui itère sur `config.features.feature_list`, résout chaque feature dans le registre, et assemble le DataFrame résultat. L'auto-registration via `features/__init__.py` doit peupler le registre au chargement du package.

Références :
- Plan : `docs/plan/implementation.md` (WS-3.6, détails d'architecture points 3–5)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§6.2, Annexe E.1)
- Config : `configs/default.yaml` (section `features.feature_list`, `features.params`)
- Code : `ai_trading/features/pipeline.py` (à créer), `ai_trading/features/__init__.py` (à modifier)

Dépendances :
- Tâche 008 — Features log-returns (doit être DONE)
- Tâche 009 — Features de volatilité (doit être DONE)
- Tâche 010 — Feature RSI (doit être DONE)
- Tâche 011 — Feature EMA ratio (doit être DONE)
- Tâche 012 — Features de volume (doit être DONE)

## Objectif
1. Créer `ai_trading/features/pipeline.py` avec `compute_features(ohlcv, config) -> pd.DataFrame`.
2. Modifier `ai_trading/features/__init__.py` pour importer explicitement tous les modules feature (auto-registration).
3. Le pipeline itère sur `config.features.feature_list`, résout dans `FEATURE_REGISTRY`, valide les `required_params`, appelle `compute()`, et assemble le résultat.

## Règles attendues
- **Strict code** : erreur explicite (`ValueError`) si une feature demandée n'est pas enregistrée.
- **Strict code** : erreur explicite si un `required_params` d'une feature est absent de `config.features.params`.
- **Config-driven** : la liste des features et leurs paramètres viennent de la config.
- **Traçabilité** : `feature_version` est lu depuis `config.features.feature_version`.

## Évolutions proposées
- Créer `ai_trading/features/pipeline.py` :
  - `compute_features(ohlcv: pd.DataFrame, config) -> pd.DataFrame` : itère sur `feature_list`, résout dans le registre, valide `required_params`, appelle `compute()`, assemble.
  - Validation : erreur explicite si feature manquante dans le registre.
  - Validation : erreur explicite si paramètre requis absent.
- Modifier `ai_trading/features/__init__.py` :
  - Ajouter les imports explicites : `from ai_trading.features import log_returns, volatility, rsi, ema, volume`.
  - Exposer `compute_features` et `FEATURE_REGISTRY`.

## Critères d'acceptation
- [ ] `compute_features(ohlcv, config)` produit un DataFrame de shape `(N_total, F=9)` avec les bonnes colonnes.
- [ ] `feature_version` est lu depuis la config et tracé.
- [ ] Le registre contient exactement les 9 features MVP après import du package `ai_trading.features`.
- [ ] Feature inconnue dans `feature_list` → `ValueError` avec nom de la feature manquante.
- [ ] Paramètre requis absent dans `config.features.params` → `ValueError` avec nom du paramètre.
- [ ] Registre vide (pas d'import des modules) → erreur explicite.
- [ ] Ordre des colonnes correspond à l'ordre de `feature_list`.
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords.
- [ ] Suite de tests verte après implémentation.
- [ ] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/013-feature-pipeline` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/013-feature-pipeline` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-3] #013 RED: tests feature pipeline`.
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-3] #013 GREEN: feature pipeline`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-3] #013 — Feature pipeline`.
