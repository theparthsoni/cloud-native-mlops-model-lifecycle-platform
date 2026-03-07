import hashlib
import json
import time
from typing import Any, Dict

import mlflow
import pandas as pd
from mlflow.models.signature import infer_signature
from mlflow.tracking import MlflowClient
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from services.common.config import settings
from services.common.errors import ModelLoadError
from services.common.logging import setup_logging

logger = setup_logging("trainer")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_reference_stats(df_features: pd.DataFrame) -> Dict[str, Any]:
    """Compute reference feature distribution stats for drift detection."""
    stats: Dict[str, Any] = {
        "version": 1,
        "created_at": int(time.time()),
        "features": {},
    }

    for col in df_features.columns:
        series = pd.to_numeric(df_features[col], errors="coerce").dropna()
        if series.empty:
            logger.warning("Skipping feature '%s' because it has no valid numeric values", col)
            continue

        quantiles = series.quantile(
            [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        ).tolist()

        edges = [float(quantiles[0])]
        for q in quantiles[1:]:
            qf = float(q)
            if qf > edges[-1]:
                edges.append(qf)

        if len(edges) < 3:
            logger.warning("Skipping feature '%s' because bin edges are insufficient", col)
            continue

        bins = pd.cut(series, bins=edges, include_lowest=True)
        proportions = bins.value_counts(normalize=True).sort_index().tolist()

        stats["features"][col] = {
            "bin_edges": edges,
            "proportions": proportions,
            "count": int(series.shape[0]),
        }

    return stats


def main() -> None:
    logger.info("Starting training pipeline for model '%s'", settings.MODEL_NAME)

    try:
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)

        data = load_breast_cancer(as_frame=True)
        df = data.frame.copy()

        X = df.drop(columns=["target"])
        y = df["target"]

        data_hash = sha256_bytes(pd.util.hash_pandas_object(df, index=True).values.tobytes())

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=42,
            stratify=y,
        )

        pipeline = Pipeline(
            [
                ("scaler", StandardScaler(with_mean=True, with_std=True)),
                ("clf", LogisticRegression(max_iter=200)),
            ]
        )

        with mlflow.start_run() as run:
            run_id = run.info.run_id
            logger.info("Started MLflow run: %s", run_id)

            mlflow.log_param("model_type", "logreg")
            mlflow.log_param("max_iter", 200)
            mlflow.set_tag("data_hash", data_hash)
            mlflow.set_tag("framework", "scikit-learn")
            mlflow.set_tag("train_timestamp", int(time.time()))
            mlflow.set_tag("git_sha", settings.GIT_SHA)

            pipeline.fit(X_train, y_train)
            predictions = pipeline.predict(X_test)

            accuracy = float(accuracy_score(y_test, predictions))
            f1 = float(f1_score(y_test, predictions))

            mlflow.log_metric("accuracy", accuracy)
            mlflow.log_metric("f1", f1)

            logger.info(
                "Training complete for run_id=%s accuracy=%.4f f1=%.4f",
                run_id,
                accuracy,
                f1,
            )

            reference_stats = compute_reference_stats(X_train)
            reference_path = "/tmp/reference_stats.json"
            with open(reference_path, "w", encoding="utf-8") as file:
                json.dump(reference_stats, file)

            mlflow.log_artifact(reference_path, artifact_path="drift")

            signature = infer_signature(X_test, predictions)
            mlflow.sklearn.log_model(
                sk_model=pipeline,
                artifact_path="model",
                signature=signature,
                registered_model_name=settings.MODEL_NAME,
                input_example=X_test.iloc[:5],
            )

            client = MlflowClient()
            versions = client.search_model_versions(f"name='{settings.MODEL_NAME}'")

            version = None
            for model_version in versions:
                if model_version.run_id == run_id:
                    version = model_version.version
                    break

            if version is None:
                version = str(max(int(model_version.version) for model_version in versions))

            client.set_model_version_tag(settings.MODEL_NAME, version, "reference_run_id", run_id)
            client.set_model_version_tag(
                settings.MODEL_NAME,
                version,
                "reference_artifact_path",
                "drift/reference_stats.json",
            )

            promoted = False
            if settings.PROMOTE_TO_STAGE and f1 >= settings.F1_GATE:
                client.transition_model_version_stage(
                    name=settings.MODEL_NAME,
                    version=version,
                    stage=settings.PROMOTE_TO_STAGE,
                    archive_existing_versions=False,
                )
                promoted = True
                client.set_model_version_tag(settings.MODEL_NAME, version, "gate_passed", "true")
                logger.info(
                    "Promoted model '%s' version '%s' to stage '%s'",
                    settings.MODEL_NAME,
                    version,
                    settings.PROMOTE_TO_STAGE,
                )
            else:
                client.set_model_version_tag(settings.MODEL_NAME, version, "gate_passed", "false")
                logger.info(
                    "Model '%s' version '%s' did not pass promotion gate",
                    settings.MODEL_NAME,
                    version,
                )

            logger.info(
                "Training pipeline completed successfully: %s",
                json.dumps(
                    {
                        "run_id": run_id,
                        "model_name": settings.MODEL_NAME,
                        "model_version": version,
                        "promoted": promoted,
                        "metrics": {"accuracy": accuracy, "f1": f1},
                        "data_hash": data_hash,
                    }
                ),
            )

    except Exception as exc:
        logger.exception("Training pipeline failed")
        raise ModelLoadError(f"Training pipeline failed: {exc}") from exc


if __name__ == "__main__":
    main()