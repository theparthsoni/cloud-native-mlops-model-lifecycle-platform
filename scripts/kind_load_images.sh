#!/usr/bin/env bash
set -euo pipefail
CLUSTER_NAME=${1:-mlops-local}
shift || true
IMAGES=("$@")

for img in "${IMAGES[@]}"; do
  echo "Loading $img into kind..."
  kind load docker-image --name "${CLUSTER_NAME}" "$img"
done

echo "[OK] loaded images into kind"
