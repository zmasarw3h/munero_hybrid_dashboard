#!/bin/bash

echo "=== Testing Chat Integration ==="
echo "Make sure backend is running: cd backend && uvicorn main:app --reload"
echo "Make sure Ollama is running: ollama serve"
echo ""

# Test 1: Health check
echo -e "\n1. Health Check:"
curl -s http://localhost:8000/api/chat/health | jq

# Test 2: Simple query
echo -e "\n2. Simple Query (Top Products):"
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are my top 5 products by revenue?"}' | jq

# Test 3: Query with filters
echo -e "\n3. Query with Filters:"
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me monthly revenue",
    "filters": {
      "date_range": {"start": "2025-01-01", "end": "2025-06-30"}
    }
  }' | jq

# Test 4: Single metric
echo -e "\n4. Single Metric (Total Revenue):"
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the total revenue?"}' | jq

# Test 5: Time series
echo -e "\n5. Time Series:"
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me sales trend by month"}' | jq

# Test 6: Error handling (bad query)
echo -e "\n6. Error Handling:"
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "asdfghjkl"}' | jq

# Test 7: Pie chart query
echo -e "\n7. Pie Chart (Revenue by Product Type):"
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me revenue breakdown by product type as a pie chart"}' | jq

# Test 8: Client leaderboard
echo -e "\n8. Client Leaderboard:"
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Which clients have the highest order volume?"}' | jq

echo -e "\n=== Tests Complete ==="
