import json

import mlflow

from services.common.config import settings
from services.common.errors import PredictionError
from services.common.logging import setup_logging
from services.common.storage import read_csv_s3, write_csv_s3

logger = setup_logging("batch")


def main() -> None:
    logger.info("Starting batch scoring for model '%s'", settings.MODEL_NAME)

    try:
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        model_uri = f"models:/{settings.MODEL_NAME}/{settings.MODEL_STAGE}"
        model = mlflow.pyfunc.load_model(model_uri)

        df = read_csv_s3(settings.BATCH_INPUT)
        predictions = model.predict(df)

        output_df = df.copy()
        output_df["prediction"] = predictions
        write_csv_s3(output_df, settings.BATCH_OUTPUT)

        logger.info(
            "Batch scoring completed: %s",
            json.dumps(
                {
                    "model_uri": model_uri,
                    "input": settings.BATCH_INPUT,
                    "output": settings.BATCH_OUTPUT,
                    "rows": int(df.shape[0]),
                }
            ),
        )

    except Exception as exc:
        logger.exception("Batch scoring failed")
        raise PredictionError(f"Batch scoring failed: {exc}") from exc


if __name__ == "__main__":
    main()