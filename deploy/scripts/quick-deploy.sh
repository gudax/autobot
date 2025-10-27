#!/bin/bash

###############################################################################
# Quick Deploy Script - For rapid deployments without full configuration
#
# Usage: bash quick-deploy.sh SERVER_IP
###############################################################################

set -e

if [ -z "$1" ]; then
    echo "Usage: bash quick-deploy.sh SERVER_IP"
    echo "Example: bash quick-deploy.sh 123.45.67.89"
    exit 1
fi

SERVER_IP=$1
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Starting quick deployment to $SERVER_IP...${NC}"

# 1. Test SSH connection
echo -e "${GREEN}[1/6] Testing SSH connection...${NC}"
if ! ssh -o ConnectTimeout=5 root@$SERVER_IP "echo 'SSH OK'"; then
    echo "Error: Cannot connect to server"
    exit 1
fi

# 2. Run server setup
echo -e "${GREEN}[2/6] Running server setup...${NC}"
ssh root@$SERVER_IP 'bash -s' < ./scripts/server_setup.sh

# 3. Setup database
echo -e "${GREEN}[3/6] Setting up database...${NC}"
ssh root@$SERVER_IP << 'EOF'
sudo -u postgres psql << EOSQL
CREATE DATABASE autobot_trading;
CREATE USER autobot_user WITH ENCRYPTED PASSWORD 'changeme123';
GRANT ALL PRIVILEGES ON DATABASE autobot_trading TO autobot_user;
EOSQL
EOF

# 4. Clone repository
echo -e "${GREEN}[4/6] Cloning repository...${NC}"
ssh root@$SERVER_IP << 'EOF'
cd /opt
git clone https://github.com/gudax/autobot.git || (cd autobot && git pull)
EOF

# 5. Configure environment
echo -e "${GREEN}[5/6] Configuring environment...${NC}"
ssh root@$SERVER_IP << 'EOF'
cd /opt/autobot

# Generate keys
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Create .env for back office
cat > back_office_server/.env << ENVEOF
APP_ENV=production
SECRET_KEY=$SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY
DATABASE_URL=postgresql://autobot_user:changeme123@postgres:5432/autobot_trading
MATCH_TRADE_API_URL=https://api.match-trade.com
HOST=0.0.0.0
PORT=8000
WORKERS=4
ENVEOF

# Create .env for dashboard
cat > dashboard/.env << ENVEOF
VITE_API_URL=http://$SERVER_IP:8000
VITE_WS_URL=ws://$SERVER_IP:8000
ENVEOF

# Create .env for trading engine
cat > trading_engine/.env << ENVEOF
MATCH_TRADE_API_URL=https://api.match-trade.com
BACK_OFFICE_API_URL=http://localhost:8000
LOG_LEVEL=INFO
ENVEOF
EOF

# 6. Start services
echo -e "${GREEN}[6/6] Starting services...${NC}"
ssh root@$SERVER_IP << 'EOF'
cd /opt/autobot
docker compose -f docker-compose.prod.yml up -d --build
EOF

echo ""
echo -e "${GREEN}=========================================="
echo "Deployment Complete!"
echo "==========================================${NC}"
echo ""
echo "Access your services:"
echo "  - Dashboard: http://$SERVER_IP"
echo "  - API: http://$SERVER_IP:8000"
echo "  - API Docs: http://$SERVER_IP:8000/docs"
echo ""
echo -e "${YELLOW}Important: Change the default database password!${NC}"
echo ""
