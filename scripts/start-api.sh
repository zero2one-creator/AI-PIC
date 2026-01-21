#!/bin/bash
# Start PicKitchen API server locally (without Docker)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "🚀 Starting PicKitchen API Server"
echo "=================================="

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

# Check if PostgreSQL is running
echo "Checking PostgreSQL..."
if ! redis-cli ping &> /dev/null; then
    echo "⚠️  Redis is not running. Starting Redis..."
    brew services start redis || true
fi

# Check if Redis is running
echo "Checking Redis..."
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
echo "Starting FastAPI development server..."
echo "API will be available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start FastAPI with auto-reload
fastapi dev app/main.py
