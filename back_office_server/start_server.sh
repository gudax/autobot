#!/bin/bash

# Start script for Back Office Server

echo "========================================="
echo "Starting Back Office Server"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found. Copying from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}Please edit .env file with your configuration before running!${NC}"
    exit 1
fi

# Create logs directory
mkdir -p logs

# Check PostgreSQL connection
echo "Checking PostgreSQL connection..."
if command -v pg_isready &> /dev/null; then
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        echo -e "${GREEN}✓ PostgreSQL is running${NC}"
    else
        echo -e "${RED}✗ PostgreSQL is not running${NC}"
        echo "Start PostgreSQL with: docker-compose up -d postgres"
        exit 1
    fi
else
    echo -e "${YELLOW}! pg_isready not found, skipping PostgreSQL check${NC}"
fi

# Run database migrations
echo ""
echo "Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database migrations completed${NC}"
else
    echo -e "${YELLOW}! Database migrations may have issues (this is normal for first run)${NC}"
fi

# Start server
echo ""
echo "Starting FastAPI server..."
echo "API Documentation: http://localhost:8000/docs"
echo "ReDoc: http://localhost:8000/redoc"
echo ""

# Start with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
