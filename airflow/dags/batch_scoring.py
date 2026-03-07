from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.models import Variable
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

ENV = Variable.get("deployment_env", default_var="dev")

ENV_CONFIG = {
    "dev": {
        "namespace": "mlops-dev",
        "model_stage": "Staging",
        "batch_input": "s3://mlflow/batch/input/batch_input.csv",
        "batch_output": "s3://mlflow/batch/output/dev_batch_output_predictions.csv",
    },
    "staging": {
        "namespace": "mlops-staging",
        "model_stage": "Staging",
        "batch_input": "s3://mlflow/batch/input/batch_input.csv",
        "batch_output": "s3://mlflow/batch/output/staging_batch_output_predictions.csv",
    },
    "prod": {
        "namespace": "mlops-prod",
        "model_stage": "Production",
        "batch_input": "s3://mlflow/batch/input/batch_input.csv",
        "batch_output": "s3://mlflow/batch/output/prod_batch_output_predictions.csv",
    },
}

if ENV not in ENV_CONFIG:
    raise ValueError(f"Unsupported deployment_env: {ENV}")

cfg = ENV_CONFIG[ENV]

with DAG(
    dag_id="batch_scoring",
    start_date=datetime(2025, 1, 1),
    schedule="0 2 * * *",
    catchup=False,
    tags=["mlops", ENV],
) as dag:
    score = KubernetesPodOperator(
        name="batch-score",
        task_id="batch-score",
        namespace=cfg["namespace"],
        image="mlops-batch:latest",
        image_pull_policy="IfNotPresent",
        cmds=["python", "-m", "services.batch.score"],
        env_vars={
            "MLFLOW_TRACKING_URI": "http://mlflow.mlops-platform.svc.cluster.local:5000",
            "MODEL_NAME": "demo_classifier",
            "MODEL_STAGE": cfg["model_stage"],
            "BATCH_INPUT": cfg["batch_input"],
            "BATCH_OUTPUT": cfg["batch_output"],
            "MLFLOW_S3_ENDPOINT_URL": "http://mlops-minio.mlops-platform.svc.cluster.local:9000",
            "AWS_ACCESS_KEY_ID": "minio",
            "AWS_SECRET_ACCESS_KEY": "minio12345",
        },
        get_logs=True,
        is_delete_operator_pod=False,
        in_cluster=True,
    )