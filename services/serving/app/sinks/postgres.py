from __future__ import annotations

from typing import Any, Dict

from psycopg2.extras import Json

from services.common.db import get_predlog_connection
from services.common.errors import DatabaseError
from services.common.logging import setup_logging

from .base import PredictionSink

logger = setup_logging("serving-postgres-sink")


class PostgresPredictionSink(PredictionSink):
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
        connection = None
        try:
            connection = get_predlog_connection()
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO prediction_logs
                      (request_id, model_name, model_version, features, prediction, latency_ms, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        request_id,
                        model_name,
                        model_version,
                        Json(features),
                        Json(prediction),
                        float(latency_ms),
                        status,
                    ),
                )
            connection.commit()
        except Exception as exc:
            logger.exception("Failed to write prediction log")
            raise DatabaseError(f"Failed to write prediction log: {exc}") from exc
        finally:
            if connection is not None:
                connection.close()