from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.models import Variable
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

ENV = Variable.get("deployment_env", default_var="dev")

ENV_CONFIG = {
    "dev": {
        "namespace": "mlops-dev",
        "promote_stage": "Staging",
    },
    "staging": {
        "namespace": "mlops-staging",
        "promote_stage": "Staging",
    },
    "prod": {
        "namespace": "mlops-prod",
        "promote_stage": "Production",
    },
}

if ENV not in ENV_CONFIG:
    raise ValueError(f"Unsupported deployment_env: {ENV}")

cfg = ENV_CONFIG[ENV]

with DAG(
    dag_id="train_register",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["mlops", ENV],
) as dag:
    train = KubernetesPodOperator(
        name="train-model",
        task_id="train-model",
        namespace=cfg["namespace"],
        image="mlops-trainer:latest",
        image_pull_policy="IfNotPresent",
        cmds=["python", "-m", "services.trainer.train"],
        env_vars={
            "MLFLOW_TRACKING_URI": "http://mlflow.mlops-platform.svc.cluster.local:5000",
            "MLFLOW_EXPERIMENT_NAME": "demo-classifier",
            "MODEL_NAME": "demo_classifier",
            "PROMOTE_TO_STAGE": cfg["promote_stage"],
            "F1_GATE": "0.92",
            "MLFLOW_S3_ENDPOINT_URL": "http://mlops-minio.mlops-platform.svc.cluster.local:9000",
            "AWS_ACCESS_KEY_ID": "minio",
            "AWS_SECRET_ACCESS_KEY": "minio12345",
            "GIT_SHA": "local",
            "GIT_PYTHON_REFRESH": "quiet",
        },
        get_logs=True,
        is_delete_operator_pod=False,
        in_cluster=True,
    )