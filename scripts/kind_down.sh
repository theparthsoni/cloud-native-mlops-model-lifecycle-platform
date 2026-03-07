#!/usr/bin/env bash
set -euo pipefail
CLUSTER_NAME=${1:-mlops-local}
kind delete cluster --name "${CLUSTER_NAME}" || true
