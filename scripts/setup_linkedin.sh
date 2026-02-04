#!/bin/bash
# Automated LinkedIn OAuth Setup
# Gets access token and person URN for API posting

set -e

echo "🔐 LinkedIn OAuth 2.0 Setup"
echo "================================"

# Load env vars
source "$(dirname "$0")/../../.env"

# Check credentials
if [ -z "$LINKEDIN_CLIENT_ID" ] || [ -z "$LINKEDIN_CLIENT_SECRET" ]; then
    echo "❌ LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in .env"
    exit 1
fi

# LinkedIn OAuth URLs
AUTH_URL="https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL="https://www.linkedin.com/oauth/v2/accessToken"
REDIRECT_URI="https://localhost:8443/callback"
SCOPES="openid profile w_member_social email"

# Generate auth URL
STATE="rlhf_$(date +%s)"
AUTH_PARAMS="response_type=code&client_id=$LINKEDIN_CLIENT_ID&redirect_uri=$REDIRECT_URI&scope=$SCOPES&state=$STATE"
FULL_AUTH_URL="${AUTH_URL}?${AUTH_PARAMS}"

echo ""
echo "📋 MANUAL STEP REQUIRED:"
echo "================================"
echo "1. Open this URL in your browser:"
echo ""
echo "$FULL_AUTH_URL"
echo ""
echo "2. Log in with: $LINKEDIN_EMAIL"
echo "3. Click 'Allow' to authorize"
echo "4. Copy the 'code' parameter from the redirect URL"
echo "   (It will look like: https://localhost:8443/callback?code=XXXXXX&state=...)"
echo ""
echo -n "5. Paste the CODE here and press Enter: "
read AUTH_CODE

if [ -z "$AUTH_CODE" ]; then
    echo "❌ No code provided"
    exit 1
fi

echo ""
echo "🔄 Exchanging code for access token..."

# Exchange code for token
RESPONSE=$(curl -s -X POST "$TOKEN_URL" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=authorization_code" \
    -d "code=$AUTH_CODE" \
    -d "redirect_uri=$REDIRECT_URI" \
    -d "client_id=$LINKEDIN_CLIENT_ID" \
    -d "client_secret=$LINKEDIN_CLIENT_SECRET")

# Extract access token
ACCESS_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null || echo "")

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Failed to get access token"
    echo "Response: $RESPONSE"
    exit 1
fi

echo "✅ Got access token"

# Get user info for person URN
echo "🔄 Getting user info..."
USER_INFO=$(curl -s -X GET "https://api.linkedin.com/v2/userinfo" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

PERSON_ID=$(echo "$USER_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('sub', ''))" 2>/dev/null || echo "")
NAME=$(echo "$USER_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name', ''))" 2>/dev/null || echo "")

if [ -z "$PERSON_ID" ]; then
    echo "❌ Failed to get user info"
    exit 1
fi

PERSON_URN="urn:li:person:$PERSON_ID"
echo "✅ User: $NAME"
echo "✅ Person URN: $PERSON_URN"

# Save to .env
echo "" >> "$(dirname "$0")/../../.env"
echo "# LinkedIn OAuth Token (Generated $(date))" >> "$(dirname "$0")/../../.env"
echo "LINKEDIN_ACCESS_TOKEN=$ACCESS_TOKEN" >> "$(dirname "$0")/../../.env"
echo "LINKEDIN_PERSON_URN=$PERSON_URN" >> "$(dirname "$0")/../../.env"

# Save to token file
TOKEN_FILE="$(dirname "$0")/../data/linkedin_token.json"
mkdir -p "$(dirname "$TOKEN_FILE")"
cat > "$TOKEN_FILE" << EOF
{
  "access_token": "$ACCESS_TOKEN",
  "person_urn": "$PERSON_URN",
  "name": "$NAME",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo ""
echo "✅ Setup complete!"
echo "   Token saved to: $TOKEN_FILE"
echo "   Credentials added to .env"
echo ""
echo "🚀 Ready to auto-post to LinkedIn on every thumbs up/down"
