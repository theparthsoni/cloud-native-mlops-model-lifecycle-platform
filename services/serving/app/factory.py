from __future__ import annotations

import os
from typing import Tuple

from .backends.mlflow_pyfunc import MLflowModelRef, MLflowPyFuncBackend
from .sinks.null import NullSink
from .sinks.postgres import PostgresPredictionSink


def create_backend() -> Tuple[str, MLflowPyFuncBackend]:
    model_name = os.getenv("MODEL_NAME", "demo_classifier")
    stage = os.getenv("MODEL_STAGE", "Production")
    version = os.getenv("MODEL_VERSION")
    tracking_uri = os.environ["MLFLOW_TRACKING_URI"]

    ref = MLflowModelRef(model_name=model_name, stage=stage, version=version)
    backend = MLflowPyFuncBackend(ref=ref, tracking_uri=tracking_uri)
    return model_name, backend


def create_prediction_sink():
    required = ["PREDLOG_HOST", "PREDLOG_DB", "PREDLOG_USER", "PREDLOG_PASSWORD"]
    if all(os.getenv(k) for k in required):
        return PostgresPredictionSink()
    return NullSink()
