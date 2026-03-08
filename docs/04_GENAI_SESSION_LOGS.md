# GenAI Session Logs

This document records how **Generative AI (ChatGPT, Claude, Perplexity)** was used during the development of the platform.

GenAI was used as a **technical assistant for troubleshooting and documentation support**, similar to consulting technical documentation or developer forums.

All **system architecture, implementation, and engineering decisions were visioned and implemented manually.**

---

# 1. Troubleshooting Sessions

This section documents runtime errors encountered during development and how GenAI assisted with debugging and diagnosis.

---

## 1.1 Kubernetes PVC Error

### Problem

During **MinIO deployment**, the following error appeared:

```text
Error from server (NotFound):
persistentvolumeclaims "mlops-minio" not found
```

### Prompt Used

```
Why is Kubernetes showing PVC not found when deploying MinIO Helm chart?
```

### Diagnosis

The Helm chart expected a **PersistentVolumeClaim (PVC)** but the configuration did not automatically create one.

### Resolution

Updated MinIO Helm values:

```yaml
persistence:
  enabled: true
  size: 10Gi
```

After redeployment the **PVC was created successfully**.

---

## 1.2 Kubernetes Pod Stuck in ContainerCreating

### Error

```
container "psql" in pod "predlog-init" is waiting to start: ContainerCreating
```

### Prompt Used

```
Why is Kubernetes Job stuck in ContainerCreating state?
```

### Diagnosis

Kubernetes was still:

* scheduling the container
* pulling the container image

### Resolution

Verified pod state using:

```bash
kubectl get pods -n mlops-platform
```

The job later started and completed successfully.

---

## 1.3 Airflow UI Port Conflict

### Error

```
Unable to listen on port 8080
bind: address already in use
```

### Prompt Used

```
How to fix port-forward conflict when running kubectl port-forward?
```

### Diagnosis

Another `kubectl port-forward` process had already bound port **8080**.

### Resolution

Identified the process:

```bash
lsof -i :8080
```

Killed the process and restarted port-forward.

---

## 1.4 Airflow Logs Not Loading

### Error

```
Could not read served logs:
NameResolutionError: Failed to resolve
```

### Prompt Used

```
Airflow KubernetesPodOperator logs cannot resolve pod hostname
```

### Diagnosis

Airflow log retrieval may fail when:

* pod hostnames change
* DNS propagation delays occur

### Resolution

Logs were accessed directly using the Kubernetes API:

```bash
kubectl logs job/<job-name>
```

---

## 1.5 MLflow Artifact Download Failure

### Error

```
Failed to load model from uri 'models:/demo_classifier/Staging':
No module named 'boto3'
```

### Prompt Used

```
MLflow loading model from S3 fails with boto3 missing
```

### Diagnosis

MLflow requires **boto3** when artifacts are stored in **S3-compatible storage (MinIO)**.

The serving container lacked this dependency.

### Resolution

Added dependency:

```
boto3
```

to the serving container requirements and rebuilt the image.

---

## 1.6 Prediction API Failure

### Error

```
Object of type int64 is not JSON serializable
```

### Prompt Used

```
FastAPI JSON serialization error numpy.int64
```

### Diagnosis

Numpy integers returned from the model are **not JSON serializable**.

### Resolution

Converted prediction values to Python primitives:

```python
prediction = int(prediction)
```

After patching, predictions succeeded.

---

## 1.7 Drift Detection Dependency Failure

### Error

```
No module named 'boto3'
```

### Prompt Used

```
MLflow drift detection job failing due to boto3 missing
```

### Diagnosis

The drift container also loads models from the **MLflow artifact store (MinIO)**.

### Resolution

Added `boto3` to drift container dependencies.

Rebuilt images:

```bash
make build-images
make kind-load
```

---

## 1.8 Drift Detection Triggering Retraining

### Output

```
max_psi = 12.46
threshold = 0.2
drift_detected = true
```

### Prompt Used

```
Drift DAG failing intentionally when drift detected
```

### Diagnosis

The DAG intentionally raises an exception when drift exceeds the threshold to trigger retraining.

### Workflow

```
drift-check (fails)
     ↓
TriggerDagRunOperator
     ↓
train_register DAG
```

The failure therefore indicates **correct pipeline behavior**.

---

## 1.9 Namespace Environment Switch Failure

### Problem

After updating the Airflow variable:

```
deployment_env = staging
```

training jobs failed.

### Prompt Used

```
Why KubernetesPodOperator not creating pods in new namespace?
```

### Diagnosis

Airflow lacked **RBAC permissions** in the `mlops-staging` namespace.

### Resolution

Implemented **environment-scoped RBAC using Kustomize overlays**.

```
infra/kustomize/airflow-rbac
 ├─ base
 └─ overlays
      ├─ dev
      ├─ staging
      └─ prod
```

Applied RBAC:

```bash
kubectl apply -k overlays/dev
kubectl apply -k overlays/staging
kubectl apply -k overlays/prod
```

---

## 1.10 Deployment Script Update

### Problem

The deployment bootstrap script still used a static RBAC manifest.

### Prompt Used

```
Should deploy_platform.sh be updated for Kustomize RBAC overlays?
```

### Resolution

Replaced:

```bash
kubectl apply -f airflow-rbac.yaml
```

with:

```bash
kubectl apply -k airflow-rbac/overlays/dev
kubectl apply -k airflow-rbac/overlays/staging
kubectl apply -k airflow-rbac/overlays/prod
```

---

# 2. Documentation and Diagram Assistance

GenAI was also used to assist with **technical documentation formatting and architecture diagram generation**.

---

## 2.1 Architecture Diagram Generation

### Prompt Used

```
Generate a clean Mermaid architecture diagram for a Kubernetes-based MLOps platform including Airflow, MLflow, MinIO, PostgreSQL, Prometheus, Grafana, and environment namespaces.
```

### Outcome

Generated Mermaid diagrams used in:

```
docs/01_ARCHITECTURE_DESIGN.md
```

---

## 2.2 Sequence Diagram Generation

### Prompt Used

```
Create Mermaid sequence diagrams for training pipeline, prediction API flow, and drift monitoring loop in an MLOps platform.
```

### Outcome

Generated diagrams integrated into:

```
docs/03_SEQUENCES.md
```

---

## 2.3 Architecture Documentation Structuring

### Prompt Used

```
Help structure a technical architecture document for an MLOps platform including system architecture, components, lifecycle, deployment topology, and monitoring.
```

### Outcome

Used to organize documentation in:

```
docs/01_ARCHITECTURE_DESIGN.md
```

---

## 2.4 ML Lifecycle Documentation

### Prompt Used

```
Explain the ML lifecycle for a Kubernetes-based MLOps platform including training, model registry, serving, batch scoring, drift detection, and retraining triggers.
```

### Outcome

Documentation incorporated into:

```
docs/02_ML_LIFECYCLE.md
```

---

## 2.5 README Documentation Assistance

### Prompt Used

```
Generate a concise README.md for a cloud-native MLOps platform project including architecture overview, components, deployment instructions, and documentation links.
```

### Outcome

Generated the project **README.md structure**.

---

# 3. Final System Behavior

The platform dynamically supports **multiple environments**.

| Environment | Airflow Variable         | Namespace       | Model Stage |
| ----------- | ------------------------ | --------------- | ----------- |
| Dev         | `deployment_env=dev`     | `mlops-dev`     | Staging     |
| Staging     | `deployment_env=staging` | `mlops-staging` | Staging     |
| Production  | `deployment_env=prod`    | `mlops-prod`    | Production  |

The same **Airflow DAG dynamically targets the correct environment**.

---

# 4. Scope of GenAI Usage

GenAI assistance was limited to:

* troubleshooting runtime errors
* explaining Kubernetes behaviors
* suggesting debugging commands
* generating diagram templates
* improving documentation structure

GenAI **was not used to generate the core platform implementation code**.

---

# 5. Development Ownership & Code References

The core platform was **designed and implemented manually**, including:

* system architecture
* Kubernetes deployment structure
* Airflow DAG workflows
* ML training pipeline
* drift detection logic
* namespace-based environment strategy
* RBAC configuration
* deployment automation scripts
* code modularization and project structure
* Python coding standards
* service design (`trainer`, `serving`, `batch`, `drift`)
* design patterns and configuration management
* monitoring and observability integration

## Code References

Some basic **Python snippets for synthetic data generation** were referenced from publicly available examples (e.g., Scikit-Learn dataset usage).

Example:

```python
from sklearn.datasets import load_breast_cancer
data = load_breast_cancer()
```

These references were used only for **demo dataset generation**, while the overall architecture, engineering design, and platform implementation were developed independently.

GenAI served strictly as a **technical assistant**, similar to consulting documentation or developer forums.
