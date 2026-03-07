import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # MLflow
    MLFLOW_TRACKING_URI: str = os.getenv(
        "MLFLOW_TRACKING_URI",
        "http://mlflow.mlops-platform.svc.cluster.local:5000",
    )
    MLFLOW_EXPERIMENT_NAME: str = os.getenv("MLFLOW_EXPERIMENT_NAME", "demo-classifier")

    # Model selection / promotion
    MODEL_NAME: str = os.getenv("MODEL_NAME", "demo_classifier")
    MODEL_STAGE: str = os.getenv("MODEL_STAGE", "Production")
    MODEL_VERSION: str | None = os.getenv("MODEL_VERSION")
    PROMOTE_TO_STAGE: str = os.getenv("PROMOTE_TO_STAGE", "Staging")
    F1_GATE: float = float(os.getenv("F1_GATE", "0.92"))
    GIT_SHA: str = os.getenv("GIT_SHA", "local")

    # Serving auth
    API_KEYS_RAW: str = os.getenv("API_KEYS", "dev-key")

    # Batch IO
    BATCH_INPUT: str = os.getenv("BATCH_INPUT", "s3://data/batch_input.csv")
    BATCH_OUTPUT: str = os.getenv("BATCH_OUTPUT", "s3://data/batch_output_predictions.csv")

    # S3 / MinIO
    MLFLOW_S3_ENDPOINT_URL: str | None = os.getenv("MLFLOW_S3_ENDPOINT_URL")
    AWS_ACCESS_KEY_ID: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")

    # Prediction log DB
    PREDLOG_HOST: str | None = os.getenv("PREDLOG_HOST")
    PREDLOG_DB: str = os.getenv("PREDLOG_DB", "mlops")
    PREDLOG_USER: str = os.getenv("PREDLOG_USER", "postgres")
    PREDLOG_PASSWORD: str | None = os.getenv("PREDLOG_PASSWORD")

    # Drift
    DRIFT_LOOKBACK_HOURS: int = int(os.getenv("DRIFT_LOOKBACK_HOURS", "24"))
    DRIFT_PSI_THRESHOLD: float = float(os.getenv("DRIFT_PSI_THRESHOLD", "0.2"))
    DRIFT_PUSHGATEWAY_URL: str | None = os.getenv("DRIFT_PUSHGATEWAY_URL")


settings = Settings()