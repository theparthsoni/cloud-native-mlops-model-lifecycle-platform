#!/usr/bin/env bash
set -euo pipefail
CLUSTER_NAME=${1:-mlops-local}

cat > /tmp/kind-mlops-config.yaml <<'YAML'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    kubeadmConfigPatches:
      - |
        kind: InitConfiguration
        nodeRegistration:
          kubeletExtraArgs:
            node-labels: "ingress-ready=true"
    extraPortMappings:
      - containerPort: 80
        hostPort: 8081
        protocol: TCP
      - containerPort: 443
        hostPort: 8443
        protocol: TCP
YAML

if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
  echo "[OK] kind cluster already exists: ${CLUSTER_NAME}"
else
  kind create cluster --name "${CLUSTER_NAME}" --config /tmp/kind-mlops-config.yaml
fi

kubectl cluster-info

if ! kubectl get ns ingress-nginx >/dev/null 2>&1; then
  kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
  echo "[OK] installed ingress-nginx"
fi

