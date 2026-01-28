# FastAPI Project - Deployment (Docker)

You can deploy this project with Docker Compose to a remote server. The stack is backend-only (API + admin tools),
and it relies on external PostgreSQL/Redis services.

This template can integrate with a shared Traefik instance that handles HTTPS certificates and routes traffic by subdomain.

## Preparation

- Remote server with Docker Engine installed (not Docker Desktop).
- DNS records pointing to your server IP (commonly):
  - `api.<your-domain>` -> backend API
  - `adminer.<your-domain>` -> Adminer (optional)
  - `traefik.<your-domain>` -> Traefik dashboard (optional)

## Public Traefik (optional, recommended for HTTPS)

You only need to do this once per server.

1) Copy `docker-compose.traefik.yml` to the server (example path):

```bash
mkdir -p /root/code/traefik-public/
rsync -a docker-compose.traefik.yml root@your-server:/root/code/traefik-public/
```

2) Create the shared Docker network:

```bash
docker network create traefik-public
```

3) Set required env vars and start Traefik:

```bash
export USERNAME=admin
export PASSWORD=changethis
export HASHED_PASSWORD=$(openssl passwd -apr1 "$PASSWORD")
export DOMAIN=example.com
export EMAIL=admin@example.com

cd /root/code/traefik-public/
docker compose -f docker-compose.traefik.yml up -d
```

## Deploy the Backend Stack

On the server (or via CI/CD), set at least:

- `ENVIRONMENT=staging|production`
- `DOMAIN=<your-domain>`
- Database/Redis: `POSTGRES_*`, `REDIS_*`
- Secrets: `SECRET_KEY`, `POSTGRES_PASSWORD`, `FIRST_SUPERUSER_PASSWORD`

Then deploy:

```bash
docker compose -f docker-compose.yml up -d
```

For production you normally run without `docker-compose.override.yml`, hence the explicit `-f docker-compose.yml`.

## Environment Variables

Core variables live in `.env`. Common ones:

- `PROJECT_NAME`, `STACK_NAME`
- `BACKEND_CORS_ORIGINS`
- `SECRET_KEY`
- `FIRST_SUPERUSER`, `FIRST_SUPERUSER_PASSWORD`
- `SMTP_*`, `EMAILS_FROM_EMAIL` (if sending real emails)
- `POSTGRES_*`, `REDIS_*`
- `SENTRY_DSN` (optional)
