from __future__ import annotations

from datetime import datetime
import os

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator


def run_drift_check() -> None:
    """
    Execute drift detection locally without Kubernetes.

    Drift check reads recent production inputs from the prediction_logs table and
    compares them to reference statistics stored as an MLflow artifact.
    """
    from services.drift.drift import main

    os.environ["MLFLOW_TRACKING_URI"] = "http://localhost:5000"
    os.environ["MODEL_NAME"] = "demo_classifier"
    os.environ["DRIFT_LOOKBACK_HOURS"] = "24"
    os.environ["DRIFT_PSI_THRESHOLD"] = "0.2"

    os.environ["PREDLOG_HOST"] = "localhost"
    os.environ["PREDLOG_DB"] = "mlops"
    os.environ["PREDLOG_USER"] = "postgres"
    os.environ["PREDLOG_PASSWORD"] = "postgres"

    os.environ["MLFLOW_S3_ENDPOINT_URL"] = "http://localhost:9000"
    os.environ["AWS_ACCESS_KEY_ID"] = "minio"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "minio12345"

    os.environ["PUSHGATEWAY_URL"] = "http://localhost:9091"

    main()


with DAG(
    dag_id="drift_check_and_retrain",
    start_date=datetime(2025, 1, 1),
    schedule="0 * * * *",
    catchup=False,
    tags=["mlops"],
) as dag:

    drift = PythonOperator(
        task_id="drift_check",
        python_callable=run_drift_check,
    )

    trigger_retrain = TriggerDagRunOperator(
        task_id="trigger_retrain",
        trigger_dag_id="train_register",
        wait_for_completion=False,
        trigger_rule="all_done",
    )

    drift >> trigger_retrain