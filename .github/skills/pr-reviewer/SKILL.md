---
name: pr-reviewer
description: Revue systématique de Pull Request pour le projet AI Trading Pipeline. Vérifie conformité TDD, anti-fuite, strict code, config-driven, conventions de branche et qualité globale. À utiliser quand l'utilisateur demande « review la PR », « revue de la branche task/NNN-* », « vérifie avant merge ».
argument-hint: "[branche: task/NNN-short-slug] ou [PR number]"
---

# Agent Skill — PR Reviewer (AI Trading Pipeline)

## Objectif
Effectuer une revue systématique et exigeante d'une Pull Request (ou d'une branche `task/NNN-*`) avant merge vers `Max6000i1`, en vérifiant la conformité avec les règles du projet AI Trading Pipeline.

## Prérequis
> **Avant de commencer**, lire `.github/shared/coding_rules.md` pour disposer des checklists détaillées (§R1-§R10) et des commandes de scan (§GREP) référencées dans ce workflow.

## Contexte repo

- **Spécification** : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (v1.0 + addendum v1.1 + v1.2)
- **Plan** : `docs/plan/implementation.md` (WS-1..WS-12, M1..M5)
- **Tâches** : `docs/tasks/<milestone>/NNN__slug.md`
- **Code source** : `ai_trading/` (package Python principal)
- **Tests** : `tests/` (pytest)
- **Configs** : `configs/default.yaml`
- **Linter** : ruff (`line-length = 100`, `target-version = "py311"`)
- **Langue** : anglais pour code/tests, français pour docs/tâches

## Rôle de l'agent

Tu dois :
- auditer **tous les fichiers modifiés** de la PR/branche par rapport à `Max6000i1` ;
- **lire le diff ligne par ligne** pour chaque fichier source modifié ;
- **exécuter des scans automatisés** (grep) pour prouver factuellement chaque vérification ;
- vérifier la conformité avec chaque règle du projet ;
- produire un **rapport de revue structuré** avec verdict global et **annotations inline par fichier** ;
- ne jamais approuver une PR qui viole une règle non négociable.

> **Principe fondamental** : chaque `✅` du rapport DOIT être accompagné d'une **preuve d'exécution** (output grep, résultat pytest, diff lu). Un `✅` sans preuve = non vérifié = `❌`.

## Workflow de revue

Le workflow est organisé en deux phases. **Phase A** (compliance rapide) valide le processus TDD. Si elle échoue → REJECT immédiat sans passer à la Phase B. **Phase B** (code review adversariale) représente **80% du temps de la revue** et analyse le code en profondeur.

---

## PHASE A — Compliance rapide

> But : valider le processus TDD, la tâche et le CI. Blocage ici = REJECT immédiat.

### A1. Identifier le périmètre

- Déterminer la branche source (`task/NNN-short-slug`).
- Identifier la tâche associée dans `docs/tasks/<milestone>/NNN__slug.md`.
- Lister les fichiers modifiés vs `Max6000i1` :
  ```bash
  git diff --name-only Max6000i1...HEAD
  ```
- Capturer le nombre de fichiers source (`ai_trading/`), de tests (`tests/`), et de docs.

### A2. Vérifier la structure de branche et commits

- [ ] La branche suit la convention `task/NNN-short-slug`.
- [ ] Il existe un commit RED au format `[WS-X] #NNN RED: <résumé>`.
- [ ] Il existe un commit GREEN au format `[WS-X] #NNN GREEN: <résumé>`.
- [ ] Le commit RED contient uniquement des fichiers de tests.
- [ ] Le commit GREEN contient l'implémentation + mise à jour de la tâche.
- [ ] Pas de commits parasites entre RED et GREEN (sauf refactoring mineur).

### A3. Vérifier la tâche associée

- [ ] Le fichier `docs/tasks/<milestone>/NNN__slug.md` est modifié dans la PR.
- [ ] `Statut` est passé à `DONE`.
- [ ] Tous les critères d'acceptation sont cochés `[x]`.
- [ ] Toute la checklist de fin de tâche est cochée `[x]`.
- [ ] Les critères cochés correspondent à des preuves vérifiables (code, tests, artefacts). **Pour chaque critère coché `[x]`**, le reviewer doit citer la **ligne de code exacte** (ou le test) qui le satisfait. Si un critère affirme une propriété (ex : « paramètres lus depuis config.X ») et qu'aucune ligne de code dans la PR ne l'implémente, le critère ne peut pas être validé — signaler comme **BLOQUANT** même si un test passe par voie indirecte.

### A4. Exécuter la suite de validation

```bash
pytest tests/ -v --tb=short
ruff check ai_trading/ tests/
```

- [ ] **pytest GREEN** : NNN passed, 0 failed (noter le nombre exact).
- [ ] **ruff clean** : 0 erreur.

> Si pytest RED ou ruff erreurs → **REJECT** immédiat. Ne pas continuer en Phase B.

---

## PHASE B — Code review adversariale

> But : analyse du code en profondeur (bugs, edge cases, anti-patterns, logique métier).
> Cette phase représente **80% du temps** de la revue.

### B1. Scan automatisé obligatoire (GREP)

**Exécuter TOUTES les commandes ci-dessous** sur les fichiers modifiés et documenter les résultats dans le rapport. Aucun raccourci : même si « ça a l'air OK », exécuter le grep et noter le résultat.

> **Commandes et classification** : voir `.github/shared/coding_rules.md` §GREP.
> Exécuter **toutes** les commandes listées et documenter chaque résultat dans le rapport.

### B2. Lecture du diff ligne par ligne (OBLIGATOIRE)

Pour **CHAQUE fichier source modifié** (pas les docs/tâches), lire le diff complet :

```bash
git diff Max6000i1...HEAD -- <fichier>
```

Pour chaque hunk de diff, appliquer cette grille de lecture :

1. **Type safety** : les valeurs lues depuis l'extérieur (JSON, YAML, fichiers, args) sont-elles validées en type ? Une valeur lue depuis un `json.loads()` ou `yaml.safe_load()` sans vérification de type est un **WARNING**.
2. **Edge cases** : que se passe-t-il si l'entrée est `None`, vide, du mauvais type, très grande ?
3. **Domaine mathématique des paramètres** : pour chaque paramètre validé par une borne (ex : `>= 0`), vérifier que la **borne opposée** est également couverte. En particulier pour les **taux et proportions** (`fee_rate`, `slippage_rate`, `position_fraction`, tout paramètre utilisé comme multiplicateur `(1 - p)` ou `(1 + p)`) : le domaine valide est typiquement `[0, 1)` — une valeur `>= 1` rend le calcul mathématiquement incohérent (multiplicateur négatif ou nul). Si la validation ne couvre que `>= 0` sans borne supérieure → **BLOQUANT**.
4. **Path handling** : si un paramètre `path` ou `run_dir` est reçu et utilisé pour de l'I/O (écriture de fichiers, sous-répertoires), vérifier **impérativement** : (a) est-il créé avant usage (`mkdir(parents=True, exist_ok=True)`) ou le contrat exige-t-il explicitement qu'il préexiste ? (b) supporte-t-il directory ET fichier si documenté comme tel ? (c) les parents sont-ils créés ? **Un `run_dir / "model"` sans `run_dir.mkdir()` préalable est un bug latent — BLOQUANT.**
5. **Return contract** : le type de retour est-il garanti en toute circonstance (shape, dtype, clés dict) ?
6. **Resource cleanup** : fichiers ouverts, connections — sont-ils fermés en cas d'erreur ?
7. **Cohérence doc/code** : la docstring correspond-elle au comportement réel ?

Documenter **chaque observation** dans la section « Annotations par fichier » du rapport. Si un fichier n'a aucune observation, noter « RAS après lecture complète du diff (N lignes) ».

### B3. Vérifier les tests

- [ ] Les tests dans `tests/` suivent la convention du plan (`test_config.py`, `test_features.py`, `test_splitter.py`, etc.). L'ID tâche `#NNN` dans les docstrings, pas les noms de fichiers.
- [ ] Chaque critère d'acceptation est couvert par au moins un test.
- [ ] Les tests couvrent : cas nominaux, cas d'erreur, cas de bords.
- [ ] **Boundary fuzzing mental** : pour chaque paramètre numérique d'entrée (`n`, `L`, `H`, taille, etc.), vérifier qu'il existe un test pour chacune de ces situations : `param = 0`, `param = 1`, `param > n` (dépassement), `param = n` (limite exacte). Si une combinaison critique manque, la signaler comme bloquante.
- [ ] **Boundary fuzzing — taux et proportions** : pour chaque paramètre de type taux/proportion/ratio (`fee_rate`, `slippage_rate`, `position_fraction`, ou tout paramètre apparaissant dans une formule `(1 - p)` ou `(1 + p)`), vérifier qu'il existe un test pour : `param = 0` (neutre), `param = 1` (boundary — souvent invalide), `param > 1` (invalide — doit lever une erreur). Si le code valide uniquement `>= 0` sans borne supérieure et qu'aucun test ne vérifie le rejet de `param >= 1` → **BLOQUANT**.
- [ ] Pas de test désactivé (`@pytest.mark.skip`, `xfail`) sans justification explicite.
- [ ] Les tests sont déterministes (seeds fixées si aléatoire).
- [ ] Les tests utilisent des données synthétiques (pas de dépendance réseau).
- [ ] **Portabilité des chemins** (prouvé par scan B1) : pas de chemin OS-spécifique hardcodé (`/tmp/...`). Tous les chemins temporaires utilisent la fixture pytest `tmp_path`.
- [ ] **Tests de registre réalistes** (prouvé par scan B1) : si un test vérifie l'enregistrement automatique dans un registre via décorateur, il doit utiliser `importlib.reload(module)` après nettoyage du registre — pas un appel manuel à `register_xxx()`. Comparer avec `mod.ClassName` (module rechargé).
- [ ] **Contrat ABC complètement testé** : si une méthode abstraite documente qu'elle accepte plusieurs types d'entrée (ex : `path` = directory ou fichier), les tests couvrent chaque variante.

### B4. Audit du code — Règles non négociables

> Checklists détaillées : `.github/shared/coding_rules.md`.
> Prouver chaque item par scan B1 ou lecture diff B2.

#### B4a. Strict code (no fallbacks)
> Checklist : §R1. Preuve : scan B1 (fallbacks, except).

#### B4a-bis. Defensive indexing / slicing
> Checklist : §R10. Preuve : lecture diff B2.

#### B4b. Config-driven (pas de hardcoding)
> Checklist : §R2. Preuve : lecture diff B2.

#### B4c. Anti-fuite (look-ahead)
> Checklist : §R3. Preuve : scan B1 (`.shift(-`) + lecture diff B2.

#### B4d. Reproductibilité
> Checklist : §R4. Preuve : scan B1 (legacy random).

#### B4e. Float conventions
> Checklist : §R5. Preuve : lecture diff B2.

#### B4f. Anti-patterns Python / numpy / pandas
> Checklist : §R6. Preuve : scan B1 (mutable defaults, open) + lecture diff B2.

### B5. Qualité du code
> Checklist : `.github/shared/coding_rules.md` §R7. Preuve : scan B1 + lecture diff B2.

Compléments spécifiques PR :
- [ ] `.gitignore` couvre les artefacts générés.
- [ ] Pas de fichiers générés ou temporaires inclus dans la PR.

### B5-bis. Bonnes pratiques métier (concepts de domaine)
> Checklist : `.github/shared/coding_rules.md` §R9. Preuve : lecture diff B2.

### B6. Cohérence avec les specs

- [ ] Le code est conforme à la spec v1.0 (sections référencées dans la tâche).
- [ ] Le code est conforme au plan d'implémentation.
- [ ] Pas d'exigence inventée hors des documents source.
- [ ] **Formules doc vs code** : si la tâche ou un critère d'acceptation contient une formule mathématique (intervalles, bornes, indices), vérifier qu'elle correspond **exactement** à l'implémentation et aux tests. Un off-by-one entre la doc et le code est **bloquant** (ambiguïté potentiellement masquant un bug).

### B7. Cohérence intermodule
> Checklist : `.github/shared/coding_rules.md` §R8. Preuve : `grep_search` des signatures + lecture diff B2.

## Format du rapport de revue

```markdown
# Revue PR — [WS-X] #NNN — <titre de la tâche>

Branche : `task/NNN-short-slug`
Tâche : `docs/tasks/<milestone>/NNN__slug.md`
Date : YYYY-MM-DD

## Verdict global : ✅ APPROVE | ⚠️ REQUEST CHANGES | ❌ REJECT

## Résumé
[2-3 phrases résumant les changements et le verdict]

---

## Phase A — Compliance

### Structure branche & commits
| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche | ✅/❌ | `git branch` output |
| Commit RED présent | ✅/❌ | hash + `git show --stat` |
| Commit GREEN présent | ✅/❌ | hash + `git show --stat` |
| Pas de commits parasites | ✅/❌ | `git log --oneline` output |

### Tâche
| Critère | Verdict |
|---|---|
| Statut DONE | ✅/❌ |
| Critères d'acceptation cochés | ✅/❌ (N/N) |
| Checklist cochée | ✅/❌ (N/N) |

### CI
| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **NNN passed**, 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** / N erreurs |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| Fallbacks silencieux | `grep 'or []\|or {}...'` | 0 occurrences / N matches (détail ci-dessous) |
| Except trop large | `grep 'except:$...'` | 0 occurrences |
| Print résiduel | `grep 'print('` | 0 occurrences |
| Shift négatif | `grep '.shift(-'` | 0 occurrences |
| Legacy random API | `grep 'np.random.seed...'` | 0 occurrences |
| TODO/FIXME orphelins | `grep 'TODO\|FIXME...'` | 0 occurrences |
| Chemins hardcodés | `grep '/tmp\|C:\\'` | 0 occurrences |
| Imports absolus __init__ | `grep 'from ai_trading\.'` | 0 occurrences |
| Registration manuelle tests | `grep 'register_model...'` | 0 occurrences / à analyser |
| Mutable defaults | `grep 'def.*=[]\|def.*={}'` | 0 occurrences |

> Chaque ligne DOIT montrer le résultat réel de la commande.

### Annotations par fichier (B2)

#### `ai_trading/<module>.py`

- **L<N>** `<extrait de code>` : <observation>.
  Sévérité : BLOQUANT / WARNING / MINEUR / RAS
  Suggestion : <correction proposée>

- **L<N>** `<extrait de code>` : <observation>.
  ...

> Si aucune observation : « RAS après lecture complète du diff (N lignes). »

#### `tests/test_<module>.py`

- **L<N>** `<extrait de code>` : <observation>.
  ...

### Tests (B3)
| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères | ✅/❌ | Mapping critère → test |
| Cas nominaux + erreurs + bords | ✅/❌ | Liste des classes de test |
| Boundary fuzzing | ✅/❌ | Params testés: N=0, N=1, ... |
| Déterministes | ✅/❌ | Seeds listées |
| Portabilité chemins | ✅/❌ | Scan B1: 0 `/tmp` |
| Tests registre réalistes | ✅/❌ ou N/A | Scan B1 + vérification reload |
| Contrat ABC complet | ✅/❌ ou N/A | Variantes testées |

### Code — Règles non négociables (B4)
| Règle | Verdict | Preuve |
|---|---|---|
| Strict code (no fallbacks) | ✅/❌ | Scan B1 + lecture diff B2 |
| Defensive indexing | ✅/❌ | Expressions vérifiées |
| Config-driven | ✅/❌ | |
| Anti-fuite | ✅/❌ | Scan B1 (.shift) + lecture |
| Reproductibilité | ✅/❌ | Scan B1 (legacy random) |
| Float conventions | ✅/❌ | |
| Anti-patterns Python | ✅/❌ | Scan B1 + lecture B2 |

### Qualité du code (B5)
| Critère | Verdict | Preuve |
|---|---|---|
| Nommage et style | ✅/❌ | |
| Pas de code mort/debug | ✅/❌ | Scan B1 |
| Imports propres / relatifs | ✅/❌ | Scan B1 |
| DRY | ✅/❌ | |

### Conformité spec v1.0 (B6)
| Critère | Verdict |
|---|---|
| Spécification | ✅/❌ |
| Plan d'implémentation | ✅/❌ |
| Formules doc vs code | ✅/❌ |

### Cohérence intermodule (B7)
| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅/❌ | |
| Noms de colonnes DataFrame | ✅/❌ | |
| Clés de configuration | ✅/❌ | |
| Registres et conventions partagées | ✅/❌ | |
| Structures de données partagées | ✅/❌ | |
| Conventions numériques | ✅/❌ | |
| Imports croisés | ✅/❌ | |

### Bonnes pratiques métier (B5-bis)
| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅/❌ | |
| Nommage métier cohérent | ✅/❌ | |
| Séparation des responsabilités métier | ✅/❌ | |
| Invariants de domaine | ✅/❌ | |
| Cohérence des unités/échelles | ✅/❌ | |
| Patterns de calcul financier | ✅/❌ | |

---

## Remarques mineures
> **Toutes les remarques, même mineures ou cosmétiques, doivent figurer ici.**
> Elles ne bloquent pas le merge mais doivent être corrigées à terme.

- [Remarque mineure 1]
- [Remarque mineure 2]

## Remarques et blocages
- [Blocage 1]
- [Blocage 2]

## Actions requises (si REQUEST CHANGES ou REJECT)
1. [Action corrective 1]
2. [Action corrective 2]
```

## Règles de verdict

| Verdict | Condition |
|---|---|
| **✅ APPROVE** | Tous les critères non négociables sont satisfaits. Remarques mineures OK post-merge. |
| **⚠️ REQUEST CHANGES** | Au moins un critère non négociable partiellement violé ou tests manquants. |
| **❌ REJECT** | Violation grave : fuite de données, ghost completion, strict code violé, tests RED, ou absence de TDD. |

## Principes de revue

1. **Diff-centric** : le cœur de la revue est la lecture du diff ligne par ligne (B2). Ne jamais cocher un item sans avoir lu le code correspondant dans le diff.
2. **Prouvé par exécution** : chaque `✅` dans le rapport est accompagné d'une preuve (output grep, résultat d'exécution, numéro de ligne). Un `✅` sans preuve est un `❌`.
3. **Scan avant checklist** : toujours exécuter le scan automatisé (B1) AVANT d'évaluer les items du checklist. Le scan grep est la première ligne de défense — pas un complément optionnel.
4. **Exhaustif** : passer en revue tous les fichiers modifiés, annoter chaque fichier source dans le rapport.
5. **Constructif** : chaque blocage accompagné d'une action corrective claire avec le fichier et la ligne concernés.
6. **Proportionné mais exhaustif** : ne pas **bloquer** pour du cosmétique, mais **toujours signaler** les points mineurs dans la section « Remarques mineures ». Aucune observation ne doit être omise.
7. **Adversarial** : ne pas se limiter aux tests existants. Pour chaque fonction modifiée, imaginer 2-3 inputs extrêmes (param > taille données, param = 0, tableaux vides, type inattendu) et vérifier que le code ou les tests les couvrent. Si non → bloquant.
8. **Domain-aware** : vérifier que l'implémentation des concepts métier (indicateurs techniques, mécaniques de trading, calculs financiers) respecte les bonnes pratiques du domaine. Une erreur de concept métier est **bloquante**.
9. **Python-aware** : appliquer la grille des anti-patterns Python/numpy/pandas (B4f) à chaque fichier. Les bugs de type safety, path handling et mutable defaults sont des sources fréquentes de régressions silencieuses.
