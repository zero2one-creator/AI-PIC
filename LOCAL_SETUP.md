# Local Development Setup Guide

## 🎯 Overview

This project can be developed **without Docker** using local PostgreSQL and Redis services. This guide provides everything you need to get started.

## ✅ Prerequisites

- macOS (for Linux, adjust Homebrew commands to your package manager)
- Homebrew installed
- Internet connection for downloading dependencies

## 🚀 Quick Start (5 minutes)

### Step 1: Run Setup Script

```bash
bash scripts/setup-local.sh
```

This script will:
- ✅ Install PostgreSQL 17 (if not present)
- ✅ Install Redis (if not present)
- ✅ Install uv package manager (if not present)
- ✅ Create PostgreSQL user and database
- ✅ Install Python dependencies (139 packages)
- ✅ Run database migrations

### Step 2: Start Services

**Terminal 1 - API Server:**
```bash
bash scripts/start-api.sh
```

**Terminal 2 - Worker (for async tasks):**
```bash
bash scripts/start-worker.sh
```

### Step 3: Access the Application

- **API Documentation:** http://localhost:8000/docs
- **API Schema:** http://localhost:8000/openapi.json
- **Health Check:** http://localhost:8000/health

## 📋 Available Scripts

### `scripts/setup-local.sh`
One-time setup for local development environment.

```bash
bash scripts/setup-local.sh
```

### `scripts/start-api.sh`
Start the FastAPI development server with auto-reload.

```bash
bash scripts/start-api.sh
```

Features:
- Auto-reload on code changes
- Full API documentation at `/docs`
- Checks for running services before starting

### `scripts/start-worker.sh`
Start the background worker for async emoji generation tasks.

```bash
bash scripts/start-worker.sh
```

Features:
- Processes emoji generation tasks from Redis Streams
- Automatic retry on failure
- Service health checks

### `scripts/run-tests.sh`
Run the test suite with pytest.

```bash
# Run all tests
bash scripts/run-tests.sh

# Run specific test file
bash scripts/run-tests.sh tests/test_api_flows.py

# Run with coverage report
bash scripts/run-tests.sh --cov=app tests/

# Run with verbose output
bash scripts/run-tests.sh -v
```

### `scripts/manage-services.sh`
Manage PostgreSQL and Redis services.

```bash
# Check service status
bash scripts/manage-services.sh status

# Start services
bash scripts/manage-services.sh start

# Stop services
bash scripts/manage-services.sh stop

# Restart services
bash scripts/manage-services.sh restart

# View PostgreSQL logs
bash scripts/manage-services.sh logs-db

# View Redis logs
bash scripts/manage-services.sh logs-redis
```

## 🔧 Manual Commands

If you prefer to run commands manually:

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

### Run Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/
```

### Database Migrations

```bash
cd backend
source .venv/bin/activate

# Run all pending migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"

# Rollback one migration
alembic downgrade -1
```

### Code Quality

```bash
cd backend
source .venv/bin/activate

# Install pre-commit hooks
uv run prek install -f

# Run all checks
uv run prek run --all-files

# Format code
uv run ruff format

# Lint code
uv run ruff check --fix
```

## 📊 Project Structure

```
.
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── models.py          # Database models
│   │   ├── crud.py            # Database operations
│   │   ├── api/               # API routes
│   │   ├── core/              # Core utilities
│   │   ├── integrations/      # External services
│   │   └── alembic/           # Database migrations
│   ├── worker/                # Background workers
│   ├── tests/                 # Test suite
│   ├── scripts/               # Utility scripts
│   ├── pyproject.toml         # Python dependencies
│   └── .venv/                 # Virtual environment
├── scripts/                   # Project scripts
│   ├── setup-local.sh         # Setup script
│   ├── start-api.sh           # Start API
│   ├── start-worker.sh        # Start worker
│   ├── run-tests.sh           # Run tests
│   └── manage-services.sh     # Manage services
├── .env                       # Environment variables
└── development.md             # Development guide
```

## 🌍 Environment Variables

Key environment variables in `.env`:

```bash
# Database
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=app
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changethis

# Cache
REDIS_HOST=localhost
REDIS_PORT=6379

# Application
PROJECT_NAME=PicKitchen
ENVIRONMENT=local
SECRET_KEY=your-secret-key-here

# Aliyun (mock for local development)
ALIYUN_EMOJI_MOCK=true
```

## 🐛 Troubleshooting

### PostgreSQL Connection Error

```bash
# Check if PostgreSQL is running
brew services list | grep postgresql

# Start PostgreSQL
brew services start postgresql@17

# Check PostgreSQL logs
tail -f /opt/homebrew/var/log/postgres.log
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

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
fastapi dev app/main.py --port 8001
```

### Virtual Environment Issues

```bash
# Reinstall dependencies
cd backend
uv sync --refresh

# Clear uv cache
uv cache clean

# Recreate virtual environment
rm -rf .venv
uv sync
```

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Pytest Documentation](https://docs.pytest.org/)
- [uv Documentation](https://docs.astral.sh/uv/)

## 🆘 Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Review the logs using the manage-services script
3. Check the `.env` file for correct configuration
4. Ensure all services are running: `bash scripts/manage-services.sh status`

## 🎉 You're Ready!

You now have a fully functional local development environment. Start coding! 🚀
