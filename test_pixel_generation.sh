#!/bin/bash
# test_pixel_generation.sh
# Test script for dynamic pixel generation

echo "🧪 Testing Dynamic Pixel Generation"
echo "=================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}1. Testing pixel endpoint for existing client...${NC}"

# Test with development client (should exist from pixel-management setup)
echo "Fetching pixel for client_development:"
curl -s -w "\nHTTP Status: %{http_code}\nContent-Type: %{content_type}\nResponse Time: %{time_total}s\n" \
  http://localhost/pixel/client_development/tracking.js | head -20

echo ""
echo -e "${BLUE}2. Testing pixel endpoint for non-existent client...${NC}"

# Test with non-existent client (should return 404)
echo "Fetching pixel for non_existent_client:"
curl -s -w "\nHTTP Status: %{http_code}\n" \
  http://localhost/pixel/non_existent_client/tracking.js

echo ""
echo -e "${BLUE}3. Testing cache statistics...${NC}"

# Check cache stats
echo "Cache statistics:"
curl -s http://localhost:8000/pixel/cache/stats | python3 -m json.tool

echo ""
echo -e "${BLUE}4. Testing configuration integration...${NC}"

# Test direct config API from pixel-management
echo "Direct config API test:"
curl -s http://localhost:8000/api/v1/config/client/client_development | python3 -m json.tool

echo ""
echo -e "${BLUE}5. Testing pixel functionality...${NC}"

# Create a simple HTML test page
cat > test_pixel.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Pixel Test Page</title>
</head>
<body>
    <h1>Testing Dynamic Pixel</h1>
    <button onclick="alert('Button clicked!')">Test Button</button>
    
    <script src="http://localhost/pixel/client_development/tracking.js"></script>
    
    <script>
        // Test that the pixel loaded
        setTimeout(function() {
            console.log('Testing pixel functionality...');
            
            // Check if tracking is working
            if (typeof localStorage !== 'undefined') {
                console.log('Session ID:', localStorage.getItem('_evothesis_session_id'));
                console.log('Visitor ID:', localStorage.getItem('_evothesis_visitor_id'));
            }
        }, 1000);
    </script>
</body>
</html>
EOF

echo "Created test_pixel.html - open in browser to test pixel functionality"

echo ""
echo -e "${BLUE}6. Performance test...${NC}"

# Simple performance test
echo "Testing response times for 10 requests:"
for i in {1..10}; do
    curl -s -w "Request $i: %{time_total}s\n" \
      http://localhost/pixel/client_development/tracking.js > /dev/null
done

echo ""
echo -e "${GREEN}✅ Dynamic pixel generation testing complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Open test_pixel.html in browser"
echo "2. Check browser console for tracking logs"
echo "3. Verify events are collected: curl http://localhost:8000/events/recent"
echo "4. Monitor logs: docker compose logs -f fastapi"