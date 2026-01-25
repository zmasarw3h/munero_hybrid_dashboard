#!/bin/bash
# Test script for scatter endpoint (Market Analysis)

BASE_URL="http://localhost:8000/api/dashboard"

echo "🧪 Testing Scatter Endpoint (Client Behavior Analysis)"
echo "====================================================="
echo ""

# Test 1: All clients
echo "📊 Test 1: All Clients Analysis"
echo "-------------------------------"
curl -s -X POST "${BASE_URL}/scatter" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | jq '{
    total_clients: (.data | length),
    top_5_revenue: .data | sort_by(.total_revenue) | reverse | .[0:5] | map({
      name: .client_name,
      country: .country,
      revenue: (.total_revenue | floor),
      orders: .total_orders,
      aov: (.aov | floor),
      type: .dominant_type
    })
  }'

echo ""
echo ""

# Test 2: UAE clients only
echo "📊 Test 2: UAE Clients Only"
echo "---------------------------"
curl -s -X POST "${BASE_URL}/scatter" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED", "countries": ["United Arab Emirates"]}' | jq '{
    total_uae_clients: (.data | length),
    avg_aov: (.data | map(.aov) | add / length | floor),
    product_types: (.data | group_by(.dominant_type) | map({type: .[0].dominant_type, count: length}))
  }'

echo ""
echo ""

# Test 3: High-value clients
echo "📊 Test 3: High-Value Clients (AOV > 1000)"
echo "------------------------------------------"
curl -s -X POST "${BASE_URL}/scatter" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | jq '{
    high_value_clients: (.data | map(select(.aov > 1000)) | length),
    sample: .data | map(select(.aov > 1000)) | sort_by(.aov) | reverse | .[0:5] | map({
      name: .client_name,
      aov: (.aov | floor),
      orders: .total_orders
    })
  }'

echo ""
echo ""

# Test 4: Behavior segmentation
echo "📊 Test 4: Client Behavior Segmentation"
echo "---------------------------------------"
curl -s -X POST "${BASE_URL}/scatter" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | jq '{
    segments: {
      high_volume_low_value: (.data | map(select(.total_orders > 100 and .aov < 200)) | length),
      high_volume_high_value: (.data | map(select(.total_orders > 100 and .aov > 1000)) | length),
      low_volume_low_value: (.data | map(select(.total_orders < 50 and .aov < 200)) | length),
      low_volume_high_value: (.data | map(select(.total_orders < 50 and .aov > 1000)) | length)
    }
  }'

echo ""
echo ""

# Test 5: Product type analysis
echo "📊 Test 5: Product Type Distribution"
echo "------------------------------------"
curl -s -X POST "${BASE_URL}/scatter" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | jq '{
    product_types: (
      .data | group_by(.dominant_type) | map({
        type: .[0].dominant_type,
        clients: length,
        total_revenue: (map(.total_revenue) | add),
        avg_aov: (map(.aov) | add / length | floor)
      }) | sort_by(.total_revenue) | reverse
    )
  }'

echo ""
echo "✅ All tests completed!"
