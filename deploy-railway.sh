#!/bin/bash
# Deploy to Railway with Authentication

echo "🚂 Railway Deployment Setup"
echo ""

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found!"
    echo "📦 Install: npm i -g @railway/cli"
    echo "🔗 https://docs.railway.app/develop/cli"
    exit 1
fi

echo "✅ Railway CLI found"
echo ""

# Read railway-vars.json if it exists
if [ -f railway-vars.json ]; then
    echo "📋 Found railway-vars.json with these variables:"
    cat railway-vars.json | jq -r 'to_entries[] | "\(.key)=\(.value)"' | head -10
    echo ""
fi

echo "🔧 Required variables for authentication:"
echo ""
echo "  API_KEY_REQUIRED=true"
echo "  API_KEYS=repoaudit"
echo ""

# Check if already logged in
if railway whoami &> /dev/null; then
    echo "✅ Already logged in to Railway"
else
    echo "🔐 Logging in to Railway..."
    railway login
fi

echo ""
echo "📦 Deploying backend..."
cd backend

# Set environment variables
echo "🔑 Setting authentication variables..."
railway variables set API_KEY_REQUIRED=true
railway variables set API_KEYS=repoaudit

echo ""
echo "🚀 Deploying to Railway..."
railway up

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Get your Railway URL: railway domain"
echo "   2. Update CORS in Railway dashboard:"
echo "      CORS_ORIGINS=[\"https://your-app.vercel.app\",\"http://localhost:3000\"]"
echo "   3. Update frontend .env.local:"
echo "      NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app"
