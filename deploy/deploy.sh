#!/bin/bash

###############################################################################
# AutoBot Trading System - Deployment Script
#
# This script deploys the application to Vultr server via SSH
#
# Usage:
#   ./deploy.sh [environment] [component]
#
# Arguments:
#   environment: production|staging (default: production)
#   component: all|trading|backend|frontend (default: all)
#
# Examples:
#   ./deploy.sh                          # Deploy all to production
#   ./deploy.sh production backend       # Deploy only backend
#   ./deploy.sh staging all              # Deploy all to staging
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${SCRIPT_DIR}/config.env"

# Default values
ENVIRONMENT="${1:-production}"
COMPONENT="${2:-all}"

# Load configuration
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Configuration file not found: $CONFIG_FILE${NC}"
    echo -e "${YELLOW}Please copy config.env.example to config.env and configure it${NC}"
    exit 1
fi

source "$CONFIG_FILE"

# Validate configuration
if [ -z "$SERVER_HOST" ] || [ "$SERVER_HOST" == "your-server-ip" ]; then
    echo -e "${RED}Error: SERVER_HOST not configured in $CONFIG_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}=========================================="
echo "AutoBot Trading System - Deployment"
echo "=========================================="
echo "Environment: $ENVIRONMENT"
echo "Component: $COMPONENT"
echo "Server: $SERVER_USER@$SERVER_HOST"
echo -e "==========================================${NC}"
echo ""

# Function to execute commands on remote server
remote_exec() {
    ssh -i "$SSH_KEY_PATH" -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" "$@"
}

# Function to copy files to remote server
remote_copy() {
    scp -i "$SSH_KEY_PATH" -P "$SERVER_PORT" -r "$1" "$SERVER_USER@$SERVER_HOST:$2"
}

# Step 1: Check server connection
echo -e "${GREEN}[1/8] Checking server connection...${NC}"
if ! remote_exec "echo 'Connection successful'" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to server${NC}"
    echo "Please check:"
    echo "  - SERVER_HOST: $SERVER_HOST"
    echo "  - SERVER_USER: $SERVER_USER"
    echo "  - SSH_KEY_PATH: $SSH_KEY_PATH"
    exit 1
fi
echo -e "${GREEN}✓ Server connection successful${NC}"

# Step 2: Prepare deployment directory on server
echo -e "${GREEN}[2/8] Preparing deployment directory...${NC}"
remote_exec "mkdir -p /opt/autobot/{trading_engine,back_office_server,dashboard,logs,backups}"
echo -e "${GREEN}✓ Deployment directory ready${NC}"

# Step 3: Clone/Update repository on server
echo -e "${GREEN}[3/8] Updating code from GitHub...${NC}"
remote_exec "cd /opt/autobot && \
    if [ -d .git ]; then \
        git fetch origin && \
        git reset --hard origin/$GITHUB_BRANCH && \
        git clean -fd; \
    else \
        git clone -b $GITHUB_BRANCH https://github.com/$GITHUB_REPO.git /tmp/autobot-tmp && \
        mv /tmp/autobot-tmp/* . && \
        rm -rf /tmp/autobot-tmp; \
    fi"
echo -e "${GREEN}✓ Code updated from GitHub${NC}"

# Step 4: Copy environment files
echo -e "${GREEN}[4/8] Deploying environment configuration...${NC}"

# Create production .env file for back office server
remote_exec "cat > /opt/autobot/back_office_server/.env << 'EOF'
# Production Environment Variables
APP_ENV=$APP_ENV
SECRET_KEY=$SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY

# Database
DATABASE_URL=postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB

# Match-Trade API
MATCH_TRADE_API_URL=$MATCH_TRADE_API_URL
MATCH_TRADE_WS_URL=$MATCH_TRADE_WS_URL

# Server Configuration
HOST=0.0.0.0
PORT=$BACK_OFFICE_PORT
WORKERS=4

# CORS
CORS_ORIGINS=http://$SERVER_HOST,http://$APP_DOMAIN,https://$APP_DOMAIN

# Session
SESSION_REFRESH_INTERVAL_MINUTES=10
SESSION_EXPIRY_HOURS=24

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/autobot/back_office.log
EOF"

# Create production .env file for dashboard
remote_exec "cat > /opt/autobot/dashboard/.env << 'EOF'
VITE_API_URL=http://$SERVER_HOST:$BACK_OFFICE_PORT
VITE_WS_URL=ws://$SERVER_HOST:$BACK_OFFICE_PORT
VITE_APP_ENV=$APP_ENV
EOF"

# Create production .env file for trading engine
remote_exec "cat > /opt/autobot/trading_engine/.env << 'EOF'
# Trading Engine Configuration
MATCH_TRADE_API_URL=$MATCH_TRADE_API_URL
MATCH_TRADE_WS_URL=$MATCH_TRADE_WS_URL
BACK_OFFICE_API_URL=http://localhost:$BACK_OFFICE_PORT
LOG_LEVEL=INFO
LOG_FILE=/var/log/autobot/trading_engine.log
EOF"

echo -e "${GREEN}✓ Environment configuration deployed${NC}"

# Step 5: Deploy components
if [ "$COMPONENT" == "all" ] || [ "$COMPONENT" == "backend" ]; then
    echo -e "${GREEN}[5/8] Deploying Back Office Server...${NC}"

    remote_exec "cd /opt/autobot && docker compose -f docker-compose.prod.yml up -d --build back_office_server postgres"

    echo -e "${GREEN}✓ Back Office Server deployed${NC}"
fi

if [ "$COMPONENT" == "all" ] || [ "$COMPONENT" == "frontend" ]; then
    echo -e "${GREEN}[5/8] Building and deploying Dashboard...${NC}"

    # Build dashboard on server
    remote_exec "cd /opt/autobot/dashboard && \
        npm install && \
        npm run build"

    # Copy built files to nginx
    remote_exec "rm -rf /var/www/autobot && \
        mkdir -p /var/www/autobot && \
        cp -r /opt/autobot/dashboard/dist/* /var/www/autobot/"

    echo -e "${GREEN}✓ Dashboard deployed${NC}"
fi

if [ "$COMPONENT" == "all" ] || [ "$COMPONENT" == "trading" ]; then
    echo -e "${GREEN}[5/8] Deploying Trading Engine...${NC}"

    remote_exec "cd /opt/autobot && docker compose -f docker-compose.prod.yml up -d --build trading_engine"

    echo -e "${GREEN}✓ Trading Engine deployed${NC}"
fi

# Step 6: Run database migrations
if [ "$COMPONENT" == "all" ] || [ "$COMPONENT" == "backend" ]; then
    echo -e "${GREEN}[6/8] Running database migrations...${NC}"

    remote_exec "cd /opt/autobot/back_office_server && \
        docker compose -f ../docker-compose.prod.yml exec -T back_office_server \
        alembic upgrade head" || echo -e "${YELLOW}Warning: Migration failed or no migrations needed${NC}"

    echo -e "${GREEN}✓ Migrations completed${NC}"
fi

# Step 7: Health check
echo -e "${GREEN}[7/8] Running health checks...${NC}"

sleep 5  # Wait for services to start

# Check Back Office Server
if [ "$COMPONENT" == "all" ] || [ "$COMPONENT" == "backend" ]; then
    if remote_exec "curl -f http://localhost:$BACK_OFFICE_PORT/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Back Office Server is healthy${NC}"
    else
        echo -e "${YELLOW}⚠ Back Office Server health check failed${NC}"
    fi
fi

# Check PostgreSQL
if remote_exec "docker compose -f /opt/autobot/docker-compose.prod.yml exec -T postgres pg_isready" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is healthy${NC}"
else
    echo -e "${YELLOW}⚠ PostgreSQL health check failed${NC}"
fi

# Step 8: Show service status
echo -e "${GREEN}[8/8] Service status:${NC}"
remote_exec "cd /opt/autobot && docker compose -f docker-compose.prod.yml ps"

echo ""
echo -e "${GREEN}=========================================="
echo "Deployment Complete!"
echo "==========================================${NC}"
echo ""
echo "Service URLs:"
echo "  - Dashboard: http://$SERVER_HOST:$NGINX_PORT"
echo "  - Back Office API: http://$SERVER_HOST:$BACK_OFFICE_PORT"
echo "  - API Docs: http://$SERVER_HOST:$BACK_OFFICE_PORT/docs"
echo ""
echo "To view logs:"
echo "  ssh $SERVER_USER@$SERVER_HOST 'cd /opt/autobot && docker compose -f docker-compose.prod.yml logs -f'"
echo ""
echo "To restart services:"
echo "  ssh $SERVER_USER@$SERVER_HOST 'cd /opt/autobot && docker compose -f docker-compose.prod.yml restart'"
echo ""
