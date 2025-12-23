#!/bin/bash
# Repo Auditor — Test Runner Script

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo " Repo Auditor — Test Suite"
echo "=========================================="

cd backend

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo -e "${RED}Virtual environment not found. Run ./scripts/setup.sh first${NC}"
    exit 1
fi

# Parse arguments
COVERAGE=false
VERBOSE=false
UNIT_ONLY=false
INTEGRATION_ONLY=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --coverage|-c) COVERAGE=true ;;
        --verbose|-v) VERBOSE=true ;;
        --unit|-u) UNIT_ONLY=true ;;
        --integration|-i) INTEGRATION_ONLY=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Build pytest command
PYTEST_CMD="pytest"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=app --cov-report=term-missing --cov-report=html"
fi

if [ "$UNIT_ONLY" = true ]; then
    PYTEST_CMD="$PYTEST_CMD tests/unit/"
elif [ "$INTEGRATION_ONLY" = true ]; then
    PYTEST_CMD="$PYTEST_CMD tests/integration/"
fi

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
echo "Command: $PYTEST_CMD"
echo ""

$PYTEST_CMD

# Show coverage report location if generated
if [ "$COVERAGE" = true ]; then
    echo ""
    echo -e "${GREEN}Coverage report generated: backend/htmlcov/index.html${NC}"
fi
