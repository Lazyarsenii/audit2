#!/bin/bash
# Deploy Frontend to Vercel as "auditor"

echo "▲ Vercel Frontend Deployment"
echo ""

cd ui

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found!"
    echo "📦 Install: npm i -g vercel"
    exit 1
fi

echo "✅ Vercel CLI found"
echo ""

# Check current project
echo "📋 Current Vercel projects:"
vercel projects ls 2>&1 | grep -E "repo-auditor|auditor"
echo ""

# Ask if should rename
read -p "🔄 Rename project to 'auditor'? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 Renaming project to 'auditor'..."
    
    # Deploy with new name
    vercel --prod --name auditor --yes
    
    echo ""
    echo "✅ Deployed as 'auditor'!"
else
    echo "📦 Deploying with current name..."
    vercel --prod --yes
fi

echo ""
echo "📝 Remember to update:"
echo "   1. NEXT_PUBLIC_API_URL in Vercel dashboard"
echo "   2. CORS_ORIGINS in Railway to include your Vercel domain"
