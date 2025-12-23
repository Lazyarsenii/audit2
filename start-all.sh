#!/bin/bash
# Start Full Stack Locally

echo "🚀 Starting Repo Auditor..."
echo ""

# Kill any existing processes
echo "🧹 Cleaning up old processes..."
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "next dev" 2>/dev/null

# Start backend in background
echo "📦 Starting backend..."
cd "$(dirname "$0")/backend"
pip3 install -r requirements.txt --quiet
python3 -m uvicorn app.main:app --reload --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend..."
sleep 3

# Start frontend in background  
echo "🎨 Starting frontend..."
cd "$(dirname "$0")/ui"
npm install --silent
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!

echo ""
echo "✅ Services started!"
echo ""
echo "🔗 Backend:  http://localhost:8000"
echo "🔗 Frontend: http://localhost:3000"
echo "📋 Docs:     http://localhost:8000/docs"
echo ""
echo "🔑 Local dev has NO authentication (API_KEY_REQUIRED=false)"
echo "   To test auth, set API_KEY_REQUIRED=true in backend/.env"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f /tmp/backend.log"
echo "   Frontend: tail -f /tmp/frontend.log"
echo ""
echo "🛑 To stop: pkill -f 'uvicorn app.main:app' && pkill -f 'next dev'"
