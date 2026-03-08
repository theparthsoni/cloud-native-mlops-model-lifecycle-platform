## Sequence Diagram: End-to-End Lifecycle 

```mermaid
sequenceDiagram
    participant Op as Operator
    participant AF as Airflow
    participant TR as Trainer Pod
    participant MF as MLflow
    participant MI as MinIO
    participant SV as Serving API
    participant CL as Client
    participant PG as PostgreSQL
    participant DR as Drift Pod
    participant PW as Pushgateway

    Op->>AF: Deploy platform and enable DAGs
    AF->>TR: Start train_register job
    TR->>TR: Load sklearn breast_cancer dataset
    TR->>TR: Train StandardScaler + LogisticRegression pipeline
    TR->>MF: Log params, metrics, tags, model
    MF->>MI: Store model artifact + reference_stats.json
    TR->>MF: Register model version
    TR->>MF: Promote version if F1 >= gate

    CL->>SV: POST /predict with x-api-key
    SV->>MF: Load current model by stage/version
    MF-->>SV: Model artifact reference
    SV->>PG: Insert prediction_logs row
    SV-->>CL: prediction + model_uri + model_version + request_id

    AF->>DR: Start drift_check job
    DR->>MF: Download reference_stats.json
    DR->>PG: Query recent successful features
    DR->>DR: Compute PSI by feature
    DR->>PW: Push PSI metrics
    alt PSI >= threshold
        DR-->>AF: Task failure (DriftDetectionError)
        AF->>AF: Trigger train_register DAG
    else PSI below threshold
        DR-->>AF: Task success
    end
```

---

## Sequence Diagram: Realtime Inference 

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI Serving
    participant Backend as MLflowPyFuncBackend
    participant Registry as MLflow Registry
    participant DB as PostgreSQL
    participant Prom as Prometheus

    Client->>API: POST /predict
    API->>API: Validate API key + request body
    API->>Backend: predict_one(DataFrame)
    Backend->>Backend: load() if model not cached
    Backend->>Registry: Resolve stage/version and load model
    Registry-->>Backend: pyfunc model
    Backend-->>API: prediction
    API->>DB: write prediction_logs row
    API-->>Client: JSON response
    Prom->>API: scrape /metrics
    API-->>Prom: counters + latency histogram
```

## Sequence Diagram: Training to Deployment
```mermaid
sequenceDiagram
    participant Operator
    participant Airflow
    participant Trainer
    participant MLflow
    participant MinIO
    participant ServingAPI

    Operator->>Airflow: Trigger training DAG
    Airflow->>Trainer: Launch Kubernetes trainer job
    Trainer->>Trainer: Load dataset and train model
    Trainer->>MLflow: Log run and register model
    MLflow->>MinIO: Store model artifact
    MLflow-->>Trainer: Registration complete
    Trainer-->>Airflow: Training finished
    Airflow-->>Operator: DAG success
    ServingAPI->>MLflow: Load Production model
    MLflow->>MinIO: Fetch model artifact
    MLflow-->>ServingAPI: Return model reference
    ServingAPI->>ServingAPI: Ready to serve requests
```

## Sequence Diagram: Prediction Request
```mermaid
sequenceDiagram
    participant Client
    participant API as Serving API
    participant MLflow
    participant Postgres
    participant Prometheus

    Client->>API: POST /predict
    API->>MLflow: Resolve production model
    MLflow-->>API: Model artifact / URI
    API->>API: Execute inference
    API->>Postgres: Insert prediction log
    API-->>Client: Prediction response
    Prometheus->>API: Scrape /metrics
    API-->>Prometheus: Request metrics
```

## Sequence Diagram: Drift Monitoring Loop
```mermaid
sequenceDiagram
    participant Airflow
    participant Drift as Drift Job
    participant Postgres
    participant MLflow
    participant Pushgateway
    participant Prometheus
    participant Grafana

    Airflow->>Drift: Launch drift detection job
    Drift->>Postgres: Read recent inference feature data
    Drift->>MLflow: Download reference statistics artifact
    MLflow-->>Drift: Reference stats
    Drift->>Drift: Compute PSI / drift metrics
    Drift->>Pushgateway: Push metrics
    Prometheus->>Pushgateway: Scrape drift metrics
    Pushgateway-->>Prometheus: Return metrics
    Grafana->>Prometheus: Query metrics
    Prometheus-->>Grafana: Drift time series
```