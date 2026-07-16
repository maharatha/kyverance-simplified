# Kyverance Simplified API

FastAPI modular monolith for Kyverance Simplified.

## Local setup

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
cp .env.example .env
```

Start Postgres and Redis from the repo root:

```bash
docker compose -f infrastructure/docker-compose.yml up -d
```

Run the API:

```bash
uvicorn kyverance.main:app --reload --host 0.0.0.0 --port 8000
```

Run tests:

```bash
python -m pytest tests -q
```
