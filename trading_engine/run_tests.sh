#!/bin/bash

# Test runner script for Trading Engine

echo "========================================"
echo "Running Trading Engine Tests"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Create logs directory if not exists
mkdir -p logs

# Run pytest
echo "Running pytest..."
python -m pytest tests/ -v --tb=short

# Check result
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi

echo ""
echo "To run specific tests:"
echo "  pytest tests/test_market_data.py -v"
echo "  pytest tests/test_orderbook.py -v"
echo "  pytest tests/test_websocket.py -v"
echo "  pytest tests/test_integration.py -v"
echo ""
echo "To run with coverage:"
echo "  pytest tests/ --cov=. --cov-report=html"
