#!/bin/bash

###############################################################################
# Vultr Server Initial Setup Script
#
# This script prepares a fresh Vultr Ubuntu/Debian server for running
# the AutoBot Trading System
#
# Usage: bash server_setup.sh
###############################################################################

set -e  # Exit on error

echo "=========================================="
echo "AutoBot Trading System - Server Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${GREEN}[1/10] Updating system packages...${NC}"
apt-get update
apt-get upgrade -y

echo -e "${GREEN}[2/10] Installing essential tools...${NC}"
apt-get install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    build-essential \
    software-properties-common \
    ca-certificates \
    gnupg \
    lsb-release

echo -e "${GREEN}[3/10] Installing Docker...${NC}"
# Remove old Docker installations
apt-get remove -y docker docker-engine docker.io containerd runc || true

# Add Docker's official GPG key
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Add current user to docker group (if not root)
if [ -n "$SUDO_USER" ]; then
    usermod -aG docker $SUDO_USER
    echo -e "${YELLOW}Note: User $SUDO_USER added to docker group. Re-login required.${NC}"
fi

echo -e "${GREEN}[4/10] Installing Docker Compose...${NC}"
# Docker Compose v2 is already installed as plugin above
docker compose version

echo -e "${GREEN}[5/10] Installing Python 3.11...${NC}"
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip

# Set Python 3.11 as default (optional)
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

echo -e "${GREEN}[6/10] Installing Node.js 20.x and npm...${NC}"
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Install pnpm (optional, faster than npm)
npm install -g pnpm

echo -e "${GREEN}[7/10] Installing PostgreSQL 15...${NC}"
# Add PostgreSQL repository
sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
apt-get update
apt-get install -y postgresql-15 postgresql-contrib-15

# Start and enable PostgreSQL
systemctl start postgresql
systemctl enable postgresql

echo -e "${GREEN}[8/10] Installing Nginx...${NC}"
apt-get install -y nginx
systemctl start nginx
systemctl enable nginx

echo -e "${GREEN}[9/10] Configuring firewall (UFW)...${NC}"
apt-get install -y ufw

# Allow SSH (important!)
ufw allow 22/tcp

# Allow HTTP and HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Allow application ports (optional, if not using reverse proxy)
ufw allow 8000/tcp  # Back Office Server
ufw allow 3000/tcp  # Dashboard

# Enable firewall
ufw --force enable

echo -e "${GREEN}[10/10] Creating application directory...${NC}"
mkdir -p /opt/autobot
mkdir -p /var/log/autobot
mkdir -p /var/backups/autobot

# Set permissions
chmod 755 /opt/autobot
chmod 755 /var/log/autobot
chmod 700 /var/backups/autobot

echo ""
echo -e "${GREEN}=========================================="
echo "Server Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "Installed versions:"
echo "  - Docker: $(docker --version)"
echo "  - Docker Compose: $(docker compose version)"
echo "  - Python: $(python3 --version)"
echo "  - Node.js: $(node --version)"
echo "  - npm: $(npm --version)"
echo "  - PostgreSQL: $(psql --version)"
echo "  - Nginx: $(nginx -v 2>&1)"
echo ""
echo -e "${YELLOW}Important Next Steps:${NC}"
echo "1. Configure PostgreSQL database and user"
echo "2. Set up SSL certificates (Let's Encrypt)"
echo "3. Configure Nginx reverse proxy"
echo "4. Clone application repository"
echo "5. Set up environment variables"
echo ""
echo -e "${YELLOW}Note: If you added a user to docker group, please re-login for changes to take effect${NC}"
echo ""
