FROM python:3.11-slim AS base

RUN groupadd -r auditor && useradd -r -g auditor -d /app -s /sbin/nologin auditor

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir .

USER auditor

EXPOSE 8000

ENTRYPOINT ["snow-itom-auditor"]
