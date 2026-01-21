#!/bin/bash
# Manage local services (PostgreSQL, Redis)

set -e

COMMAND=${1:-help}

case $COMMAND in
    start)
        echo "🚀 Starting local services..."
        brew services start postgresql@17 || true
        brew services start redis || true
        echo "✅ Services started"
        brew services list | grep -E "postgresql|redis"
        ;;
    stop)
        echo "🛑 Stopping local services..."
        brew services stop postgresql@17 || true
        brew services stop redis || true
        echo "✅ Services stopped"
        ;;
    status)
        echo "📊 Service status:"
        brew services list | grep -E "postgresql|redis"
        ;;
    restart)
        echo "🔄 Restarting local services..."
        brew services restart postgresql@17 || true
        brew services restart redis || true
        echo "✅ Services restarted"
        brew services list | grep -E "postgresql|redis"
        ;;
    logs-db)
        echo "📋 PostgreSQL logs:"
        tail -f /opt/homebrew/var/log/postgres.log 2>/dev/null || echo "Log file not found"
        ;;
    logs-redis)
        echo "📋 Redis logs:"
        tail -f /opt/homebrew/var/log/redis.log 2>/dev/null || echo "Log file not found"
        ;;
    *)
        echo "Usage: bash scripts/manage-services.sh [command]"
        echo ""
        echo "Commands:"
        echo "  start       - Start PostgreSQL and Redis"
        echo "  stop        - Stop PostgreSQL and Redis"
        echo "  status      - Show service status"
        echo "  restart     - Restart PostgreSQL and Redis"
        echo "  logs-db     - Show PostgreSQL logs"
        echo "  logs-redis  - Show Redis logs"
        ;;
esac
