#!/bin/bash
# Test script for enhanced trend endpoint with anomaly detection

BASE_URL="http://localhost:8000/api/dashboard"

echo "🧪 Testing Enhanced Trend API Endpoint"
echo "========================================"
echo ""

# Test 1: Monthly trend with default anomaly threshold
echo "📊 Test 1: Monthly Trend with Anomaly Detection (Default Threshold = 3.0)"
echo "------------------------------------------------------------------------"
curl -X POST "${BASE_URL}/trend?granularity=month" \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "AED",
    "anomaly_threshold": 3.0
  }' | jq '.'

echo ""
echo ""

# Test 2: Monthly trend with lower threshold (more anomalies)
echo "📊 Test 2: Monthly Trend with Lower Threshold (2.0 - More Sensitive)"
echo "-------------------------------------------------------------------"
curl -X POST "${BASE_URL}/trend?granularity=month" \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "AED",
    "anomaly_threshold": 2.0,
    "start_date": "2020-01-01",
    "end_date": "2023-12-31"
  }' | jq '.'

echo ""
echo ""

# Test 3: Daily trend for recent period
echo "📊 Test 3: Daily Trend (Recent Period)"
echo "--------------------------------------"
curl -X POST "${BASE_URL}/trend?granularity=day" \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "AED",
    "anomaly_threshold": 3.0,
    "start_date": "2023-01-01",
    "end_date": "2023-03-31"
  }' | jq '.'

echo ""
echo ""

# Test 4: Filtered trend by country
echo "📊 Test 4: Monthly Trend Filtered by Country (UAE)"
echo "--------------------------------------------------"
curl -X POST "${BASE_URL}/trend?granularity=month" \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "AED",
    "anomaly_threshold": 3.0,
    "countries": ["UAE"]
  }' | jq '.'

echo ""
echo ""

# Test 5: Check specific data point structure
echo "📊 Test 5: Verify Data Point Structure (First 3 points)"
echo "-------------------------------------------------------"
curl -X POST "${BASE_URL}/trend?granularity=month" \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "AED",
    "anomaly_threshold": 3.0
  }' | jq '.data[:3]'

echo ""
echo "✅ All tests completed!"
