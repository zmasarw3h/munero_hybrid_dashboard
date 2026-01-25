#!/bin/bash
# Test script for the new AI Chat endpoint
# Tests the full pipeline: LLM Service + SmartRender Service

BASE_URL="http://localhost:8000/api/chat"

echo "=============================================="
echo "  Testing AI Chat Endpoint"
echo "=============================================="
echo ""

# Test 1: Health Check
echo "🏥 Test 1: Health Check"
echo "GET /api/chat/health"
curl -s "$BASE_URL/health" | python3 -m json.tool
echo ""
echo ""

# Test 2: Quick Test
echo "🔧 Test 2: Quick Test"
echo "GET /api/chat/test"
curl -s "$BASE_URL/test" | python3 -m json.tool
echo ""
echo ""

# Test 3: Simple Metric Query (Total Revenue)
echo "💰 Test 3: Total Revenue Query"
echo "POST /api/chat"
curl -s -X POST "$BASE_URL/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the total revenue?",
    "filters": null
  }' | python3 -m json.tool
echo ""
echo ""

# Test 4: Top N Query (Top 5 Products)
echo "📊 Test 4: Top 5 Products by Revenue"
echo "POST /api/chat"
curl -s -X POST "$BASE_URL/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the top 5 products by revenue?",
    "filters": null
  }' | python3 -m json.tool
echo ""
echo ""

# Test 5: Time Series Query (Monthly Trend)
echo "📈 Test 5: Monthly Revenue Trend"
echo "POST /api/chat"
curl -s -X POST "$BASE_URL/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show monthly revenue trend",
    "filters": null
  }' | python3 -m json.tool
echo ""
echo ""

# Test 6: Query with Filters
echo "🔍 Test 6: Query with Date Filters"
echo "POST /api/chat"
curl -s -X POST "$BASE_URL/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the total revenue?",
    "filters": {
      "start_date": "2025-01-01",
      "end_date": "2025-12-31"
    }
  }' | python3 -m json.tool
echo ""
echo ""

# Test 7: Country Breakdown
echo "🌍 Test 7: Revenue by Country"
echo "POST /api/chat"
curl -s -X POST "$BASE_URL/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show revenue breakdown by country",
    "filters": null
  }' | python3 -m json.tool
echo ""
echo ""

echo "=============================================="
echo "  All tests completed!"
echo "=============================================="
