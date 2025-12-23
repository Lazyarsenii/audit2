#!/bin/bash
# Repo Auditor — Docker Development Script
# Starts all services using Docker Compose

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo " Repo Auditor — Docker Development"
echo "=========================================="

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}No .env file found. Running setup...${NC}"
    ./scripts/setup.sh
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Build and start services
echo -e "${YELLOW}Starting Docker services...${NC}"
docker-compose up -d --build

echo ""
echo -e "${GREEN}Services started!${NC}"
echo ""
echo "Backend API:  http://localhost:8000"
echo "API Docs:     http://localhost:8000/docs"
echo "Health:       http://localhost:8000/health"
echo ""
echo "Logs: docker-compose logs -f"
echo "Stop: docker-compose down"
echo ""

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
sleep 5

# Check health
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}Backend is healthy!${NC}"
else
    echo -e "${YELLOW}Backend not responding yet. Check logs: docker-compose logs backend${NC}"
fi
