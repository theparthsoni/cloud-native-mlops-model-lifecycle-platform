from __future__ import annotations

from typing import Any, Dict

from .base import PredictionSink


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
        return
