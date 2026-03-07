from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

with DAG(
    dag_id="batch_scoring",
    start_date=datetime(2025, 1, 1),
    schedule="0 2 * * *",
    catchup=False,
    tags=["mlops"],
) as dag:

    score = KubernetesPodOperator(
        name="batch-score",
        task_id="batch-score",
        namespace="mlops-prod",
        image="mlops-batch:latest",
        image_pull_policy="IfNotPresent",
        env_vars={
            "MLFLOW_TRACKING_URI": "http://mlflow.mlops-platform.svc.cluster.local:5000",
            "MODEL_NAME": "demo_classifier",
            "MODEL_STAGE": "Production",
            "BATCH_INPUT": "s3://data/batch_input.csv",
            "BATCH_OUTPUT": "s3://data/batch_output_predictions.csv",
            "MLFLOW_S3_ENDPOINT_URL": "http://mlops-minio.mlops-platform.svc.cluster.local:9000",
            "AWS_ACCESS_KEY_ID": "minio",
            "AWS_SECRET_ACCESS_KEY": "minio12345",
        },
        get_logs=True,
        is_delete_operator_pod=True,
    )
