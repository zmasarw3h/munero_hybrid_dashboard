#!/bin/bash

# PHASE 1 PART 4: AI Engine Testing Suite
# Tests LLM with dashboard filter injection and business logic understanding

set -e

BASE_URL="http://localhost:8000"
API_ENDPOINT="$BASE_URL/api/ai/chat"

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                   PHASE 1 PART 4: AI ENGINE TEST SUITE                ║"
echo "║               Testing LLM with Dashboard Filter Injection             ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# Test 1: Global query with no filters
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 1: Global Revenue Query (No Filters)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the total revenue?",
    "filters": {
      "currency": "AED",
      "comparison_mode": "none",
      "anomaly_threshold": 3.0
    }
  }' | jq '{
    question: "Total revenue (all data)",
    answer: .answer_text,
    sql_generated: .sql_generated,
    chart_type: .related_chart.chart_type,
    data_points: (.related_chart.data | length)
  }'

echo ""
sleep 2

# Test 2: Revenue filtered by country (UAE only)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 2: UAE Revenue Query (Country Filter)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the total revenue?",
    "filters": {
      "countries": ["AE"],
      "currency": "AED",
      "comparison_mode": "none",
      "anomaly_threshold": 3.0
    }
  }' | jq '{
    question: "Total revenue (UAE only)",
    filter_context: "Countries: AE",
    answer: .answer_text,
    sql_has_country_filter: (.sql_generated | contains("client_country")),
    sql_generated: .sql_generated
  }'

echo ""
sleep 2

# Test 3: Margin calculation query (tests business logic understanding)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 3: Profit Margin Analysis (Business Logic Test)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Which brands have the highest profit margins?",
    "filters": {
      "currency": "AED",
      "comparison_mode": "none",
      "anomaly_threshold": 3.0
    }
  }' | jq '{
    question: "Top brands by margin",
    answer: .answer_text,
    sql_has_margin_calc: (.sql_generated | contains("cogs")),
    sql_formula: (.sql_generated | capture("(?<formula>\\(.*cogs.*\\))"; "i").formula // "Not found"),
    chart_type: .related_chart.chart_type,
    top_5_brands: (.related_chart.data[:5] | map({brand: .label, value: .value}))
  }'

echo ""
sleep 2

# Test 4: Multi-filter query (Country + Brand)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 4: Apple Sales in UAE (Multi-Filter Test)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the sales for Apple products?",
    "filters": {
      "countries": ["AE"],
      "brands": ["Apple"],
      "currency": "AED",
      "comparison_mode": "none",
      "anomaly_threshold": 3.0
    }
  }' | jq '{
    question: "Apple sales in UAE",
    filter_context: "Countries: AE | Brands: Apple",
    answer: .answer_text,
    sql_has_brand_filter: (.sql_generated | contains("product_brand")),
    sql_has_country_filter: (.sql_generated | contains("client_country")),
    sql_generated: .sql_generated
  }'

echo ""
sleep 2

# Test 5: Date range filter
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 5: June 2025 Revenue (Date Filter Test)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me the daily revenue trend",
    "filters": {
      "start_date": "2025-06-01",
      "end_date": "2025-06-30",
      "currency": "AED",
      "comparison_mode": "none",
      "anomaly_threshold": 3.0
    }
  }' | jq '{
    question: "Daily revenue for June 2025",
    filter_context: "Date: 2025-06-01 to 2025-06-30",
    answer: .answer_text,
    sql_has_date_filter: (.sql_generated | contains("order_date")),
    sql_has_between: (.sql_generated | contains("BETWEEN")),
    chart_type: .related_chart.chart_type,
    data_points: (.related_chart.data | length)
  }'

echo ""
sleep 2

# Test 6: Negative margin detection (unprofitable clients)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 6: Unprofitable Clients Analysis"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Which clients are unprofitable (negative margin)?",
    "filters": {
      "currency": "AED",
      "comparison_mode": "none",
      "anomaly_threshold": 3.0
    }
  }' | jq '{
    question: "Clients with negative margins",
    answer: .answer_text,
    sql_has_having_clause: (.sql_generated | contains("HAVING")),
    sql_checks_negative: (.sql_generated | contains("< 0")),
    chart_type: .related_chart.chart_type,
    unprofitable_count: (.related_chart.data | length)
  }'

echo ""
sleep 2

# Test 7: AOV (Average Order Value) calculation
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 7: Client AOV Analysis"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the average order value by client?",
    "filters": {
      "currency": "AED",
      "comparison_mode": "none",
      "anomaly_threshold": 3.0
    }
  }' | jq '{
    question: "AOV by client",
    answer: .answer_text,
    sql_has_division: (.sql_generated | contains("/")),
    sql_has_distinct_orders: (.sql_generated | contains("DISTINCT order_number")),
    chart_type: .related_chart.chart_type,
    top_3_clients: (.related_chart.data[:3] | map({client: .label, aov: .value}))
  }'

echo ""
sleep 2

# Test 8: Complex multi-filter with supplier
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 8: Gift Cards Performance (Product Type Filter)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the total orders and revenue?",
    "filters": {
      "product_types": ["gift_cards"],
      "countries": ["AE"],
      "currency": "AED",
      "comparison_mode": "none",
      "anomaly_threshold": 3.0
    }
  }' | jq '{
    question: "Gift cards in UAE",
    filter_context: "Product Type: gift_cards | Country: AE",
    answer: .answer_text,
    sql_has_type_filter: (.sql_generated | contains("order_type")),
    sql_has_country_filter: (.sql_generated | contains("client_country")),
    sql_generated: .sql_generated
  }'

echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                         TEST SUITE COMPLETE                            ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ All 8 AI Engine tests completed!"
echo ""
echo "VALIDATION CHECKLIST:"
echo "  [ ] SQL queries include WHERE clauses for active filters"
echo "  [ ] Margin calculations use proper formula: (Revenue - COGS) / Revenue * 100"
echo "  [ ] AOV calculations use DISTINCT order_number"
echo "  [ ] Date filters use BETWEEN or >= syntax"
echo "  [ ] Multi-filters combine with AND"
echo "  [ ] Summaries reference active filters in context"
echo "  [ ] Charts are generated with appropriate types (bar, line, pie, scatter)"
echo ""
