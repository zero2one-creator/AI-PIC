# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Backend FastAPI Template - a production-ready backend API with FastAPI, PostgreSQL, and Docker Compose.

## Common Commands

### Development

```bash
# Start services (recommended for local dev)
docker compose watch

# View logs
docker compose logs backend
docker compose logs db
docker compose logs adminer
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

# Create database migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

### Code Quality

```bash
# Install pre-commit hooks (from backend/)
uv run prek install -f

# Run all pre-commit checks manually
uv run prek run --all-files

# Lint and format
uv run ruff check --fix
uv run ruff format
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

### Key Patterns

- **API versioning**: All endpoints under `/api/v1`
- **Authentication**: JWT tokens via `/api/v1/login/access-token`
- **Database models**: SQLModel classes with `table=True` for DB tables, without for Pydantic schemas

### Development URLs

- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- Adminer (DB admin): http://localhost:8080
- MailCatcher: http://localhost:1080

## Configuration

Environment variables are in `.env` at project root. Key settings:
- `SECRET_KEY`, `POSTGRES_PASSWORD`, `FIRST_SUPERUSER_PASSWORD` - must change from "changethis" for non-local environments
- Backend reads config via `pydantic-settings` from `backend/app/core/config.py`

