# Templates Markdown — AI Trading Pipeline

> Templates réutilisables pour les documents du projet.

## Template 1 — Document technique

```markdown
# <Titre du document>

> <Résumé en 1-2 phrases.>

## Contexte

<Pourquoi ce document existe, quel problème il adresse.>

## Contenu

### <Sous-section 1>

<Détails techniques.>

### <Sous-section 2>

<Détails techniques.>

## Références

- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` §X.Y
- Plan : `docs/plan/implementation.md` WS-N
```

## Template 2 — Tâche d'implémentation

> **Note** : le template canonique des tâches est défini dans le skill `task-creator`
> (`.github/skills/task-creator/SKILL.md` § Format des fichiers de tâche).
> Utiliser ce template-là pour toute création de tâche `docs/tasks/<milestone>/NNN__slug.md`.

## Template 3 — Guide technique

```markdown
# Guide — <Sujet>

> <Ce que le lecteur saura faire après lecture.>

## Prérequis

- <Prérequis 1>
- <Prérequis 2>

## Étapes

### 1. <Première étape>

<Instructions détaillées.>

```python
# Exemple de code
```

### 2. <Deuxième étape>

<Instructions détaillées.>

## Validation

<Comment vérifier que le résultat est correct.>

## Erreurs courantes

| Erreur | Cause | Solution |
|---|---|---|
| <Erreur 1> | <Cause> | <Solution> |
```

## Template 4 — Synthèse courte

```markdown
# <Titre>

> <Résumé en 1 phrase.>

## Points clés

- **<Point 1>** : <détail>
- **<Point 2>** : <détail>
- **<Point 3>** : <détail>

## Décision

<Décision prise et justification.>

## Actions

- [ ] <Action 1> — responsable, deadline
- [ ] <Action 2> — responsable, deadline
```

## Template 5 — ADR (Architecture Decision Record) light

```markdown
# ADR-NNN — <Titre de la décision>

> <Résumé de la décision en 1 phrase.>

| Champ | Valeur |
|---|---|
| **Statut** | Proposé / Accepté / Remplacé |
| **Date** | YYYY-MM-DD |
| **Workstream** | WS-X |

## Contexte

<Quel problème ou question a motivé cette décision.>

## Options considérées

### Option A — <Nom>
- ✅ <Avantage>
- ❌ <Inconvénient>

### Option B — <Nom>
- ✅ <Avantage>
- ❌ <Inconvénient>

## Décision

Option <X> retenue car <justification>.

## Conséquences

- <Impact 1>
- <Impact 2>
```
