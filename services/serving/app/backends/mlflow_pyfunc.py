from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Optional

import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient

from services.common.errors import ModelLoadError
from services.common.logging import setup_logging

logger = setup_logging("serving-backend")


@dataclass(frozen=True)
class MLflowModelRef:
    model_name: str
    stage: Optional[str] = None
    version: Optional[str] = None


class MLflowPyFuncBackend:
    """MLflow pyfunc backend.

    Loads a model either by explicit version or by stage.
    Supports hot reload when the stage's latest version changes.
    """

    def __init__(self, ref: MLflowModelRef, tracking_uri: str):
        self._ref = ref
        self._tracking_uri = tracking_uri
        self._client = MlflowClient(tracking_uri=tracking_uri)
        mlflow.set_tracking_uri(tracking_uri)

        self._lock = threading.Lock()
        self._model = None
        self._model_uri = ""
        self._loaded_version = ""

    def _resolve_uri(self) -> str:
        if self._ref.version:
            return f"models:/{self._ref.model_name}/{self._ref.version}"
        stage = self._ref.stage or "Production"
        return f"models:/{self._ref.model_name}/{stage}"

    def _resolve_version(self) -> str:
        if self._ref.version:
            return str(self._ref.version)
        stage = self._ref.stage or "Production"
        versions = self._client.get_latest_versions(self._ref.model_name, stages=[stage])
        if not versions:
            raise ModelLoadError(
                f"No versions found for model '{self._ref.model_name}' in stage '{stage}'"
            )
        return str(versions[0].version)

    def load(self) -> None:
        target_version = self._resolve_version()

        with self._lock:
            if self._model is not None and target_version == self._loaded_version:
                return

            uri = self._resolve_uri()
            logger.info(
                "Loading model '%s' from uri='%s' target_version='%s'",
                self._ref.model_name,
                uri,
                target_version,
            )

            try:
                self._model = mlflow.pyfunc.load_model(uri)
            except Exception as exc:
                raise ModelLoadError(f"Failed to load model from uri '{uri}': {exc}") from exc

            self._model_uri = uri
            self._loaded_version = target_version

    def predict_one(self, df: pd.DataFrame) -> Any:
        self.load()
        with self._lock:
            if self._model is None:
                raise ModelLoadError("Model is not loaded")
            return self._model.predict(df)[0]

    @property
    def model_uri(self) -> str:
        return self._model_uri

    @property
    def model_version(self) -> str:
        return self._loaded_version

    def force_reload(self) -> None:
        with self._lock:
            self._model = None
            logger.info("Forced model reload requested for '%s'", self._ref.model_name)