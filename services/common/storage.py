from urllib.parse import urlparse

import boto3
import pandas as pd

from services.common.config import settings
from services.common.errors import StorageError


def parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3":
        raise StorageError(f"Expected s3:// URI, got: {uri}")
    return parsed.netloc, parsed.path.lstrip("/")


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.MLFLOW_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def read_csv_s3(uri: str) -> pd.DataFrame:
    bucket, key = parse_s3_uri(uri)
    client = get_s3_client()
    obj = client.get_object(Bucket=bucket, Key=key)
    return pd.read_csv(obj["Body"])


def write_csv_s3(df: pd.DataFrame, uri: str) -> None:
    bucket, key = parse_s3_uri(uri)
    client = get_s3_client()
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=csv_bytes,
        ContentType="text/csv",
    )