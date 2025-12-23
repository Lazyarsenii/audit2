#!/bin/bash
# Repo Auditor — Setup Script
# Run this script to set up the development environment

set -e

echo "=========================================="
echo " Repo Auditor — Setup"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo -e "\n${YELLOW}Checking Python version...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo -e "${GREEN}Python $PYTHON_VERSION found${NC}"

    # Check if version is 3.11+
    if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)'; then
        echo -e "${GREEN}Python version is compatible${NC}"
    else
        echo -e "${RED}Warning: Python 3.11+ recommended${NC}"
    fi
else
    echo -e "${RED}Python 3 not found. Please install Python 3.11+${NC}"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "\n${YELLOW}Creating .env file from template...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env

        # Generate secret key
        SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")

        # Generate postgres password
        POSTGRES_PASSWORD=$(openssl rand -base64 16 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(16))")

        # Update .env with generated values
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/your-secure-password-here/$POSTGRES_PASSWORD/" .env
            sed -i '' "s/generate-a-secure-key-here/$SECRET_KEY/" .env
            sed -i '' "s/your-pgadmin-password-here/$POSTGRES_PASSWORD/" .env
        else
            # Linux
            sed -i "s/your-secure-password-here/$POSTGRES_PASSWORD/" .env
            sed -i "s/generate-a-secure-key-here/$SECRET_KEY/" .env
            sed -i "s/your-pgadmin-password-here/$POSTGRES_PASSWORD/" .env
        fi

        echo -e "${GREEN}.env file created with generated credentials${NC}"
        echo -e "${YELLOW}Review .env file and update as needed${NC}"
    else
        echo -e "${RED}.env.example not found${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}.env file already exists${NC}"
fi

# Setup backend
echo -e "\n${YELLOW}Setting up backend...${NC}"
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}Backend setup complete${NC}"

cd ..

# Setup frontend (optional)
if [ -d "ui" ]; then
    echo -e "\n${YELLOW}Setting up frontend...${NC}"
    cd ui

    if command -v npm &> /dev/null; then
        echo "Installing npm dependencies..."
        npm install
        echo -e "${GREEN}Frontend setup complete${NC}"
    else
        echo -e "${YELLOW}npm not found. Skipping frontend setup.${NC}"
    fi

    cd ..
fi

echo -e "\n=========================================="
echo -e "${GREEN} Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review and update .env file"
echo "2. Start PostgreSQL (or use Docker):"
echo "   docker-compose up -d db"
echo "3. Run database migrations:"
echo "   cd backend && source venv/bin/activate && alembic upgrade head"
echo "4. Start the backend:"
echo "   ./scripts/dev.sh"
echo ""
