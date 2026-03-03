"""Model interface (BaseModel ABC) and model registry."""

from ai_trading.models.base import MODEL_REGISTRY, BaseModel, get_model_class, register_model

from . import (
    dummy,  # noqa: F401
    xgboost,  # noqa: F401
)

__all__ = ["MODEL_REGISTRY", "BaseModel", "get_model_class", "register_model"]
