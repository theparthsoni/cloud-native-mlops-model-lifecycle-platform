from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

# Uses trainer image to train + log to MLflow + register model.

with DAG(
    dag_id="train_register",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["mlops"],
) as dag:

    train = KubernetesPodOperator(
        name="train-model",
        task_id="train-model",
        namespace="mlops-dev",
        image="mlops-trainer:latest",
        image_pull_policy="IfNotPresent",
        env_vars={
            "MLFLOW_TRACKING_URI": "http://mlflow.mlops-platform.svc.cluster.local:5000",
            "MLFLOW_EXPERIMENT_NAME": "demo-classifier",
            "MODEL_NAME": "demo_classifier",
            "PROMOTE_TO_STAGE": "Staging",
            "F1_GATE": "0.92",
            # MinIO for artifacts
            "MLFLOW_S3_ENDPOINT_URL": "http://mlops-minio.mlops-platform.svc.cluster.local:9000",
            "AWS_ACCESS_KEY_ID": "minio",
            "AWS_SECRET_ACCESS_KEY": "minio12345",
        },
        get_logs=True,
        is_delete_operator_pod=True,
    )
