from __future__ import annotations

import os
from typing import Any, Dict, Optional

import psycopg2
from psycopg2.extras import Json

from .base import PredictionSink


class PostgresPredictionSink(PredictionSink):
    def __init__(self):
        self._host = os.getenv("PREDLOG_HOST")
        self._db = os.getenv("PREDLOG_DB")
        self._user = os.getenv("PREDLOG_USER")
        self._password = os.getenv("PREDLOG_PASSWORD")

    def _connect(self):
        if not all([self._host, self._db, self._user, self._password]):
            return None
        return psycopg2.connect(host=self._host, dbname=self._db, user=self._user, password=self._password)

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
        conn = None
        try:
            conn = self._connect()
            if conn is None:
                return
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO prediction_logs
                      (request_id, model_name, model_version, features, prediction, latency_ms, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (request_id, model_name, model_version, Json(features), Json(prediction), float(latency_ms), status),
                )
            conn.commit()
        finally:
            if conn is not None:
                conn.close()
