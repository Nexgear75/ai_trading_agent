# Revue du plan d'implémentation — AI Trading Pipeline

**Date** : 2026-02-28
**Scope** : `docs/plan/implementation.md` vs `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (v1.0 + addendum v1.1 + v1.2), `configs/default.yaml`, schémas JSON, `pyproject.toml`


## Verdict global : ✅ Le plan est solide et prêt pour l'implémentation

Le plan est bien structuré, exhaustif, et fidèle à la spécification. Les Work Streams sont clairement découpés, les dépendances sont correctes, et les critères d'acceptation sont vérifiables. Cependant, **15 points** méritent une clarification ou une décision avant implémentation pour éviter des allers-retours.


---


## 1. Cohérence plan ↔ spec ↔ config : points résolus ✅

Les éléments suivants sont conformes et ne présentent pas d'ambiguïté :

| Aspect | Verdict |
|---|---|
| 9 features MVP (noms, formules, paramètres) | ✅ Cohérent |
| Label `log_return_trade` et alternative `close_to_close` | ✅ Cohérent |
| Walk-forward (180/30/30, val 20%, embargo = H) | ✅ Cohérent |
| Modèle de coûts multiplicatif per-side | ✅ Cohérent |
| Backtest `one_at_a_time` + `long_only` imposés | ✅ Cohérent |
| Calibration θ par grille de quantiles | ✅ Cohérent |
| Bypass θ pour RL et baselines | ✅ Cohérent |
| Schémas JSON (manifest + metrics) alignés | ✅ Cohérent |
| Arborescence cible du code | ✅ Cohérent |
| Config default.yaml couvre tous les paramètres E.1 | ✅ Cohérent |
| Fallback θ (E.2.2) | ✅ Cohérent |
| Profit factor cas limites (E.2.5) | ✅ Cohérent |
| Un symbole par run (E.2.6) | ✅ Cohérent |
| Scaler global par feature (E.2.7) | ✅ Cohérent |
| Formats CSV artefacts (E.2.8) | ✅ Cohérent |


---


## 2. Ambiguïtés et points à trancher avant implémentation

### AMB-01 — Nom du package Python : `ai_trading` vs `stockgpt`

**Constat** : Le plan définit le package comme `ai_trading/` avec `import ai_trading`. Le `pyproject.toml` actuel confirme `name = "ai_trading"` et `[tool.setuptools.packages.find] include = ["ai_trading*"]`. Cependant les instructions repo (`.github/instructions/`) référencent un projet « StockGPT » avec un répertoire `stockgpt/`. L'arborescence actuelle du workspace ne contient **aucun** répertoire `ai_trading/` ni `stockgpt/`.

**Décision requise** : Confirmer que le nom du package est bien `ai_trading` (conforme au plan et au pyproject.toml). Si c'est `stockgpt`, il faudra mettre à jour le plan et le pyproject.toml.

**Recommandation** : Garder `ai_trading` (cohérent avec le plan, le pyproject.toml, et la spécification).


### AMB-02 — Splitter : formule exacte du nombre de folds

**Constat** : WS-4.5 donne deux formules différentes pour le nombre de folds :
- Formule générale : `n_folds = floor((total_days - train_days - test_days) / step_days) + 1`
- Formule simplifiée (cas MVP `test_days == step_days`) : `n_folds = floor((total_days - train_days) / step_days)`

Avec les paramètres MVP (total_days = 731, train_days = 180, test_days = 30, step_days = 30) :
- Formule générale : `floor((731 - 180 - 30) / 30) + 1 = floor(17.37) + 1 = 18`
- Formule simplifiée : `floor((731 - 180) / 30) = floor(18.37) = 18`

Les deux concordent ici, **mais la politique de troncation** (fold exclu si `test_end > dataset.end`) peut réduire ce nombre. La formule est donc un **maximum théorique**, pas un nombre garanti.

**Décision requise** : Aucune (la formule est correcte et la politique de troncation est claire). Mais il faudrait un test qui vérifie le nombre de folds réels avec les paramètres MVP. Documenter que c'est un upper bound.

**Recommandation** : Ajouter un test d'intégration qui calcule les folds avec la config MVP et vérifie le nombre exact.


### AMB-03 — Splitter : sémantique de `dataset.end` (exclus ou inclus ?)

**Constat** : La config indique `end: "2026-01-01"` avec le commentaire « Date fin (UTC, exclue) ». Le plan WS-4.5 utilise `total_days = (dataset.end - dataset.start).days` et tronque si `test_end[k] > dataset.end`. Mais la dernière bougie du dataset est `2025-12-31T23:00:00Z`, pas `2026-01-01T00:00:00Z`.

**Décision requise** : Confirmer que `dataset.end` est une borne **exclusive** (convention Python standard `[start, end[`). Ce choix est implicite dans la config mais jamais formalisé dans la spec.

**Recommandation** : Ajouter une note explicite dans WS-2.1 et WS-4.5 : « `dataset.end` est exclusif : la dernière bougie téléchargée est celle dont `timestamp_utc < end` ».


### AMB-04 — Splitter : définition de `train_val_end` et dernière bougie incluse

**Constat** : WS-4.5 définit `train_val_end[k] = train_start[k] + timedelta(days=train_days) - timedelta(hours=1)` pour inclure la dernière bougie. Cette arithmétique assume un timeframe de 1h (Δ = 1 heure). Si le timeframe change (ex: 15m), `timedelta(hours=1)` est incorrect.

**Décision requise** : Généraliser en utilisant `timedelta(hours=Δ_hours)` au lieu de `timedelta(hours=1)` pour le calcul des bornes, ou confirmer que le plan est valide uniquement pour Δ = 1h (MVP).

**Recommandation** : Remplacer `timedelta(hours=1)` par `timedelta(hours=Δ_hours)` dans les formules du plan pour une cohérence avec le paramètre `dataset.timeframe`. Cela ne change rien pour le MVP (Δ = 1h) mais prépare le terrain.


### AMB-05 — Equity curve mark-to-market : calcul exact de `r_unrealized`

**Constat** : WS-8.3 définit l'equity mark-to-market avec `M_unrealized = (1-f) * Close[t']*(1-s) / (p_entry_eff)`. Cette formule n'applique le frais `(1-f)` qu'une seule fois côté sortie, alors que le calcul du rendement net réel applique `(1-f)²` (entrée + sortie). La formule devrait être :

`M_unrealized = (1-f) * Close[t']*(1-s) / p_entry_eff`

où `p_entry_eff = Open[t+1] * (1+s)` contient déjà le slippage d'entrée, et les frais d'entrée sont déjà payés (capturés dans `E_entry`). Il faut donc bien un seul `(1-f)` côté sortie pour le mark-to-market.

**Décision requise** : Clarifier si `E_entry` dans la formule `E_t' = E_entry * (1 + w * r_unrealized_t')` est l'equity **avant** le trade (donc les frais d'entrée sont dans `r_unrealized`) ou **après** les frais d'entrée. La cohérence dépend de cette convention.

**Recommandation** : Préciser dans le plan que `E_entry = E_before_trade` (equity avant tout frais du trade) et que `M_unrealized` inclut les frais d'entrée dans `p_entry_eff` et les frais de sortie fictifs via `(1-f)`. Ajouter un exemple numérique dans les critères d'acceptation.


### AMB-06 — Metric `exposure_time_frac` : non définie dans le plan

**Constat** : Le schéma `metrics.schema.json` et WS-10.2 mentionnent `exposure_time_frac` dans la liste des métriques trading, mais le plan ne donne **aucune formule** pour la calculer.

**Décision requise** : Aucune (la formule est intuitive), mais à documenter explicitement.

**Recommandation** : Ajouter dans WS-10.2 : `exposure_time_frac = n_bougies_en_trade / n_bougies_total_test`. Préciser si les bougies de transition (entrée/sortie) comptent comme « en trade ».


### AMB-07 — Sharpe ratio : sur quelle série exactement ?

**Constat** : La spec §14.2 définit le Sharpe sur les rendements par pas de temps `r_t = E_t / E_{t-1} - 1` sur la grille test. WS-8.3 produit une equity mark-to-market par bougie. Mais WS-10.2 ne précise pas :
- Le Sharpe est-il calculé sur **tous** les `r_t` (y compris les pas hors trade où `r_t = 0`) ?
- Ou seulement sur les `r_t` des bougies en trade ?

La convention a un impact majeur : inclure les `r_t = 0` hors trade réduit mécaniquement le Sharpe.

**Décision requise** : Confirmer que le Sharpe est calculé sur la **totalité** de la grille test (convention spec §14.2, incluant les pas `r_t = 0` hors trade).

**Recommandation** : En accord avec la spec, calculer sur toute la grille (cohérent avec la formule `r_t = E_t / E_{t-1} - 1`, où E est constant hors trade → r_t = 0). Documenter ce choix dans WS-10.2.


### AMB-08 — `output_dir` manquant dans WS-11.1 config path

**Constat** : WS-11.1 mentionne la dépendance `WS-1.2 (config pour output_dir)`, mais la clé config est `artifacts.output_dir` (pas `output_dir` directement). Le plan ne fait pas référence à la section `artifacts` de la config dans la description de WS-11.1.

**Décision requise** : Aucune (mineur, cohérence de nommage). La config est correcte.

**Recommandation** : Clarifier dans WS-11.1 que le répertoire de sortie est lu depuis `config.artifacts.output_dir`.


### AMB-09 — Buy & Hold baseline : un seul trade sur toute la période test

**Constat** : WS-9.2 indique que `predict()` retourne un vecteur de uns, et que « le backtest gère la logique d'un seul trade (mode `one_at_a_time`) ». C'est correct : le premier Go ouvre un trade, et les Go suivants sont ignorés. Mais le trade se ferme à `Close[t+H]` (4 bougies plus tard), pas à la fin du test. Après la clôture de ce trade, le prochain Go (un sur les suivants) réouvrira.

Cela signifie que Buy & Hold ne sera **pas** un seul trade long mais plutôt une **série de trades consécutifs de H bougies chacun** — ce qui est inconsistent avec la définition spec §12.5 (« position ouverte au début et fermée à la fin »).

**Décision requise** : La baseline Buy & Hold ne peut pas passer par le moteur de backtest standard (qui impose H = 4 bougies par trade). Il faut un traitement spécifique : entrée Open[premier timestamp], sortie Close[dernier timestamp], un seul trade.

**Recommandation** : Le moteur de backtest doit détecter `strategy.name == "buy_hold"` et exécuter un trade unique couvrant toute la période test. Alternativement, `BuyHoldBaseline.predict()` ne retourne `1` que pour le premier timestamp et `0` ensuite — mais cela ne couvre qu'un trade de H bougies, pas toute la période. **C'est un point de design critique à trancher.**


### AMB-10 — RL PPO : ohlcv et meta dans `fit()` pour l'environnement

**Constat** : WS-6.1 documente que le modèle RL utilise `meta_train` et `meta_val` passés à `fit()` pour construire son environnement interactif. Mais le plan ne précise pas comment le modèle RL gère le mode `one_at_a_time` dans son environnement d'entraînement :
- Après un Go à t, l'agent avance-t-il directement à `t + H + 1` (pas de décision pendant le trade) ?
- Ou l'agent décide-t-il à chaque pas de temps et les Go pendant un trade actif sont ignorés ?

**Décision requise** : Les deux approches sont valides. La spec E.2.10 dit « Transition : passage à la bougie suivante disponible (après t+H si trade ouvert) ». Cela suggère l'approche « skip » (l'agent ne voit pas les pas intermédiaires pendant un trade).

**Recommandation** : Confirmer l'approche « skip » pour la transition RL. L'agent décide → s'il fait Go, le prochain état est à `t + H + 1`. S'il fait No-Go, le prochain état est à `t + 1`. Documenter dans WS-6.1.


### AMB-11 — Scaler `fit()` : dimensions exactes

**Constat** : WS-5.1 dit « estimer μ_j et σ_j sur l'ensemble des N_train × L valeurs du train pour chaque feature j ». Cela signifie que le scaler aplatit le tenseur (N_train, L, F) en (N_train * L, F) avant de calculer μ et σ. C'est conforme à E.2.7 (un seul scaler global par feature). Mais le plan ne dit pas si les NaN potentiels (dus au warmup) doivent être exclus du calcul de μ/σ.

**Décision requise** : En principe, aucun NaN ne devrait exister dans X_train après le passage par le sample builder (WS-4.2 exclut les samples invalides). Confirmer ce pré-requis.

**Recommandation** : Ajouter une assertion dans WS-5.1 : « pré-condition : X_train ne contient aucun NaN (garanti par le sample builder). Si NaN détecté → raise ValueError ».


### AMB-12 — Métriques de prédiction pour baselines

**Constat** : WS-10.1 traite le cas RL (métriques prédiction → null) mais ne mentionne pas les baselines. Les baselines (no-trade, buy_hold, sma_rule) ne produisent pas de `y_hat` en float (elles retournent des signaux 0/1). Les métriques MAE, RMSE, Spearman IC n'ont pas de sens pour des prédictions binaires.

**Décision requise** : Les métriques de prédiction doivent-elles être `null` pour toutes les baselines, ou uniquement pour RL ?

**Recommandation** : Fixer toutes les métriques de prédiction à `null` pour les baselines (`strategy_type == "baseline"`) et pour RL. Cela est cohérent avec le fait que les baselines ne prédisent pas un rendement. Documenter dans WS-10.1.


### AMB-13 — Walk-forward splitter : embargo en bougies vs en heures

**Constat** : WS-4.5 calcule les bornes en dates UTC mais utilise l'embargo en bougies : `test_start[k] = train_start[k] + timedelta(days=train_days) + timedelta(hours=embargo_bars * Δ_hours)`. Or WS-4.6 dit « purge_cutoff = test_start − embargo_bars * Δ ». Il y a potentiellement un double comptage :
1. Le splitter ajoute un gap d'embargo entre `train_val_end` et `test_start`.
2. La purge retire des samples dont `t + H > purge_cutoff`.

Le plan WS-4.6 précise explicitement « l'embargo est appliqué une seule fois, pas en double ». Le schéma temporel clarifie le mécanisme. **Mais** le calcul de `purge_cutoff` semble redondant avec le gap déjà créé par le splitter.

**Décision requise** : Confirmer que `purge_cutoff = test_start - embargo_bars * Δ` est bien **calculé à partir du `test_start` déjà décalé par l'embargo**. Si oui, `purge_cutoff ≈ train_val_end`, et la purge ne retire que les samples dont le label dépasse `train_val_end` — ce qui est l'objectif.

**Recommandation** : Le mechanism est correct mais subtil. Ajouter un diagramme numérique avec les paramètres MVP dans les critères d'acceptation pour vérifier concrètement : avec embargo_bars = 4 et Δ = 1h, le gap entre val et test est de 4h, et tout sample t tel que `t + 4 > train_val_end` est purgé du train/val.


### AMB-14 — `spread_bps` dans l'override CLI vs config key

**Constat** : WS-1.2 donne l'exemple `--set costs.spread_bps=5` pour l'override CLI. Mais la config utilise `costs.slippage_rate_per_side` (un taux décimal), pas `spread_bps`. L'exemple est donc invalide par rapport à la config actuelle.

**Décision requise** : Corriger l'exemple dans WS-1.2.

**Recommandation** : Remplacer par `--set costs.slippage_rate_per_side=0.0005` ou `--set splits.train_days=240`.


### AMB-15 — Stitched equity curve : multi-fold gaps ?

**Constat** : WS-10.3 spécifie que la courbe d'équité stitchée respecte `E_start[k+1] = E_end[k]`. Mais les folds test sont consécutifs dans le temps (pas de gap entre test[k] et test[k+1] si step_days == test_days). Avec les paramètres MVP (step = test = 30 jours), c'est correct. Mais si `step_days > test_days`, il y aurait un gap entre les périodes test. Le plan ne précise pas comment gérer ce cas.

**Décision requise** : Aucune pour le MVP (step == test). Mais documenter que la courbe stitchée n'est valide que si les périodes test sont contiguës.

**Recommandation** : Ajouter une assertion dans WS-10.3 : si des gaps existent entre les périodes test, émettre un warning et maintenir l'equity constante pendant le gap.


---


## 3. Incohérences mineures (non bloquantes)

| # | Constat | Recommandation |
|---|---|---|
| MIN-01 | `pyproject.toml` utilise `build-backend = "setuptools.backends._legacy:_Backend"` — non standard. Le standard est `"setuptools.build_meta"`. | Corriger en `"setuptools.build_meta"`. |
| MIN-02 | La spec §10.1 ne mentionne pas `meta` ni `ohlcv` dans la signature `fit()`. Le plan étend la signature pour RL/SMA. C'est un choix d'implémentation légitime mais une extension par rapport à la spec. | Documenter dans WS-6.1 que c'est une extension implementation-defined. Déjà fait ✅. |
| MIN-03 | Le plan mentionne `metrics_fold.json` dans chaque fold (WS-11.3) mais le schéma manifest ne rend pas `metrics_fold_json` obligatoire dans `per_fold.files` (il est optionnel). | Acceptable (optionnel dans le schéma, systématique dans l'implémentation). |
| MIN-04 | WS-1.1 mentionne `__version__ = "1.0.0"` dans `__init__.py`. Le `pyproject.toml` définit aussi `version = "1.0.0"`. Risque de désynchronisation. | Utiliser `importlib.metadata.version("ai_trading")` au lieu de hardcoder dans `__init__.py`, ou maintenir un single source of truth. |
| MIN-05 | La config a une section `strategy.framework: xgboost` décrite comme « Informatif uniquement (manifest) ». La spec ne la requiert pas. | Acceptable, garder pour le manifest. |
| MIN-06 | `Dockerfile` : `COPY configs/ configs/` puis `COPY . .` copie deux fois `configs/`. | Supprimer la première ligne `COPY configs/`. |
| MIN-07 | Le plan ne prévoit pas de GitHub Actions workflow file. WS-12.4 mentionne « ajouter un workflow CI minimal » sans spécifier le fichier. | Créer `.github/workflows/ci.yml` avec lint + tests. Peut être fait au moment de l'implémentation. |


---


## 4. Couverture spec → plan : éléments non couverts

| Réf. spec | Sujet | Couverture dans le plan |
|---|---|---|
| §4.2 | Alignement multi-symboles | ❌ Non mentionné (acceptable : un seul symbole MVP) |
| §14.2 | Sharpe annualisé (optionnel) | ✅ Config `metrics.sharpe_annualized: false`. Pas de code annualisé dans le plan. OK pour MVP. |
| §15.1 | `report.html` / `report.pdf` | ✅ Explicitement reporté post-MVP dans WS-11.1. |
| §15.1 | `summary_metrics.csv` (optionnel) | ✅ Mentionné dans WS-10.3 comme post-MVP. |
| E.2.10 | RL PPO early stopping sur val P&L | ✅ Mentionné dans E.2.10. Le plan renvoie au modèle RL pour l'implémentation interne. |
| §16 | Hash SHA-256 des données | ✅ WS-2.1 (calcul), WS-11.2 (manifest). |
| §16.1 | `PYTHONHASHSEED` | ✅ WS-12.1. |


---


## 5. Risques identifiés

| Risque | Impact | Mitigation |
|---|---|---|
| **Buy & Hold non compatible avec le backtest standard** (AMB-09) | Le backtest exécutera des trades de H bougies au lieu d'un trade long unique → métriques incorrectes | Implémenter un chemin spécifique dans le backtest engine pour Buy & Hold |
| **Performance du sample builder** avec L=128 et ~17000 bougies | Potentiel memoire élevée si le tenseur est construit naïvement (N × 128 × 9 float64) | Utiliser des vues (stride tricks) ou construire par fold plutôt que globalement |
| **ccxt rate limiting** pour 2 ans de données à 1h | ~17520 bougies → ~18 appels de 1000 → risque de rate limit | WS-2.1 mentionne retry + backoff. OK. |
| **reproductibilité torch** (`deterministic_algorithms`) peut être lente ou lever des erreurs sur certaines ops | Impact performance | Documenter les opérations non déterministes à éviter. Le plan mentionne l'option. |


---


## 6. Synthèse des actions requises

### Actions bloquantes (à résoudre avant implémentation)

| # | Action | Priorité |
|---|---|---|
| **A1** | Trancher AMB-01 : confirmer le nom du package (`ai_trading`) | 🔴 Haute |
| **A2** | Trancher AMB-09 : décider du traitement Buy & Hold dans le backtest (trade unique vs chemin spécifique) | 🔴 Haute |
| **A3** | Trancher AMB-12 : métriques de prédiction → `null` pour toutes les baselines | 🔴 Haute |

### Actions recommandées (améliorations de clarté)

| # | Action | Priorité |
|---|---|---|
| **A4** | Clarifier AMB-03 : `dataset.end` est exclusif (convention `[start, end[`) | 🟡 Moyenne |
| **A5** | Généraliser AMB-04 : `timedelta(hours=Δ_hours)` au lieu de `timedelta(hours=1)` | 🟡 Moyenne |
| **A6** | Documenter AMB-05 : formule exacte equity mark-to-market avec exemple numérique | 🟡 Moyenne |
| **A7** | Définir AMB-06 : formule `exposure_time_frac` | 🟡 Moyenne |
| **A8** | Confirmer AMB-07 : Sharpe sur toute la grille test (y compris `r_t = 0`) | 🟡 Moyenne |
| **A9** | Confirmer AMB-10 : transition RL en mode « skip » | 🟡 Moyenne |
| **A10** | Ajouter AMB-11 : assertion no-NaN dans X_train avant scaling | 🟡 Moyenne |
| **A11** | Corriger AMB-14 : exemple CLI `spread_bps` → `slippage_rate_per_side` | 🟢 Basse |
| **A12** | Corriger MIN-01 : `build-backend` dans pyproject.toml | 🟢 Basse |
| **A13** | Corriger MIN-06 : doublon `COPY` dans Dockerfile | 🟢 Basse |
