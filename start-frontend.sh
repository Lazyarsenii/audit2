#!/bin/bash
# Start Frontend

cd "$(dirname "$0")/ui"

echo "🔧 Installing dependencies..."
npm install --silent

echo "🚀 Starting frontend on http://localhost:3000"
echo "🔑 API Key can be set in Settings → Integrations"
echo ""

npm run dev
