from __future__ import annotations

from typing import Tuple

from services.common.config import settings

from .backends.mlflow_pyfunc import MLflowModelRef, MLflowPyFuncBackend
from .sinks.null import NullSink
from .sinks.postgres import PostgresPredictionSink


def create_backend() -> Tuple[str, MLflowPyFuncBackend]:
    ref = MLflowModelRef(
        model_name=settings.MODEL_NAME,
        stage=settings.MODEL_STAGE,
        version=settings.MODEL_VERSION,
    )
    backend = MLflowPyFuncBackend(
        ref=ref,
        tracking_uri=settings.MLFLOW_TRACKING_URI,
    )
    return settings.MODEL_NAME, backend


def create_prediction_sink():
    if settings.PREDLOG_HOST and settings.PREDLOG_PASSWORD:
        return PostgresPredictionSink()
    return NullSink()