from __future__ import annotations

from datetime import datetime
import os

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_training() -> None:

    from services.trainer.train import main

    os.environ["MLFLOW_TRACKING_URI"] = "http://localhost:5000"
    os.environ["MLFLOW_EXPERIMENT_NAME"] = "demo-classifier"
    os.environ["MODEL_NAME"] = "demo_classifier"

    os.environ["PROMOTE_TO_STAGE"] = "Production"
    os.environ["F1_GATE"] = "0.92"

    os.environ["MLFLOW_S3_ENDPOINT_URL"] = "http://localhost:9000"
    os.environ["AWS_ACCESS_KEY_ID"] = "minio"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "minio12345"

    main()


with DAG(
    dag_id="train_register",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["mlops"],
) as dag:

    train = PythonOperator(
        task_id="train_model",
        python_callable=run_training,
    )