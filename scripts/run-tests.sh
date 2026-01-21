#!/bin/bash
# Run tests locally (without Docker)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "🧪 Running PicKitchen Tests"
echo "==========================="

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

echo "Running pytest..."
echo ""

# Run pytest with all arguments passed through
pytest "$@"

echo ""
echo "✅ Tests completed"
