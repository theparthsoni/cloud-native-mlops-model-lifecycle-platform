#!/usr/bin/env bash
set -euo pipefail

PLATFORM_NS="mlops-platform"
TARGET_NAMESPACES=("mlops-dev" "mlops-staging" "mlops-prod")
SECRETS=("mlops-postgresql" "mlops-minio")

copy_secret() {
  local secret_name="$1"
  local target_ns="$2"

  kubectl get secret "$secret_name" -n "$PLATFORM_NS" -o json | \
    jq --arg ns "$target_ns" '
      del(
        .metadata.annotations,
        .metadata.creationTimestamp,
        .metadata.managedFields,
        .metadata.ownerReferences,
        .metadata.resourceVersion,
        .metadata.selfLink,
        .metadata.uid
      )
      | .metadata.namespace = $ns
    ' | kubectl apply -f -

  echo "[OK] copied ${secret_name} to ${target_ns}"
}

for ns in "${TARGET_NAMESPACES[@]}"; do
  kubectl get namespace "$ns" >/dev/null 2>&1 || kubectl create namespace "$ns"

  for secret in "${SECRETS[@]}"; do
    copy_secret "$secret" "$ns"
  done
done