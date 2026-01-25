#!/bin/bash
# Test script for leaderboard endpoint (Top Performers Analysis)

BASE_URL="http://localhost:8000/api/dashboard"

echo "🧪 Testing Leaderboard Endpoint (Top Performers with Margin Analysis)"
echo "===================================================================="
echo ""

# Test 1: Top Brands
echo "📊 Test 1: Top Brands with Margin Analysis"
echo "------------------------------------------"
curl -s -X POST "${BASE_URL}/breakdown?dimension=brand" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | jq '{
    title,
    dimension,
    total_brands: (.data | length),
    top_5: .data[0:5] | map({
      brand: .label,
      revenue: (.revenue | floor),
      orders: .orders,
      margin: .margin_pct,
      market_share: (.share_pct | . * 100 | floor | . / 100)
    }),
    profitability: {
      profitable: (.data | map(select(.margin_pct != null and .margin_pct > 0)) | length),
      unprofitable: (.data | map(select(.margin_pct != null and .margin_pct < 0)) | length)
    }
  }'

echo ""
echo ""

# Test 2: Top Clients
echo "📊 Test 2: Top Clients with Market Share"
echo "----------------------------------------"
curl -s -X POST "${BASE_URL}/breakdown?dimension=client" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | jq '{
    title,
    total_clients: (.data | length),
    top_3: .data[0:3] | map({
      client: .label,
      revenue: (.revenue | floor),
      orders: .orders,
      margin: .margin_pct,
      share: (.share_pct | . * 100 | floor | . / 100)
    }),
    concentration: {
      top_3_share: (.data[0:3] | map(.share_pct) | add | . * 100 | floor | . / 100),
      top_10_share: (.data[0:10] | map(.share_pct) | add | . * 100 | floor | . / 100)
    }
  }'

echo ""
echo ""

# Test 3: Top Suppliers
echo "📊 Test 3: Top Suppliers with Profitability"
echo "-------------------------------------------"
curl -s -X POST "${BASE_URL}/breakdown?dimension=supplier" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | jq '{
    title,
    total_suppliers: (.data | length),
    top_5: .data[0:5] | map({
      supplier: .label,
      revenue: (.revenue | floor),
      margin: .margin_pct,
      share: (.share_pct | . * 100 | floor | . / 100)
    })
  }'

echo ""
echo ""

# Test 4: Top Products
echo "📊 Test 4: Top Products Analysis"
echo "--------------------------------"
curl -s -X POST "${BASE_URL}/breakdown?dimension=product" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | jq '{
    title,
    total_products: (.data | length),
    top_5: .data[0:5] | map({
      product: (.label | .[0:40]),
      revenue: (.revenue | floor),
      orders: .orders,
      margin: .margin_pct
    })
  }'

echo ""
echo ""

# Test 5: Filtered Leaderboard (UAE clients only)
echo "📊 Test 5: Top UAE Clients (Filtered)"
echo "-------------------------------------"
curl -s -X POST "${BASE_URL}/breakdown?dimension=client" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED", "countries": ["United Arab Emirates"]}' | jq '{
    title,
    total_uae_clients: (.data | length),
    top_5: .data[0:5] | map({
      client: .label,
      revenue: (.revenue | floor),
      margin: .margin_pct,
      share: (.share_pct | . * 100 | floor | . / 100)
    })
  }'

echo ""
echo ""

# Test 6: Margin Analysis Summary
echo "📊 Test 6: Global Margin Analysis (All Brands)"
echo "----------------------------------------------"
curl -s -X POST "${BASE_URL}/breakdown?dimension=brand" \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | jq '{
    margin_distribution: {
      high_margin: (.data | map(select(.margin_pct != null and .margin_pct > 20)) | length),
      medium_margin: (.data | map(select(.margin_pct != null and .margin_pct > 0 and .margin_pct <= 20)) | length),
      low_margin: (.data | map(select(.margin_pct != null and .margin_pct <= 0)) | length),
      no_data: (.data | map(select(.margin_pct == null)) | length)
    },
    avg_margin: (
      .data | 
      map(select(.margin_pct != null)) | 
      map(.margin_pct) | 
      add / length | 
      . * 100 | floor | . / 100
    ),
    worst_performer: (
      .data | 
      map(select(.margin_pct != null)) | 
      sort_by(.margin_pct) | 
      first | 
      {brand: .label, margin: .margin_pct}
    ),
    best_performer: (
      .data | 
      map(select(.margin_pct != null)) | 
      sort_by(.margin_pct) | 
      last | 
      {brand: .label, margin: .margin_pct}
    )
  }'

echo ""
echo "✅ All tests completed!"
