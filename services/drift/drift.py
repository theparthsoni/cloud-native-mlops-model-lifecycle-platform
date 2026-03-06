import os
import json
import math
from typing import Dict, Any, List

import pandas as pd
import psycopg2
from mlflow.tracking import MlflowClient
import mlflow

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway


def psi(expected: List[float], actual: List[float], eps: float = 1e-6) -> float:
    """Population Stability Index for two distributions over the same bins."""
    if len(expected) != len(actual):
        raise ValueError("expected/actual length mismatch")

    s = 0.0
    for e, a in zip(expected, actual):
        e = max(float(e), eps)
        a = max(float(a), eps)
        s += (a - e) * math.log(a / e)
    return float(s)


def load_reference_stats(client: MlflowClient, model_name: str) -> Dict[str, Any]:
    versions = client.get_latest_versions(model_name, stages=["Production"])
    if not versions:
        raise RuntimeError(f"No Production model found for {model_name}")

    mv = versions[0]
    run_id = mv.run_id

    # Download drift/reference_stats.json artifact
    local_dir = client.download_artifacts(run_id, "drift")
    ref_file = os.path.join(local_dir, "reference_stats.json")
    with open(ref_file, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_recent_features(hours: int) -> pd.DataFrame:
    host = os.environ["PREDLOG_HOST"]
    db = os.environ.get("PREDLOG_DB", "mlops")
    user = os.environ.get("PREDLOG_USER", "postgres")
    password = os.environ["PREDLOG_PASSWORD"]

    conn = psycopg2.connect(host=host, dbname=db, user=user, password=password)
    try:
        q = f"""
        SELECT features
        FROM prediction_logs
        WHERE ts >= NOW() - INTERVAL '{int(hours)} hours'
          AND status = 'success'
        ORDER BY ts DESC
        LIMIT 5000;
        """
        df = pd.read_sql(q, conn)
        if df.empty:
            return pd.DataFrame()
        feats = pd.json_normalize(df["features"].apply(lambda x: x))
        return feats
    finally:
        conn.close()


def compute_drift(ref: Dict[str, Any], recent: pd.DataFrame) -> Dict[str, float]:
    out: Dict[str, float] = {}
    features = ref.get("features", {})

    for col, st in features.items():
        if col not in recent.columns:
            continue
        edges = st.get("bin_edges")
        expected = st.get("proportions")
        if not edges or not expected:
            continue

        series = pd.to_numeric(recent[col], errors="coerce").dropna()
        if series.empty:
            continue

        bins = pd.cut(series, bins=edges, include_lowest=True)
        actual = (bins.value_counts(normalize=True).sort_index()).tolist()

        # Align lengths (pd.cut can drop empty bins if edges are weird)
        if len(actual) != len(expected):
            m = min(len(actual), len(expected))
            actual = actual[:m]
            expected = expected[:m]

        out[col] = psi(expected, actual)

    return out


def publish_metrics(model_name: str, drift_scores: Dict[str, float]) -> None:
    pushgateway = os.getenv("PUSHGATEWAY_URL")
    if not pushgateway:
        return

    registry = CollectorRegistry()
    g = Gauge("feature_drift_psi", "Feature drift PSI", ["model", "feature"], registry=registry)

    for feat, score in drift_scores.items():
        g.labels(model=model_name, feature=feat).set(score)

    push_to_gateway(pushgateway, job="drift-check", registry=registry)


def main() -> None:
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        raise RuntimeError("MLFLOW_TRACKING_URI is required")

    model_name = os.getenv("MODEL_NAME", "demo_classifier")
    hours = int(os.getenv("DRIFT_LOOKBACK_HOURS", "24"))
    threshold = float(os.getenv("DRIFT_PSI_THRESHOLD", "0.2"))

    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)

    ref = load_reference_stats(client, model_name)
    recent = fetch_recent_features(hours)

    if recent.empty:
        print(json.dumps({"status": "no_recent_data"}))
        return

    scores = compute_drift(ref, recent)
    publish_metrics(model_name, scores)

    worst = max(scores.values()) if scores else 0.0
    status = "ok" if worst < threshold else "drift_detected"

    print(json.dumps({
        "status": status,
        "worst_psi": worst,
        "threshold": threshold,
        "scores": scores,
        "rows": int(recent.shape[0]),
    }))

    if status != "ok":
        raise SystemExit(10)


if __name__ == "__main__":
    main()
