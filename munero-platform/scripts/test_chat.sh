#!/bin/bash

# Test script for AI Chat endpoints
# Tests the natural language query processing pipeline

BASE_URL="http://localhost:8000"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Munero AI Chat Endpoint Test Suite                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Test 1: LLM Connectivity Test
echo -e "${YELLOW}━━━ Test 1: LLM Connectivity ━━━${NC}"
echo -e "${BLUE}GET ${BASE_URL}/api/chat/test${NC}"
echo ""
curl -s "${BASE_URL}/api/chat/test" | python3 -m json.tool
echo -e "\n${GREEN}✓ Test 1 Complete${NC}\n"
sleep 2

# Test 2: Simple Query - Top Products
echo -e "${YELLOW}━━━ Test 2: Top 5 Products by Revenue ━━━${NC}"
echo -e "${BLUE}POST ${BASE_URL}/api/chat/${NC}"
echo ""
curl -s -X POST "${BASE_URL}/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the top 5 products by revenue?",
    "filters": {
      "currency": "AED"
    }
  }' | python3 -m json.tool
echo -e "\n${GREEN}✓ Test 2 Complete${NC}\n"
sleep 3

# Test 3: Time Series Query
echo -e "${YELLOW}━━━ Test 3: Revenue Trend Over Time ━━━${NC}"
echo -e "${BLUE}POST ${BASE_URL}/api/chat/${NC}"
echo ""
curl -s -X POST "${BASE_URL}/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me the revenue trend by month for 2025",
    "filters": {
      "start_date": "2025-01-01",
      "end_date": "2025-12-31",
      "currency": "AED"
    }
  }' | python3 -m json.tool
echo -e "\n${GREEN}✓ Test 3 Complete${NC}\n"
sleep 3

# Test 4: Country Analysis with Filters
echo -e "${YELLOW}━━━ Test 4: Country Sales (UAE Only) ━━━${NC}"
echo -e "${BLUE}POST ${BASE_URL}/api/chat/${NC}"
echo ""
curl -s -X POST "${BASE_URL}/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Which countries have the highest sales?",
    "filters": {
      "countries": ["United Arab Emirates"],
      "currency": "AED"
    }
  }' | python3 -m json.tool
echo -e "\n${GREEN}✓ Test 4 Complete${NC}\n"
sleep 3

# Test 5: Brand Comparison
echo -e "${YELLOW}━━━ Test 5: Apple vs Samsung Revenue ━━━${NC}"
echo -e "${BLUE}POST ${BASE_URL}/api/chat/${NC}"
echo ""
curl -s -X POST "${BASE_URL}/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Compare revenue between Apple and Samsung",
    "filters": {
      "brands": ["Apple", "Samsung"],
      "currency": "AED"
    }
  }' | python3 -m json.tool
echo -e "\n${GREEN}✓ Test 5 Complete${NC}\n"
sleep 3

# Test 6: Top Customers
echo -e "${YELLOW}━━━ Test 6: Top 10 Customers by Order Value ━━━${NC}"
echo -e "${BLUE}POST ${BASE_URL}/api/chat/${NC}"
echo ""
curl -s -X POST "${BASE_URL}/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Who are the top 10 customers by total order value?",
    "filters": {
      "currency": "AED"
    }
  }' | python3 -m json.tool
echo -e "\n${GREEN}✓ Test 6 Complete${NC}\n"
sleep 3

# Test 7: Profit Analysis
echo -e "${YELLOW}━━━ Test 7: Most Profitable Products ━━━${NC}"
echo -e "${BLUE}POST ${BASE_URL}/api/chat/${NC}"
echo ""
curl -s -X POST "${BASE_URL}/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the most profitable products?",
    "filters": {
      "currency": "AED"
    }
  }' | python3 -m json.tool
echo -e "\n${GREEN}✓ Test 7 Complete${NC}\n"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         All AI Chat Tests Completed! 🎉                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
