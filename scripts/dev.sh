#!/bin/bash
# Repo Auditor — Development Server Script
# Starts the backend development server with hot reload

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo " Repo Auditor — Development Server"
echo "=========================================="

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Set debug mode
export DEBUG=true

cd backend

# Activate virtual environment
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}Virtual environment not found. Run ./scripts/setup.sh first${NC}"
    exit 1
fi

# Check if database is running
echo -e "${YELLOW}Checking database connection...${NC}"
if ! pg_isready -h ${POSTGRES_HOST:-localhost} -p ${POSTGRES_PORT:-5432} -U ${POSTGRES_USER:-postgres} > /dev/null 2>&1; then
    echo -e "${YELLOW}Database not running. Starting with docker-compose...${NC}"
    cd ..
    docker-compose up -d db
    cd backend

    # Wait for database to be ready
    echo "Waiting for database to start..."
    sleep 3
fi

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
alembic upgrade head

# Start server
echo -e "${GREEN}Starting development server...${NC}"
echo ""
echo "API:      http://localhost:8000"
echo "Docs:     http://localhost:8000/docs"
echo "Health:   http://localhost:8000/health"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
