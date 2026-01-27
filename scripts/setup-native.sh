#!/bin/bash
# Server setup script for Native deployment (without Docker)
# Run this script once on your Alibaba Cloud ECS
#
# Architecture:
# - Single PostgreSQL instance with two databases: nicosia_prod, nicosia_staging
# - Single Redis instance (keys prefixed by ENVIRONMENT in app code)
# - Production API on port 8000, Staging API on port 8001

set -e

echo "=== Installing system dependencies ==="
# For CentOS/Alibaba Cloud Linux
yum update -y
yum install -y git curl nginx postgresql-server postgresql-contrib redis

# For Ubuntu, use:
# apt update && apt install -y git curl nginx postgresql postgresql-contrib redis-server

echo "=== Installing Python via uv ==="
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env

echo "=== Setting up PostgreSQL ==="
postgresql-setup --initdb || true
systemctl enable postgresql
systemctl start postgresql

# Create databases (same instance, different database names)
sudo -u postgres psql << 'SQLEOF'
CREATE DATABASE nicosia_prod;
CREATE DATABASE nicosia_staging;
SQLEOF

# Allow password authentication
sed -i 's/ident/md5/g' /var/lib/pgsql/data/pg_hba.conf
sed -i 's/peer/md5/g' /var/lib/pgsql/data/pg_hba.conf
systemctl restart postgresql

echo "=== Setting up Redis ==="
systemctl enable redis
systemctl start redis

echo "=== Cloning repository ==="
cd /root
git clone https://github.com/YOUR_ORG/nicosia.git
cd nicosia/backend
uv sync

echo "=== Creating systemd services ==="

# Production API service (port 8000)
cat > /etc/systemd/system/nicosia-prod.service << 'EOF'
[Unit]
Description=Nicosia Production API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/nicosia/backend
Environment="PATH=/root/nicosia/backend/.venv/bin:/usr/local/bin:/usr/bin"
EnvironmentFile=/root/nicosia/backend/.env.production
ExecStart=/root/nicosia/backend/.venv/bin/fastapi run --host 0.0.0.0 --port 8000 --workers 4 app/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Staging API service (port 8001)
cat > /etc/systemd/system/nicosia-staging.service << 'EOF'
[Unit]
Description=Nicosia Staging API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/nicosia/backend
Environment="PATH=/root/nicosia/backend/.venv/bin:/usr/local/bin:/usr/bin"
EnvironmentFile=/root/nicosia/backend/.env.staging
ExecStart=/root/nicosia/backend/.venv/bin/fastapi run --host 0.0.0.0 --port 8001 --workers 2 app/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Production Worker service
cat > /etc/systemd/system/nicosia-worker-prod.service << 'EOF'
[Unit]
Description=Nicosia Production Worker
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/nicosia/backend
Environment="PATH=/root/nicosia/backend/.venv/bin:/usr/local/bin:/usr/bin"
EnvironmentFile=/root/nicosia/backend/.env.production
ExecStart=/root/nicosia/backend/.venv/bin/python -m app.worker.emoji_worker
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Staging Worker service
cat > /etc/systemd/system/nicosia-worker-staging.service << 'EOF'
[Unit]
Description=Nicosia Staging Worker
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/nicosia/backend
Environment="PATH=/root/nicosia/backend/.venv/bin:/usr/local/bin:/usr/bin"
EnvironmentFile=/root/nicosia/backend/.env.staging
ExecStart=/root/nicosia/backend/.venv/bin/python -m app.worker.emoji_worker
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Production Scheduler service
cat > /etc/systemd/system/nicosia-scheduler-prod.service << 'EOF'
[Unit]
Description=Nicosia Production Scheduler
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/nicosia/backend
Environment="PATH=/root/nicosia/backend/.venv/bin:/usr/local/bin:/usr/bin"
EnvironmentFile=/root/nicosia/backend/.env.production
ExecStart=/root/nicosia/backend/.venv/bin/python -m app.worker.scheduler
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Staging Scheduler service
cat > /etc/systemd/system/nicosia-scheduler-staging.service << 'EOF'
[Unit]
Description=Nicosia Staging Scheduler
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/nicosia/backend
Environment="PATH=/root/nicosia/backend/.venv/bin:/usr/local/bin:/usr/bin"
EnvironmentFile=/root/nicosia/backend/.env.staging
ExecStart=/root/nicosia/backend/.venv/bin/python -m app.worker.scheduler
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "=== Enabling services ==="
systemctl daemon-reload
systemctl enable nicosia-prod nicosia-staging
systemctl enable nicosia-worker-prod nicosia-worker-staging
systemctl enable nicosia-scheduler-prod nicosia-scheduler-staging

echo "=== Setting up Nginx (optional reverse proxy) ==="
cat > /etc/nginx/conf.d/nicosia.conf << 'EOF'
# Production API
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Staging API
server {
    listen 80;
    server_name staging-api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

systemctl enable nginx
systemctl restart nginx

echo "=== Creating example environment files ==="

cat > /root/nicosia/backend/.env.production.example << 'EOF'
ENVIRONMENT=production
DOMAIN=yourdomain.com
SECRET_KEY=your-secret-key-here
FIRST_SUPERUSER=admin@yourdomain.com
FIRST_SUPERUSER_PASSWORD=changethis
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=nicosia_prod
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changethis
REDIS_HOST=localhost
REDIS_PORT=6379
SENTRY_DSN=
EOF

cat > /root/nicosia/backend/.env.staging.example << 'EOF'
ENVIRONMENT=staging
DOMAIN=staging.yourdomain.com
SECRET_KEY=your-secret-key-here
FIRST_SUPERUSER=admin@yourdomain.com
FIRST_SUPERUSER_PASSWORD=changethis
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=nicosia_staging
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changethis
REDIS_HOST=localhost
REDIS_PORT=6379
SENTRY_DSN=
EOF

echo "=== Setup complete! ==="
echo ""
echo "Architecture:"
echo "  PostgreSQL: localhost:5432 (databases: nicosia_prod, nicosia_staging)"
echo "  Redis: localhost:6379 (shared, keys prefixed by ENVIRONMENT)"
echo "  Production API: http://your-server:8000"
echo "  Staging API: http://your-server:8001"
echo ""
echo "Next steps:"
echo "1. Copy and edit environment files:"
echo "   cp /root/nicosia/backend/.env.production.example /root/nicosia/backend/.env.production"
echo "   cp /root/nicosia/backend/.env.staging.example /root/nicosia/backend/.env.staging"
echo ""
echo "2. Run migrations for both environments:"
echo "   cd /root/nicosia/backend && source .venv/bin/activate"
echo "   export \$(cat .env.production | xargs) && alembic upgrade head"
echo "   export \$(cat .env.staging | xargs) && alembic upgrade head"
echo ""
echo "3. Start services:"
echo "   systemctl start nicosia-prod nicosia-worker-prod nicosia-scheduler-prod"
echo "   systemctl start nicosia-staging nicosia-worker-staging nicosia-scheduler-staging"
