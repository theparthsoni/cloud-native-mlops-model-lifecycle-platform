from __future__ import annotations

from typing import Protocol, Any

import pandas as pd


class ModelBackend(Protocol):
    """Strategy interface for model loading + inference."""

    def load(self) -> None:
        ...

    def predict_one(self, df: pd.DataFrame) -> Any:
        ...

    @property
    def model_uri(self) -> str:
        ...

    @property
    def model_version(self) -> str:
        ...
