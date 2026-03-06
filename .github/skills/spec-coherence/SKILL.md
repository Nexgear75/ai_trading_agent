---
name: spec-coherence
description: "Vérifie la cohérence intrinsèque d'une spécification technique : terminologie, formules, références croisées, paramètres, contrats I/O, glossaire, addenda. Produit un rapport structuré avec incohérences classées par sévérité. À utiliser quand l'utilisateur demande « vérifie la cohérence de la spec », « audit de la spécification », « la spec est-elle cohérente ? »."
argument-hint: "[spec: chemin/vers/spec.md] [scope: all|section-range] [fix: false|true]"
---

# Agent Skill — Vérification de cohérence d'une spécification

## Objectif

Auditer la **cohérence intrinsèque** d'un document de spécification technique. Détecter les contradictions internes, ambiguïtés, références casées, incohérences terminologiques et parametriques — **sans consulter le code ni les tests**. La spécification est analysée en isolation, comme un document autonome.

Le skill opère en deux phases :
- **Phase A** : analyse exhaustive, production d'un rapport structuré.
- **Phase B** (optionnelle, si `fix: true`) : correction séquentielle des incohérences détectées dans le document source.

## Contexte repo

> Les conventions complètes, la stack, les principes non négociables sont définis dans **`AGENTS.md`** (racine du repo). Ce skill ne duplique pas AGENTS.md.

- **Spécification par défaut** : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md`
- **Rapport de sortie** : `docs/review_coherence_spec/NNNN_spec_coherence.md`

## Déclencheurs

- « vérifie la cohérence de la spec »
- « audit de la spécification »
- « la spec est-elle cohérente ? »
- « incohérences dans la spec »
- « revue de la spec »
- « spec coherence check »

---

## Phase A — Analyse de cohérence intrinsèque

### Principe fondamental

L'analyse porte **exclusivement** sur le contenu du document de spécification. Aucun autre fichier (code, tests, plan, tâches, configs) ne doit être consulté pendant cette phase.

L'objectif est de détecter les **contradictions du document avec lui-même** : une règle énoncée en §5 qui contredit une règle en §12, un paramètre défini différemment dans deux sections, une formule dont les variables ne correspondent pas au glossaire, etc.

### Périmètre de lecture

1. Lire **intégralement** le document de spécification cible.
2. Si le document contient des addenda ou annexes, les inclure dans l'analyse.
3. Si le scope est restreint (ex : `scope: §5-§9`), lire tout le document mais concentrer l'analyse sur les sections demandées tout en vérifiant leurs interactions avec le reste.

### Axes d'analyse

Pour chaque axe, vérifier la cohérence **interne** du document :

#### A1. Cohérence terminologique

Vérifier que les mêmes concepts utilisent **les mêmes termes** dans tout le document.

- [ ] Un concept est-il désigné par des termes différents dans différentes sections ? (ex : « horizon » vs « fenêtre de prédiction » pour la même chose)
- [ ] Un même terme est-il utilisé avec des sens différents dans différentes sections ?
- [ ] Les abréviations sont-elles définies à leur première occurrence et utilisées de manière cohérente ensuite ?
- [ ] Les termes du glossaire correspondent-ils exactement à l'usage dans le corps du document ?
- [ ] Les noms de paramètres, variables, modules sont-ils orthographiés de manière identique partout ?

**Méthode** : construire un index des termes clés et vérifier leur unicité sémantique.

#### A2. Cohérence des notations et formules mathématiques

Vérifier que l'appareil mathématique est auto-cohérent.

- [ ] Une même grandeur est-elle notée avec le même symbole partout ? (ex : $H$ pour horizon, pas $h$ ailleurs)
- [ ] Les formules utilisent-elles des variables toutes définies (pas de variable apparaissant sans définition) ?
- [ ] Les dimensions/unités sont-elles cohérentes entre formules qui se composent ? (ex : si $y_t$ est un log-return, les formules qui le consomment traitent-elles bien un log-return, pas un return arithmétique ?)
- [ ] Les conventions d'indexation sont-elles uniformes ? (0-based vs 1-based, inclusif vs exclusif)
- [ ] Les cas dégénérés d'une formule (division par zéro, log(0), tableau vide) sont-ils traités de manière cohérente avec les erreurs prescrites ailleurs ?
- [ ] Les formules des addenda sont-elles compatibles avec celles du corps principal ?

**Méthode** : pour chaque formule, inventorier ses variables et vérifier qu'elles sont définies avec le même sens dans la section Notations (§2) ou au point de définition.

#### A3. Cohérence des références croisées

Vérifier que les renvois internes au document sont valides.

- [ ] Chaque référence `§X.Y` pointe-t-elle vers une section qui existe réellement ?
- [ ] Le contenu référencé correspond-il à ce que la section citante affirme ? (ex : « comme défini en §8.2 » — le contenu de §8.2 dit-il bien ce qui est affirmé ?)
- [ ] Les références aux annexes sont-elles valides ? (Annexe A, B, etc.)
- [ ] Y a-t-il des sections orphelines (jamais référencées et non auto-suffisantes) ?
- [ ] Les renvois sont-ils bidirectionnels quand la logique l'exige ? (si §5 dépend de §12, §12 devrait aussi mentionner §5)

**Méthode** : extraire toutes les occurrences de `§` et vérifier chaque renvoi.

#### A4. Cohérence paramétrique

Vérifier que les paramètres configurables sont définis et utilisés de manière cohérente.

- [ ] Un paramètre mentionné dans une formule est-il défini avec les mêmes contraintes dans la section de configuration ? (ex : `embargo_bars >= H` en §8.2, mais la config en §17.5 ne valide pas cette contrainte)
- [ ] Les valeurs par défaut d'un paramètre sont-elles identiques partout où elles sont citées ?
- [ ] Les plages de validité (min, max, type) sont-elles cohérentes entre la définition et les usages ?
- [ ] Les paramètres présentés comme « configurables » dans une section sont-ils effectivement listés dans la section de configuration ?
- [ ] Les paramètres des addenda remplacent-ils ou complètent-ils ceux du corps principal ? En cas de complément, y a-t-il contradiction ?

**Méthode** : construire un registre des paramètres (nom, type, valeur par défaut, contraintes, sections de définition/usage) et vérifier la cohérence du registre.

#### A5. Cohérence du flux de données (pipeline I/O)

Vérifier que les contrats d'entrée/sortie entre étapes du pipeline décrites dans la spec sont compatibles.

- [ ] Les colonnes/champs produits par l'étape N sont-ils ceux attendus par l'étape N+1 ?
- [ ] Les types de données (float32, float64, datetime, string) sont-ils cohérents aux frontières d'étapes ?
- [ ] Les dimensions tensorielles décrites pour un format (ex : `(N, L, F)`) sont-elles compatibles avec les opérations décrites en aval ?
- [ ] Les conditions de rejet/filtrage d'une étape sont-elles prises en compte par les étapes suivantes ? (ex : warm-up exclusion en §6.6 impacte-t-elle le comptage N en §7.1 ?)
- [ ] Les formats d'artefacts de sortie (JSON, CSV) sont-ils cohérents entre la description textuelle et les schémas/exemples en annexe ?

**Méthode** : pour chaque étape du pipeline, dresser la liste des entrées et sorties décrites, puis vérifier la compatibilité en chaîne.

#### A6. Cohérence des contraintes et règles

Vérifier que les contraintes et règles métier ne se contredisent pas.

- [ ] Deux contraintes s'appliquant au même objet sont-elles compatibles ? (ex : « embargo_bars >= H » et « embargo_bars < n_split_bars » — est-il toujours possible de satisfaire les deux ?)
- [ ] Les comportements en cas d'erreur sont-ils cohérents ? (une section prescrit `raise ValueError`, une autre dit « ignorer silencieusement »)
- [ ] Les exigences de déterminisme/reproductibilité sont-elles cohérentes avec les algorithmes décrits ? (ex : un algorithme stochastique prescrit sans mention de seed)
- [ ] Les conditions de déclenchement (if/then) sont-elles exhaustives ? (pas de cas non couvert)
- [ ] Les assertions spécifiées pour les tests (§17.6) sont-elles vérifiables avec les formules décrites ?

#### A7. Cohérence glossaire ↔ corps

Vérifier la cohérence bidirectionnelle entre le glossaire et le corps du document.

- [ ] Chaque entrée du glossaire est-elle utilisée dans le corps du document ?
- [ ] Chaque terme technique significatif du corps est-il défini dans le glossaire ?
- [ ] Les définitions du glossaire sont-elles compatibles avec l'usage dans les formules ? (ex : le glossaire définit « return » comme arithmétique, mais les formules utilisent des log-returns)
- [ ] Les glossaires multiples (ML, Finance) sont-ils mutuellement cohérents ?

#### A8. Cohérence addenda ↔ corps principal

Si le document contient des addenda ou versions successives :

- [ ] Les addenda contredisent-ils le corps principal sans le signaler explicitement ?
- [ ] Les paramètres ajoutés par les addenda sont-ils cohérents avec les formules du corps ?
- [ ] Les résolutions d'ambiguïté des addenda créent-elles de nouvelles ambiguïtés ?
- [ ] La numérotation des addenda est-elle séquentielle et stable ?
- [ ] Les décisions « best-practice » des addenda sont-elles compatibles entre elles ?

#### A9. Cohérence structurelle et complétude

Vérifier la qualité structurelle du document.

- [ ] Toutes les sections listées dans la table des matières sont-elles présentes dans le corps ?
- [ ] La numérotation des sections est-elle séquentielle et sans trou ?
- [ ] Les niveaux de titre sont-ils cohérents (#, ##, ###) ?
- [ ] Chaque section qui introduit un concept le définit-elle avant de l'utiliser ?
- [ ] Y a-t-il des sections vides ou placeholder ?
- [ ] Les exemples en annexe sont-ils conformes aux schémas/formats décrits dans le corps ?
- [ ] Le document couvre-t-il le périmètre annoncé dans §1 (objet et périmètre) sans débordement ni omission ?

---

### Sortie de la Phase A

Créer le répertoire `docs/review_coherence_spec/` si nécessaire, puis produire le rapport avec le prochain numéro séquentiel.

```bash
mkdir -p docs/review_coherence_spec
# Numéroter : 0001, 0002, ...
ls docs/review_coherence_spec/ | sort | tail -1
```

Le rapport suit cette structure :

```markdown
# Revue de cohérence — Spécification <titre>

**Date** : YYYY-MM-DD
**Document audité** : `<chemin du document>`
**Version spec** : <version>
**Scope** : <all | sections auditées>
**Verdict** : ✅ COHÉRENT | ⚠️ INCOHÉRENCES MINEURES | ❌ INCOHÉRENCES STRUCTURELLES

---

## Résumé exécutif

<2-3 phrases synthèse, nombre d'incohérences par axe>

| Axe | Incohérences | BLOQUANT | WARNING | MINEUR |
|---|---|---|---|---|
| A1. Terminologie | N | n | n | n |
| A2. Formules | N | n | n | n |
| A3. Références croisées | N | n | n | n |
| A4. Paramètres | N | n | n | n |
| A5. Flux I/O | N | n | n | n |
| A6. Contraintes | N | n | n | n |
| A7. Glossaire | N | n | n | n |
| A8. Addenda | N | n | n | n |
| A9. Structure | N | n | n | n |
| **Total** | **N** | **n** | **n** | **n** |

---

## Incohérences détectées

### I-1. <titre court de l'incohérence>

- **Axe** : A1|A2|...|A9
- **Sévérité** : BLOQUANT|WARNING|MINEUR
- **Localisation** : §X.Y ↔ §Z.W (citations du document)
- **Description** : <description factuelle, avec extraits textuels entre guillemets>
- **Contradiction** : <formulation précise de la contradiction>
- **Recommandation** : <correction suggérée, avec proposition de texte si pertinent>

### I-2. ...

---

## Registre des termes clés (A1)

| Terme | Sections d'occurrence | Sens | Cohérent ? |
|---|---|---|---|
| <terme> | §X, §Y, §Z | <sens identifié> | ✅ / ❌ |

---

## Registre des paramètres (A4)

| Paramètre | Défini en | Val. défaut | Contraintes | Utilisé en | Cohérent ? |
|---|---|---|---|---|---|
| <param> | §X.Y | <val> | <contrainte> | §A.B, §C.D | ✅ / ❌ |

---

## Matrice flux I/O (A5)

| Étape source | Sortie décrite | Étape cible | Entrée attendue | Compatible ? |
|---|---|---|---|---|
| §X <nom> | <format/colonnes> | §Y <nom> | <format/colonnes> | ✅ / ❌ |

---

## Conclusion

<verdict final, principaux risques, priorisation des corrections>
```

### Règles de sévérité

| Niveau | Définition | Exemple |
|---|---|---|
| **BLOQUANT** | Contradiction rendant l'implémentation impossible ou ambiguë : deux formules incompatibles pour la même grandeur, parameter avec deux définitions contradictoires, contrat I/O cassé entre étapes. | §5.2 utilise $O_{t+1}$, §12.3 utilise $O_t$ pour la même formule |
| **WARNING** | Ambiguïté créant un risque d'interprétation divergente : terme flou, paramètre sans contrainte explicite, cas de bord non couvert. | `ddof` non spécifié pour une formule de std |
| **MINEUR** | Incohérence cosmétique sans impact fonctionnel : coquille, numérotation cassée, terme du glossaire non utilisé, doublon inoffensif. | §6.5 écrit `vol_w` mais le glossaire écrit `vol_window` |

---

## Phase B — Correction des incohérences (optionnelle)

> Phase B activée uniquement si l'utilisateur passe `fix: true`.

### Pré-conditions

1. Le rapport Phase A existe.
2. L'utilisateur a validé les incohérences à corriger (ou a demandé la correction de toutes).

### Workflow

#### B1. Lire le rapport et créer les TODOs

Lire le rapport produit en Phase A. Pour chaque incohérence I-N, créer une entrée TODO via `manage_todo_list`, ordonnées par sévérité (BLOQUANT → WARNING → MINEUR).

#### B2. Corriger chaque incohérence

Pour chaque TODO, dans l'ordre :

1. **Lire les sections concernées** du document de spécification.
2. **Déterminer la correction** : quelle section fait foi ? En cas de doute, proposer les deux options à l'utilisateur.
3. **Appliquer la correction** en éditant le document source.
4. **Vérifier** que la correction ne casse pas d'autres références ou formules.
5. **Marquer le TODO comme complété**.

#### B3. Règles de correction

- **Principe du moindre changement** : modifier le minimum de texte nécessaire.
- **Cohérence de la correction** : si une formule est corrigée, propager la correction partout où la formule est citée ou utilisée.
- **Pas de nouveau contenu** : les corrections alignent des sections entre elles, elles n'ajoutent pas de fonctionnalité ni de spécification nouvelle.
- **Traçabilité** : chaque correction est rattachée à un I-N du rapport.
- **Addenda** : ne jamais modifier un addendum pour masquer une contradiction avec le corps — corriger le corps OU l'addendum, de manière explicite.

#### B4. Re-vérification

Après toutes les corrections, relancer la Phase A sur le document corrigé pour vérifier la convergence. Si de nouvelles incohérences apparaissent (créées par les corrections), itérer.

**Garde-fou** : maximum **3 itérations**. Si le document ne converge pas, signaler les incohérences résiduelles à l'utilisateur.

#### B5. Mettre à jour le rapport

Mettre à jour le rapport en marquant chaque incohérence :
- ✅ RÉSOLU — correction appliquée
- ⚠️ DIFFÉRÉ — nécessite arbitrage utilisateur
- ❌ NON RÉSOLU — correction impossible sans changement de périmètre

---

## Principes de revue

1. **Le document est analysé en isolation** : de même que l'on revoit un contrat juridique sans consulter les parties prenantes, on revoit la spec sans consulter le code. La question n'est pas « le code fait-il ce que dit la spec ? » (c'est le rôle de `global-review` et `test-adherence`), mais « la spec se contredit-elle elle-même ? ».

2. **Factuel, pas interprétatif** : chaque incohérence doit citer les passages exacts du document qui se contredisent. Pas de « il semble que » ou « on pourrait interpréter que ».

3. **Exhaustivité par axe** : chaque axe A1–A9 doit être couvert dans le rapport, même si aucune incohérence n'est trouvée (mentionner « Aucune incohérence détectée sur cet axe »).

4. **Adversarial reading** : lire le document comme un développeur qui chercherait à justifier deux implémentations contradictoires. Si deux interprétations valides coexistent, c'est une incohérence (au minimum WARNING).

5. **Composabilité des formules** : ne pas se contenter de vérifier chaque formule isolément — vérifier que la composition de formules (quand une formule utilise le résultat d'une autre) est mathématiquement cohérente.

6. **Stabilité des addenda** : les addenda sont censés résoudre des ambiguïtés, pas en créer de nouvelles. Vérifier qu'un addendum ne contredit pas un autre addendum.

---

## Quand utiliser ce skill

- « vérifie la cohérence de la spec »
- « la spec est contradictoire ? »
- « audit de la spécification »
- « cohérence interne de la spec »
- « revue de la spécification »
- « y a-t-il des incohérences dans la spec ? »
- Avant de créer des tâches à partir de la spec (vérifier que la base est saine).
- Après un addendum ou une mise à jour de la spec (vérifier l'absence de régression).
- En amont d'un gate ou milestone, pour s'assurer que la source de vérité est cohérente.

---

## Complémentarité avec les autres skills

| Skill | Focus | Relation |
|---|---|---|
| **spec-coherence** (ce skill) | Cohérence interne de la spec | Source de vérité amont |
| `plan-coherence` | Cohérence interne du plan | Plan dérivé de la spec |
| `test-adherence` | Tests vs spec | Consomme la spec |
| `global-review` | Code vs spec + qualité | Consomme la spec |
| `gate-validator` | Preuves de conformité | Consomme spec + plan |

L'ordre logique d'audit est : **spec-coherence** → `plan-coherence` → `test-adherence` → `global-review` → `gate-validator`. Si la spec est incohérente, tous les audits aval sont compromis.
