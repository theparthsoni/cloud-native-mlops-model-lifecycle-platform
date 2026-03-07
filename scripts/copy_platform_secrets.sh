#!/usr/bin/env bash
set -euo pipefail

# Copy platform secrets into model namespaces for demo convenience.
# In production, use External Secrets/Vault and avoid copying secrets across namespaces.

SRC_NS=mlops-platform
TARGETS=(mlops-dev mlops-staging mlops-prod)
SECRETS=(mlops-postgresql mlops-minio)

for ns in "${TARGETS[@]}"; do
  kubectl get ns "$ns" >/dev/null
  for secret in "${SECRETS[@]}"; do
    kubectl -n "$SRC_NS" get secret "$secret" -o yaml \
      | sed "s/namespace: $SRC_NS/namespace: $ns/" \
      | kubectl apply -n "$ns" -f -
    echo "[OK] copied $secret to $ns"
  done
done
