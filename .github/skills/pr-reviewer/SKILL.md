---
name: pr-reviewer
description: Revue systématique de Pull Request pour le projet AI Trading Pipeline. Vérifie conformité TDD, anti-fuite, strict code, config-driven, conventions de branche et qualité globale. À utiliser quand l'utilisateur demande « review la PR », « revue de la branche task/NNN-* », « vérifie avant merge ».
argument-hint: "[branche: task/NNN-short-slug] ou [PR number]"
---

# Agent Skill — PR Reviewer (AI Trading Pipeline)

## Objectif
Effectuer une revue systématique et exigeante d'une Pull Request (ou d'une branche `task/NNN-*`) avant merge vers `Max6000i1`, en vérifiant la conformité avec les règles du projet AI Trading Pipeline.

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
- [ ] Les critères cochés correspondent à des preuves vérifiables (code, tests, artefacts).

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

```bash
# Fichiers modifiés (source + tests)
CHANGED=$(git diff --name-only Max6000i1...HEAD | grep '\.py$')
CHANGED_SRC=$(echo "$CHANGED" | grep '^ai_trading/')
CHANGED_TEST=$(echo "$CHANGED" | grep '^tests/')

# --- Anti-patterns code source ---
# Fallbacks silencieux
grep -n ' or \[\]\| or {}\| or ""\| or 0\b\| if .* else ' $CHANGED_SRC

# Except trop large
grep -n 'except:$\|except Exception:' $CHANGED_SRC

# Print résiduel
grep -n 'print(' $CHANGED_SRC

# Shift négatif (look-ahead)
grep -n '\.shift(-' $CHANGED_SRC

# Legacy random API
grep -n 'np\.random\.seed\|np\.random\.randn\|np\.random\.RandomState\|random\.seed' $CHANGED

# TODO/FIXME orphelins
grep -n 'TODO\|FIXME\|HACK\|XXX' $CHANGED

# --- Anti-patterns tests ---
# Chemins hardcodés OS-spécifiques
grep -n '/tmp\|/var/tmp\|C:\\' $CHANGED_TEST

# Imports absolus dans __init__.py
grep -n 'from ai_trading\.' $(echo "$CHANGED" | grep '__init__.py')

# Tests de registre : registration manuelle au lieu de importlib.reload
grep -n 'register_model\|register_feature' $CHANGED_TEST

# Mutable default arguments
grep -n 'def .*=\[\]\|def .*={}' $CHANGED

# open() sans context manager
grep -n '\.read_text\|open(' $CHANGED_SRC
```

**Pour chaque match** : analyser en contexte (lire les lignes autour) et classer :
- **BLOQUANT** si c'est un vrai problème
- **WARNING** si risque potentiel
- **Faux positif** si le pattern est utilisé correctement (noter dans le rapport)

**Si aucun match** pour un pattern → noter « 0 occurrences (grep exécuté) » dans le rapport comme preuve d'exécution.

### B2. Lecture du diff ligne par ligne (OBLIGATOIRE)

Pour **CHAQUE fichier source modifié** (pas les docs/tâches), lire le diff complet :

```bash
git diff Max6000i1...HEAD -- <fichier>
```

Pour chaque hunk de diff, appliquer cette grille de lecture :

1. **Type safety** : les valeurs lues depuis l'extérieur (JSON, YAML, fichiers, args) sont-elles validées en type ? Une valeur lue depuis un `json.loads()` ou `yaml.safe_load()` sans vérification de type est un **WARNING**.
2. **Edge cases** : que se passe-t-il si l'entrée est `None`, vide, du mauvais type, très grande ?
3. **Path handling** : si un paramètre `path` est manipulé, supporte-t-il tous les cas documentés par le contrat (directory ET fichier) ? Crée-t-il les parents si nécessaire ?
4. **Return contract** : le type de retour est-il garanti en toute circonstance (shape, dtype, clés dict) ?
5. **Resource cleanup** : fichiers ouverts, connections — sont-ils fermés en cas d'erreur ?
6. **Cohérence doc/code** : la docstring correspond-elle au comportement réel ?

Documenter **chaque observation** dans la section « Annotations par fichier » du rapport. Si un fichier n'a aucune observation, noter « RAS après lecture complète du diff (N lignes) ».

### B3. Vérifier les tests

- [ ] Les tests dans `tests/` suivent la convention du plan (`test_config.py`, `test_features.py`, `test_splitter.py`, etc.). L'ID tâche `#NNN` dans les docstrings, pas les noms de fichiers.
- [ ] Chaque critère d'acceptation est couvert par au moins un test.
- [ ] Les tests couvrent : cas nominaux, cas d'erreur, cas de bords.
- [ ] **Boundary fuzzing mental** : pour chaque paramètre numérique d'entrée (`n`, `L`, `H`, taille, etc.), vérifier qu'il existe un test pour chacune de ces situations : `param = 0`, `param = 1`, `param > n` (dépassement), `param = n` (limite exacte). Si une combinaison critique manque, la signaler comme bloquante.
- [ ] Pas de test désactivé (`@pytest.mark.skip`, `xfail`) sans justification explicite.
- [ ] Les tests sont déterministes (seeds fixées si aléatoire).
- [ ] Les tests utilisent des données synthétiques (pas de dépendance réseau).
- [ ] **Portabilité des chemins** (prouvé par scan B1) : pas de chemin OS-spécifique hardcodé (`/tmp/...`). Tous les chemins temporaires utilisent la fixture pytest `tmp_path`.
- [ ] **Tests de registre réalistes** (prouvé par scan B1) : si un test vérifie l'enregistrement automatique dans un registre via décorateur, il doit utiliser `importlib.reload(module)` après nettoyage du registre — pas un appel manuel à `register_xxx()`. Comparer avec `mod.ClassName` (module rechargé).
- [ ] **Contrat ABC complètement testé** : si une méthode abstraite documente qu'elle accepte plusieurs types d'entrée (ex : `path` = directory ou fichier), les tests couvrent chaque variante.

### B4. Audit du code — Règles non négociables

#### B4a. Strict code (no fallbacks)
- [ ] Aucun fallback silencieux (prouvé par scan B1).
- [ ] Aucun `except` trop large qui continue l'exécution (prouvé par scan B1).
- [ ] Aucun paramètre optionnel avec default implicite masquant une erreur.
- [ ] Validation explicite aux frontières (entrées utilisateur, données externes).
- [ ] Erreur explicite (`raise`) en cas d'entrée invalide ou manquante.

#### B4a-bis. Revue défensive indexing / slicing
- [ ] Pour tout `array[expr:]` ou `array[:expr]` : vérifier manuellement le comportement quand `expr` est **négatif**, **zéro**, ou **> len(array)**. En Python/NumPy, `array[-k:]` ne fait **pas** `array[0:]` — c'est un piège silencieux.
- [ ] Pour tout `range(a, b)` ou `mask[lo : hi + 1]` : vérifier que `lo` et `hi` sont clampés (`max(0, ...)`, `min(n-1, ...)`) pour toutes les valeurs extrêmes des paramètres d'entrée.
- [ ] Si un paramètre numérique peut dépasser la taille des données (ex. `H > N`), vérifier que le code produit un résultat correct (tout False, raise, etc.) et non un comportement silencieusement faux.

#### B4b. Config-driven (pas de hardcoding)
- [ ] Tout paramètre modifiable est lu depuis `configs/default.yaml` via l'objet config Pydantic v2.
- [ ] Aucune valeur magique ou constante significative hardcodée dans le code.
- [ ] Les formules respectent celles de la spec (§6 features, §5 labels, §8 splits, §12 backtest).
- [ ] Tout choix implementation-defined est explicite dans la config YAML.

#### B4c. Anti-fuite (look-ahead)
- [ ] Aucun accès à des données futures (point-in-time respecté).
- [ ] Embargo respecté : `embargo_bars >= label.horizon_H_bars` (§8.2).
- [ ] Pas de `.shift(-n)` (prouvé par scan B1) ou équivalent sans justification temporelle correcte.
- [ ] Scaler fit sur train uniquement (pas de données val/test dans fit).
- [ ] Splits walk-forward séquentiels (train < val < test).
- [ ] θ calibré uniquement sur val, jamais sur test.
- [ ] Features causales : backward-looking uniquement.

#### B4d. Reproductibilité
- [ ] Seeds fixées et tracées via `utils/seed.py`.
- [ ] Pas de legacy random API (prouvé par scan B1).
- [ ] Hashes SHA-256 (données, config) si applicable.
- [ ] Résultats reproductibles sur relance (test de déterminisme si pertinent).

#### B4e. Float conventions
- [ ] Float32 pour tenseurs X_seq et y (mémoire).
- [ ] Float64 pour calculs de métriques (précision).

#### B4f. Anti-patterns Python / numpy / pandas

Vérifier l'absence de ces anti-patterns courants dans les fichiers modifiés :

- [ ] **Mutable default arguments** : pas de `def f(x=[])` ni `def f(x={})` (prouvé par scan B1).
- [ ] **Données désérialisées non validées** : après `json.loads()`, `yaml.safe_load()` ou lecture de fichier, les valeurs sont validées en type (`isinstance`) avant utilisation. Un `data["key"]` utilisé directement sans vérification de type est un **WARNING**.
- [ ] **Path incomplet** : si un paramètre `path` est documenté comme acceptant directory OU fichier, l'implémentation gère les deux cas. Un `path.write_text()` sans vérifier `path.is_dir()` est un bug potentiel.
- [ ] **open() sans context manager** : tout `open()` utilise `with`. Les raccourcis `Path.read_text()` / `Path.write_text()` sont acceptés.
- [ ] **Comparaison float avec ==** : pas de `==` sur des floats numpy. Utiliser `np.isclose`, `np.testing.assert_allclose`, ou `pytest.approx`.
- [ ] **`.values` perdant l'index** : pas de `.values` implicite sur un DataFrame/Series pandas sans raison documentée.
- [ ] **f-string ou format** : pas de `str + str` dans les messages d'erreur — utiliser f-string.
- [ ] **Side-effects dans les paramètres par défaut** : pas de `datetime.now()`, `time.time()`, ou appel de fonction dans les valeurs par défaut de paramètres.

### B5. Qualité du code

- [ ] Nommage snake_case cohérent.
- [ ] Pas de code mort, commenté ou TODO orphelin (prouvé par scan B1).
- [ ] Pas de `print()` de debug restant (prouvé par scan B1).
- [ ] Imports propres (pas d'imports inutilisés, pas d'imports `*`).
- [ ] **Imports intra-package relatifs** (prouvé par scan B1) : les `__init__.py` qui importent des sous-modules pour side-effect (peuplement de registres) doivent utiliser des imports relatifs (`from . import module`), jamais des imports absolus auto-référençants (`from ai_trading.package import module`).
- [ ] Pas de fichiers générés ou temporaires inclus dans la PR.
- [ ] `.gitignore` couvre les artefacts générés.
- [ ] **DRY — pas de duplication de constantes/mappings** entre modules du même package. Si un dict, une constante ou un mapping est identique dans 2+ fichiers, exiger l'extraction vers un module partagé. Classer comme **bloquant** (risque de drift silencieux).

### B5-bis. Bonnes pratiques métier (concepts de domaine)

- [ ] **Exactitude des concepts financiers** : les indicateurs techniques (RSI, EMA, volatilité, log-returns, etc.) sont implémentés conformément à leur définition canonique (formules standard de référence). Toute déviation par rapport à la formule standard doit être justifiée et documentée.
- [ ] **Nommage métier cohérent** : les noms de variables, fonctions et classes reflètent fidèlement les concepts financiers qu'ils modélisent (ex. `log_return` et non `lr`, `equity_curve` et non `curve`). Pas d'abréviation ambiguë.
- [ ] **Séparation des responsabilités métier** : chaque module encapsule un concept métier unique (ex. features ≠ labels ≠ backtest). Pas de mélange de responsabilités de domaine dans un même module.
- [ ] **Invariants de domaine respectés** : les invariants propres au domaine financier sont vérifiés explicitement dans le code (ex. prix > 0, volume >= 0, equity curve monotone sur un trade, etc.).
- [ ] **Cohérence des unités et échelles** : les grandeurs sont manipulées avec des unités cohérentes (returns en log vs arithmétique, prix en quote currency, timestamps en UTC). Pas de mélange implicite d'échelles.
- [ ] **Patterns de calcul financier** : utilisation des bonnes pratiques pour les calculs numériques financiers (ex. `np.log` au lieu de `math.log` sur des Series, rolling windows via pandas natif, éviter les boucles Python sur les séries temporelles).

### B6. Cohérence avec les specs

- [ ] Le code est conforme à la spec v1.0 (sections référencées dans la tâche).
- [ ] Le code est conforme au plan d'implémentation.
- [ ] Pas d'exigence inventée hors des documents source.
- [ ] **Formules doc vs code** : si la tâche ou un critère d'acceptation contient une formule mathématique (intervalles, bornes, indices), vérifier qu'elle correspond **exactement** à l'implémentation et aux tests. Un off-by-one entre la doc et le code est **bloquant** (ambiguïté potentiellement masquant un bug).

### B7. Cohérence intermodule

Vérifier que les changements de la PR ne créent pas de divergence avec les modules existants.

- [ ] **Signatures et types de retour** : les fonctions/classes modifiées ou créées respectent les signatures attendues par les modules appelants existants (mêmes noms de paramètres, mêmes types, même ordre). Si une signature existante est modifiée, vérifier tous les appels dans le codebase (`grep_search`).
- [ ] **Noms de colonnes DataFrame** : les colonnes produites ou consommées (ex : `close`, `logret_1`, `vol_24`) sont identiques à celles utilisées dans les modules amont/aval. Pas de renommage silencieux ni de divergence de convention.
- [ ] **Clés de configuration** : les clés lues depuis `configs/default.yaml` correspondent aux noms définis dans le modèle Pydantic (`config.py`). Pas de clé orpheline (présente en YAML mais pas lue) ni manquante (lue mais absente du YAML).
- [ ] **Registres et conventions partagées** : si le module s'inscrit dans un registre (ex : `FEATURE_REGISTRY`), vérifier que l'interface implémentée (méthodes, attributs comme `name`, `min_periods`) est cohérente avec les autres entrées du registre et avec le code qui itère dessus.
- [ ] **Structures de données partagées** : les dataclasses, TypedDict ou NamedTuple partagées entre modules sont utilisées de manière identique (mêmes champs, mêmes types). Pas de champ ajouté dans un module sans mise à jour des consommateurs.
- [ ] **Conventions numériques** : les dtypes (float32 vs float64), les conventions NaN (NaN en tête vs valeurs par défaut), et les index (DatetimeIndex, RangeIndex) sont cohérents avec les modules voisins.
- [ ] **Imports croisés** : si le nouveau code importe des symboles d'autres modules du projet, vérifier que ces symboles existent bien dans la branche `Max6000i1` (pas de dépendance sur du code non encore mergé).

Une incohérence intermodule est **bloquante** — elle provoque des bugs silencieux à l'intégration.

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
