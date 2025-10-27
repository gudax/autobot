#!/bin/bash

###############################################################################
# Status Check Script - Check deployment status on server
#
# Usage: bash status.sh SERVER_IP
###############################################################################

if [ -z "$1" ]; then
    echo "Usage: bash status.sh SERVER_IP"
    exit 1
fi

SERVER_IP=$1

echo "=========================================="
echo "AutoBot Trading System - Status Check"
echo "Server: $SERVER_IP"
echo "=========================================="
echo ""

ssh root@$SERVER_IP << 'EOF'

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "1. Docker Services Status:"
echo "-------------------------------------------"
cd /opt/autobot
docker compose -f docker-compose.prod.yml ps
echo ""

echo "2. Service Health Checks:"
echo "-------------------------------------------"

# Check Back Office Server
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Back Office Server: Healthy${NC}"
else
    echo -e "${RED}✗ Back Office Server: Unhealthy${NC}"
fi

# Check PostgreSQL
if docker compose -f /opt/autobot/docker-compose.prod.yml exec -T postgres pg_isready > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL: Healthy${NC}"
else
    echo -e "${RED}✗ PostgreSQL: Unhealthy${NC}"
fi

# Check Redis
if docker compose -f /opt/autobot/docker-compose.prod.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis: Healthy${NC}"
else
    echo -e "${YELLOW}⚠ Redis: Not running (optional)${NC}"
fi

echo ""
echo "3. System Resources:"
echo "-------------------------------------------"
echo "CPU Usage:"
top -bn1 | grep "Cpu(s)" | awk '{print "  " $2 "% used"}'

echo "Memory Usage:"
free -h | awk 'NR==2{printf "  %s / %s (%.2f%%)\n", $3, $2, $3*100/$2 }'

echo "Disk Usage:"
df -h / | awk 'NR==2{printf "  %s / %s (%s)\n", $3, $2, $5}'

echo ""
echo "4. Recent Logs (last 20 lines):"
echo "-------------------------------------------"
docker compose -f /opt/autobot/docker-compose.prod.yml logs --tail=20 back_office_server

echo ""
echo "5. Database Stats:"
echo "-------------------------------------------"
docker compose -f /opt/autobot/docker-compose.prod.yml exec -T postgres \
  psql -U autobot_user -d autobot_trading -c "
    SELECT
      'Users' as table, COUNT(*) as count FROM users
    UNION ALL
    SELECT 'Sessions', COUNT(*) FROM user_sessions
    UNION ALL
    SELECT 'Orders', COUNT(*) FROM orders
    UNION ALL
    SELECT 'Trades', COUNT(*) FROM trades;
  " 2>/dev/null || echo "Database not accessible"

echo ""
EOF

echo "=========================================="
echo "Status check complete"
echo "=========================================="
