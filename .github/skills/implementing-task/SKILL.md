---
name: implementing-task
description: Implémenter une ou plusieurs tâches de docs/tasks/ via TDD strict (tests d'acceptation → rouge → vert), conventions du repo AI Trading Pipeline, seuils de couverture, mise à jour du fichier de tâche et commits. Orchestre 4 parties via custom agents : A (TDD-Implementer), B (TDD-Reviewer), C (TDD-Fixer), Post-PR (PR-Review-Fixer). À utiliser quand l'utilisateur demande « implémente/exécute/travaille sur la tâche #NNN ».
---

# Agent Skill — Implementing Task (AI Trading Pipeline)

## Objectif
Orchestrer l'implémentation de tâches décrites dans `docs/tasks/<milestone>/NNN__slug.md` en déléguant le travail à des **custom agents spécialisés** via un workflow en 4 parties :

- **Partie A** : Agent `TDD-Implementer` (TDD strict RED→GREEN).
- **Partie B** : Agent `TDD-Reviewer` (revue de branche + rapport).
- **Partie C** (conditionnel) : Agent `TDD-Fixer` (corrections si la revue relève des items).
- **Partie Post-PR** : Agent `PR-Review-Fixer` (attend la review GitHub automatique, corrige les commentaires, push unique).

Les parties B+C sont itérées jusqu'à 5 fois maximum, ou jusqu'à obtention d'un verdict CLEAN.
La partie Post-PR est exécutée une seule fois (pas de re-review GitHub après push sur PR existante).

## Agents workers

Les instructions détaillées de chaque agent sont dans `.github/agents/` :

| Agent | Fichier | Rôle |
|---|---|---|
| `TDD-Implementer` | `.github/agents/tdd-implementer.agent.md` | Implémentation TDD RED→GREEN |
| `TDD-Reviewer` | `.github/agents/tdd-reviewer.agent.md` | Revue de branche (audit complet) |
| `TDD-Fixer` | `.github/agents/tdd-fixer.agent.md` | Corrections post-revue |
| `PR-Review-Fixer` | `.github/agents/pr-review-fixer.agent.md` | Corrections post-review GitHub automatique |

> **Modèle** : par défaut, les agents héritent du modèle de la session principale. Pour forcer un modèle spécifique, décommenter la ligne `model:` dans le frontmatter de chaque agent `.agent.md`.

## Contexte repo

> Les conventions complètes, la stack, les principes non négociables et la structure des workstreams sont définis dans **`AGENTS.md`** (racine du repo). Ce skill ne duplique pas AGENTS.md — il le **complète** avec le workflow opérationnel spécifique à l'implémentation de tâches.

- **Tâches** : `docs/tasks/<milestone>/NNN__slug.md` (ex : `docs/tasks/M1/001__ws1_config_loader.md`)
- **Spécification** : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (v1.0 + addendum v1.1 + v1.2)
- **Plan** : `docs/plan/implementation.md` (WS-1..WS-12, M1..M5)
- **Code source** : `ai_trading/` (package Python principal)
- **Tests** : `tests/` (pytest, config dans `pyproject.toml`)
- **Configs** : `configs/default.yaml` (Pydantic v2)
- **Linter** : ruff (`line-length = 100`, `target-version = "py311"`)
- **Langue** : anglais pour code/tests, français pour docs/tâches

## Principes non négociables

> Source de vérité : **`AGENTS.md` § Règles non négociables**. Résumé opérationnel ci-dessous.

- **Zéro "ghost completion"** : ne jamais marquer une tâche `DONE` ni cocher un critère `[x]` sans **code + tests** et **exécution vérifiée**.
- **TDD réel** : écrire les tests avant l'implémentation, vérifier qu'ils échouent, puis implémenter.
- **Strict code (no fallbacks)** : aucun fallback silencieux, aucun `or default`, aucun `except` trop large. Validation explicite + `raise`.
- **Config-driven** : tout paramètre modifiable lu depuis `configs/default.yaml` via Pydantic v2. Zéro hardcoding.
- **Anti-fuite** : ne jamais introduire de look-ahead. Données point-in-time. Embargo `embargo_bars >= H`. Scaler fit sur train uniquement. Splits walk-forward séquentiels (train < val < test).
- **Reproductibilité** : seeds fixées et tracées. Hashes SHA-256 (données, config).
- **Branche dédiée** : `task/NNN-short-slug` depuis `Max6000i1`. Jamais de commit direct sur `Max6000i1`.
- **Pull Request obligatoire** vers `Max6000i1` — créée **uniquement par l'orchestrateur** dans la Partie Finale, après que toutes les itérations de revue (Partie B/C) aient abouti à un verdict CLEAN. Les agents workers ne doivent **jamais** exécuter `git push` ni créer de PR.
- **Ambiguïté** : si specs ou tâche ambiguës → demander des clarifications avant d'implémenter.
- **Zéro suppression lint injustifiée** : `# noqa` et `per-file-ignores` dans `pyproject.toml` sont interdits sauf pour les noms **imposés par l'interface/spec** (ex : N803 sur `X_train` paramètre d'une ABC).

## Discipline de contexte

- Lire **ciblé** : utiliser grep/recherche et ne charger que les sections pertinentes de la spec.
- Ne pas charger le document de spécification par défaut : le lire **uniquement si nécessaire**.
- Préférer **exécuter** une commande plutôt que décrire longuement.

---

# WORKFLOW ORCHESTRATEUR (1 tâche)

L'agent orchestrateur coordonne les 3 parties. Il ne code pas lui-même — il délègue aux agents workers via `runSubagent` avec `agentName`.

## Étape 0 — Préparation (orchestrateur)

1. **Pré-condition GREEN** : exécuter `pytest` → tous les tests existants doivent être GREEN. Si RED : corriger d'abord.
2. **Lire la tâche** : ouvrir `docs/tasks/<milestone>/NNN__slug.md`, extraire le milestone `<milestone>`, le numéro `NNN`, le workstream `WS-X`, le slug, les dépendances.
3. **Créer le dossier de review** : `docs/tasks/<milestone>/<NNN>/` (s'il n'existe pas).
4. **Créer la branche dédiée** :
   ```bash
   git checkout Max6000i1
   git pull
   git checkout -b task/NNN-short-slug
   ```
5. **Initialiser le compteur de review** : `review_iteration = 0`.

---

## Partie A — Implémentation (agent TDD-Implementer)

Lancer l'agent `TDD-Implementer` comme subagent (`runSubagent` avec `agentName: "TDD-Implementer"`) en passant le prompt suivant :

```
Implémente la tâche `docs/tasks/<milestone>/NNN__slug.md`.
Branche : `task/NNN-short-slug` (déjà créée et checkoutée).
Workstream : WS-X.
```

L'agent retourne :
- La liste des fichiers modifiés.
- Le résultat de `pytest` (nombre de tests passed/failed).
- Le résultat de `ruff check ai_trading/ tests/`.
- Confirmation du commit RED et GREEN effectués.

---

## Partie B — Revue de branche (agent TDD-Reviewer)

Incrémenter : `review_iteration += 1`.

Lancer l'agent `TDD-Reviewer` comme subagent (`runSubagent` avec `agentName: "TDD-Reviewer"`) en passant le prompt suivant :

```
Branche à auditer : `task/NNN-short-slug`
Tâche associée : `docs/tasks/<milestone>/NNN__slug.md`
Itération de revue : v<review_iteration>

Écris le rapport dans : `docs/tasks/<milestone>/<NNN>/review_v<review_iteration>.md`
```

### Décision de l'orchestrateur après Partie B

**Validation préalable obligatoire** : avant d'accepter un verdict CLEAN, l'orchestrateur **doit vérifier la cohérence** entre le verdict annoncé et les compteurs d'items retournés par l'agent. Si l'agent retourne `CLEAN` mais que le nombre de bloquants + warnings + mineurs > 0, **rejeter le verdict** et le traiter comme REQUEST CHANGES. Un verdict CLEAN n'est valide que si les trois compteurs sont **exactement 0**.

- **Si verdict = CLEAN** (validé : 0 bloquants, 0 warnings, 0 mineurs) → passer à la Partie Finale (push + PR).
- **Si verdict = REQUEST CHANGES** (ou verdict CLEAN invalidé car compteurs > 0) ET `review_iteration < 5` → lancer la Partie C.
- **Si verdict = REQUEST CHANGES** ET `review_iteration >= 5` → **stopper les itérations**. Informer l'utilisateur que 5 itérations de revue ont été effectuées sans atteindre CLEAN. Lister les items restants. Laisser l'utilisateur décider de la suite.

---

## Partie C — Corrections (agent TDD-Fixer, conditionnel)

Lancer l'agent `TDD-Fixer` comme subagent (`runSubagent` avec `agentName: "TDD-Fixer"`) en passant le prompt suivant :

```
Rapport de revue à traiter : `docs/tasks/<milestone>/<NNN>/review_v<review_iteration>.md`
Branche : `task/NNN-short-slug` (déjà checkoutée).
Tâche : `docs/tasks/<milestone>/NNN__slug.md`
Workstream : WS-X, numéro tâche : NNN.
```

L'agent retourne :
- La liste des items corrigés.
- Le résultat de `pytest` (nombre de tests passed/failed).
- Le résultat de `ruff check ai_trading/ tests/`.
- Confirmation des commits FIX effectués.

Après la Partie C, **reboucler sur la Partie B** (nouvelle itération de revue).

---

## Partie Finale — Push et Pull Request (orchestrateur)

Quand la Partie B retourne un verdict CLEAN :

1. **Commiter les fichiers de revue** :
```bash
git add docs/tasks/<milestone>/<NNN>/
git commit -m "[WS-X] #NNN REVIEW: rapports de revue v1..v<review_iteration>"
```

2. **Mettre à jour la checklist procédurale de la tâche** :
Ouvrir `docs/tasks/<milestone>/NNN__slug.md` et cocher les items restants de la checklist. Amender le dernier commit si nécessaire.

3. **Push et création de la PR** :
```bash
git push -u origin task/NNN-short-slug
```
- Titre de la PR : `[WS-X] #NNN — <titre de la tâche>`
- Description : résumé des changements, lien vers la tâche, nombre d'itérations de revue effectuées.

4. **Cocher l'item PR dans la checklist** :
Mettre à jour le fichier de tâche. Commiter et pousser l'update.

---

## Partie Post-PR — Review GitHub automatique (orchestrateur + agent PR-Review-Fixer)

Après la création de la PR, GitHub déclenche une review automatique (Copilot PR reviewer). L'orchestrateur attend cette review, corrige les commentaires, pousse les corrections, et termine. **Pas de re-polling** : la review GitHub n'est pas ré-exécutée automatiquement après un push sur une PR existante.

### Étape 1 — Polling de la review (orchestrateur)

L'orchestrateur interroge la PR via l'outil `github-pull-request_activePullRequest` pour récupérer les commentaires de review.

**Stratégie de polling** :
- **Délai initial** : attendre 60 secondes après le push avant le premier poll (la review GitHub prend typiquement 30s à 2min).
- **Intervalle** : 30 secondes entre chaque tentative.
- **Durée minimale de polling** : **15 minutes complètes** (900 secondes). Il est **INTERDIT** d'abandonner le polling avant que 15 minutes se soient écoulées depuis le premier poll. Compter les itérations : avec un intervalle de 30s, cela correspond à **au moins 28 itérations** après le délai initial de 60s.
- **Timeout** : après 15 minutes de polling sans review, **abandonner le polling**, informer l'utilisateur, et **NE PAS merger la PR**. La PR reste ouverte pour que l'utilisateur décide de la suite (attente manuelle, merge manuel, ou relance).
- **Détection** : la review est considérée comme arrivée quand le champ `comments` de `activePullRequest` contient au moins un commentaire dont l'auteur est `copilot-pull-request-reviewer`.

> **⚠️ RÈGLE STRICTE** : abandonner le polling avant 15 minutes ou merger sans review sont des violations du workflow. Le merge automatique (Étape 5) n'est autorisé que si la review a été reçue et traitée (Étapes 2-4), OU si tous les commentaires sont IGNORÉS avec justification.

### Étape 2 — Extraction et triage (orchestrateur)

Une fois les commentaires récupérés :

1. **Filtrer** : ne garder que les commentaires de `copilot-pull-request-reviewer` avec `commentState == "unresolved"`.
2. **Classifier** chaque commentaire par sévérité :
   - **BLOQUANT** : le commentaire signale un bug, une régression potentielle, une violation de convention, ou une faille.
   - **MINEUR** : le commentaire concerne le style, la documentation, ou une suggestion d'amélioration.
   - **IGNORÉ** : le commentaire est un faux positif, non pertinent, ou contredit les conventions du repo (ex : le reviewer suggère un pattern interdit par AGENTS.md). Documenter la raison.
3. **Si 0 items actionnables** (tout IGNORÉ) : passer directement à l'Étape 5 (merge).
4. **Si aucun commentaire de review** (timeout 15 min atteint) : **NE PAS passer à l'Étape 5**. Informer l'utilisateur et **STOPPER**. La PR reste ouverte.

### Étape 3 — Corrections (agent PR-Review-Fixer)

Formuler un rapport structuré à partir des commentaires extraits et lancer l'agent `PR-Review-Fixer` :

```
Commentaires de review GitHub à traiter :

1. [BLOQUANT|MINEUR] <résumé du commentaire>
   - Fichier : `<chemin>`
   - Commentaire original : <texte complet>
   - Suggestion : <suggestion du reviewer si présente>

2. ...

Commentaires IGNORÉS (pas de correction) :
- <commentaire> → Raison : <justification>

Branche : `task/NNN-short-slug` (déjà checkoutée).
Tâche : `docs/tasks/<milestone>/NNN__slug.md`
Workstream : WS-X, numéro tâche : NNN.
```

L'agent retourne :
- La liste des items corrigés.
- Le résultat de `pytest` (nombre de tests passed/failed).
- Le résultat de `ruff check ai_trading/ tests/`.
- Confirmation des commits PR-FIX effectués.

### Étape 4 — Push (orchestrateur)

Après les corrections :

1. **Push** : `git push` (la branche est déjà trackée).
2. Passer à l'Étape 5.

### Étape 5 — Merge automatique (orchestrateur)

> **Pré-condition** : cette étape n'est accessible que si la review GitHub a été reçue et traitée (Étapes 2-4), y compris le cas où tous les commentaires sont IGNORÉS. Si le polling a expiré sans review (timeout 15 min), cette étape est **INTERDITE** — la PR reste ouverte.

Vérifier l'état de mergeabilité de la PR via `gh pr view --json mergeable` :

- **Si `mergeable == "MERGEABLE"`** (pas de conflits avec la branche de base) : exécuter le merge :
  ```bash
  gh pr merge --squash --delete-branch
  ```
  Confirmer le merge à l'utilisateur. **FIN**.
- **Si conflits ou statut non-mergeable** : informer l'utilisateur que le merge automatique n'est pas possible (conflits détectés). Laisser l'utilisateur résoudre manuellement. **FIN**.

---

## Plusieurs tâches

- Traiter **dans l'ordre**, en respectant les dépendances.
- Terminer le workflow complet (Étape 0 → Partie A → Boucle B/C → Partie Finale) **pour chaque tâche** avant de passer à la suivante.
- Commits **par tâche** (pas de batch multi-tâches).
- Chaque tâche a sa propre branche et sa propre PR.

## Procédure d'abandon

Si à n'importe quelle étape la tâche s'avère irréalisable :

1. **Sauvegarder** : `git stash push -m "WIP #NNN"`.
2. **Documenter** dans le fichier de tâche : section `## Blocage` avec raison et date.
3. **Statut** → `BLOCKED`.
4. **Informer l'utilisateur** avec raison et suggestion d'action.
5. **Ne pas supprimer la branche**.

## Format de commits

| Moment | Format | Contenu |
|---|---|---|
| Après tests RED (Partie A) | `[WS-X] #NNN RED: <résumé>` | Fichiers de tests (+ conftest.py, configs/ si nécessaire) |
| Clôture tâche (Partie A) | `[WS-X] #NNN GREEN: <résumé>` | Implémentation + tests ajustés + tâche + configs |
| Corrections post-revue (Partie C) | `[WS-X] #NNN FIX: <résumé>` | Corrections demandées (code + tests + docs mélangés) |
| Corrections post-review GitHub (Post-PR) | `[WS-X] #NNN PR-FIX: <résumé>` | Corrections des commentaires du reviewer GitHub |

Aucun commit intermédiaire entre RED et GREEN sauf refactoring mineur (tests verts).

## Résumé du flux orchestrateur

```
Étape 0 : Préparation (branche, dossier review)
    │
    ▼
Partie A : Agent TDD-Implementer (RED → GREEN)
    │
    ▼
┌─► Partie B : Agent TDD-Reviewer → review_v<N>.md
│       │
│       ├── CLEAN → Partie Finale (push + PR)
│       │                   │
│       └── REQUEST CHANGES │ (et N < 5)
│               │           │
│               ▼           ▼
│       Partie C          Partie Post-PR
│       TDD-Fixer          Poll review GitHub (timeout 15min)
│               │               │
└───────────────┘           0 items ──┐
  (reboucle B, N+1)             │     │
                            items → Agent PR-Review-Fixer
                                │     │
                            push ─────┤
                                      │
                                      ▼
                              Merge si MERGEABLE
                                      │
                                      ▼
                                     FIN

Si N >= 5 et toujours REQUEST CHANGES → STOP.
```

## Conventions Python / AI Trading

> Source de vérité : **`AGENTS.md`** § Conventions de code + `.github/shared/coding_rules.md` (§R1-§R10).
