#!/bin/bash

# Munero AI Platform - Chart Endpoints Testing Script
# Tests all Phase 2 chart endpoints with various filters

echo "============================================================"
echo "📊 Munero AI Platform - Chart Endpoints Tests"
echo "============================================================"
echo ""

BASE_URL="http://localhost:8000"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Sales Trend - Monthly
echo -e "${BLUE}Test 1: Sales Trend - Monthly Granularity${NC}"
echo "POST $BASE_URL/api/dashboard/trend?granularity=month"
curl -s -X POST "$BASE_URL/api/dashboard/trend?granularity=month" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | python3 -m json.tool | head -20
echo ""
echo ""

# Test 2: Sales Trend - Daily (with date filter)
echo -e "${BLUE}Test 2: Sales Trend - Daily Granularity (June 2025)${NC}"
echo "POST $BASE_URL/api/dashboard/trend?granularity=day"
curl -s -X POST "$BASE_URL/api/dashboard/trend?granularity=day" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-06-01",
    "end_date": "2025-06-07",
    "currency": "AED"
  }' | python3 -m json.tool | head -30
echo ""
echo ""

# Test 3: Breakdown by Country
echo -e "${BLUE}Test 3: Revenue Breakdown by Country${NC}"
echo "POST $BASE_URL/api/dashboard/breakdown?dimension=client_country"
curl -s -X POST "$BASE_URL/api/dashboard/breakdown?dimension=client_country" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | python3 -m json.tool | head -35
echo ""
echo ""

# Test 4: Breakdown by Brand
echo -e "${BLUE}Test 4: Revenue Breakdown by Brand${NC}"
echo "POST $BASE_URL/api/dashboard/breakdown?dimension=product_brand"
curl -s -X POST "$BASE_URL/api/dashboard/breakdown?dimension=product_brand" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | python3 -m json.tool | head -35
echo ""
echo ""

# Test 5: Breakdown by Product Type
echo -e "${BLUE}Test 5: Revenue Breakdown by Product Type${NC}"
echo "POST $BASE_URL/api/dashboard/breakdown?dimension=order_type"
curl -s -X POST "$BASE_URL/api/dashboard/breakdown?dimension=order_type" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | python3 -m json.tool | head -35
echo ""
echo ""

# Test 6: Breakdown by Client
echo -e "${BLUE}Test 6: Revenue Breakdown by Client (Top 10)${NC}"
echo "POST $BASE_URL/api/dashboard/breakdown?dimension=client_name"
curl -s -X POST "$BASE_URL/api/dashboard/breakdown?dimension=client_name" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | python3 -m json.tool | head -35
echo ""
echo ""

# Test 7: Top 5 Products
echo -e "${BLUE}Test 7: Top 5 Products by Revenue${NC}"
echo "POST $BASE_URL/api/dashboard/top-products?limit=5"
curl -s -X POST "$BASE_URL/api/dashboard/top-products?limit=5" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | python3 -m json.tool
echo ""
echo ""

# Test 8: Top 10 Products with Brand Filter
echo -e "${BLUE}Test 8: Top 10 Products - Apple Brand Only${NC}"
echo "POST $BASE_URL/api/dashboard/top-products?limit=10"
curl -s -X POST "$BASE_URL/api/dashboard/top-products?limit=10" \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "AED",
    "brands": ["Apple"]
  }' | python3 -m json.tool | head -40
echo ""
echo ""

# Test 9: Sales Trend with Multiple Filters
echo -e "${BLUE}Test 9: Sales Trend - Filtered by Country + Brand${NC}"
echo "POST $BASE_URL/api/dashboard/trend?granularity=month"
curl -s -X POST "$BASE_URL/api/dashboard/trend?granularity=month" \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "AED",
    "countries": ["United Arab Emirates"],
    "brands": ["Apple", "Amazon.ae"]
  }' | python3 -m json.tool | head -25
echo ""
echo ""

echo "============================================================"
echo -e "${GREEN}✅ All Chart Endpoint Tests Complete!${NC}"
echo "============================================================"
echo ""
echo "📊 Available Chart Endpoints:"
echo "  1. POST /api/dashboard/trend         - Sales trend over time"
echo "  2. POST /api/dashboard/breakdown     - Top 10 by dimension"
echo "  3. POST /api/dashboard/top-products  - Top N products"
echo ""
echo "📚 Interactive API Docs: $BASE_URL/docs"
echo ""
