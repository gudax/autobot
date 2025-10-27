#!/bin/bash

###############################################################################
# AutoBot Trading System - Server Setup Script
# Server: 158.247.198.24
#
# This script automates the initial server setup
###############################################################################

set -e

SERVER_IP="158.247.198.24"
SERVER_USER="root"
DB_PASSWORD="AutoBot2024!SecurePassword"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=========================================="
echo "AutoBot - Server Setup Automation"
echo "Server: $SERVER_IP"
echo "==========================================${NC}"
echo ""

# Function to execute commands on remote server
remote_exec() {
    ssh "$SERVER_USER@$SERVER_IP" "$@"
}

# Step 1: Test connection
echo -e "${GREEN}[1/8] Testing SSH connection...${NC}"
if ! remote_exec "echo 'SSH connection successful'"; then
    echo -e "${RED}Error: Cannot connect to server${NC}"
    echo "Please ensure:"
    echo "  - Server is accessible: ping $SERVER_IP"
    echo "  - SSH key is set up: ssh-copy-id $SERVER_USER@$SERVER_IP"
    exit 1
fi
echo -e "${GREEN}✓ SSH connection successful${NC}"
echo ""

# Step 2: Run server setup script
echo -e "${GREEN}[2/8] Running server setup (Docker, PostgreSQL, etc.)...${NC}"
echo "This will take 5-10 minutes..."
remote_exec 'bash -s' < ./server_setup.sh
echo -e "${GREEN}✓ Server setup complete${NC}"
echo ""

# Step 3: Setup PostgreSQL
echo -e "${GREEN}[3/8] Setting up PostgreSQL database...${NC}"
remote_exec "sudo -u postgres psql << 'EOSQL'
CREATE DATABASE autobot_trading;
CREATE USER autobot_user WITH ENCRYPTED PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE autobot_trading TO autobot_user;
\q
EOSQL"
echo -e "${GREEN}✓ PostgreSQL database configured${NC}"
echo ""

# Step 4: Clone repository
echo -e "${GREEN}[4/8] Cloning repository...${NC}"
remote_exec "cd /opt && git clone https://github.com/gudax/autobot.git || (cd autobot && git pull)"
echo -e "${GREEN}✓ Repository cloned${NC}"
echo ""

# Step 5: Generate keys
echo -e "${GREEN}[5/8] Generating encryption keys...${NC}"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

echo "Generated keys:"
echo "  SECRET_KEY: $SECRET_KEY"
echo "  ENCRYPTION_KEY: $ENCRYPTION_KEY"
echo ""

# Save keys locally
cat > ./generated_keys.txt << EOF
Server: $SERVER_IP
Generated: $(date)

SECRET_KEY=$SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY
DB_PASSWORD=$DB_PASSWORD
EOF
chmod 600 ./generated_keys.txt
echo -e "${GREEN}✓ Keys saved to: ./generated_keys.txt${NC}"
echo ""

# Step 6: Configure environment
echo -e "${GREEN}[6/8] Configuring environment variables...${NC}"
remote_exec "cat > /opt/autobot/back_office_server/.env << 'EOF'
APP_ENV=production
APP_NAME=AutoBot Trading System
DEBUG=false
DATABASE_URL=postgresql://autobot_user:$DB_PASSWORD@postgres:5432/autobot_trading
MATCH_TRADE_API_URL=https://mtr-demo-prod.match-trader.com
MATCH_TRADE_WS_URL=wss://mtr-demo-prod.match-trader.com
HOST=0.0.0.0
PORT=8000
WORKERS=4
SECRET_KEY=$SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY
CORS_ORIGINS=http://$SERVER_IP,http://localhost:3000
SESSION_REFRESH_INTERVAL_MINUTES=10
SESSION_EXPIRY_HOURS=24
LOG_LEVEL=INFO
LOG_FILE=/var/log/autobot/back_office.log
EOF"

remote_exec "cat > /opt/autobot/dashboard/.env << 'EOF'
VITE_API_URL=http://$SERVER_IP:8000
VITE_WS_URL=ws://$SERVER_IP:8000
VITE_APP_ENV=production
EOF"

remote_exec "cat > /opt/autobot/trading_engine/.env << 'EOF'
MATCH_TRADE_API_URL=https://mtr-demo-prod.match-trader.com
MATCH_TRADE_WS_URL=wss://mtr-demo-prod.match-trader.com
BACK_OFFICE_API_URL=http://localhost:8000
LOG_LEVEL=INFO
LOG_FILE=/var/log/autobot/trading_engine.log
EOF"

remote_exec "mkdir -p /var/log/autobot && chmod 755 /var/log/autobot"
echo -e "${GREEN}✓ Environment configured${NC}"
echo ""

# Step 7: Start services
echo -e "${GREEN}[7/8] Starting services...${NC}"
remote_exec "cd /opt/autobot && docker compose -f docker-compose.prod.yml up -d --build"
sleep 10
echo -e "${GREEN}✓ Services started${NC}"
echo ""

# Step 8: Health check
echo -e "${GREEN}[8/8] Running health checks...${NC}"
sleep 5

if remote_exec "curl -f http://localhost:8000/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Back Office Server: Healthy${NC}"
else
    echo -e "${YELLOW}⚠ Back Office Server: Starting (check logs)${NC}"
fi

if remote_exec "docker compose -f /opt/autobot/docker-compose.prod.yml exec -T postgres pg_isready" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL: Healthy${NC}"
else
    echo -e "${YELLOW}⚠ PostgreSQL: Starting (check logs)${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "Server Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "Access your services:"
echo "  - Dashboard: http://$SERVER_IP"
echo "  - API: http://$SERVER_IP:8000"
echo "  - API Docs: http://$SERVER_IP:8000/docs"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "  - Keys saved to: ./generated_keys.txt"
echo "  - Keep this file secure!"
echo "  - Next: Set up GitHub Secrets"
echo ""
echo "View service status:"
echo "  ssh $SERVER_USER@$SERVER_IP 'cd /opt/autobot && docker compose -f docker-compose.prod.yml ps'"
echo ""
echo "View logs:"
echo "  ssh $SERVER_USER@$SERVER_IP 'cd /opt/autobot && docker compose -f docker-compose.prod.yml logs -f'"
echo ""
