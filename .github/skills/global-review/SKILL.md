---
name: global-review
description: Revue de code globale d'une branche complète du projet AI Trading Pipeline. Audite la cohérence inter-modules, la conformité spec, les conventions, la qualité et produit un rapport structuré avec recommandations classées par sévérité. À utiliser quand l'utilisateur demande « revue globale », « audit du code », « revue de la branche ».
argument-hint: "[branche: Max6000i1 ou nom de branche] [scope: all|ai_trading|tests|features|data]"
---

# Agent Skill — Global Review (AI Trading Pipeline)

## Objectif
Effectuer un audit de code complet et transversal d'une branche (pas limité aux derniers changements), en évaluant la **cohérence globale** entre tous les modules, la conformité aux specs, les conventions du projet et la qualité du code. Produire un rapport structuré avec des recommandations classées par sévérité.

## Différence avec `pr-reviewer`

| Aspect | `pr-reviewer` | `global-review` |
|---|---|---|
| **Périmètre** | Fichiers modifiés d'une PR | Tout le code de la branche |
| **Focus** | Conformité TDD, commits, tâche | Cohérence inter-modules, architecture |
| **Déclencheur** | « review la PR #NNN » | « revue globale », « audit du code » |
| **Sortie** | Verdict APPROVE/REJECT par PR | Rapport avec recommandations classées |
| **Fréquence** | À chaque PR | Périodique (avant gate, milestone, ou à la demande) |

## Contexte repo

- **Spécification** : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (v1.0 + addendum v1.1 + v1.2)
- **Plan** : `docs/plan/implementation.md` (WS-1..WS-12, M1..M5)
- **Tâches** : `docs/tasks/<milestone>/NNN__slug.md`
- **Code source** : `ai_trading/` (package Python principal)
- **Tests** : `tests/` (pytest)
- **Configs** : `configs/default.yaml`
- **Linter** : ruff (`line-length = 100`, `target-version = "py311"`)
- **Request changes précédentes** : `docs/request_changes/NNNN_slug.md`
- **Langue** : anglais pour code/tests, français pour docs/tâches

## Rôle de l'agent

Tu dois :
- auditer **tous les fichiers source** (`ai_trading/`) et **tous les tests** (`tests/`) de la branche ;
- vérifier la cohérence **inter-modules** (interfaces, conventions de nommage, contrats) ;
- vérifier la conformité globale avec la spécification et le plan ;
- exécuter `pytest` et `ruff check` pour confirmer le statut de la suite ;
- produire un **rapport structuré** avec un verdict global et des recommandations classées ;
- écrire le rapport dans `docs/request_changes/NNNN_slug.md` (prochain numéro séquentiel).

## Workflow de revue globale

### 1. Établir le périmètre

- Identifier la branche cible (par défaut : branche courante).
- Lister tous les modules source :
  ```bash
  find ai_trading/ -name "*.py" -not -path "*__pycache__*"
  ```
- Lister tous les fichiers de tests :
  ```bash
  find tests/ -name "*.py" -not -path "*__pycache__*"
  ```
- Identifier les tâches DONE vs IN_PROGRESS vs TODO.

### 2. Exécuter la suite de validation

Exécuter **obligatoirement** :
```bash
pytest tests/ -v --tb=short
ruff check ai_trading/ tests/
```

Résultats attendus : **tous tests GREEN**, **ruff clean**. Si des échecs existent, les documenter comme BLOQUANT.

### 3. Audit des interfaces inter-modules

C'est le cœur de la revue globale. Pour chaque paire de modules qui interagissent :

#### 3a. Contrat de données
- [ ] Les colonnes attendues par le consommateur correspondent à celles produites par le producteur.
- [ ] Les types (datetime tz-aware/naive, float32/64, int) sont cohérents aux frontières.
- [ ] Les conventions de nommage (colonnes DataFrame, clés dict) sont uniformes.

#### 3b. Contrat de paramètres
- [ ] Les clés de config lues par chaque module existent dans `configs/default.yaml`.
- [ ] Les noms de paramètres sont cohérents entre config, code et spec.
- [ ] Aucun paramètre config n'est trompeur (expose un réglage sans effet réel).

#### 3c. Contrat de registre (features)
- [ ] Toutes les features listées dans `feature_list` config sont enregistrées dans `FEATURE_REGISTRY`.
- [ ] Les `required_params` de chaque feature correspondent à des clés existantes dans `features.params`.
- [ ] `min_periods` est cohérent avec le comportement réel de `compute()`.

#### 3d. Chaîne d'appel pipeline
- [ ] Ingestion → QA → Features → Dataset → Splits → Scaling → Training : les interfaces sont compatibles bout-en-bout.
- [ ] Aucun module ne fait d'hypothèse implicite sur le format d'un autre sans validation.

### 4. Audit des règles non négociables (transversal)

#### 4a. Strict code (no fallbacks) — sur TOUT le code source
- [ ] Rechercher `or default`, `value if value else default`, `except:` (trop large) dans tout `ai_trading/`.
- [ ] Vérifier que chaque module valide ses entrées explicitement avec `raise`.
- [ ] Aucun paramètre optionnel avec default implicite masquant une erreur.

#### 4b. Config-driven — sur TOUT le code source
- [ ] Rechercher les constantes magiques hardcodées qui devraient être en config.
- [ ] Vérifier que les constantes légitimement fixes (spec §6.5 : fenêtres 24/72) sont documentées comme telles.
- [ ] Aucun paramètre config trompeur (tunable en apparence, sans effet réel).

#### 4c. Anti-fuite — sur TOUT le code source
- [ ] Rechercher `.shift(-n)` (accès futur).
- [ ] Vérifier que chaque feature est backward-looking uniquement.
- [ ] Vérifier l'embargo, les splits, le scaler (si implémentés).

#### 4d. Reproductibilité
- [ ] Rechercher l'usage de l'API random legacy (`np.random.seed()`, `np.random.randn()`, `np.random.RandomState()`).
- [ ] Vérifier l'usage exclusif de `np.random.default_rng(seed)`.
- [ ] Seeds fixées et tracées.

### 5. Audit de la qualité du code (transversal)

#### 5a. DRY — Duplication inter-modules
- [ ] Constantes/mappings dupliqués entre modules source.
- [ ] Helpers de test dupliqués entre fichiers de tests.
- [ ] Fixtures identiques dans plusieurs fichiers (à extraire dans `conftest.py`).

#### 5b. Conventions
- [ ] `snake_case` cohérent partout.
- [ ] Aucun `print()` résiduel (utiliser `logging`).
- [ ] Aucun `TODO`, `FIXME`, `HACK`, `XXX` orphelin.
- [ ] Imports propres (pas d'imports inutilisés, pas d'imports `*`).
- [ ] Ordre des imports ruff/isort (stdlib → third-party → local).

#### 5c. Patterns de test
- [ ] Convention de construction OHLCV cohérente entre fichiers de tests.
- [ ] Pattern d'isolation du registre (fixture `_clean_registry`) uniforme.
- [ ] `Series.name` convention uniforme entre features.
- [ ] Seeds déterministes.
- [ ] Données synthétiques uniquement (pas de réseau).

### 6. Conformité avec la spécification

- [ ] Formules implémentées vs spec (§5 labels, §6 features, §8 splits, §12 backtest).
- [ ] Colonnes canoniques (§4.1) respectées.
- [ ] QA checks (§4.2) conformes.
- [ ] Missing candles policy (§4.3) conforme.
- [ ] Invariants de domaine financier vérifiés (prix > 0, volume >= 0, etc.).

### 7. Bonnes pratiques métier

- [ ] Exactitude des concepts financiers (RSI Wilder, EMA SMA-init, ddof=0, etc.).
- [ ] Nommage métier fidèle (pas d'abréviation ambiguë).
- [ ] Séparation des responsabilités métier.
- [ ] Cohérence des unités et échelles (log vs arithmétique, UTC).
- [ ] Patterns de calcul financier idiomatiques (numpy/pandas vectorisé, pas de boucles Python sur séries temporelles sauf nécessité).

### 8. Produire le rapport

Écrire le rapport dans `docs/request_changes/NNNN_slug.md` (prochain numéro séquentiel). Utiliser le format ci-dessous.

## Niveaux de sévérité

| Niveau | Préfixe | Définition | Impact |
|---|---|---|---|
| **BLOQUANT** | `B-N` | Bug actif, interface cassée, violation de règle non négociable, données corrompues silencieusement. | Doit être corrigé avant tout merge ou gate. |
| **WARNING** | `W-N` | Risque réel mais non déclenché en l'état (config par défaut OK, edge case non couvert), violation de convention projet. | Devrait être corrigé avant le prochain gate/milestone. |
| **MINEUR** | `M-N` | Amélioration de qualité, DRY, cohérence cosmétique, documentation. Ne provoque pas de bug. | À corriger à terme, ne bloque pas. |

## Format du rapport

### Convention de nommage

Fichiers : `NNNN_slug.md` dans `docs/request_changes/`

- `NNNN` : numéro séquentiel sur 4 chiffres (0001, 0002, ...)
- `_` : séparateur fixe
- `slug` : minuscule, underscores, orienté contenu

Exemples :
- `0001_revue_globale_max6000i1.md`
- `0002_revue_globale_post_rc0001.md`
- `0003_audit_pre_gate_m2.md`

### Valeurs de statut

- `TODO` — rapport émis, corrections non commencées
- `IN_PROGRESS` — corrections en cours (au moins un item traité)
- `DONE` — tous les items traités (résolus ou explicitement différés)

### Template

```markdown
# Request Changes — <titre de la revue>

Statut : TODO
Ordre : NNNN

**Date** : YYYY-MM-DD
**Périmètre** : <description du périmètre audité>
**Résultat** : NNN tests GREEN/RED, ruff clean/N erreurs
**Verdict** : ✅ CLEAN | ⚠️ REQUEST CHANGES | ❌ BLOCAGES CRITIQUES

---

## Résultats d'exécution

| Check | Résultat |
|---|---|
| `pytest tests/` | **NNN passed** / X failed |
| `ruff check ai_trading/ tests/` | **All checks passed** / N erreurs |
| `print()` résiduel | Aucun / N occurrences |
| `TODO`/`FIXME` orphelin | Aucun / N occurrences |
| `.shift(-n)` (look-ahead) | Aucun / N occurrences |
| Broad `except` | Aucun / N occurrences |
| Legacy random API | Aucun / N occurrences |

---

## BLOQUANTS (N)

### B-1. <Titre descriptif>

**Fichiers** : `chemin/fichier.py` (LNNN)
**Sévérité** : BLOQUANT — <impact>.

<Description du problème avec extraits de code si pertinent.>

**Action** :
1. <Action corrective spécifique>
2. <Action corrective spécifique>

---

## WARNINGS (N)

### W-1. <Titre descriptif>

**Fichiers** : `chemin/fichier.py` (LNNN)
**Sévérité** : WARNING — <risque>.

<Description.>

**Action** : <Action corrective>

---

## MINEURS (N)

### M-1. <Titre descriptif>

**Fichiers** : `chemin/fichier.py`
**Sévérité** : MINEUR — <amélioration>.

<Description.>

**Action** : <Action corrective>

---

## Conformité formules métier

| Feature/Module | Section spec | Verdict |
|---|---|---|
| `logret_k` | §6.2 | ✅ Correct / ❌ Incorrect |
| ... | ... | ... |

---

## Anti-fuite

| Module | Check | Verdict |
|---|---|---|
| `log_returns.py` | backward-looking only | ✅ / ❌ |
| ... | ... | ... |

---

## Résumé des actions

| # | Sévérité | Action | Fichier(s) |
|---|---|---|---|
| B-1 | BLOQUANT | <action résumée> | `fichier.py` |
| W-1 | WARNING | <action résumée> | `fichier.py` |
| M-1 | MINEUR | <action résumée> | `fichier.py` |
```

## Règles de verdict

| Verdict | Condition |
|---|---|
| **✅ CLEAN** | Zéro bloquant, zéro warning. Mineurs seulement. |
| **⚠️ REQUEST CHANGES** | Au moins un bloquant ou warning. Corrections nécessaires. |
| **❌ BLOCAGES CRITIQUES** | Bloquants impactant l'intégrité des données ou la reproductibilité. |

## Principes de revue

1. **Exhaustif** : auditer tous les modules source et tous les fichiers de tests, pas seulement les changements récents.
2. **Inter-modules** : la valeur ajoutée de la revue globale est la détection de problèmes aux **interfaces** entre modules que les PR reviews individuelles ne voient pas.
3. **Factuel** : chaque constat basé sur des preuves concrètes (fichier, ligne, exécution). Pas d'hypothèses.
4. **Adversarial** : pour chaque interface entre modules, imaginer des scénarios de rupture (type mismatch, colonne renommée, config modifiée, edge case).
5. **Constructif** : chaque constat accompagné d'une action corrective claire et d'un niveau de sévérité.
6. **Proportionné mais exhaustif** : signaler **tout**, y compris les mineurs. Ne rien omettre sous prétexte que c'est cosmétique. Classer correctement par sévérité.
7. **Domain-aware** : vérifier la justesse des concepts financiers, pas seulement la syntaxe.
8. **Traçable** : le rapport est versionné dans `docs/request_changes/` et référençable depuis les tâches de correction.

## Quand utiliser ce skill

- Avant un **gate** (G-Features, G-Split, G-Backtest, etc.) pour détecter les incohérences inter-modules.
- Avant un **milestone** (M1, M2, etc.) comme audit de qualité globale.
- Après un **batch de merges** de PR pour vérifier que l'intégration est cohérente.
- À la **demande** de l'utilisateur (« revue globale », « audit du code », « vérifie la cohérence »).
- Après une **longue période sans revue** pour rattraper la dette technique.

## Interaction avec les autres skills

| Skill | Relation |
|---|---|
| `pr-reviewer` | La revue globale **complète** la revue PR en détectant les problèmes inter-modules invisibles PR par PR. |
| `gate-validator` | La revue globale est un **prérequis informel** avant le gate. Les constats WARNING+ doivent être résolus avant de passer un gate. |
| `implementing-task` | Les constats de la revue globale peuvent générer des **tâches correctives** via `task-creator`. |
| `task-creator` | Les résultats de la revue globale alimentent la création de tâches de correction. |

```
