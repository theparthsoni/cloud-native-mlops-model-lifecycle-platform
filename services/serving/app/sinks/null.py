from __future__ import annotations

from typing import Any, Dict

from services.common.logging import setup_logging

from .base import PredictionSink

logger = setup_logging("serving-null-sink")


class NullSink(PredictionSink):
    def write(
        self,
        *,
        request_id: str,
        model_name: str,
        model_version: str,
        features: Dict[str, float],
        prediction: Any,
        latency_ms: float,
        status: str,
    ) -> None:
        logger.debug(
            "NullSink write skipped for request_id=%s model=%s version=%s",
            request_id,
            model_name,
            model_version,
        )
        return