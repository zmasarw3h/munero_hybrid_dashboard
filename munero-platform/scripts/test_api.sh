#!/bin/bash

# Munero AI Platform - API Testing Script
# Quick tests for all Phase 2 endpoints

echo "============================================================"
echo "🧪 Munero AI Platform - API Tests"
echo "============================================================"
echo ""

BASE_URL="http://localhost:8000"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${BLUE}Test 1: Health Check${NC}"
echo "GET $BASE_URL/health"
curl -s $BASE_URL/health | python3 -m json.tool
echo ""
echo ""

# Test 2: Dashboard Database Test
echo -e "${BLUE}Test 2: Dashboard Database Test${NC}"
echo "GET $BASE_URL/api/dashboard/test"
curl -s $BASE_URL/api/dashboard/test | python3 -m json.tool
echo ""
echo ""

# Test 3: Headline KPIs (No Filters)
echo -e "${BLUE}Test 3: Headline KPIs - All Data${NC}"
echo "POST $BASE_URL/api/dashboard/headline"
curl -s -X POST $BASE_URL/api/dashboard/headline \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | python3 -m json.tool
echo ""
echo ""

# Test 4: Headline KPIs (Date Filter)
echo -e "${BLUE}Test 4: Headline KPIs - June 2025${NC}"
echo "POST $BASE_URL/api/dashboard/headline (with date filter)"
curl -s -X POST $BASE_URL/api/dashboard/headline \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-06-01",
    "end_date": "2025-06-30",
    "currency": "AED"
  }' | python3 -m json.tool
echo ""
echo ""

# Test 5: Headline KPIs (Multiple Filters)
echo -e "${BLUE}Test 5: Headline KPIs - June 2025, UAE Only${NC}"
echo "POST $BASE_URL/api/dashboard/headline (with date + country filter)"
curl -s -X POST $BASE_URL/api/dashboard/headline \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-06-01",
    "end_date": "2025-06-30",
    "currency": "AED",
    "countries": ["United Arab Emirates"]
  }' | python3 -m json.tool
echo ""
echo ""

echo "============================================================"
echo -e "${GREEN}✅ All Tests Complete!${NC}"
echo "============================================================"
echo ""
echo "📚 Interactive API Docs: $BASE_URL/docs"
echo ""
