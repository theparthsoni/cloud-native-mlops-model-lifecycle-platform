import json
import math
import os
from typing import Any, Dict, List

import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

from services.common.config import settings
from services.common.db import get_predlog_connection
from services.common.errors import DriftDetectionError
from services.common.logging import setup_logging

logger = setup_logging("drift")


def psi(expected: List[float], actual: List[float], eps: float = 1e-6) -> float:
    """Population Stability Index for two distributions over the same bins."""
    if len(expected) != len(actual):
        raise ValueError("expected/actual length mismatch")

    total = 0.0
    for expected_value, actual_value in zip(expected, actual):
        expected_value = max(float(expected_value), eps)
        actual_value = max(float(actual_value), eps)
        total += (actual_value - expected_value) * math.log(actual_value / expected_value)
    return float(total)


def load_reference_stats(client: MlflowClient, model_name: str) -> Dict[str, Any]:
    versions = client.get_latest_versions(model_name, stages=["Production"])
    if not versions:
        raise DriftDetectionError(f"No Production model found for {model_name}")

    model_version = versions[0]
    run_id = model_version.run_id

    local_dir = client.download_artifacts(run_id, "drift")
    ref_file = os.path.join(local_dir, "reference_stats.json")
    with open(ref_file, "r", encoding="utf-8") as file:
        return json.load(file)


def fetch_recent_features(hours: int) -> pd.DataFrame:
    connection = get_predlog_connection()
    try:
        query = f"""
        SELECT features
        FROM prediction_logs
        WHERE ts >= NOW() - INTERVAL '{int(hours)} hours'
          AND status = 'success'
        ORDER BY ts DESC
        LIMIT 5000;
        """
        df = pd.read_sql(query, connection)
        if df.empty:
            return pd.DataFrame()
        return pd.json_normalize(df["features"].apply(lambda value: value))
    finally:
        connection.close()


def compute_drift(reference: Dict[str, Any], recent: pd.DataFrame) -> Dict[str, float]:
    output: Dict[str, float] = {}
    features = reference.get("features", {})

    for column, stats in features.items():
        if column not in recent.columns:
            continue

        edges = stats.get("bin_edges")
        expected = stats.get("proportions")
        if not edges or not expected:
            continue

        series = pd.to_numeric(recent[column], errors="coerce").dropna()
        if series.empty:
            continue

        bins = pd.cut(series, bins=edges, include_lowest=True)
        actual = bins.value_counts(normalize=True).sort_index().tolist()

        if len(actual) != len(expected):
            continue

        output[column] = psi(expected, actual)

    return output


def push_metrics(model_name: str, drift_scores: Dict[str, float]) -> None:
    if not settings.DRIFT_PUSHGATEWAY_URL:
        logger.info("No pushgateway configured; skipping metric push")
        return

    registry = CollectorRegistry()
    gauge = Gauge(
        "model_feature_psi",
        "Population Stability Index by feature",
        ["model_name", "feature"],
        registry=registry,
    )

    max_score = 0.0
    for feature, score in drift_scores.items():
        gauge.labels(model_name=model_name, feature=feature).set(score)
        max_score = max(max_score, score)

    max_gauge = Gauge(
        "model_max_feature_psi",
        "Maximum feature PSI across all monitored features",
        ["model_name"],
        registry=registry,
    )
    max_gauge.labels(model_name=model_name).set(max_score)

    push_to_gateway(
        settings.DRIFT_PUSHGATEWAY_URL,
        job="model_drift",
        registry=registry,
    )


def main() -> None:
    logger.info("Starting drift detection for model '%s'", settings.MODEL_NAME)

    try:
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        client = MlflowClient(tracking_uri=settings.MLFLOW_TRACKING_URI)

        reference = load_reference_stats(client, settings.MODEL_NAME)
        recent = fetch_recent_features(settings.DRIFT_LOOKBACK_HOURS)

        if recent.empty:
            logger.info("No recent production features found; exiting without drift result")
            return

        drift_scores = compute_drift(reference, recent)
        if not drift_scores:
            logger.info("No comparable features found for drift calculation")
            return

        push_metrics(settings.MODEL_NAME, drift_scores)

        max_psi = max(drift_scores.values())
        drift_detected = max_psi >= settings.DRIFT_PSI_THRESHOLD

        logger.info(
            "Drift detection completed: %s",
            json.dumps(
                {
                    "model_name": settings.MODEL_NAME,
                    "lookback_hours": settings.DRIFT_LOOKBACK_HOURS,
                    "max_psi": max_psi,
                    "threshold": settings.DRIFT_PSI_THRESHOLD,
                    "drift_detected": drift_detected,
                    "feature_count": len(drift_scores),
                }
            ),
        )

        if drift_detected:
            raise DriftDetectionError(
                f"Drift detected for model '{settings.MODEL_NAME}' with max PSI={max_psi:.4f}"
            )

    except DriftDetectionError:
        logger.exception("Drift threshold breached")
        raise
    except Exception as exc:
        logger.exception("Drift detection failed")
        raise DriftDetectionError(f"Drift detection failed: {exc}") from exc


if __name__ == "__main__":
    main()