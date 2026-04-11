# Plan : Ajout du modèle PatchTST

## TL;DR
Ajouter un modèle PatchTST (Patch Time Series Transformer) dans `models/patch_tst/` en suivant exactement le pattern des modèles existants (CNN, CNN-BiLSTM-AM). Le data_preparator est réutilisé tel quel du CNN (DataLoaders 3D). L'évaluation passe par `run_evaluation()`. La config est centralisée dans `config.py`.

## Phase 1 — Config (config.py)

1. Ajouter `PATCHTST_CONFIGS` dict avec profils `"1d"` et `"1h"`
   - `"1d"`: patch_len=6, stride=3, d_model=64, n_heads=4, n_layers=3, d_ff=128, dropout=0.2, dropout_fc=0.3
   - `"1h"`: patch_len=12, stride=6, d_model=64, n_heads=4, n_layers=3, d_ff=128, dropout=0.2, dropout_fc=0.3
   - Contraintes : `d_model % n_heads == 0`, `num_patches = (window_size - patch_len) // stride + 1 >= 2`
2. Ajouter `get_patchtst_config(timeframe)` avec fallback dynamique (patch_len = window_size // 5, stride = patch_len // 2)

**Fichier** : `config.py` (ajouter après `get_xgboost_config`)

## Phase 2 — Architecture (PatchTST.py)

3. Créer `models/patch_tst/__init__.py` (vide)
4. Créer `models/patch_tst/PatchTST.py` avec classe `PatchTST(nn.Module)`
   - **Input** : `(batch, window_size, n_features)` — même format que CNN
   - **Patching** : unfold la dimension temporelle en patches `(batch, num_patches, patch_len * n_features)`
   - **Projection** : `nn.Linear(patch_len * n_features, d_model)`
   - **Positional embedding** : `nn.Parameter` apprenable de shape `(1, num_patches, d_model)`
   - **Transformer Encoder** : `nn.TransformerEncoder` avec `nn.TransformerEncoderLayer(d_model, n_heads, d_ff, dropout, batch_first=True)`
   - **Head** : flatten `(batch, num_patches * d_model)` → MLP `→ d_model → 32 → 1`
   - **Init poids** : Xavier pour les couches Linear, avec `gain=2.0` pour la dernière couche
   - Paramètres constructeur : `window_size, n_features, patch_len, stride, d_model, n_heads, n_layers, d_ff, dropout, dropout_fc`
   - `from __future__ import annotations` en haut (Python 3.9 compat)

**Fichier** : `models/patch_tst/PatchTST.py`

## Phase 3 — Data Preparator

5. Créer `models/patch_tst/data_preparator.py` — simple réexport :
   ```python
   from models.cnn.data_preparator import prepare_data  # noqa: F401
   ```
   Identique au pattern `cnn_bilstm_am/data_preparator.py`. Le pipeline CNN retourne des DataLoaders avec tenseurs 3D `(batch, window, features)` — exactement ce que PatchTST attend.

**Fichier** : `models/patch_tst/data_preparator.py`

## Phase 4 — Training

6. Créer `models/patch_tst/training.py` — calqué sur `models/cnn/training.py` avec les adaptations Transformer :
   - Import `get_patchtst_config` au lieu de `get_cnn_config`
   - Instanciation : `PatchTST(window_size=..., n_features=..., **patchtst_cfg)`
   - **Loss** : `HuberLoss(delta=1.0)` (même que CNN)
   - **Optimizer** : `AdamW(weight_decay=1e-3)` — régularisation plus forte pour Transformers
   - **Scheduler** : `CosineAnnealingLR(T_max=epochs)` — mieux adapté que ReduceLROnPlateau pour Transformers
   - **Gradient clipping** : `torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)` après `loss.backward()`
   - **Checkpoint** : sauvegarde `model_state`, `history`, `timeframe`, `window_size`, `patchtst_cfg`, `n_features`
   - **Scalers** : même structure joblib que CNN
   - `_get_checkpoint_paths()` → `models/patch_tst/checkpoints/{timeframe}/`
   - CLI : `--symbol, --timeframe, --epochs (200), --batch-size (32), --lr (1e-4), --patience (15)`
   - `from __future__ import annotations` (Python 3.9)

**Fichier** : `models/patch_tst/training.py`

## Phase 5 — Evaluation

7. Créer `models/patch_tst/evaluation.py` — calqué sur `models/cnn/evaluation.py` :
   - `load_model()` reconstruit PatchTST depuis le checkpoint (`patchtst_cfg`)
   - `evaluate()` délègue à `run_evaluation()` (identique au CNN)
   - `_get_checkpoint_paths()` → `models/patch_tst/checkpoints/{timeframe}/`
   - `from __future__ import annotations` (Python 3.9)

**Fichier** : `models/patch_tst/evaluation.py`

## Phase 6 — Tests

8. Créer `tests/test_patch_tst.py` — calqué sur `tests/test_xgboost.py` :
   - Mock torch si non installé (même pattern)
   - `TestPatchTSTModel` : vérifier shapes forward pass, output shape, gradient flow
   - `TestDataPreparator` : réutilise celui du CNN (vérifier que l'import fonctionne)
   - `TestTraining` : train avec n_layers=1, d_model=16, epochs réduits, vérifier checkpoint
   - `TestEvaluation` : load_model + run_evaluation
   - `TestConfig` : get_patchtst_config pour 1d, 1h, fallback
   - Fixtures : synthetic_csv, _patch_output (même pattern que test_xgboost)

**Fichier** : `tests/test_patch_tst.py`

## Phase 7 — Lint & Validation

9. `ruff check models/patch_tst/ tests/test_patch_tst.py config.py` → clean
10. `pytest tests/test_patch_tst.py -v` → 0 failures

## Relevant files

- `config.py` — ajouter `PATCHTST_CONFIGS` + `get_patchtst_config()`, pattern identique à `get_cnn_config()` (L161-183) et `get_cnn_bilstm_am_config()` (L222-244)
- `models/cnn/CNN.py` — référence architecture PyTorch, pattern `__init__` + `forward()`
- `models/cnn_bilstm_am/CNN_BiLSTM_AM.py` — référence `_init_weights()` pour Xavier/Kaiming
- `models/cnn/training.py` — template boucle d'entraînement, checkpoint, early stopping
- `models/cnn/evaluation.py` — template `load_model()` + `evaluate()` → `run_evaluation()`
- `models/cnn_bilstm_am/data_preparator.py` — pattern réexport `prepare_data`
- `models/cnn/data_preparator.py` — pipeline complet (clipping, scaling, DataLoaders)
- `utils/evaluation.py` — `run_evaluation()` orchestrateur (model, dataloader, scaler → metrics + plots)
- `tests/test_xgboost.py` — template tests (fixtures, synthetic data, monkeypatch)
- `data/features/pipeline.py` — `FEATURE_COLUMNS` (16 pour 1d), `get_feature_columns()`

## Verification

1. `ruff check models/patch_tst/ tests/test_patch_tst.py config.py` → 0 errors
2. `pytest tests/test_patch_tst.py -v` → all tests pass
3. Vérifier manuellement que `PatchTST.forward()` accepte `(batch, 30, 16)` et retourne `(batch,)`
4. Vérifier que `num_patches` est calculé correctement pour chaque profil timeframe
5. Vérifier `d_model % n_heads == 0` dans chaque config

## Decisions

- **Réutiliser le data_preparator CNN** tel quel (même tenseur 3D) — pas de data prep spécifique
- **Pas de channel-independence** : on traite toutes les features ensemble par patch (supervised, pas forecasting multivarié pur). Le paper PatchTST original propose channel-independence, mais notre cas est de la régression supervisée avec 16 features corrélées → le mode "channel-mixing" est plus adapté.
- **Positional embedding apprenable** (pas sinusoïdal) — plus flexible pour des séquences courtes (9 patches max)
- **Flatten + MLP head** au lieu de CLS token — plus simple, le nombre de patches est petit et fixe
- **CosineAnnealingLR** au lieu de ReduceLROnPlateau — mieux adapté aux Transformers (warm-up implicite via le cosine decay)
- **AdamW** avec weight_decay=1e-3 — les Transformers ont plus de paramètres et bénéficient de régularisation
- **Gradient clipping max_norm=1.0** — essentiel pour stabiliser le training des Transformers
- **`from __future__ import annotations`** dans tous les fichiers (compatibilité Python 3.9)
- **Scope** : uniquement le modèle + tests. Pas de modification du backtesting ou realtime_testing.
