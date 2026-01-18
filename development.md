# FastAPI Project - Development

## Docker Compose

Start the local stack with Docker Compose:

```bash
docker compose watch
```

Local URLs:

- Backend API: http://localhost:8000
- API Docs (Swagger UI): http://localhost:8000/docs
- Adminer (DB admin): http://localhost:8080
- Traefik UI (local dev proxy): http://localhost:8090
- MailCatcher: http://localhost:1080

If the stack is still starting up, check logs:

```bash
docker compose logs
docker compose logs backend
```

## Mailcatcher

Mailcatcher is a local SMTP server that captures outgoing emails and shows them in a web UI.

When running with Docker Compose locally, the backend is configured to send emails to Mailcatcher (SMTP on port 1025).

- MailCatcher UI: http://localhost:1080

## Local Development (without Docker)

The Docker Compose files expose the backend on the same port you'd use locally (`8000`), so you can stop the container and run the dev server directly:

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

