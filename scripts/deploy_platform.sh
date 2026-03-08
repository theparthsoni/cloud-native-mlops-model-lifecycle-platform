#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

kubectl apply -f "$ROOT_DIR/infra/manifests/namespaces.yaml"

helm repo add bitnami https://charts.bitnami.com/bitnami >/dev/null 2>&1 || true
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null 2>&1 || true
helm repo add apache-airflow https://airflow.apache.org >/dev/null 2>&1 || true
helm repo update >/dev/null

helm upgrade --install mlops-postgresql bitnami/postgresql \
  -n mlops-platform \
  -f "$ROOT_DIR/infra/helm/values/postgresql.yaml"

kubectl apply -n mlops-platform -f "$ROOT_DIR/infra/manifests/minio.yaml"

helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n mlops-platform \
  -f "$ROOT_DIR/infra/helm/values/kube-prometheus-stack.yaml"

kubectl apply -n mlops-platform -f "$ROOT_DIR/infra/manifests/pushgateway.yaml"
kubectl apply -n mlops-platform -f "$ROOT_DIR/infra/manifests/mlflow.yaml"
kubectl apply -n mlops-platform -f "$ROOT_DIR/infra/manifests/pushgateway-servicemonitor.yaml"

kubectl apply -k "$ROOT_DIR/infra/kustomize/airflow-rbac/overlays/dev"
kubectl apply -k "$ROOT_DIR/infra/kustomize/airflow-rbac/overlays/staging"
kubectl apply -k "$ROOT_DIR/infra/kustomize/airflow-rbac/overlays/prod"

helm upgrade --install airflow apache-airflow/airflow \
  -n mlops-platform \
  -f "$ROOT_DIR/infra/helm/values/airflow.yaml"

kubectl apply -n mlops-platform -f "$ROOT_DIR/infra/manifests/predlog-init-job.yaml"
kubectl apply -n mlops-platform -f "$ROOT_DIR/infra/manifests/minio-seed-job.yaml"

"$ROOT_DIR/scripts/copy_platform_secrets.sh"

kubectl -n mlops-platform rollout status deploy/mlflow --timeout=180s
kubectl -n mlops-platform rollout status deploy/airflow-webserver --timeout=600s

echo "[OK] platform deployed"

printf "\nUI Access (port-forward):\n"
echo "  MLflow:   kubectl -n mlops-platform port-forward svc/mlflow 5000:5000"
echo "  Airflow:  kubectl -n mlops-platform port-forward svc/airflow-webserver 8080:8080"
echo "  Grafana:  kubectl -n mlops-platform port-forward svc/kube-prometheus-stack-grafana 3000:80"
echo "  MinIO:    kubectl -n mlops-platform port-forward svc/mlops-minio-console 9090:9090"