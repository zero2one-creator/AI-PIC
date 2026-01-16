# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Full Stack FastAPI Template - a production-ready web application with FastAPI backend, React frontend, PostgreSQL database, and Docker Compose orchestration.

## Common Commands

### Development

```bash
# Start full stack with Docker Compose (recommended)
docker compose watch

# View logs
docker compose logs backend
docker compose logs frontend
```

### Backend (from backend/ directory)

```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate

# Run local dev server (without Docker)
fastapi dev app/main.py

# Run tests in Docker (from project root)
docker compose exec backend bash scripts/tests-start.sh

# Run single test
docker compose exec backend bash scripts/tests-start.sh -x tests/path/to/test.py::test_name

# Run tests with coverage (inside container)
bash scripts/test.sh

# Create database migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

### Frontend (from frontend/ directory)

```bash
# Install dependencies
npm install

# Run local dev server
npm run dev

# Lint and format
npm run lint

# Build
npm run build

# Generate API client from OpenAPI spec
npm run generate-client

# Run E2E tests (requires backend running)
npx playwright test
```

### Code Quality

```bash
# Install pre-commit hooks (from backend/)
uv run prek install -f

# Run all pre-commit checks manually
uv run prek run --all-files

# Backend linting
uv run ruff check --fix
uv run ruff format

# Frontend linting
cd frontend && npm run lint
```

### Generate Frontend Client

```bash
# From project root (requires backend venv activated)
./scripts/generate-client.sh
```

## Architecture

### Backend Structure (backend/app/)

- `main.py` - FastAPI app initialization, CORS, Sentry setup
- `models.py` - SQLModel database models and Pydantic schemas (User, Item, Token)
- `crud.py` - Database CRUD operations
- `core/config.py` - Settings via pydantic-settings (reads from ../.env)
- `core/db.py` - Database session management
- `core/security.py` - Password hashing, JWT token handling
- `api/main.py` - API router aggregation
- `api/routes/` - Endpoint modules (login, users, items, utils, private)
- `api/deps.py` - FastAPI dependencies (auth, db session)
- `alembic/` - Database migrations

### Frontend Structure (frontend/src/)

- `main.tsx` - App entry point
- `client/` - Auto-generated OpenAPI client (regenerate after backend API changes)
- `components/` - React components using shadcn/ui
- `routes/` - TanStack Router file-based routes
- `hooks/` - Custom React hooks
- `routeTree.gen.ts` - Auto-generated route tree

### Key Patterns

- **API versioning**: All endpoints under `/api/v1`
- **Authentication**: JWT tokens via `/api/v1/login/access-token`
- **Database models**: SQLModel classes with `table=True` for DB tables, without for Pydantic schemas
- **Frontend state**: TanStack Query for server state, React Hook Form for forms
- **Styling**: Tailwind CSS with shadcn/ui components

### Development URLs

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- Adminer (DB admin): http://localhost:8080
- MailCatcher: http://localhost:1080

## Configuration

Environment variables are in `.env` at project root. Key settings:
- `SECRET_KEY`, `POSTGRES_PASSWORD`, `FIRST_SUPERUSER_PASSWORD` - must change from "changethis" for non-local environments
- Backend reads config via `pydantic-settings` from `backend/app/core/config.py`
