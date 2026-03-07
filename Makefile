SHELL := /bin/bash

KIND_CLUSTER ?= mlops-local
NAMESPACE_PLATFORM ?= mlops-platform

# Images (local)
IMG_MLFLOW  ?= mlops-mlflow:latest
IMG_TRAINER ?= mlops-trainer:latest
IMG_SERVING ?= mlops-serving:latest
IMG_BATCH   ?= mlops-batch:latest
IMG_DRIFT   ?= mlops-drift:latest
IMG_AIRFLOW ?= mlops-airflow:latest

.PHONY: help
help:
	@echo "Targets: kind-up, kind-down, minikube-up, build-images, kind-load, deploy-platform, deploy-dev, deploy-staging, deploy-prod, teardown"

.PHONY: kind-up
kind-up:
	./scripts/kind_up.sh "$(KIND_CLUSTER)"

.PHONY: kind-down
kind-down:
	./scripts/kind_down.sh "$(KIND_CLUSTER)"

.PHONY: minikube-up
minikube-up:
	./scripts/minikube_up.sh

.PHONY: build-images
build-images:
	./scripts/build_images.sh "$(IMG_MLFLOW)" "$(IMG_TRAINER)" "$(IMG_SERVING)" "$(IMG_BATCH)" "$(IMG_DRIFT)" "$(IMG_AIRFLOW)"

.PHONY: kind-load
kind-load:
	./scripts/kind_load_images.sh "$(KIND_CLUSTER)" "$(IMG_MLFLOW)" "$(IMG_TRAINER)" "$(IMG_SERVING)" "$(IMG_BATCH)" "$(IMG_DRIFT)" "$(IMG_AIRFLOW)"

.PHONY: deploy-platform
deploy-platform:
	./scripts/deploy_platform.sh

.PHONY: deploy-dev
deploy-dev:
	kubectl apply -k infra/kustomize/serving/overlays/dev

.PHONY: deploy-staging
deploy-staging:
	kubectl apply -k infra/kustomize/serving/overlays/staging

.PHONY: deploy-prod
deploy-prod:
	kubectl apply -k infra/kustomize/serving/overlays/prod

.PHONY: teardown
teardown:
	./scripts/teardown.sh
