#!/bin/bash
# Start Backend with Authentication

cd "$(dirname "$0")/backend"

echo "🔧 Installing dependencies..."
pip3 install -r requirements.txt --quiet

echo "🚀 Starting backend on http://localhost:8000"
echo "📝 API Key authentication is DISABLED for local dev (see .env)"
echo ""

python3 -m uvicorn app.main:app --reload --port 8000
