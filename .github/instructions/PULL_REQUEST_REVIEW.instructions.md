---
applyTo: "**"
---

# Revue de Pull Request — AI Trading Pipeline

## Sortie obligatoire

À la fin de la revue, **produire un fichier de rapport** :
- **Chemin** : `docs/pr_review_copilot/<nom_de_branche>_review.md`
  - `<nom_de_branche>` = nom de la branche source de la PR (ex : `task/014-warmup-validation` → `task_014-warmup-validation_review.md`). Remplacer les `/` par `_`.
- **Contenu** : la grille d'audit ci-dessous, remplie avec les résultats (`[x]` = OK, `[ ]` = non conforme, `[N/A]` = non applicable), plus une section verdict final (APPROVE / REQUEST CHANGES) et la liste des remarques numérotées avec recommandations.

## Contexte repo

- **Spécification** : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md`
- **Plan** : `docs/plan/implementation.md` (WS-1..WS-12, M1..M5)
- **Tâches** : `docs/tasks/<milestone>/NNN__slug.md`
- **Code source** : `ai_trading/`
- **Tests** : `tests/` (pytest)
- **Configs** : `configs/default.yaml`
- **Linter** : ruff (`line-length = 100`, `target-version = "py311"`)

## Grille d'audit

### Structure branche & commits
- [ ] Branche `task/NNN-short-slug` depuis `Max6000i1`.
- [ ] Commit RED : `[WS-X] #NNN RED: <résumé>` (tests uniquement).
- [ ] Commit GREEN : `[WS-X] #NNN GREEN: <résumé>` (implémentation + tâche).
- [ ] Pas de commits parasites entre RED et GREEN.

### Tâche associée
- [ ] `docs/tasks/<milestone>/NNN__slug.md` : statut DONE.
- [ ] Critères d'acceptation cochés `[x]`.
- [ ] Checklist cochée `[x]`.

### Tests
- [ ] Convention de nommage (`test_config.py`, `test_features.py`, etc.).
- [ ] Couverture des critères d'acceptation.
- [ ] Cas nominaux + erreurs + bords.
- [ ] `pytest` GREEN, 0 échec.
- [ ] `ruff check ai_trading/ tests/` clean.
- [ ] Données synthétiques (pas réseau).
- [ ] Tests déterministes (seeds fixées).

### Strict code (no fallbacks)
- [ ] Aucun `or default`, `value if value else default`.
- [ ] Aucun `except` trop large.
- [ ] Validation explicite + `raise`.

### Config-driven
- [ ] Paramètres dans `configs/default.yaml`, pas hardcodés.
- [ ] Formules conformes à la spec.

### Anti-fuite (look-ahead)
- [ ] Données point-in-time.
- [ ] Embargo `embargo_bars >= H` (§8.2).
- [ ] Scaler fit sur train uniquement.
- [ ] Splits train < val < test.
- [ ] Features backward-looking.
- [ ] θ calibré sur val, pas test.

### Reproductibilité
- [ ] Seeds fixées et tracées.
- [ ] Hashes SHA-256 si applicable.

### Float conventions
- [ ] Float32 pour tenseurs X_seq, y.
- [ ] Float64 pour métriques.

### Qualité
- [ ] snake_case.
- [ ] Pas de print(), code mort, TODO orphelin.
- [ ] Imports propres.
- [ ] DRY : pas de duplication de logique (ex : formules, conditions) dans tout le projet.

## Format du fichier de rapport

Le fichier `docs/pr_review_copilot/<nom_de_branche>_review.md` doit suivre cette structure :

```markdown
# PR Review — <titre de la PR>

**Branche** : `<nom_de_branche>`
**Date** : <date de la revue>
**Verdict** : APPROVE | REQUEST CHANGES

## Grille d'audit

<copier la grille ci-dessus avec les cases cochées/décochées>

## Remarques

1. [BLOQUANT|WARNING|MINEUR] <description>
   - Fichier : `<chemin>`
   - Ligne(s) : <numéros>
   - Suggestion : <correction proposée>

## Résumé

<synthèse en 2-3 phrases>
```
