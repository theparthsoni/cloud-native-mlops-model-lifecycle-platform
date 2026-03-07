#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

# Namespaces
kubectl apply -f "$ROOT_DIR/infra/manifests/namespaces.yaml"

# Helm repos
helm repo add bitnami https://charts.bitnami.com/bitnami >/dev/null 2>&1 || true
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null 2>&1 || true
helm repo add apache-airflow https://airflow.apache.org >/dev/null 2>&1 || true
helm repo update >/dev/null

# Postgres (mlflow backend + pred logging)
helm upgrade --install mlops-postgresql bitnami/postgresql \
  -n mlops-platform \
  -f "$ROOT_DIR/infra/helm/values/postgresql.yaml"

# MinIO (S3 artifact store)
helm upgrade --install mlops-minio bitnami/minio \
  -n mlops-platform \
  -f "$ROOT_DIR/infra/helm/values/minio.yaml"

# Monitoring stack
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n mlops-platform \
  -f "$ROOT_DIR/infra/helm/values/kube-prometheus-stack.yaml"

# Optional pushgateway (for drift metrics)
kubectl apply -n mlops-platform -f "$ROOT_DIR/infra/manifests/pushgateway.yaml"

# MLflow
kubectl apply -n mlops-platform -f "$ROOT_DIR/infra/manifests/mlflow.yaml"

# ServiceMonitor for pushgateway
kubectl apply -n mlops-platform -f "$ROOT_DIR/infra/manifests/pushgateway-servicemonitor.yaml"

# Airflow RBAC (allow creating pods/jobs across namespaces)
kubectl apply -f "$ROOT_DIR/infra/manifests/airflow-rbac.yaml"

# Airflow (custom image includes DAGs)
helm upgrade --install airflow apache-airflow/airflow \
  -n mlops-platform \
  -f "$ROOT_DIR/infra/helm/values/airflow.yaml"

# Prediction log table initializer (idempotent)
kubectl apply -n mlops-platform -f "$ROOT_DIR/infra/manifests/predlog-init-job.yaml"

# Seed MinIO with a sample batch input CSV (optional)
kubectl apply -n mlops-platform -f "$ROOT_DIR/infra/manifests/minio-seed-job.yaml"

# Copy Postgres secret to model namespaces (demo convenience)
"$ROOT_DIR/scripts/copy_platform_secrets.sh"

# Wait a bit for core services
kubectl -n mlops-platform rollout status deploy/mlflow --timeout=180s
kubectl -n mlops-platform rollout status deploy/airflow-webserver --timeout=180s || true

echo "[OK] platform deployed"

echo "\nAccess (port-forward examples):"
echo "  MLflow:   kubectl -n mlops-platform port-forward svc/mlflow 5000:5000"
echo "  Airflow:  kubectl -n mlops-platform port-forward svc/airflow-webserver 8080:8080"
echo "  Grafana:  kubectl -n mlops-platform port-forward svc/kube-prometheus-stack-grafana 3000:80"
