import os
import time
import json
import hashlib
from typing import Dict, Any

import pandas as pd
import mlflow
from mlflow.tracking import MlflowClient
from mlflow.models.signature import infer_signature

from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, accuracy_score


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def compute_reference_stats(df_features: pd.DataFrame) -> Dict[str, Any]:
    stats: Dict[str, Any] = {"version": 1, "created_at": int(time.time()), "features": {}}

    for col in df_features.columns:
        series = pd.to_numeric(df_features[col], errors="coerce")
        series = series.dropna()
        if series.empty:
            continue

        qs = series.quantile([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]).tolist()
        edges = [float(qs[0])]
        for q in qs[1:]:
            if float(q) > edges[-1]:
                edges.append(float(q))
        if len(edges) < 3:
            continue

        bins = pd.cut(series, bins=edges, include_lowest=True)
        proportions = (bins.value_counts(normalize=True).sort_index()).tolist()

        stats["features"][col] = {
            "bin_edges": edges,
            "proportions": proportions,
            "count": int(series.shape[0]),
        }

    return stats


def main() -> None:
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow.mlops-platform.svc.cluster.local:5000")
    experiment = os.getenv("MLFLOW_EXPERIMENT_NAME", "demo-classifier")
    model_name = os.getenv("MODEL_NAME", "demo_classifier")
    promote_to = os.getenv("PROMOTE_TO_STAGE", "Staging")
    f1_gate = float(os.getenv("F1_GATE", "0.92"))

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment)

    data = load_breast_cancer(as_frame=True)
    df = data.frame.copy()

    X = df.drop(columns=["target"])
    y = df["target"]

    data_hash = sha256_bytes(pd.util.hash_pandas_object(df, index=True).values.tobytes())

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipe = Pipeline([
        ("scaler", StandardScaler(with_mean=True, with_std=True)),
        ("clf", LogisticRegression(max_iter=200)),
    ])

    with mlflow.start_run() as run:
        run_id = run.info.run_id

        mlflow.log_param("model_type", "logreg")
        mlflow.log_param("max_iter", 200)
        mlflow.set_tag("data_hash", data_hash)
        mlflow.set_tag("framework", "scikit-learn")
        mlflow.set_tag("train_timestamp", int(time.time()))
        mlflow.set_tag("git_sha", os.getenv("GIT_SHA", "local"))

        pipe.fit(X_train, y_train)
        preds = pipe.predict(X_test)

        acc = float(accuracy_score(y_test, preds))
        f1 = float(f1_score(y_test, preds))

        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("f1", f1)

        ref_stats = compute_reference_stats(X_train)
        ref_path = "/tmp/reference_stats.json"
        with open(ref_path, "w", encoding="utf-8") as f:
            json.dump(ref_stats, f)
        mlflow.log_artifact(ref_path, artifact_path="drift")

        signature = infer_signature(X_test, preds)
        mlflow.sklearn.log_model(
            sk_model=pipe,
            artifact_path="model",
            signature=signature,
            registered_model_name=model_name,
            input_example=X_test.iloc[:5],
        )

        client = MlflowClient()
        versions = client.search_model_versions(f"name='{model_name}'")
        version = None
        for v in versions:
            if v.run_id == run_id:
                version = v.version
                break
        if version is None:
            version = str(max(int(v.version) for v in versions))

        client.set_model_version_tag(model_name, version, "reference_run_id", run_id)
        client.set_model_version_tag(model_name, version, "reference_artifact_path", "drift/reference_stats.json")

        promoted = False
        if promote_to and f1 >= f1_gate:
            client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=promote_to,
                archive_existing_versions=False,
            )
            promoted = True
            client.set_model_version_tag(model_name, version, "gate_passed", "true")
        else:
            client.set_model_version_tag(model_name, version, "gate_passed", "false")

        print(json.dumps({
            "run_id": run_id,
            "model_name": model_name,
            "model_version": version,
            "promoted": promoted,
            "metrics": {"accuracy": acc, "f1": f1},
            "data_hash": data_hash,
        }))


if __name__ == "__main__":
    main()
