SHELL := /bin/bash

KIND_CLUSTER ?= mlops-local
NAMESPACE_PLATFORM ?= mlops-platform
ENV ?= dev

# Images (local)
IMG_MLFLOW  ?= mlops-mlflow:latest
IMG_TRAINER ?= mlops-trainer:latest
IMG_SERVING ?= mlops-serving:latest
IMG_BATCH   ?= mlops-batch:latest
IMG_DRIFT   ?= mlops-drift:latest
IMG_AIRFLOW ?= mlops-airflow:latest

.PHONY: help
help:
	@echo "Targets:"
	@echo "  kind-up, kind-down, minikube-up"
	@echo "  build-images, kind-load"
	@echo "  deploy-platform"
	@echo "  deploy-serving ENV=dev|staging|prod"
	@echo "  deploy-dev, deploy-staging, deploy-prod"
	@echo "  restart-airflow, rebuild-airflow"
	@echo "  teardown"

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

.PHONY: deploy-serving
deploy-serving:
	kubectl apply -k infra/kustomize/serving/overlays/$(ENV)

.PHONY: deploy-dev
deploy-dev:
	$(MAKE) deploy-serving ENV=dev

.PHONY: deploy-staging
deploy-staging:
	$(MAKE) deploy-serving ENV=staging

.PHONY: deploy-prod
deploy-prod:
	$(MAKE) deploy-serving ENV=prod

.PHONY: restart-airflow
restart-airflow:
	kubectl rollout restart deployment/airflow-scheduler -n $(NAMESPACE_PLATFORM)
	kubectl rollout restart deployment/airflow-webserver -n $(NAMESPACE_PLATFORM)
	-kubectl rollout restart deployment/airflow-dag-processor -n $(NAMESPACE_PLATFORM)

.PHONY: deploy-airflow-rbac
deploy-airflow-rbac:
	kubectl apply -k infra/kustomize/airflow-rbac/overlays/dev
	kubectl apply -k infra/kustomize/airflow-rbac/overlays/staging
	kubectl apply -k infra/kustomize/airflow-rbac/overlays/prod

.PHONY: rebuild-airflow
rebuild-airflow: build-images kind-load restart-airflow

.PHONY: teardown
teardown:
	./scripts/teardown.sh