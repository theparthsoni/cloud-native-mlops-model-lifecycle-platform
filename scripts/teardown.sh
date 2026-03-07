#!/usr/bin/env bash
set -euo pipefail

kubectl delete -k infra/kustomize/serving/overlays/dev --ignore-not-found
kubectl delete -k infra/kustomize/serving/overlays/staging --ignore-not-found
kubectl delete -k infra/kustomize/serving/overlays/prod --ignore-not-found

helm -n mlops-platform uninstall airflow || true
helm -n mlops-platform uninstall kube-prometheus-stack || true
helm -n mlops-platform uninstall mlops-minio || true
helm -n mlops-platform uninstall mlops-postgresql || true

kubectl delete -f infra/manifests/mlflow.yaml -n mlops-platform --ignore-not-found
kubectl delete -f infra/manifests/pushgateway.yaml -n mlops-platform --ignore-not-found
kubectl delete -f infra/manifests/predlog-init-job.yaml -n mlops-platform --ignore-not-found
kubectl delete -f infra/manifests/namespaces.yaml --ignore-not-found

echo "[OK] removed resources"
