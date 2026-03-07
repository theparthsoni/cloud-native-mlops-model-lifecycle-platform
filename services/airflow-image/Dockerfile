FROM apache/airflow:2.9.3-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
 && rm -rf /var/lib/apt/lists/*
USER airflow

WORKDIR /opt/airflow

COPY services /opt/airflow/services
COPY airflow /opt/airflow/airflow
COPY services/airflow-image/requirements.txt /opt/airflow/requirements.txt

RUN pip install --no-cache-dir -r /opt/airflow/requirements.txt