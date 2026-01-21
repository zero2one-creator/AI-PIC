#!/bin/bash
# Local development environment setup script
# This script sets up PostgreSQL, Redis, and Python dependencies for local development

set -e

echo "🚀 PicKitchen Local Development Setup"
echo "======================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}❌ This script is designed for macOS. For Linux, please adjust the commands.${NC}"
    exit 1
fi

# 1. Check and install Homebrew
echo -e "\n${YELLOW}1. Checking Homebrew...${NC}"
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo -e "${GREEN}✅ Homebrew already installed${NC}"
fi

# 2. Install PostgreSQL if not present
echo -e "\n${YELLOW}2. Checking PostgreSQL...${NC}"
if ! brew services list | grep -q "postgresql"; then
    echo "Installing PostgreSQL..."
    brew install postgresql@17
    brew services start postgresql@17
    echo -e "${GREEN}✅ PostgreSQL installed and started${NC}"
else
    echo -e "${GREEN}✅ PostgreSQL already installed${NC}"
    if ! brew services list | grep "postgresql" | grep -q "started"; then
        echo "Starting PostgreSQL..."
        brew services start postgresql@17
    fi
fi

# 3. Install Redis if not present
echo -e "\n${YELLOW}3. Checking Redis...${NC}"
if ! command -v redis-cli &> /dev/null; then
    echo "Installing Redis..."
    brew install redis
    brew services start redis
    echo -e "${GREEN}✅ Redis installed and started${NC}"
else
    echo -e "${GREEN}✅ Redis already installed${NC}"
    if ! brew services list | grep "redis" | grep -q "started"; then
        echo "Starting Redis..."
        brew services start redis
    fi
fi

# 4. Install uv if not present
echo -e "\n${YELLOW}4. Checking uv...${NC}"
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo -e "${GREEN}✅ uv installed${NC}"
else
    echo -e "${GREEN}✅ uv already installed${NC}"
fi

# 5. Create PostgreSQL user and database
echo -e "\n${YELLOW}5. Setting up PostgreSQL user and database...${NC}"
PSQL_PATH=$(find /opt/homebrew -name "psql" 2>/dev/null | head -1)
if [ -z "$PSQL_PATH" ]; then
    PSQL_PATH=$(which psql)
fi

if [ -z "$PSQL_PATH" ]; then
    echo -e "${RED}❌ Could not find psql binary${NC}"
    exit 1
fi

# Create postgres user if not exists
if ! $PSQL_PATH -U $(whoami) -d postgres -c "SELECT 1 FROM pg_user WHERE usename = 'postgres'" 2>/dev/null | grep -q 1; then
    echo "Creating postgres user..."
    $PSQL_PATH -U $(whoami) -d postgres -c "CREATE USER postgres WITH SUPERUSER PASSWORD 'changethis';" 2>/dev/null || true
fi

# Create app database if not exists
if ! $PSQL_PATH -U postgres -d postgres -c "SELECT 1 FROM pg_database WHERE datname = 'app'" 2>/dev/null | grep -q 1; then
    echo "Creating app database..."
    $PSQL_PATH -U postgres -d postgres -c "CREATE DATABASE app OWNER postgres;" 2>/dev/null || true
fi

echo -e "${GREEN}✅ PostgreSQL user and database ready${NC}"

# 6. Install Python dependencies
echo -e "\n${YELLOW}6. Installing Python dependencies...${NC}"
cd "$(dirname "$0")/../backend"
uv sync
echo -e "${GREEN}✅ Python dependencies installed${NC}"

# 7. Run database migrations
echo -e "\n${YELLOW}7. Running database migrations...${NC}"
source .venv/bin/activate
alembic upgrade head
echo -e "${GREEN}✅ Database migrations completed${NC}"

# 8. Create helper scripts
echo -e "\n${YELLOW}8. Creating helper scripts...${NC}"
mkdir -p "$(dirname "$0")"

# Create .env.local if not exists
if [ ! -f "$(dirname "$0")/../.env.local" ]; then
    cat > "$(dirname "$0")/../.env.local" << 'ENVEOF'
# Local development environment variables
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=app
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changethis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
PROJECT_NAME=PicKitchen
ENVIRONMENT=local
SECRET_KEY=local-dev-secret-key-change-in-production-at-least-32-chars
ALIYUN_EMOJI_MOCK=true
ENVEOF
    echo -e "${GREEN}✅ Created .env.local${NC}"
fi

echo -e "\n${GREEN}✅ Setup completed successfully!${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Start the API server:"
echo "   cd backend && source .venv/bin/activate && fastapi dev app/main.py"
echo ""
echo "2. In another terminal, start the Worker:"
echo "   cd backend && source .venv/bin/activate && python -m worker.emoji_worker"
echo ""
echo "3. Access API documentation:"
echo "   http://localhost:8000/docs"
echo ""
echo "4. Run tests:"
echo "   cd backend && source .venv/bin/activate && pytest tests/"
