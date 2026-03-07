from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from airflow.kubernetes.secret import Secret

postgres_pw = Secret(
    deploy_type="env",
    deploy_target="PREDLOG_PASSWORD",
    secret="mlops-postgresql",
    key="postgres-password",
)

minio_user = Secret(
    deploy_type="env",
    deploy_target="AWS_ACCESS_KEY_ID",
    secret="mlops-minio",
    key="root-user",
)

minio_pass = Secret(
    deploy_type="env",
    deploy_target="AWS_SECRET_ACCESS_KEY",
    secret="mlops-minio",
    key="root-password",
)

with DAG(
    dag_id="drift_check_and_retrain",
    start_date=datetime(2025, 1, 1),
    schedule="0 * * * *",
    catchup=False,
    tags=["mlops"],
) as dag:

    drift = KubernetesPodOperator(
        name="drift-check",
        task_id="drift-check",
        namespace="mlops-prod",
        image="mlops-drift:latest",
        image_pull_policy="IfNotPresent",
        secrets=[postgres_pw, minio_user, minio_pass],
        env_vars={
            "MLFLOW_TRACKING_URI": "http://mlflow.mlops-platform.svc.cluster.local:5000",
            "MODEL_NAME": "demo_classifier",
            "DRIFT_LOOKBACK_HOURS": "24",
            "DRIFT_PSI_THRESHOLD": "0.2",
            "PREDLOG_HOST": "mlops-postgresql.mlops-platform.svc.cluster.local",
            "PREDLOG_DB": "mlops",
            "PREDLOG_USER": "postgres",
            "MLFLOW_S3_ENDPOINT_URL": "http://mlops-minio.mlops-platform.svc.cluster.local:9000",
            "PUSHGATEWAY_URL": "http://pushgateway.mlops-platform.svc.cluster.local:9091",
        },
        get_logs=True,
        is_delete_operator_pod=True,
    )

    trigger_retrain = TriggerDagRunOperator(
        task_id="trigger_retrain",
        trigger_dag_id="train_register",
        wait_for_completion=False,
        trigger_rule="all_done",
    )

    drift >> trigger_retrain
