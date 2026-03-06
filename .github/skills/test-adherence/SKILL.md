---
name: test-adherence
description: Vérifie que les tests adhèrent exactement à la spécification. Pour chaque module testé, croise les critères d'acceptation des tâches, les formules de la spec et le code source pour détecter les écarts, oublis et assertions incorrectes. À utiliser quand l'utilisateur demande « vérifie l'adhérence des tests », « les tests collent à la spec ? », « audit tests vs spec ».
argument-hint: "[scope: all|module_name|WS-X] [severity: strict|normal]"
---

# Agent Skill — Test Adherence (AI Trading Pipeline)

## Objectif

Auditer systématiquement l'adhérence des tests (`tests/`) à la spécification (`docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md`), aux tâches (`docs/tasks/<milestone>/NNN__slug.md`) et au code source (`ai_trading/`). Détecter :

1. **Tests manquants** : critères d'acceptation sans test correspondant.
2. **Tests incorrects** : assertions qui ne valident pas la formule/le comportement de la spec.
3. **Tests divergents** : tests qui valident un comportement différent de la spec (off-by-one, formule approchée, paramètre hardcodé vs config).
4. **Tests orphelins** : tests qui ne correspondent à aucun critère d'acceptation ni section de spec.

## Contexte repo

- **Spécification** : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (v1.0 + addendum v1.1 + v1.2)
- **Plan** : `docs/plan/implementation.md` (WS-1..WS-12, M1..M5)
- **Tâches** : `docs/tasks/<milestone>/NNN__slug.md`
- **Code source** : `ai_trading/`
- **Tests** : `tests/` (pytest)
- **Configs** : `configs/default.yaml`
- **Linter** : ruff (`line-length = 100`, `target-version = "py311"`)

## Rôle de l'agent

Tu dois :
- croiser **chaque section de spec** pertinente avec les tests existants ;
- vérifier que les **formules mathématiques** de la spec sont exactement reproduites dans les tests de validation numérique ;
- vérifier que les **critères d'acceptation** des tâches DONE sont couverts par au moins un test ;
- identifier les écarts, oublis et erreurs dans les assertions ;
- produire un **rapport structuré** avec traçabilité spec → test → code.

## Workflow

### 0. Déterminer le périmètre

Si l'utilisateur spécifie un scope (module, WS, tâche), limiter l'audit à ce périmètre. Sinon, auditer l'ensemble.

```bash
# Lister tous les fichiers de tests
find tests/ -name "test_*.py" -not -path "*__pycache__*" | sort

# Lister toutes les tâches DONE
grep -rl "Statut : DONE" docs/tasks/ | sort
```

### 1. Construire la matrice spec → tâche → test

Pour chaque module/workstream dans le périmètre :

1. **Identifier la section de spec** applicable (§4 données, §5 labels, §6 features, §7 datasets, §8 splits, §9 scaling, etc.).
2. **Lire la tâche associée** (`docs/tasks/<milestone>/NNN__slug.md`) et extraire les critères d'acceptation.
3. **Lire le fichier de test** correspondant (`tests/test_*.py`) et inventorier les fonctions de test avec leurs docstrings.
4. **Mapper** chaque critère d'acceptation vers un ou plusieurs tests.

### 2. Vérifier l'adhérence formule par formule

Pour chaque formule mathématique dans la spec, vérifier dans les tests :

#### 2a. Formules numériques exactes
- [ ] La formule de la spec est reproduite dans un test de référence (hand-computed ou baseline).
- [ ] Les valeurs de référence dans le test correspondent au résultat attendu de la formule appliquée aux données de test.
- [ ] Les cas dégénérés de la formule (division par zéro, log(0), etc.) sont testés.

**Formules à vérifier (spec v1.0) :**

| Section | Formule | Test attendu |
|---|---|---|
| §5.2 | $y_t = \log(C_{t+H} / O_{t+1})$ | Valeur numérique calculée à la main |
| §5.3 | $y_t = \log(C_{t+H} / C_t)$ | Valeur numérique calculée à la main |
| §6.2 | $\text{logret}_k(t) = \log(C_t / C_{t-k})$ | Plusieurs positions connues |
| §6.2 | $\text{logvol}(t) = \log(V_t + \varepsilon)$ | Valeurs exactes |
| §6.2 | $\text{dlogvol}(t) = \text{logvol}(t) - \text{logvol}(t-1)$ | Valeurs exactes |
| §6.3 | RSI Wilder complet (SMA init + lissage récursif) | Valeurs calculées pas à pas |
| §6.4 | $\text{EMA\_ratio} = \text{EMA}_{fast} / \text{EMA}_{slow} - 1$ | Convergence, valeurs connues |
| §6.5 | $\text{vol}_w(t) = \text{std}(\text{logret}_1[t-w+1:t], \text{ddof})$ | Comparaison avec pandas rolling |
| §8.2 | $\text{purge\_cutoff} = \text{test\_start} - \text{embargo} \times \Delta$ | Vérification des bornes |
| §9.1 | $x' = (x - \mu) / (\sigma + \varepsilon)$ | Inverse transform, valeurs identiques |
| §9.2 | Robust scaler : median/IQR + clip | Valeurs connues |

#### 2b. Contrat min_periods
Pour chaque feature enregistrée :
- [ ] Le test vérifie que `min_periods()` renvoie exactement le nombre de NaN en tête de `compute()`.
- [ ] Ce nombre est cohérent avec la formule (§6.x).

#### 2c. Dimensions et types
- [ ] Tests vérifient `X_seq.shape == (N, L, F)` et `X_seq.dtype == float32` (§7.1).
- [ ] Tests vérifient `y.dtype == float32` pour tenseurs, `float64` pour métriques.
- [ ] Tests vérifient les colonnes canoniques OHLCV (§4.1).

#### 2d. Comportement aux bornes (spec §8.4, §6.6)
- [ ] `min_warmup < max(min_periods)` → ValueError (§6.6).
- [ ] `embargo_bars >= H` vérifié (§8.2).
- [ ] `train_start < val_start < test_start` séquentiel (§8).
- [ ] Splits avec données insuffisantes → erreur explicite (§8.4).

### 3. Vérifier la couverture des critères d'acceptation

Pour chaque tâche DONE dans le périmètre :

```
Pour chaque critère [x] dans la tâche :
  - Trouver le(s) test(s) qui le couvrent (via docstring #NNN ou nom de test).
  - Vérifier que le test exécute réellement le scénario décrit.
  - Si aucun test → signaler comme MANQUANT.
  - Si test existe mais n'exerce pas le critère → signaler comme INSUFFISANT.
```

### 4. Détecter les anti-patterns de test

- [ ] **Tautologie** : test qui vérifie que le code renvoie ce que le code renvoie (pas de valeur de référence indépendante).
- [ ] **Test trop permissif** : `atol` ou `rtol` excessivement large masquant un bug.
- [ ] **Test dépendant de l'implémentation** : test qui casse si on refactore le code sans changer le comportement (ex : vérifier un message d'erreur exact non spécifié).
- [ ] **Test avec données insuffisantes** : N trop petit pour exercer réellement le chemin testé (ex : tester RSI avec 5 barres quand la période est 14).
- [ ] **Assertion absente** : test qui exécute du code sans `assert` (passe toujours).
- [ ] **Valeur magique non documentée** : constante dans le test sans explication de sa provenance.
- [ ] **Paramètre hardcodé** : test qui utilise un paramètre hardcodé alors que la spec dit config-driven (ex : `period=14` au lieu de lire la config).

### 5. Vérifier la cohérence test ↔ code source

Pour chaque paire (test, module source) :
- [ ] Le test appelle la bonne API publique du module (pas d'accès à des internals).
- [ ] Le test utilise les mêmes noms de paramètres que l'API.
- [ ] Le test vérifie le comportement documenté, pas un effet de bord d'implémentation.
- [ ] Si le code source a changé (refactoring), le test couvre toujours le même comportement.

### 6. Produire le rapport

Écrire le rapport dans `docs/test_adherence/NNNN_scope.md` (créer le répertoire si nécessaire).

## Niveaux de sévérité

| Niveau | Préfixe | Définition |
|---|---|---|
| **BLOQUANT** | `B-N` | Formule de test en contradiction avec la spec. Assertion validant un résultat faux. Critère d'acceptation non couvert pour une règle non négociable. |
| **WARNING** | `W-N` | Critère d'acceptation couvert partiellement. Test tautologique. Tolérance excessive. Cas de bord manquant identifié dans la spec. |
| **MINEUR** | `M-N` | Test orphelin (pas de critère correspondant mais test valide). Docstring #NNN manquant. Valeur de référence non documentée. |

## Format du rapport

```markdown
# Test Adherence — <scope audité>

**Date** : YYYY-MM-DD
**Périmètre** : <modules/WS audités>
**Spec** : v1.0 + addendum v1.1 + v1.2
**Verdict** : ✅ CONFORME | ⚠️ ÉCARTS DÉTECTÉS | ❌ NON-CONFORMITÉS CRITIQUES

---

## Résumé exécutif

<2-3 phrases synthèse>

## Matrice de couverture spec → tests

| Section spec | Formule/Règle | Tâche(s) | Test(s) | Verdict |
|---|---|---|---|---|
| §5.2 | $y_t = \log(C_{t+H} / O_{t+1})$ | #016 | `test_label_target.py::test_log_return_trade_formula` | ✅ |
| §6.3 | RSI Wilder lissage | #010 | `test_rsi.py::TestRSINumerical::test_rsi_hand_computed_small` | ✅ |
| ... | ... | ... | ... | ... |

## Critères d'acceptation non couverts

| Tâche | Critère | Statut | Commentaire |
|---|---|---|---|
| #NNN | <critère> | ❌ MANQUANT / ⚠️ INSUFFISANT | <explication> |

## Écarts formule spec ↔ test

### B-N. <Titre>

**Spec** : §X.Y — <formule>
**Test** : `tests/test_xxx.py::TestClass::test_method` (LNNN)
**Code** : `ai_trading/module.py` (LNNN)
**Écart** : <description précise de la divergence>
**Impact** : <conséquence si non corrigé>
**Action** : <correction proposée>

### W-N. <Titre>

...

## Anti-patterns détectés

| Test | Anti-pattern | Sévérité | Action |
|---|---|---|---|
| `test_xxx.py::test_yyy` | Tautologie | WARNING | Ajouter valeur de référence indépendante |
| ... | ... | ... | ... |

## Résumé des actions

| # | Sévérité | Action | Fichier(s) |
|---|---|---|---|
| B-1 | BLOQUANT | <action> | `test_xxx.py` |
| W-1 | WARNING | <action> | `test_yyy.py` |
| M-1 | MINEUR | <action> | `test_zzz.py` |
```

## Règles de verdict

| Verdict | Condition |
|---|---|
| **✅ CONFORME** | Toutes les formules spec couvertes. Tous les critères d'acceptation testés. Zéro écart bloquant. |
| **⚠️ ÉCARTS DÉTECTÉS** | Au moins un warning (couverture partielle, tolérance excessive). Zéro bloquant. |
| **❌ NON-CONFORMITÉS CRITIQUES** | Au moins un bloquant (formule fausse, critère critique non couvert). |

## Principes de revue

1. **Spec fait foi** : en cas de divergence entre test et code, la spec est la référence. Si le code diverge de la spec et que le test valide le code, c'est un bloquant.
2. **Indépendance des valeurs de référence** : les valeurs de test doivent être calculables indépendamment du code (hand-computed, formule appliquée manuellement, ou bibliothèque de référence tierce).
3. **Exhaustivité formulaire** : chaque formule numérique de la spec doit avoir au moins un test qui valide des valeurs numériques concrètes, pas seulement des propriétés (shape, type, range).
4. **Traçabilité** : chaque test doit être traçable à un critère d'acceptation (via docstring `#NNN`) ou à une section de spec.
5. **Adversarial** : pour chaque formule, imaginer une implémentation alternative qui passerait le test mais serait fausse. Si c'est possible, le test est insuffisant.
6. **Boundary focus** : la spec définit des comportements aux bornes (§6.6, §8.4). Les tests doivent exercer ces bornes exactement, pas approximativement.

## Quand utiliser ce skill

- « vérifie l'adhérence des tests à la spec »
- « les tests collent à la spec ? »
- « audit tests vs spec »
- « est-ce que les tests valident bien les formules ? »
- « matrice de couverture spec → tests »
- « vérifie que les critères d'acceptation sont bien testés »
- Avant un gate ou milestone, pour s'assurer que la suite de tests est fiable.
