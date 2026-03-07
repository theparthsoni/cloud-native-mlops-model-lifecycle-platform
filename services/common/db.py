import psycopg2

from services.common.config import settings
from services.common.errors import ConfigurationError


def get_predlog_connection():
    if not settings.PREDLOG_HOST or not settings.PREDLOG_PASSWORD:
        raise ConfigurationError(
            "PREDLOG_HOST and PREDLOG_PASSWORD must be configured"
        )

    return psycopg2.connect(
        host=settings.PREDLOG_HOST,
        dbname=settings.PREDLOG_DB,
        user=settings.PREDLOG_USER,
        password=settings.PREDLOG_PASSWORD,
    )