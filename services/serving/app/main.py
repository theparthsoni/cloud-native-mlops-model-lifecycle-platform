from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any, Dict, Optional

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel
from pythonjsonlogger import jsonlogger
from starlette.responses import Response

from .factory import create_backend, create_prediction_sink

logger = logging.getLogger("model-serving")
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

REQUESTS = Counter("inference_requests_total", "Total inference requests", ["model", "status"])
LATENCY = Histogram("inference_latency_seconds", "Inference latency seconds", ["model"])

API_KEYS = {k.strip() for k in os.getenv("API_KEYS", "dev-key").split(",") if k.strip()}


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

    t0 = time.time()
    status = "success"
    pred: Any = None

    try:
        df = pd.DataFrame([req.features])
        pred = backend.predict_one(df)
        REQUESTS.labels(model=model_name, status="success").inc()
        return PredictResponse(
            prediction=pred,
            model_uri=backend.model_uri,
            model_version=backend.model_version,
            request_id=request_id,
        )
    except Exception as e:
        status = "error"
        REQUESTS.labels(model=model_name, status="error").inc()
        logger.exception({"event": "inference_error", "request_id": request_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Inference error: {type(e).__name__}: {e}")
    finally:
        latency_ms = (time.time() - t0) * 1000.0
        LATENCY.labels(model=model_name).observe((time.time() - t0))

        try:
            sink.write(
                request_id=request_id,
                model_name=model_name,
                model_version=str(backend.model_version),
                features=req.features,
                prediction=pred,
                latency_ms=latency_ms,
                status=status,
            )
        except Exception:
            logger.exception({"event": "prediction_log_failed", "request_id": request_id})


@app.post("/reload")
def reload_model(dep=Depends(require_api_key)):

    if hasattr(backend, "force_reload"):
        backend.force_reload()  
    return {"status": "will_reload"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
