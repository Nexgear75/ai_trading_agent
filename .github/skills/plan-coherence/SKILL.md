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
- **Tâches** : `docs/tasks/NNN__slug.md`

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

#### B3. Traiter chaque TODO via sous-agent isolé

Pour chaque TODO, dans l'ordre du rapport, **lancer un sous-agent** (`runSubagent`) qui traite l'incohérence dans un contexte vierge. Le sous-agent est stateless : il ne voit ni le contexte des corrections précédentes, ni celui des suivantes.

##### Prompt du sous-agent

Construire le prompt du sous-agent avec ces éléments **exactement** :

```
Tu dois corriger UNE incohérence dans le plan d'implémentation du projet AI Trading Pipeline.

## Incohérence à corriger

<copier intégralement le bloc I-N depuis docs/review_coherence_implementation.md>

## Milestones déjà implémentés

<liste des milestones DONE identifiés en B0>

## Règles

1. Lis les sections du plan concernées par l'incohérence (`docs/plan/implementation.md`).
2. Si la correction nécessite de comprendre l'impact sur les tâches existantes, lis les fichiers de tâches concernés (`docs/tasks/NNN__slug.md`).
3. Si la correction nécessite de vérifier une référence spec, lis la section spec ciblée (`docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md`).
4. Ne charge que les fichiers strictement nécessaires à CETTE incohérence.
5. Applique la correction dans `docs/plan/implementation.md`. La correction doit être minimale et ciblée.
6. Ne modifie JAMAIS le code, les tests, ou les configs. Uniquement les documents de planification.
7. Ne pas « améliorer » d'autres parties du plan par opportunisme.
8. Après la correction, relis les sections immédiatement adjacentes pour vérifier que tu n'as pas créé de nouvelle incohérence. Si oui, corrige-la immédiatement.
9. Pour les milestones déjà implémentés, aligne le plan sur ce qui a été livré (corrections cosmétiques uniquement).

## Réponse attendue

Retourne un rapport structuré :
- **Statut** : RÉSOLU | NON RÉSOLU (si la correction nécessiterait de modifier du code)
- **Modifications** : liste des fichiers et sections modifiés
- **Vérification** : confirmation que les sections adjacentes restent cohérentes, ou description des corrections en cascade effectuées
- **Note** : toute remarque pertinente pour le rapport final
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
2. **Lancer un sous-agent (`runSubagent`)** pour exécuter la Phase A complète sur le plan corrigé. Ce sous-agent :
   - Démarre avec un contexte vierge (aucune connaissance des incohérences précédentes ni des corrections effectuées).
   - Relit **intégralement** `docs/plan/implementation.md` depuis le début.
   - Applique **tous** les axes d'analyse (A1 à A5) sans exception.
   - Produit un nouveau `docs/review_coherence_implementation.md`.
   - **Ne doit PAS** consulter les rapports versionnés (`_v1`, `_v2`, ...) ni vérifier si des corrections précédentes ont été appliquées. Son seul input est le plan tel qu'il est maintenant.
3. Lire le nouveau rapport produit par le sous-agent.
4. Si le rapport contient **au moins une incohérence** (quel que soit son type : nouvelle, résiduelle, ou réintroduite) → relancer la **Phase B** (B1 à B4), puis revenir à l'étape 1.
5. Si le rapport ne contient **aucune incohérence** → le plan est convergent, le processus est terminé.

**Interdictions pour le sous-agent Phase A** :
- Ne **jamais** conclure « pas d'incohérence » sur la base du fait que des corrections ont été faites. L'analyse doit être un audit complet et indépendant.
- Ne **jamais** lire les rapports d'itérations précédentes (`_v1`, `_v2`, ...).
- Ne **jamais** présumer que les corrections de la Phase B sont correctes.

**Garde-fou** : si après **3 itérations** le plan ne converge pas (des incohérences persistent ou oscillent), arrêter et signaler le problème à l'utilisateur avec la liste des incohérences résiduelles.

## Contraintes opérationnelles

### Isolation des corrections
Chaque incohérence est traitée par un **sous-agent indépendant** (`runSubagent`). L'isolation est structurelle, pas comportementale :
- Le sous-agent démarre avec un contexte vierge (pas de mémoire des corrections précédentes).
- Le sous-agent retourne un rapport unique, puis son contexte est détruit.
- Chaque correction est vérifiable indépendamment.

### Périmètre strict
- **Phase A** : le plan seul. Rien d'autre.
- **Phase B** : le plan + le minimum de contexte nécessaire pour chaque correction spécifique.
- **Jamais** : modifier le code, les tests, ou les configs. Ce skill ne touche que les documents de planification.

### Milestones implémentés
Pour les milestones déjà implémentés, les corrections du plan sont cosmétiques (alignement du texte avec la réalité). On ne modifie pas le code pour suivre le plan — on aligne le plan sur ce qui a été effectivement livré.
