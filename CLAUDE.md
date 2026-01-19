# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PicKitchen AI Backend - a production-ready backend API for AI emoji generation service with FastAPI, PostgreSQL, Redis, and Docker Compose.

### Core Features
- **User Management**: Device-based authentication, user profiles, VIP subscriptions
- **Points System**: Purchase, consume, and reward points with transaction history
- **Emoji Generation**: AI-powered emoji creation via Aliyun DashScope API
- **Subscription Management**: RevenueCat webhook integration for iOS/Android subscriptions
- **Async Processing**: Redis Streams for background task processing

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
- `models.py` - SQLModel database models (User, UserPoints, PointTransaction, Subscription, Order, EmojiTask, RevenueCatEvent)
- `crud.py` - Database CRUD operations for users, points, and emoji tasks
- `core/config.py` - Settings via pydantic-settings (reads from ../.env)
- `core/db.py` - Database session management
- `core/security.py` - Password hashing, JWT token handling
- `core/snowflake.py` - Snowflake ID generator for distributed systems
- `core/redis.py` - Redis client connection management
- `api/main.py` - API router aggregation
- `api/routes/` - Endpoint modules (auth, user, points, emoji, subscription, orders, config)
- `api/deps.py` - FastAPI dependencies (auth, db session)
- `api/schemas.py` - Pydantic request/response schemas
- `api/errors.py` - Custom error handling
- `integrations/oss.py` - Aliyun OSS integration for file storage
- `integrations/aliyun_emoji.py` - Aliyun DashScope Emoji API client
- `services/config_service.py` - Dynamic configuration service (Nacos + local fallback)
- `worker/emoji_worker.py` - Background worker for emoji generation tasks
- `worker/weekly_points_reward.py` - Scheduled task for VIP weekly rewards
- `alembic/` - Database migrations

### Key Patterns

- **API versioning**: All endpoints under `/api/v1`
- **Authentication**: Device-based JWT tokens via `/api/v1/auth/login`
- **Database models**: SQLModel classes with `table=True` for DB tables, without for Pydantic schemas
- **ID Generation**: Snowflake IDs (64-bit) for distributed uniqueness across all tables
- **Points System**: Deduct-first strategy (points deducted on task creation, no refund on failure)
- **Async Processing**: Redis Streams for emoji generation tasks with consumer groups
- **Idempotency**: RevenueCat webhook events deduplicated by `event_id`
- **Transaction Safety**: `SELECT FOR UPDATE` for points balance updates to prevent race conditions

### Development URLs

- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- Adminer (DB admin): http://localhost:8080
- MailCatcher: http://localhost:1080

## Configuration

Environment variables are in `.env` at project root. Key settings:

### Security (MUST change for production)
- `SECRET_KEY` - JWT signing key (default: "changethis")
- `POSTGRES_PASSWORD` - Database password (default: "changethis")
- `REVENUECAT_WEBHOOK_SECRET` - RevenueCat webhook authentication

### Database & Cache
- `POSTGRES_SERVER`, `POSTGRES_USER`, `POSTGRES_DB` - PostgreSQL connection
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` - Redis connection

### Snowflake ID Generator
- `SNOWFLAKE_NODE_ID` - Unique node ID (0-1023) for each instance in distributed deployment

### Aliyun Services
- `OSS_ENDPOINT`, `OSS_BUCKET`, `OSS_ACCESS_KEY_ID`, `OSS_ACCESS_KEY_SECRET` - Object storage
- `OSS_DIR_PREFIX`, `OSS_RESULT_PREFIX` - Upload and result directories
- `DASHSCOPE_BASE_URL`, `DASHSCOPE_API_KEY` - DashScope Emoji API
- `ALIYUN_EMOJI_MOCK` - Set to "true" for local development without API calls

### Configuration Service
- `NACOS_SERVER_ADDR`, `NACOS_NAMESPACE`, `NACOS_GROUP`, `NACOS_DATA_ID` - Dynamic config (optional)
- Falls back to `backend/app/config/default_config.json` if Nacos unavailable

Backend reads config via `pydantic-settings` from `backend/app/core/config.py`

## Recent Bug Fixes (2026-01-19)

### 1. Weekly Rewards Duplicate Prevention
**File**: `backend/app/models.py:116-127`
- Added unique partial index on `(user_id, reward_week)` in `PointTransaction` table
- Prevents duplicate weekly reward distribution to VIP users
- Uses PostgreSQL partial index to only constrain non-null `reward_week` values

### 2. VIP Expiration Logic Fix
**File**: `backend/app/api/routes/subscription.py:221-232`
- Fixed VIP status determination in RevenueCat webhook handler
- Correctly handles lifetime subscriptions with `expiration_at = None`
- Clear three-case logic: expired → no VIP, no expiration → VIP, has expiration → check date

### 3. Snowflake Clock Drift Protection
**File**: `backend/app/core/snowflake.py:35-45`
- Added 5-second threshold for clock backwards detection
- Raises `RuntimeError` for large clock drifts (>5s) instead of blocking indefinitely
- Prevents service hang in case of significant time synchronization issues

### 4. Redis Enqueue Transaction Safety
**File**: `backend/app/api/routes/emoji.py:104-130`
- Improved transaction handling when Redis enqueue fails
- Uses flag variable to defer status update until after exception handling
- Ensures task status is updated in a clean transaction with proper refresh

## Important Notes

### Database Migrations
After pulling these bug fixes, run:
```bash
cd backend
uv run alembic revision --autogenerate -m "Add unique constraint for weekly rewards"
uv run alembic upgrade head
```

### Monitoring Recommendations
- Set up alerts for Snowflake `RuntimeError` (clock drift detection)
- Monitor Redis connection failures in emoji creation endpoint
- Track duplicate `event_id` in RevenueCat webhook logs for idempotency verification

### Worker Deployment
Two workers need to be deployed:
1. **emoji_worker.py** - Long-running process for async emoji generation
2. **weekly_points_reward.py** - Cron job (run weekly, e.g., Sunday 00:00 UTC)

