#!/bin/bash
# Test API Key Authentication

echo "🧪 Testing API Key Authentication"
echo ""

BASE_URL="http://localhost:8000"
API_KEY="repoaudit"

echo "1️⃣  Testing public endpoint (no auth needed)..."
curl -s "$BASE_URL/health" | jq '.' || echo "❌ Health check failed"
echo ""

echo "2️⃣  Testing protected endpoint WITHOUT key..."
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/v1/analyses")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "401" ]; then
    echo "✅ Correctly returned 401 Unauthorized"
    echo "$BODY" | jq '.'
else
    echo "❌ Expected 401, got $HTTP_CODE"
fi
echo ""

echo "3️⃣  Testing protected endpoint WITH valid key..."
RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: $API_KEY" "$BASE_URL/api/v1/analyses")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Correctly returned 200 OK with valid key"
    echo "$BODY" | jq '.' | head -20
else
    echo "❌ Expected 200, got $HTTP_CODE"
    echo "$BODY"
fi
echo ""

echo "4️⃣  Testing protected endpoint WITH invalid key..."
RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: wrong-key" "$BASE_URL/api/v1/analyses")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "403" ]; then
    echo "✅ Correctly returned 403 Forbidden"
    echo "$BODY" | jq '.'
else
    echo "❌ Expected 403, got $HTTP_CODE"
fi
echo ""

echo "✅ Authentication test complete!"
