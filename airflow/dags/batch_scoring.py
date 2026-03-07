from __future__ import annotations

from datetime import datetime
import os

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_batch_scoring() -> None:
    from services.batch.score import main

    os.environ["MLFLOW_TRACKING_URI"] = "http://localhost:5000"
    os.environ["MODEL_NAME"] = "demo_classifier"
    os.environ["MODEL_STAGE"] = "Production"

    os.environ["BATCH_INPUT"] = "data/batch_input.csv"
    os.environ["BATCH_OUTPUT"] = "data/batch_output_predictions.csv"

    os.environ["MLFLOW_S3_ENDPOINT_URL"] = "http://localhost:9000"
    os.environ["AWS_ACCESS_KEY_ID"] = "minio"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "minio12345"

    main()


with DAG(
    dag_id="batch_scoring",
    start_date=datetime(2025, 1, 1),
    schedule="0 2 * * *",
    catchup=False,
    tags=["mlops"],
) as dag:

    score = PythonOperator(
        task_id="batch_score",
        python_callable=run_batch_scoring,
    )