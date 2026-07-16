# Kyverance Simplified API — build from repo root:
#   docker build -f backend/Dockerfile -t kyverance-simplified-api .
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/README.md ./
COPY backend/src ./src
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic

RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["sh", "-c", "kyverance-migrate upgrade && uvicorn kyverance.main:app --host 0.0.0.0 --port 8000"]
