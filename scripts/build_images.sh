#!/usr/bin/env bash
set -euo pipefail
IMG_TRAINER=${1:-mlops-trainer:latest}
IMG_SERVING=${2:-mlops-serving:latest}
IMG_BATCH=${3:-mlops-batch:latest}
IMG_DRIFT=${4:-mlops-drift:latest}

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

docker build -t "$IMG_TRAINER" -f "$ROOT_DIR/services/trainer/Dockerfile" "$ROOT_DIR/services/trainer"
docker build -t "$IMG_SERVING" -f "$ROOT_DIR/services/serving/Dockerfile" "$ROOT_DIR/services/serving"
docker build -t "$IMG_BATCH"   -f "$ROOT_DIR/services/batch/Dockerfile"   "$ROOT_DIR/services/batch"
docker build -t "$IMG_DRIFT"   -f "$ROOT_DIR/services/drift/Dockerfile"   "$ROOT_DIR/services/drift"

echo "[OK] built images"
