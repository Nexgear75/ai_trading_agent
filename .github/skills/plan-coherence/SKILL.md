---
name: plan-coherence
description: "Revue de cohérence intrinsèque du plan d'implémentation et correction séquentielle des incohérences. À utiliser quand l'utilisateur demande « revue du plan », « cohérence du plan », « vérifie le plan d'implémentation », « audit plan »."
argument-hint: "[plan: docs/plan/implementation.md]"
---

# Agent Skill — Revue de cohérence du plan d'implémentation

## Objectif

Auditer la **cohérence intrinsèque** du plan d'implémentation (`docs/plan/implementation.md`), puis corriger les incohérences détectées une par une, de manière isolée et vérifiable.

Le skill opère en deux phases distinctes :
- **Phase A** : analyse du plan seul, production d'un rapport.
- **Phase B** : correction séquentielle de chaque incohérence identifiée.

## Contexte repo

> Les conventions complètes, la stack, les principes non négociables et la structure des workstreams sont définis dans **`AGENTS.md`** (racine du repo). Ce skill ne duplique pas AGENTS.md.

- **Plan** : `docs/plan/implementation.md` (WS-1..WS-12, M1..M5)
- **Rapport de cohérence** : `docs/review_coherence_implementation.md`
- **Tâches** : `docs/tasks/<milestone>/NNN__slug.md`

## Phase A — Analyse de cohérence intrinsèque

### Principe fondamental

L'analyse porte **exclusivement** sur le contenu du plan d'implémentation. Aucun autre fichier (spec, code, tests, configs, tâches) ne doit être consulté pendant cette phase. L'objectif est de détecter les contradictions internes du plan avec lui-même.

### Périmètre de lecture

Lire **intégralement** `docs/plan/implementation.md`.

### Axes d'analyse

Pour chaque axe, vérifier la cohérence **interne** du plan :

#### A1. Cohérence des dépendances

- Les dépendances déclarées entre WS sont-elles respectées dans l'ordonnancement des milestones ?
- Un WS dépend-il d'un autre WS qui est planifié dans un milestone ultérieur ?
- Les gates sont-ils positionnés de manière cohérente avec les dépendances qu'ils vérifient ?
- Y a-t-il des dépendances circulaires ?

#### A2. Cohérence des identifiants et références croisées

- Les numéros de tâches WS-X.Y sont-ils séquentiels et sans doublons ?
- Les références internes (un WS mentionne un autre WS, un gate référence des critères) sont-elles valides ?
- Les noms de modules/fichiers cités sont-ils cohérents entre les différentes sections du plan ?
- Les références de section (§ spec) sont-elles cohérentes quand le plan les mentionne à plusieurs endroits ?

#### A3. Cohérence du contenu sémantique

- Les descriptions de tâches au sein d'un même WS sont-elles mutuellement cohérentes ?
- Un concept est-il défini de manière contradictoire dans deux sections différentes ?
- Les responsabilités sont-elles clairement attribuées (pas de recouvrement ni de trou entre WS) ?
- Les entrées/sorties décrites pour chaque WS sont-elles compatibles avec les WS consommateurs/producteurs décrits ?
- Les critères de gate sont-ils cohérents avec le contenu des WS qu'ils évaluent ?

#### A4. Cohérence structurelle

- Le plan est-il complet ? (tous les WS listés en table des matières sont-ils détaillés ?)
- Les milestones couvrent-ils tous les WS sans omission ?
- La numérotation et la structure sont-elles homogènes d'un WS à l'autre ?
- Les conventions décrites en fin de plan sont-elles cohérentes avec celles appliquées dans le corps du plan ?

#### A5. Cohérence des gates et milestones

- Chaque milestone a-t-il des critères de gate clairement définis ?
- Les critères de gate sont-ils vérifiables avec les livrables du milestone correspondant ?
- Les gates intermédiaires (G-Features, G-Split, etc.) sont-ils cohérents avec le découpage des WS ?
- L'annexe « Synthèse des gates » est-elle fidèle au contenu détaillé ?

### Sortie de la Phase A

Produire le fichier `docs/review_coherence_implementation.md` avec la structure suivante :

```markdown
# Revue de cohérence — Plan d'implémentation

**Date** : YYYY-MM-DD
**Document audité** : `docs/plan/implementation.md`

## Résumé

<nombre d'incohérences par axe, synthèse en 2-3 phrases>

## Incohérences détectées

### I-1. <titre court de l'incohérence>

- **Axe** : A1|A2|A3|A4|A5
- **Sévérité** : BLOQUANT|WARNING|MINEUR
- **Localisation** : <sections/lignes du plan concernées>
- **Description** : <description factuelle de l'incohérence, avec citations du plan>
- **Recommandation** : <correction suggérée>

### I-2. ...

## Conclusion

<verdict : plan cohérent / incohérences mineures / incohérences structurelles à corriger>
```

**Règles de sévérité** :
- **BLOQUANT** : incohérence qui rendrait l'implémentation impossible ou contradictoire (dépendance circulaire, tâche assignée à deux WS avec des comportements différents).
- **WARNING** : incohérence qui crée de l'ambiguïté ou un risque d'erreur d'interprétation (identifiant dupliqué, référence invalide).
- **MINEUR** : incohérence cosmétique ou structurelle sans impact fonctionnel (numérotation non séquentielle, section vide).

## Phase B — Correction séquentielle des incohérences

### Pré-conditions

1. Le fichier `docs/review_coherence_implementation.md` existe (produit par la Phase A).
2. Identifier les milestones déjà implémentés (tâches DONE dans `docs/tasks/`) pour ne pas modifier rétroactivement des éléments déjà livrés — les corrections portent sur la formulation du plan uniquement, pas sur le code déjà implémenté.

### Workflow

#### B1. Lire le rapport de cohérence

Lire `docs/review_coherence_implementation.md` et extraire la liste des incohérences (I-1, I-2, ...).

#### B2. Créer les TODOs

Pour **chaque** incohérence I-N, créer une entrée TODO via `manage_todo_list`.

**Interdiction formelle** : ne pas chercher de contexte supplémentaire à cette étape. Se baser uniquement sur le contenu du rapport de cohérence.

#### B3. Traiter chaque TODO via agent Plan-Corrector

Pour chaque TODO, dans l'ordre du rapport, **lancer l'agent `Plan-Corrector`** (`runSubagent` avec `agentName: "Plan-Corrector"`) qui traite l'incohérence dans un contexte vierge. L'agent est stateless : il ne voit ni le contexte des corrections précédentes, ni celui des suivantes.

> Les instructions détaillées de l'agent sont dans `.github/agents/plan-corrector.agent.md`.

##### Prompt de l'agent

Construire le prompt avec ces éléments :

```
## Incohérence à corriger

<copier intégralement le bloc I-N depuis docs/review_coherence_implementation.md>

## Milestones déjà implémentés

<liste des milestones DONE identifiés en B0>
```

##### Traitement du résultat

Après retour du sous-agent :
1. Marquer le TODO comme complété.
2. Consigner le statut (RÉSOLU/NON RÉSOLU) et la note du sous-agent pour la mise à jour du rapport en B4.

#### B4. Mettre à jour le rapport

Une fois tous les TODOs traités, mettre à jour `docs/review_coherence_implementation.md` :
- Marquer chaque incohérence comme ✅ RÉSOLU ou ⚠️ NON RÉSOLU (si la correction nécessiterait de modifier du code déjà implémenté, ce qui est hors scope).
- Ajouter une note de résolution sous chaque item.

#### B5. Itérer jusqu'à convergence

Les corrections de la Phase B peuvent introduire de **nouvelles** incohérences (corrections en cascade, reformulations ambiguës, effets de bord entre sections). Le processus doit donc être **itéré** :

1. **Versionner** le rapport précédent : renommer `docs/review_coherence_implementation.md` en `docs/review_coherence_implementation_vN.md` (N = numéro d'itération, ex : `_v1`, `_v2`, ...).
2. **Lancer l'agent `Plan-Analyzer`** (`runSubagent` avec `agentName: "Plan-Analyzer"`) pour exécuter la Phase A complète sur le plan corrigé.
   > Les instructions détaillées et interdictions de l'agent sont dans `.github/agents/plan-analyzer.agent.md`.
3. Lire le nouveau rapport produit par le sous-agent.
4. Si le rapport contient **au moins une incohérence** (quel que soit son type : nouvelle, résiduelle, ou réintroduite) → relancer la **Phase B** (B1 à B4), puis revenir à l'étape 1.
5. Si le rapport ne contient **aucune incohérence** → le plan est convergent, le processus est terminé.

**Garde-fou** : si après **3 itérations** le plan ne converge pas (des incohérences persistent ou oscillent), arrêter et signaler le problème à l'utilisateur avec la liste des incohérences résiduelles.

## Agents workers

| Agent | Fichier | Rôle |
|---|---|---|
| `Plan-Corrector` | `.github/agents/plan-corrector.agent.md` | Correction d'une incohérence (Phase B) |
| `Plan-Analyzer` | `.github/agents/plan-analyzer.agent.md` | Analyse de cohérence complète (Phase A itérative) |

> **Modèle** : par défaut, les agents héritent du modèle de la session principale. Pour forcer un modèle spécifique, décommenter la ligne `model:` dans le frontmatter de chaque agent.

## Contraintes opérationnelles

### Isolation des corrections
Chaque incohérence est traitée par l'agent **`Plan-Corrector`** dans un contexte isolé. L'isolation est structurelle :
- L'agent démarre avec un contexte vierge (pas de mémoire des corrections précédentes).
- L'agent retourne un rapport unique, puis son contexte est détruit.
- Chaque correction est vérifiable indépendamment.

### Périmètre strict
- **Phase A** : le plan seul. Rien d'autre.
- **Phase B** : le plan + le minimum de contexte nécessaire pour chaque correction spécifique.
- **Jamais** : modifier le code, les tests, ou les configs. Ce skill ne touche que les documents de planification.

### Milestones implémentés
Pour les milestones déjà implémentés, les corrections du plan sont cosmétiques (alignement du texte avec la réalité). On ne modifie pas le code pour suivre le plan — on aligne le plan sur ce qui a été effectivement livré.
