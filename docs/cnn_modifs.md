# Modifications CNN & CNN-BiLSTM-AM — Branche `xgboost`

Les modèles CNN1D et CNN-BiLSTM-AM existaient déjà sur `main`. Cette branche y apporte deux types de modifications : des **corrections de bugs/faiblesses** et des **adaptations nécessaires** pour intégrer le pipeline d'évaluation partagé (`build_val_from_checkpoint`).

---

## 1. Corrections modèle (bugs / faiblesses existantes)

### 1.1 Split temporel par symbole (`data_preparator.py`)

**Problème** : Le split train/val se faisait sur le DataFrame concaténé global. Avec plusieurs cryptos, les derniers exemples d'un symbole pouvaient se retrouver dans train tandis que les premiers d'un autre symbole allaient dans val — violation de la causalité temporelle.

**Correction** : Le split est maintenant effectué **par symbole** (`groupby("symbol")`) avant concaténation. Chaque symbole respecte `train < val` en chronologie.

### 1.2 Clipping features vectorisé (`data_preparator.py`)

**Problème** : La boucle `for i in range(nf)` calculait les percentiles et clippait feature par feature — fonctionnellement correct mais lent.

**Correction** : Remplacement par un appel vectorisé `np.percentile(..., axis=0)` + `np.clip` broadcast. Même résultat, exécution plus rapide.

### 1.3 Suppression de la fonction orpheline `_clip_outliers` (`data_preparator.py`)

**Problème** : La fonction utilitaire `_clip_outliers` n'était plus appelée nulle part (le clipping par percentile était fait inline).

**Correction** : Suppression du code mort.

### 1.4 Fallback silencieux dans `load_model()` (`evaluation.py`)

**Problème** : `checkpoint.get("window_size", 30)` et `checkpoint.get("n_features", len(FEATURE_COLUMNS))` masquaient silencieusement l'absence de clés critiques. Si un checkpoint incomplet était chargé, le modèle se construisait avec des dimensions potentiellement fausses.

**Correction** : Remplacement par une validation stricte — les clés `model_state`, `history`, `window_size`, `n_features`, `cnn_cfg` (resp. `model_cfg`) sont toutes **requises**. Absence = `KeyError` explicite.

### 1.5 f-string sans interpolation (`training.py`)

**Problème** : `print(f"  ENTRAÎNEMENT CNN1D")` — f-string inutile sans variable.

**Correction** : Remplacement par un string simple.

### 1.6 `map_location` manquant au reload (`training.py` CNN)

**Problème** : `torch.load(paths["model"], weights_only=False)` sans `map_location` pouvait échouer si le modèle avait été entraîné sur un device différent (ex: MPS → CPU).

**Correction** : Ajout de `map_location=device`.

---

## 2. Modifications nécessaires pipeline (intégration évaluation partagée)

### 2.1 Retour de `target_clip_bounds` (`data_preparator.py`)

**Raison** : Le nouveau pipeline d'évaluation (`build_val_from_checkpoint`) a besoin de reproduire exactement le clipping appliqué aux targets pendant l'entraînement. Les bornes `[lo, hi]` du winsorize sur `y_train` sont maintenant retournées par `prepare_data()` et persistées dans `scalers.joblib`.

**Impact** : Signature de retour passe de 6 à 7 valeurs → mise à jour de l'unpack dans `training.py` des deux modèles.

### 2.2 Persistance de métadonnées supplémentaires (`training.py`)

**Raison** : L'évaluateur partagé `build_val_from_checkpoint()` valide la cohérence du checkpoint. Il exige :
- `target_clip_bounds` — pour appliquer le même clipping sur val
- `train_ratio` — pour reproduire le même split
- `prediction_horizon` — pour recalculer les forward returns identiquement

Ces 3 champs sont maintenant sauvegardés dans `scalers.joblib` par les deux training.

### 2.3 Évaluation depuis checkpoint sans refit (`evaluation.py`)

**Raison** : L'ancienne évaluation appelait `prepare_data()` qui **refittait** les scalers sur les données courantes. Si les données avaient changé depuis l'entraînement, les scalers différaient → métriques non reproductibles.

**Correction** : L'évaluation utilise désormais `build_val_from_checkpoint()` qui :
1. Charge les scalers/clip_bounds du checkpoint (pas de refit)
2. Reconstruit les fenêtres val avec le même `train_ratio` et `window_size`
3. Applique le clipping + scaling des artefacts persistés

L'import de `prepare_data` et `joblib` direct est remplacé par l'import du helper partagé.

### 2.4 Validation de dimension features (`evaluation.py`)

**Raison** : Si le pipeline de features évolue (ajout/retrait de colonnes) entre l'entraînement et l'évaluation, les dimensions ne matchent plus. Un check explicite `X_val.shape[2] != clip_bounds.shape[0]` lève un `ValueError` immédiat au lieu de laisser le modèle crasher cryptiquement.

### 2.5 Validation `train_ratio` à l'entrée (`data_preparator.py`)

**Raison** : `train_ratio` est maintenant exposé en paramètre et persisté. Une valeur invalide (≤ 0, ≥ 1, négative) produirait des splits vides. Validation stricte `0 < train_ratio < 1` ajoutée en début de `prepare_data()`.

### 2.6 Suppression de l'import `FEATURE_COLUMNS` (`evaluation.py`)

**Raison** : L'ancien code utilisait `FEATURE_COLUMNS` comme fallback pour `n_features` dans `load_model()`. Avec la validation stricte des clés checkpoint, cet import n'est plus nécessaire.

---

## Résumé

| Catégorie | Fichier | Description courte |
|-----------|---------|-------------------|
| Correction | `data_preparator.py` | Split temporel par symbole |
| Correction | `data_preparator.py` | Clipping features vectorisé |
| Correction | `data_preparator.py` | Suppression `_clip_outliers` mort |
| Correction | `evaluation.py` | Fallback silencieux → validation stricte |
| Correction | `training.py` | f-string sans interpolation |
| Correction | `training.py` (CNN) | `map_location` manquant |
| Pipeline | `data_preparator.py` | Retour `target_clip_bounds` + validation `train_ratio` |
| Pipeline | `training.py` | Persistance `target_clip_bounds`, `train_ratio`, `prediction_horizon` |
| Pipeline | `evaluation.py` | Évaluation via `build_val_from_checkpoint` (sans refit) |
| Pipeline | `evaluation.py` | Check dimension features |
| Pipeline | `evaluation.py` | Suppression import `FEATURE_COLUMNS` |
