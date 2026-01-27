# FastAPI Project - Development (Docker)

Local development guide for new teammates. This version uses Docker Compose.
For the non-Docker workflow, see [Non-Docker Development](nodocker.md).

## Environment File

The backend loads environment variables from the repo root `.env` (relative to `backend/`).
Keep `ENVIRONMENT=local` for local development, and adjust `POSTGRES_*`, `DOMAIN`,
`STACK_NAME`, and other values as needed. Avoid committing real secrets.

## Start the local stack

```bash
docker compose watch
```

If `watch` is not available, use:

```bash
docker compose up -d
```

## Local URLs

- Backend API: http://localhost:8000
- API Docs (Swagger UI): http://localhost:8000/docs
- Adminer (DB admin): http://localhost:8080
- Traefik UI (local dev proxy): http://localhost:8090
- MailCatcher: http://localhost:1080

## Logs and status

```bash
docker compose ps
docker compose logs
docker compose logs backend
```

## Local ports for dependencies

The override file maps PostgreSQL to `localhost:5433` and Redis to `localhost:6379`.
Use these when connecting from your host (for example, GUI clients).

## Reset local data (destructive)

```bash
docker compose down -v
```

## Mailcatcher

Mailcatcher is a local SMTP server that captures outgoing emails and shows them in a web UI.
When running with Docker Compose locally, the backend is configured to send emails to
Mailcatcher (SMTP on port 1025).

- MailCatcher UI: http://localhost:1080

## Hybrid: local backend + Docker dependencies

If you want to run the backend process on macOS but keep DB/Redis in Docker:

```bash
docker compose stop backend

cd backend
fastapi dev app/main.py
```

## Optional Local Domains (`localhost.tiangolo.com`)

If you want to test subdomain-based routing locally, edit `.env`:

```dotenv
DOMAIN=localhost.tiangolo.com
```

Then restart:

```bash
docker compose watch
```

With that config:

- Backend API: http://api.localhost.tiangolo.com
- API Docs: http://api.localhost.tiangolo.com/docs
- Adminer: http://adminer.localhost.tiangolo.com
- Traefik UI: http://localhost.tiangolo.com:8090
- MailCatcher: http://localhost.tiangolo.com:1080

## Tests

```bash
docker compose exec backend bash scripts/tests-start.sh
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
