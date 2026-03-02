# Tâche — Registre de features et classe de base (BaseFeature)

Statut : DONE
Ordre : 007
Workstream : WS-3
Milestone : M2
Gate lié : G-Features

## Contexte
Avant d'implémenter les 9 features MVP, il faut mettre en place l'architecture pluggable : un registre global `FEATURE_REGISTRY`, un décorateur `@register_feature`, et une classe abstraite `BaseFeature` définissant le contrat de chaque feature.

Références :
- Plan : `docs/plan/implementation.md` (WS-3.6, détails d'architecture points 1–5)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§6.2)
- Code : `ai_trading/features/registry.py` (à créer)

Dépendances :
- Tâche 006 — Politique de traitement des trous (doit être DONE)

## Objectif
Créer le module `ai_trading/features/registry.py` contenant :
1. `FEATURE_REGISTRY: dict[str, type[BaseFeature]]` — dictionnaire global nom → classe.
2. `@register_feature(name: str)` — décorateur qui enregistre la classe. Lève `ValueError` si doublon.
3. `BaseFeature(ABC)` — classe abstraite avec :
   - `compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series` — calcul causal, retourne une Series indexée par timestamp.
   - `required_params -> list[str]` (class attribute) — clés requises dans `params`.
   - `min_periods -> int` (property abstraite) — nombre minimum de bougies avant première valeur valide.

## Règles attendues
- **Strict code** : `@register_feature` lève `ValueError` si le nom est déjà enregistré (pas de remplacement silencieux). Lève `TypeError` si la classe décorée n'est pas une sous-classe de `BaseFeature`.
- **Pas de fallback** : `required_params` doit être déclaré explicitement par chaque sous-classe (même si `[]`). L'héritage silencieux du défaut de la base est interdit — `__init_subclass__` lève `TypeError` si la sous-classe omet la déclaration.
- **Anti-fuite** : la causalité est un contrat de `compute()` — documentée dans la docstring.

## Évolutions proposées
- Créer `ai_trading/features/registry.py` avec `FEATURE_REGISTRY`, `@register_feature`, `BaseFeature`.
- `BaseFeature.compute()` est abstraite (`@abstractmethod`).
- `BaseFeature.min_periods` est une property abstraite.
- `BaseFeature.required_params` est un attribut de classe (`list[str]`), défaut `[]` dans la base, mais chaque sous-classe **doit** le redéclarer explicitement (enforced par `__init_subclass__`).
- `@register_feature` valide que la classe décorée est bien une sous-classe de `BaseFeature` (`issubclass` check).
- Les tests vérifient le comportement du décorateur et du registre.

## Critères d'acceptation
- [x] `FEATURE_REGISTRY` est un dict vide au démarrage (avant import des modules feature).
- [x] `@register_feature("nom")` enregistre la classe dans le dictionnaire.
- [x] `@register_feature("nom")` sur un doublon lève `ValueError`.
- [x] `BaseFeature` est abstraite : instanciation directe lève `TypeError`.
- [x] Une sous-classe qui n'implémente pas `compute` lève `TypeError` à l'instanciation.
- [x] Une sous-classe qui n'implémente pas `min_periods` lève `TypeError` à l'instanciation.
- [x] `required_params` est accessible en tant qu'attribut de classe.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/007-feature-registry` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/007-feature-registry` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-3] #007 RED: tests registre features et BaseFeature`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-3] #007 GREEN: registre features et BaseFeature`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-3] #007 — Registre de features et BaseFeature`.
