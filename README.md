# Kyverance Simplified

AI-native community for simulated portfolios. People create and practise with portfolios, inspect their process, fork public work, collaborate with agents, and sell access to research and portfolio templates. It never sends an order to a brokerage in the initial releases.

## Stack

- **Web:** Next.js 15, React 19, TypeScript
- **API:** FastAPI, Pydantic, SQLAlchemy, Alembic, Python 3.12
- **Data:** PostgreSQL 16, Redis 7
- **Identity (later):** Microsoft Entra External ID / Auth.js
- **Cloud (later):** Azure Container Apps, ACR, Static Web Apps, Key Vault

## Repository layout

```text
frontend/                 Next.js application
backend/src/kyverance/    FastAPI modules
backend/tests/            API/domain/integration tests
infrastructure/           local stack and Azure transition assets
.github/workflows/        CI
docs/                     product and delivery source of truth
scripts/                  local/dev commands
shared/                   small cross-language contracts
```

## Local development

### 1. Infrastructure

```powershell
docker compose -f infrastructure/docker-compose.yml up -d
```

### 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn kyverance.main:app --reload --port 8000
```

API health: `http://127.0.0.1:8000/health`

Tests:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://kyverance:kyverance@localhost:5432/kyverance"
$env:REDIS_URL = "redis://localhost:6379/0"
python -m pytest tests -q
```

### 3. Frontend

```powershell
cd frontend
Copy-Item .env.example .env.local
npm ci
npm run dev
```

App: `http://localhost:3000`

Lint / test / clean production build:

```powershell
npm run lint
npm test
npm run build:clean
```

### 4. Docker images

```powershell
docker build -f backend/Dockerfile -t kyverance-simplified-api .
docker build -f frontend/Dockerfile -t kyverance-simplified-web ./frontend
```

## Documentation

Start at [docs/README.md](docs/README.md). Implementation tasks live under `docs/tasks/`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Do not commit secrets. Prefer ADRs under `docs/adr/` for material deviations from the documented baseline.
