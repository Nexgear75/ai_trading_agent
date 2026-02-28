# Task Templates — AI Trading Pipeline

## Standard Task Template

```markdown
# Tâche — [Titre descriptif en français]

Statut : TODO
Ordre : [NNN]
Workstream : [WS-X]
Milestone : [M1..M5]
Gate lié : [M1..M5|G-Features|G-Split|G-Backtest|G-Doc|N/A]

## Contexte
[Explication brève]

Références :
- Plan : `docs/plan/implementation.md` (WS-X.Y)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§X.Y)
- Code : `ai_trading/[module]`

Dépendances :
- Tâche NNN — [titre]

## Objectif
[Énoncé clair]

## Règles attendues
- [Règle 1]
- [Règle 2]

## Évolutions proposées
- [Changement 1]
- [Changement 2]

## Critères d'acceptation
- [ ] [Critère vérifiable 1]
- [ ] [Critère vérifiable 2]
- [ ] Tests couvrent cas nominaux + erreurs + bords
- [ ] `ruff check` passe sans erreur

## Pré-condition de démarrage
- Tous les tests existants sont GREEN.
- Branche `task/NNN-short-slug` créée depuis `main`.

## Checklist de fin de tâche
- [ ] Branche `task/NNN-short-slug` créée depuis `main`.
- [ ] Tests RED écrits avant implémentation.
- [ ] Commit RED : `[WS-X] #NNN RED: <résumé>`.
- [ ] Tests GREEN passants.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe.
- [ ] Commit GREEN : `[WS-X] #NNN GREEN: <résumé>`.
- [ ] PR vers `main` : `[WS-X] #NNN — <titre>`.
```

## Task for Feature Implementation

```markdown
# Tâche — Feature [nom] (WS-3.X)

Statut : TODO
Ordre : [NNN]
Workstream : WS-3
Milestone : M2
Gate lié : G-Features

## Contexte
Implémenter la feature [nom] dans le registre pluggable.

Références :
- Plan : `docs/plan/implementation.md` (WS-3.X)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§6.X)
- Code : `ai_trading/features/[module].py`

## Objectif
Implémenter `[feature_name]` via `@register_feature("[nom]")` dans le `FEATURE_REGISTRY`.

## Règles attendues
- Causalité stricte : aucune donnée future utilisée.
- Paramètres lus depuis `config.features.params`.
- NaN uniquement dans la zone warmup.

## Critères d'acceptation
- [ ] Formule conforme à §6.X de la spec.
- [ ] Test numérique : valeurs attendues sur données synthétiques.
- [ ] Test de causalité : modifier prix futurs → feature identique pour t ≤ T.
- [ ] NaN correct aux positions attendues.
- [ ] Feature enregistrée dans `FEATURE_REGISTRY`.
```

## Task for Backtest/Baseline

```markdown
# Tâche — [Baseline/Backtest component] (WS-X.Y)

Statut : TODO
Ordre : [NNN]
Workstream : [WS-8|WS-9]
Milestone : M4
Gate lié : G-Backtest

## Contexte
[Contexte]

Références :
- Plan : `docs/plan/implementation.md` (WS-X.Y)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§12.X ou §13.X)
- Code : `ai_trading/backtest/engine.py` ou `ai_trading/baselines/[module].py`

## Objectif
[Objectif]

## Règles attendues
- Mode `one_at_a_time` et `long_only` imposés (§12.1, E.2.3).
- Modèle de coûts multiplicatif per-side (§12.2).
- Déterminisme : même seed → même résultat.

## Critères d'acceptation
- [ ] Tests numériques avec calculs à la main.
- [ ] Test de déterminisme (2 runs identiques → résultat identique).
- [ ] Cohérence equity-trades.
```
