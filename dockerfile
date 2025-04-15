FROM python:3.9-alpine

WORKDIR /app

RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev

COPY . /app

RUN pip install --no-cache-dir prometheus_client requests

ENV ACCES_KEY="access_key"
ENV SECRET_KEY="secret_key"
ENV APP_KEY="app_key"
ENV RDS_ID="rds_id"

CMD ["python", "prometheus_rds.py"]
