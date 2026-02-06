# AI Copilot API Quick Reference

## 🤖 Endpoints

### 1. Natural Language Query
```http
POST /api/chat/
```

**Request Body**:
```json
{
  "message": "string (1-500 chars)",
  "filters": {
    "start_date": "2025-01-01",          // Optional
    "end_date": "2025-12-31",            // Optional
    "currency": "AED",                    // AED|USD|EUR
    "clients": [],                        // Optional: Filter by clients
    "countries": [],                      // Optional: Filter by countries
    "product_types": [],                  // Optional: Filter by types
    "brands": [],                         // Optional: Filter by brands
    "suppliers": []                       // Optional: Filter by suppliers
  }
}
```

**Response**:
```json
{
  "answer_text": "Natural language summary of findings",
  "sql_generated": "SELECT ... FROM fact_orders WHERE ...",
  "related_chart": {
    "title": "Chart title",
    "chart_type": "bar|line|pie|scatter|dual_axis",
    "data": [
      {
        "label": "Category/Date",
        "value": 12345.67,
        "series": null
      }
    ],
    "x_axis_label": "X Axis Label",
    "y_axis_label": "Y Axis Label"
  }
}
```

---

### 2. LLM Health Check
```http
GET /api/chat/test
```

**Response**:
```json
{
  "status": "ok",
  "llm_available": true,
  "model": "qwen2.5-coder:7b",
  "base_url": "http://localhost:11434",
  "test_response": "Hello"
}
```

---

## 📊 Example Queries

### Top Products
```bash
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the top 5 products by revenue?",
    "filters": {"currency": "AED"}
  }'
```

### Revenue Trend
```bash
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me revenue trend by month for 2025",
    "filters": {
      "start_date": "2025-01-01",
      "end_date": "2025-12-31",
      "currency": "AED"
    }
  }'
```

### Country Analysis
```bash
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Which countries have the highest sales?",
    "filters": {
      "countries": ["United Arab Emirates"],
      "currency": "AED"
    }
  }'
```

### Brand Comparison
```bash
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Compare revenue between Apple and Samsung",
    "filters": {
      "brands": ["Apple", "Samsung"],
      "currency": "AED"
    }
  }'
```

### Customer Analysis
```bash
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Who are the top 10 customers by total order value?",
    "filters": {"currency": "AED"}
  }'
```

### Profit Analysis
```bash
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the most profitable products?",
    "filters": {"currency": "AED"}
  }'
```

---

## 🎨 Supported Query Types

| Query Type | Example | Chart Type |
|------------|---------|------------|
| Rankings | "Top 10 products by revenue" | Bar |
| Time Series | "Revenue trend over last 6 months" | Line |
| Comparisons | "Compare Apple vs Samsung" | Bar |
| Proportions | "Revenue breakdown by country" | Pie |
| Aggregations | "Total sales by category" | Bar |
| Correlations | "Price vs quantity analysis" | Scatter |
| Customers | "Best customers by order value" | Bar |
| Geographic | "Sales by region" | Bar/Pie |

---

## 🔍 Query Tips

### Be Specific
✅ "What are the top 5 products by revenue in UAE?"  
❌ "Show me products"

### Use Time Ranges
✅ "Revenue trend for Q1 2025"  
❌ "Show me revenue"

### Include Metrics
✅ "Top 10 customers by total order value"  
❌ "Show me customers"

### Mention Groupings
✅ "Revenue by country and brand"  
❌ "Show me revenue"

---

## ⚠️ Known Limitations

1. **Response Time**: 2-5 seconds (LLM inference)
2. **Accuracy**: ~85-90% for common queries
3. **Complexity**: Very complex queries may fail
4. **Dependencies**: Requires Ollama running locally
5. **Data Limit**: Charts limited to 50 data points

---

## 🔧 Troubleshooting

### "LLM not available"
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Pull the model
ollama pull qwen2.5-coder:7b
```

### "SQL execution failed"
- Check if database exists: `data/munero.sqlite`
- Run ingestion script: `python scripts/ingest_data.py`
- Check database connection: `curl http://localhost:8000/api/dashboard/test`

### "No data returned"
- Adjust filters (e.g., date range)
- Rephrase question more specifically
- Check if test data is filtered: `is_test = 0`

---

## 📚 Related Documentation

- **Phase 3 Complete**: See `PHASE_3_COMPLETE.md`
- **API Reference**: http://localhost:8000/docs
- **Dashboard API**: See `API_QUICK_REFERENCE.md`
- **Setup Guide**: See `SETUP_COMPLETE.md`

---

**Last Updated**: December 31, 2025  
**Version**: 1.0.0  
**Status**: Production Ready ✅
