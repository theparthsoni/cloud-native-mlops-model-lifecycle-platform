import os
import json
from urllib.parse import urlparse

import pandas as pd
import mlflow
import boto3


def parse_s3_uri(uri: str):
    u = urlparse(uri)
    if u.scheme != "s3":
        raise ValueError(f"Expected s3:// URI, got: {uri}")
    bucket = u.netloc
    key = u.path.lstrip("/")
    return bucket, key


def s3_client():
    endpoint = os.getenv("MLFLOW_S3_ENDPOINT_URL")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


def read_csv_s3(uri: str) -> pd.DataFrame:
    bucket, key = parse_s3_uri(uri)
    s3 = s3_client()
    obj = s3.get_object(Bucket=bucket, Key=key)
    return pd.read_csv(obj["Body"])


def write_csv_s3(df: pd.DataFrame, uri: str) -> None:
    bucket, key = parse_s3_uri(uri)
    s3 = s3_client()
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    s3.put_object(Bucket=bucket, Key=key, Body=csv_bytes, ContentType="text/csv")


def main() -> None:
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        raise RuntimeError("MLFLOW_TRACKING_URI is required")

    model_name = os.getenv("MODEL_NAME", "demo_classifier")
    model_stage = os.getenv("MODEL_STAGE", "Production")
    input_path = os.getenv("BATCH_INPUT", "s3://data/batch_input.csv")
    output_path = os.getenv("BATCH_OUTPUT", "s3://data/batch_output_predictions.csv")

    mlflow.set_tracking_uri(tracking_uri)
    model_uri = f"models:/{model_name}/{model_stage}"

    model = mlflow.pyfunc.load_model(model_uri)

    df = read_csv_s3(input_path)
    preds = model.predict(df)

    out = df.copy()
    out["prediction"] = preds
    write_csv_s3(out, output_path)

    print(json.dumps({
        "model_uri": model_uri,
        "input": input_path,
        "output": output_path,
        "rows": int(df.shape[0]),
    }))


if __name__ == "__main__":
    main()
