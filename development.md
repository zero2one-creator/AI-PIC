# FastAPI Project - Development

## 🚀 Quick Start (Recommended - No Docker)

### One-time Setup

```bash
# Run the setup script (installs PostgreSQL, Redis, Python dependencies)
bash scripts/setup-local.sh
```

### Start Development

**Terminal 1 - Start API Server:**
```bash
bash scripts/start-api.sh
```

**Terminal 2 - Start Worker (for async tasks):**
```bash
bash scripts/start-worker.sh
```

**Terminal 3 - Manage Services:**
```bash
# Check service status
bash scripts/manage-services.sh status

# Start/stop services
bash scripts/manage-services.sh start
bash scripts/manage-services.sh stop
```

### Local URLs

- Backend API: http://localhost:8000
- API Docs (Swagger UI): http://localhost:8000/docs
- API Schema: http://localhost:8000/openapi.json

### Run Tests

```bash
bash scripts/run-tests.sh

# Run specific test file
bash scripts/run-tests.sh tests/test_api_flows.py

# Run with coverage
bash scripts/run-tests.sh --cov=app tests/
```

---

## 🐳 Docker Compose (Alternative)

If you prefer Docker, start the local stack with Docker Compose:

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

### Mailcatcher

Mailcatcher is a local SMTP server that captures outgoing emails and shows them in a web UI.

When running with Docker Compose locally, the backend is configured to send emails to Mailcatcher (SMTP on port 1025).

- MailCatcher UI: http://localhost:1080

### Local Development (without Docker)

The Docker Compose files expose the backend on the same port you'd use locally (`8000`), so you can stop the container and run the dev server directly:

```bash
docker compose stop backend

cd backend
fastapi dev app/main.py
```

---

## 📝 Pre-commits and Code Linting

This project uses [prek](https://prek.j178.dev/) (a modern alternative to pre-commit).

Install the git hook (run from `backend/`):

```bash
cd backend
uv run prek install -f
```

Run all checks manually:

```bash
cd backend
uv run prek run --all-files
```

---

## 🔧 Manual Commands (Advanced)

If you prefer to run commands manually without scripts:

### Activate Virtual Environment

```bash
cd backend
source .venv/bin/activate
```

### Start API Server

```bash
cd backend
source .venv/bin/activate
fastapi dev app/main.py
```

### Start Worker

```bash
cd backend
source .venv/bin/activate
python -m worker.emoji_worker
```

### Run Database Migrations

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

### Create New Migration

```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "Description of changes"
```

### Manage Services

```bash
# Start services
brew services start postgresql@17
brew services start redis

# Stop services
brew services stop postgresql@17
brew services stop redis

# Check status
brew services list | grep -E "postgresql|redis"
```

---

## 🐛 Troubleshooting

### PostgreSQL Connection Error

If you get "role postgres does not exist":

```bash
# Find psql binary
find /opt/homebrew -name "psql" 2>/dev/null | head -1

# Create postgres user (replace /path/to/psql with actual path)
/path/to/psql -U $(whoami) -d postgres -c "CREATE USER postgres WITH SUPERUSER PASSWORD 'changethis';"

# Create app database
/path/to/psql -U postgres -d postgres -c "CREATE DATABASE app OWNER postgres;"
```

### Redis Connection Error

```bash
# Check if Redis is running
redis-cli ping

# Start Redis
brew services start redis

# Check Redis logs
tail -f /opt/homebrew/var/log/redis.log
```

### Python Dependencies Issue

```bash
# Reinstall dependencies
cd backend
uv sync --refresh

# Clear cache
uv cache clean
```

### Port Already in Use

If port 8000 is already in use:

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
fastapi dev app/main.py --port 8001
```

