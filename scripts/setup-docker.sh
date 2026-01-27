#!/bin/bash
# Server setup script for Docker deployment
# Run this script once on your Alibaba Cloud ECS

set -e

echo "=== Installing Docker ==="
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

echo "=== Installing Git ==="
# For CentOS/Alibaba Cloud Linux
yum install -y git || apt install -y git

echo "=== Cloning repository ==="
cd /root
git clone https://github.com/YOUR_ORG/nicosia.git

echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "1. Configure GitHub Secrets (see README)"
echo "2. Push to develop branch -> deploys to staging (port 8001)"
echo "3. Merge PR to main -> deploys to production (port 8000)"
echo ""
echo "Manual deployment:"
echo "  Staging:    cd /root/nicosia && docker compose -f docker-compose.staging.yml --project-name nicosia-staging up -d"
echo "  Production: cd /root/nicosia && docker compose -f docker-compose.production.yml --project-name nicosia-prod up -d"
