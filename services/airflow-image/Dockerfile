FROM apache/airflow:2.9.3
USER root

COPY airflow/dags /opt/airflow/dags

RUN pip install --no-cache-dir apache-airflow-providers-cncf-kubernetes==8.4.2

USER airflow
