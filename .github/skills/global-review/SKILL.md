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

### 6. Conformité avec la spécification (source de vérité)

> **Principe** : la spécification (`docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md`) est la source de vérité absolue. Pour chaque section de la spec, l'agent doit **lire la section**, puis **lire le code correspondant**, puis comparer. Les 5 checkboxes génériques ne suffisent pas — il faut un audit **section par section**.

#### 6a. Workflow obligatoire

1. **Charger la spec** : lire `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md`.
2. **Pour chaque section §4 à §17** (voir grille ci-dessous), identifier le module `ai_trading/` correspondant et comparer l'implémentation à la spec.
3. **Construire la matrice** spec → code → verdict (voir template rapport §8).
4. **Signaler** toute divergence, toute section spec non implémentée, toute implémentation sans ancrage spec.

#### 6b. Grille section-par-section

Pour chaque section, **lire la spec puis le code** et vérifier :

| Section spec | Module(s) attendu(s) | Vérifications |
|---|---|---|
| **§4.1** Source et format | `data/ingestion.py` | Colonnes canoniques (timestamp, open, high, low, close, volume), types, tz-aware UTC |
| **§4.2** Contrôles qualité | `data/qa.py` | Chaque QA check listé dans la spec est implémenté (duplicatas, NaN, OHLC cohérence, gaps) |
| **§4.3** Missing candles | `data/missing.py` | Politique forward-fill conforme, seuil max_missing_ratio |
| **§5.2** Label par défaut | `data/labels.py` | Formule $y_t = \log(C_{t+H} / O_{t+1})$ exacte, colonnes utilisées, H = horizon config |
| **§5.3** Label alternatif | `data/labels.py` | Formule $y_t = \log(C_{t+H} / C_t)$ si implémentée |
| **§6.2** Features MVP | `features/log_returns.py`, `features/volume.py` | Formules logret_k, logvol, dlogvol exactes, k = config |
| **§6.3** RSI Wilder | `features/rsi.py` | SMA init + lissage récursif Wilder (pas EMA classique), période = config |
| **§6.4** EMA ratio | `features/ema.py` | Formule $\text{EMA}_{fast} / \text{EMA}_{slow} - 1$, SMA init, périodes = config |
| **§6.5** Volatilité | `features/volatility.py` | Fenêtres fixes (24, 72 doc §6.5), ddof conforme à la spec |
| **§6.6** Warm-up | `features/warmup.py` | min_warmup >= max(min_periods), invalidation des samples, erreur si insuffisant |
| **§7.1** Dataset (N,L,F) | `data/dataset.py` | Shape, dtype float32, sliding window, ordering |
| **§7.2** Adapter XGBoost | `data/dataset.py` | Flatten (N, L×F), cohérent avec §7.1 |
| **§7.3** Métadonnées | `data/dataset.py` | meta dict conforme |
| **§8.1–§8.4** Walk-forward | `data/splitter.py` | n_splits, ratios, embargo_bars >= H, purge, séquentialité train < val < test |
| **§9.1** Standard scaler | `data/scaler.py` | Formule $(x - \mu) / (\sigma + \varepsilon)$, fit sur train uniquement, inverse_transform |
| **§9.2** Robust scaler | `data/scaler.py` | Median/IQR, clip conforme |
| **§10.1–§10.4** Interface modèle | `models/base.py`, `models/dummy.py` | ABC conforme (fit, predict, get_params), conventions I/O, déterminisme |
| **§11.1–§11.3** Calibration θ | `calibration/threshold.py` | Grille quantiles, objectif max_net_pnl_with_mdd_cap, θ calibré sur val |
| **§12.1–§12.6** Backtest | `backtest/engine.py`, `backtest/costs.py` | Règles Go/No-Go, coûts, rendement net, equity curve, buy&hold, journal |
| **§13.1–§13.3** Baselines | `baselines/` | no-trade, buy&hold, SMA rule conformes |
| **§14.1–§14.3** Métriques | `metrics/` | Prédiction (MSE, MAE, R², IC), trading (Sharpe, MDD, WR, P&L), agrégation inter-fold |
| **§15.1–§15.4** Artefacts | `artifacts/` | Arborescence run, manifest.json, metrics.json, schemas |
| **§16.1–§16.3** Reproductibilité | `utils/`, config | Seeds, hashes SHA-256, versionning features |

#### 6c. Formules à vérifier explicitement

Pour chaque formule ci-dessous, **comparer le code source** (pas les tests) avec la spec :

| ID | Section | Formule spec | Fichier code | Quoi vérifier |
|---|---|---|---|---|
| F-1 | §5.2 | $y_t = \log(C_{t+H} / O_{t+1})$ | `data/labels.py` | Colonnes `close` shift vs `open` shift, horizon H |
| F-2 | §6.2 | $\text{logret}_k(t) = \log(C_t / C_{t-k})$ | `features/log_returns.py` | `np.log`, shift direction, paramètre k |
| F-3 | §6.2 | $\text{logvol}(t) = \log(V_t + \varepsilon)$ | `features/volume.py` | Epsilon, colonne volume |
| F-4 | §6.2 | $\text{dlogvol}(t) = \text{logvol}(t) - \text{logvol}(t-1)$ | `features/volume.py` | Diff sur logvol, pas sur volume brut |
| F-5 | §6.3 | RSI Wilder (SMA init + récursif $\alpha = 1/n$) | `features/rsi.py` | SMA init (pas EMA init), lissage récursif, alpha |
| F-6 | §6.4 | $\text{EMA\_ratio} = \text{EMA}_{fast} / \text{EMA}_{slow} - 1$ | `features/ema.py` | Ratio - 1 (pas ratio seul), SMA init |
| F-7 | §6.5 | $\text{vol}_w(t) = \text{std}(\text{logret}_1[t-w+1:t], \text{ddof})$ | `features/volatility.py` | Fenêtre, ddof, input = logret_1 |
| F-8 | §8.2 | $\text{embargo\_bars} \geq H$ | `data/splitter.py` | Purge cutoff, embargo appliqué |
| F-9 | §9.1 | $x' = (x - \mu) / (\sigma + \varepsilon)$ | `data/scaler.py` | Epsilon, fit train only |
| F-10 | §9.2 | Robust : $(x - \text{median}) / (\text{IQR} + \varepsilon)$ + clip | `data/scaler.py` | IQR = Q75 - Q25, clip bounds |
| F-11 | §11.2 | Grille quantiles sur val predictions | `calibration/threshold.py` | Quantiles, support, objectif |
| F-12 | §12.3 | $r_{net} = \log(C_{t+H}/O_{t+1}) - 2 \times \text{fee} - \text{slippage}$ | `backtest/engine.py`, `backtest/costs.py` | Formule coûts exacte |
| F-13 | §12.4 | $\text{equity}_{t+1} = \text{equity}_t \times \exp(r_{net})$ si Go | `backtest/engine.py` | Mise à jour equity curve |
| F-14 | §14.2 | Sharpe = $\mu(r) / \sigma(r) \times \sqrt{N_{ann}}$ | `metrics/` | Annualisation, ddof |

Pour chaque formule, produire un verdict :
- **✅ Conforme** : code = spec
- **❌ Divergent** : code ≠ spec (décrire l'écart)
- **⚠️ Non implémenté** : section spec sans code correspondant
- **🔍 Ambigu** : spec ambiguë, implémentation raisonnable mais non vérifiable

#### 6d. Détection des implémentations orphelines

Rechercher dans `ai_trading/` tout comportement significatif (formule, algorithme, heuristique) qui **n'a pas d'ancrage dans la spec**. Ce n'est pas forcément un bug, mais ça doit être signalé :
- [ ] Constantes ou seuils non documentés dans la spec.
- [ ] Algorithmes alternatifs non prévus par la spec.
- [ ] Paramètres config sans correspondance dans la spec (sauf implementation-defined explicites).

### 6bis. Conformité avec le plan d'implémentation

> **Principe** : le plan (`docs/plan/implementation.md`) détaille le découpage en WS et tâches. Le code doit refléter ce découpage et les tâches DONE doivent avoir du code correspondant.

#### 6bis-a. Workflow

1. **Charger le plan** : lire `docs/plan/implementation.md`.
2. **Lister les tâches** : parcourir `docs/tasks/<milestone>/` et identifier les statuts (DONE, IN_PROGRESS, TODO).
3. **Croiser** chaque tâche DONE avec le code source.

#### 6bis-b. Vérifications

- [ ] **Tâche DONE sans code** : une tâche marquée DONE n'a pas de module/fonction correspondant dans `ai_trading/`.
- [ ] **Tâche DONE sans test** : une tâche marquée DONE n'a pas de fichier de test correspondant dans `tests/`.
- [ ] **Code sans tâche** : un module existe dans `ai_trading/` mais ne correspond à aucune tâche du plan.
- [ ] **Critères d'acceptation non vérifiables** : les `[x]` de la tâche ne correspondent pas à ce que le code fait réellement.
- [ ] **Ordonnancement respecté** : les dépendances entre WS décrites dans le plan sont reflétées dans les imports du code.
- [ ] **Modules attendus par le plan** : les noms de modules listés dans le plan (WS-1 → config, WS-2 → ingestion/qa, WS-3 → features, etc.) correspondent aux modules réels.
- [ ] **Gates** : les critères de gate listés dans le plan pour le milestone en cours sont satisfaits par le code.

#### 6bis-c. Matrice plan → code

Construire une matrice de couverture plan → code (voir template rapport §8).

### 7. Bonnes pratiques métier

- [ ] Exactitude des concepts financiers (RSI Wilder, EMA SMA-init, ddof=0, etc.).
- [ ] Nommage métier fidèle (pas d'abréviation ambiguë).
- [ ] Séparation des responsabilités métier.
- [ ] Cohérence des unités et échelles (log vs arithmétique, UTC).
- [ ] Patterns de calcul financier idiomatiques (numpy/pandas vectorisé, pas de boucles Python sur séries temporelles sauf nécessité).

### 8. Produire le rapport

Écrire le rapport dans `docs/request_changes/NNNN_slug.md` (prochain numéro séquentiel). Utiliser le format ci-dessous.

> **Obligation** : les sections « Conformité formules métier », « Conformité spec section-par-section » et « Conformité plan → code » du rapport **doivent être remplies intégralement**. Un rapport sans ces matrices est incomplet et ne sera pas accepté.

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

## Conformité formules métier (§6c)

| ID | Section spec | Formule | Fichier code | Verdict |
|---|---|---|---|---|
| F-1 | §5.2 | $y_t = \log(C_{t+H} / O_{t+1})$ | `data/labels.py` | ✅ / ❌ / ⚠️ / 🔍 |
| F-2 | §6.2 | logret_k | `features/log_returns.py` | ✅ / ❌ / ⚠️ / 🔍 |
| F-3 | §6.2 | logvol | `features/volume.py` | ✅ / ❌ / ⚠️ / 🔍 |
| F-4 | §6.2 | dlogvol | `features/volume.py` | ✅ / ❌ / ⚠️ / 🔍 |
| F-5 | §6.3 | RSI Wilder | `features/rsi.py` | ✅ / ❌ / ⚠️ / 🔍 |
| F-6 | §6.4 | EMA_ratio | `features/ema.py` | ✅ / ❌ / ⚠️ / 🔍 |
| F-7 | §6.5 | vol_w rolling | `features/volatility.py` | ✅ / ❌ / ⚠️ / 🔍 |
| F-8 | §8.2 | embargo >= H | `data/splitter.py` | ✅ / ❌ / ⚠️ / 🔍 |
| F-9 | §9.1 | standard scaler | `data/scaler.py` | ✅ / ❌ / ⚠️ / 🔍 |
| F-10 | §9.2 | robust scaler | `data/scaler.py` | ✅ / ❌ / ⚠️ / 🔍 |
| F-11 | §11.2 | grille quantiles θ | `calibration/threshold.py` | ✅ / ❌ / ⚠️ / 🔍 |
| F-12 | §12.3 | rendement net trade | `backtest/engine.py` | ✅ / ❌ / ⚠️ / 🔍 |
| F-13 | §12.4 | equity curve update | `backtest/engine.py` | ✅ / ❌ / ⚠️ / 🔍 |
| F-14 | §14.2 | Sharpe annualisé | `metrics/` | ✅ / ❌ / ⚠️ / 🔍 |

> Légende : ✅ Conforme — ❌ Divergent (décrire dans BLOQUANTS) — ⚠️ Non encore implémenté — 🔍 Spec ambiguë

**Écarts détaillés** (pour chaque ❌ ou 🔍) :
- F-N : <description de l'écart, citation spec vs code>

---

## Conformité spec section-par-section (§6b)

| Section spec | Module code | Implémenté | Conforme | Remarques |
|---|---|---|---|---|
| §4.1 Source/format | `data/ingestion.py` | ✅/❌ | ✅/❌ | |
| §4.2 QA checks | `data/qa.py` | ✅/❌ | ✅/❌ | |
| §4.3 Missing candles | `data/missing.py` | ✅/❌ | ✅/❌ | |
| §5.2 Label trade | `data/labels.py` | ✅/❌ | ✅/❌ | |
| §6.2–§6.5 Features | `features/` | ✅/❌ | ✅/❌ | |
| §6.6 Warm-up | `features/warmup.py` | ✅/❌ | ✅/❌ | |
| §7.1–§7.3 Dataset | `data/dataset.py` | ✅/❌ | ✅/❌ | |
| §8.1–§8.4 Splits | `data/splitter.py` | ✅/❌ | ✅/❌ | |
| §9.1–§9.2 Scaling | `data/scaler.py` | ✅/❌ | ✅/❌ | |
| §10.1–§10.4 Modèle | `models/` | ✅/❌ | ✅/❌ | |
| §11.1–§11.3 Calibration | `calibration/` | ✅/❌ | ✅/❌ | |
| §12.1–§12.6 Backtest | `backtest/` | ✅/❌ | ✅/❌ | |
| §13.1–§13.3 Baselines | `baselines/` | ✅/❌ | ✅/❌ | |
| §14.1–§14.3 Métriques | `metrics/` | ✅/❌ | ✅/❌ | |
| §15.1–§15.4 Artefacts | `artifacts/` | ✅/❌ | ✅/❌ | |
| §16.1–§16.3 Repro | `utils/` | ✅/❌ | ✅/❌ | |

---

## Conformité plan → code (§6bis)

| WS | Tâches DONE | Module(s) code | Code présent | Tests présents | Remarques |
|---|---|---|---|---|---|
| WS-1 | #NNN, ... | `config.py` | ✅/❌ | ✅/❌ | |
| WS-2 | #NNN, ... | `data/ingestion.py`, `data/qa.py` | ✅/❌ | ✅/❌ | |
| WS-3 | #NNN, ... | `features/` | ✅/❌ | ✅/❌ | |
| ... | ... | ... | ... | ... | |

**Anomalies plan ↔ code** :
- Tâches DONE sans code : <liste>
- Code sans tâche : <liste>
- Critères d'acceptation [x] non vérifiables : <liste>

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
| `test-adherence` | `test-adherence` audite tests ↔ spec en profondeur (formule par formule). La revue globale audite **code** ↔ spec (complémentaire : test-adherence vérifie que les tests valident la spec, global-review vérifie que le code implémente la spec). |
| `plan-coherence` | `plan-coherence` audite la cohérence **interne** du plan. La revue globale audite la cohérence **plan ↔ code** (le plan dit-il la vérité sur ce qui est implémenté ?). |
| `gate-validator` | La revue globale est un **prérequis informel** avant le gate. Les constats WARNING+ doivent être résolus avant de passer un gate. |
| `implementing-task` | Les constats de la revue globale peuvent générer des **tâches correctives** via `task-creator`. |
| `task-creator` | Les résultats de la revue globale alimentent la création de tâches de correction. |

```
