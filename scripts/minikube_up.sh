#!/usr/bin/env bash
set -euo pipefail
minikube status >/dev/null 2>&1 || minikube start --cpus=4 --memory=8192
minikube addons enable ingress || true
kubectl cluster-info
