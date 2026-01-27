# FastAPI Project - Development (Non-Docker)

Local development guide for new teammates. This version runs Python on macOS.
For the Docker workflow, see [Docker Development](docker.md).

## Environment File

The backend loads environment variables from the repo root `.env` (relative to `backend/`).
Keep `ENVIRONMENT=local` for local development, and adjust `POSTGRES_*`, `DOMAIN`,
`STACK_NAME`, and other values as needed. Avoid committing real secrets. The repo
already contains a baseline `.env` for local use; for non-Docker runs make sure
`POSTGRES_*` and `REDIS_*` point to your local services.

## Prerequisites (macOS)

- Python 3.10+ and [uv](https://docs.astral.sh/uv/)
- PostgreSQL (required)
- Redis (optional; required for the emoji queue worker)

## Install dependencies

```bash
cd backend
uv sync
source .venv/bin/activate
```

## Configure and start local services

Update `.env` for local services, for example:

```dotenv
POSTGRES_SERVER=127.0.0.1
POSTGRES_PORT=5432
```

Make sure the database exists and is reachable, then run migrations and seed data:

```bash
cd backend
bash scripts/prestart.sh
```

## Run the API

```bash
cd backend
fastapi dev app/main.py
```

## Optional: background workers

Run workers in separate terminals when you need them:

```bash
cd backend
python worker/emoji_worker.py
python worker/weekly_points_reward.py
```

If Redis is not running, the emoji queue endpoints will return "Queue unavailable",
but the API can still start.

## Tests

```bash
cd backend
bash scripts/test.sh
```

## Pre-commits and Code Linting

This project uses [prek](https://prek.j178.dev/) (a modern alternative to pre-commit).

Install the git hook (run from `backend/`):

```bash
uv run prek install -f
```

Run all checks manually:

```bash
uv run prek run --all-files
```

## Deployment Scripts and GitHub Actions

Local scripts live under `./scripts/`:

- `scripts/build.sh`: build Docker images (`TAG` required)
- `scripts/build-push.sh`: build and push images (`TAG` required)
- `scripts/deploy.sh`: render a Swarm stack and deploy (requires `DOMAIN`, `STACK_NAME`, `TAG`)

Deployment in this repo is done by GitHub Actions on self-hosted runners in Aliyun ECS:

- Staging: push to `master` (`.github/workflows/deploy-staging.yml`)
- Production: release published (`.github/workflows/deploy-production.yml`)
- Both use `docker compose -f docker-compose.yml build` + `up -d`
- Secrets required: `DOMAIN_*`, `STACK_NAME_*`, `SECRET_KEY`,
  `FIRST_SUPERUSER`, `FIRST_SUPERUSER_PASSWORD`, `POSTGRES_PASSWORD`,
  SMTP settings, and `SENTRY_DSN` (optional)

For more workflow details, see `docs/github-actions-concepts.zh-CN.md`.
