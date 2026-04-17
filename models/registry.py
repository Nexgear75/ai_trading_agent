import importlib

from models.base_predictor import BasePredictor

# Map model name -> (module_path, class_name)
AVAILABLE_MODELS: dict[str, tuple[str, str]] = {
    "rl": ("models.rl.predictor", "RLPredictor"),
    "cnn": ("models.cnn.predictor", "CNNPredictor"),
    "bilstm": ("models.bilstm.predictor", "BiLSTMPredictor"),
    "cnn_bilstm_am": ("models.cnn_bilstm_am.predictor", "CnnBiLstmAmPredictor"),
    "transformer": ("models.transformer.predictor", "TransformerPredictor"),
    "patch_tst": ("models.patch_tst.predictor", "PatchTSTPredictor"),
    "xgboost": ("models.xgboost.predictor", "XGBoostPredictor"),
}


def get_predictor(name: str) -> BasePredictor:
    """Instantiate a predictor by name.

    Lazy-imports the module so only the requested model's
    dependencies are loaded.

    Args:
        name: Model key from AVAILABLE_MODELS (e.g. "rl", "cnn").

    Returns:
        An unloaded predictor instance. Call .load(path) before .predict().

    Raises:
        KeyError: If the model name is not registered.
    """
    if name not in AVAILABLE_MODELS:
        available = ", ".join(sorted(AVAILABLE_MODELS.keys()))
        raise KeyError(f"Unknown model '{name}'. Available: {available}")

    module_path, class_name = AVAILABLE_MODELS[name]
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls()


def list_models() -> list[str]:
    """Return names of all registered models."""
    return sorted(AVAILABLE_MODELS.keys())
