#!/bin/bash
# Start PicKitchen Worker locally (without Docker)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "🚀 Starting PicKitchen Worker"
echo "============================="

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    echo "❌ Backend directory not found at $BACKEND_DIR"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$BACKEND_DIR/.venv" ]; then
    echo "❌ Virtual environment not found. Run: bash scripts/setup-local.sh"
    exit 1
fi

# Activate virtual environment
cd "$BACKEND_DIR"
source .venv/bin/activate

# Check if Redis is running
echo "Checking Redis..."
if ! redis-cli ping &> /dev/null; then
    echo "❌ Redis is not running"
    echo "Run: brew services start redis"
    exit 1
fi

# Check if PostgreSQL is running
echo "Checking PostgreSQL..."
PSQL_PATH=$(find /opt/homebrew -name "psql" 2>/dev/null | head -1)
if [ -z "$PSQL_PATH" ]; then
    PSQL_PATH=$(which psql)
fi

if ! $PSQL_PATH -U postgres -d app -c "SELECT 1" &> /dev/null; then
    echo "❌ PostgreSQL is not running or database 'app' is not accessible"
    echo "Run: brew services start postgresql@17"
    exit 1
fi

echo "✅ All services are running"
echo ""
echo "Starting Worker..."
echo "Worker will process emoji generation tasks from Redis Streams"
echo ""
echo "Press Ctrl+C to stop the worker"
echo ""

# Start Worker
python -m worker.emoji_worker
