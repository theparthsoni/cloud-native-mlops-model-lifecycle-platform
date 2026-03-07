#!/usr/bin/env bash
set -euo pipefail

IMG_MLFLOW=${1:-mlops-mlflow:latest}
IMG_TRAINER=${2:-mlops-trainer:latest}
IMG_SERVING=${3:-mlops-serving:latest}
IMG_BATCH=${4:-mlops-batch:latest}
IMG_DRIFT=${5:-mlops-drift:latest}
IMG_AIRFLOW=${6:-mlops-airflow:latest}

if command -v minikube >/dev/null 2>&1 && minikube status >/dev/null 2>&1; then
  eval "$(minikube docker-env)"
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

docker build -t "$IMG_MLFLOW" \
  -f "$ROOT_DIR/services/mlflow-image/Dockerfile" \
  "$ROOT_DIR/services/mlflow-image"

docker build -t "$IMG_TRAINER" \
  -f "$ROOT_DIR/services/trainer/Dockerfile" \
  "$ROOT_DIR"

docker build -t "$IMG_SERVING" \
  -f "$ROOT_DIR/services/serving/Dockerfile" \
  "$ROOT_DIR"

docker build -t "$IMG_BATCH" \
  -f "$ROOT_DIR/services/batch/Dockerfile" \
  "$ROOT_DIR"

docker build -t "$IMG_DRIFT" \
  -f "$ROOT_DIR/services/drift/Dockerfile" \
  "$ROOT_DIR"

docker build -t "$IMG_AIRFLOW" \
  -f "$ROOT_DIR/services/airflow-image/Dockerfile" \
  "$ROOT_DIR"

echo "[OK] built images"