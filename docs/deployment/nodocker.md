# FastAPI Project - Deployment (Non-Docker)

This document describes a simple non-Docker deployment on a Linux server
(systemd + Nginx + PostgreSQL). Adjust paths and versions to your environment.
For Docker deployment, see [Docker Deployment](docker.md).

## Prerequisites

- Linux server with Python 3.10+.
- PostgreSQL (required).
- Redis (optional, used by emoji queue).
- Nginx or Caddy for reverse proxy (recommended).

## 1) Prepare the database

Create a database and user that match your `.env` (top-level, next to this file).
Example (PostgreSQL):

```bash
sudo -u postgres psql
```

```sql
CREATE USER app_user WITH PASSWORD 'strong_password';
CREATE DATABASE app OWNER app_user;
```

Update `.env`:

```dotenv
POSTGRES_SERVER=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=app
POSTGRES_USER=app_user
POSTGRES_PASSWORD=strong_password
```

## 2) Install dependencies

```bash
cd /opt/ai-pic__ai-emoji-revcat-gpt/backend
uv sync
```

## 3) Run migrations and initial data

```bash
cd /opt/ai-pic__ai-emoji-revcat-gpt/backend
source .venv/bin/activate
bash scripts/prestart.sh
```

## 4) Create a systemd service

Create `/etc/systemd/system/ai-emoji-backend.service`:

```ini
[Unit]
Description=AI Emoji FastAPI Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ai-pic__ai-emoji-revcat-gpt/backend
EnvironmentFile=/opt/ai-pic__ai-emoji-revcat-gpt/.env
ExecStart=/opt/ai-pic__ai-emoji-revcat-gpt/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Reload and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ai-emoji-backend
sudo systemctl status ai-emoji-backend
```

## 5) Nginx reverse proxy (example)

Create `/etc/nginx/sites-available/ai-emoji.conf`:

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/ai-emoji.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Notes

- Adminer is a Docker-only component in this repo; use your preferred DB client.
- Redis is optional. If you do not run Redis, the emoji queue will return
  "Queue unavailable" but the API can still start.
- For HTTPS, add TLS via Nginx or use Caddy with automatic certificates.
