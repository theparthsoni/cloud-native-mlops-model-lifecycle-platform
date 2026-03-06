from __future__ import annotations

from typing import Any, Dict, Protocol


class PredictionSink(Protocol):
    """Adapter interface for storing inference telemetry."""

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
        ...
