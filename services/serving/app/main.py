from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel
from starlette.responses import Response

from services.common.config import settings
from services.common.errors import PredictionError
from services.common.logging import setup_logging

from .factory import create_backend, create_prediction_sink

logger = setup_logging("serving")

REQUESTS = Counter(
    "inference_requests_total",
    "Total inference requests",
    ["model", "status"],
)
LATENCY = Histogram(
    "inference_latency_seconds",
    "Inference latency seconds",
    ["model"],
)

API_KEYS = {key.strip() for key in settings.API_KEYS_RAW.split(",") if key.strip()}


def require_api_key(x_api_key: str = Header(default="")):
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Unauthorized")


class PredictRequest(BaseModel):
    features: Dict[str, float]
    model_name: Optional[str] = None


class PredictResponse(BaseModel):
    prediction: Any
    model_uri: str
    model_version: str
    request_id: str


app = FastAPI(title="Model Serving API", version="1.1")

DEPLOYED_MODEL_NAME, backend = create_backend()
sink = create_prediction_sink()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/model")
def model_info(dep=Depends(require_api_key)):
    backend.load()
    return {
        "model_name": DEPLOYED_MODEL_NAME,
        "model_uri": backend.model_uri,
        "version": backend.model_version,
    }


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest, dep=Depends(require_api_key)):
    request_id = str(uuid.uuid4())
    model_name = req.model_name or DEPLOYED_MODEL_NAME

    if model_name != DEPLOYED_MODEL_NAME:
        raise HTTPException(
            status_code=400,
            detail=(
                "This deployment serves a single model. Deploy multiple releases for multiple models "
                "or implement a router service."
            ),
        )

    started_at = time.time()
    status = "success"
    prediction: Any = None

    try:
        logger.info("Received prediction request request_id=%s model=%s", request_id, model_name)

        df = pd.DataFrame([req.features])
        prediction = backend.predict_one(df)

        REQUESTS.labels(model=model_name, status="success").inc()

        return PredictResponse(
            prediction=prediction,
            model_uri=backend.model_uri,
            model_version=backend.model_version,
            request_id=request_id,
        )

    except Exception as exc:
        status = "error"
        REQUESTS.labels(model=model_name, status="error").inc()
        logger.exception("Inference failed for request_id=%s", request_id)
        raise HTTPException(
            status_code=500,
            detail=str(PredictionError(f"Inference failed: {exc}")),
        ) from exc

    finally:
        latency_seconds = time.time() - started_at
        latency_ms = latency_seconds * 1000.0
        LATENCY.labels(model=model_name).observe(latency_seconds)

        try:
            sink.write(
                request_id=request_id,
                model_name=model_name,
                model_version=str(backend.model_version),
                features=req.features,
                prediction=prediction,
                latency_ms=latency_ms,
                status=status,
            )
        except Exception:
            logger.exception("Prediction telemetry logging failed for request_id=%s", request_id)


@app.post("/reload")
def reload_model(dep=Depends(require_api_key)):
    if hasattr(backend, "force_reload"):
        backend.force_reload()
    return {"status": "will_reload"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)