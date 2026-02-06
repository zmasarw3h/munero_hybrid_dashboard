# 🚀 Munero AI Platform - API Quick Reference

## 📋 Available Endpoints (6 Total)

### System Endpoints
```
GET  /                 - API information
GET  /health           - Health check (DB + LLM status)
GET  /docs             - Interactive Swagger UI
GET  /redoc            - Alternative documentation
```

---

### Dashboard Endpoints

#### 1. Connection Test
```bash
GET /api/dashboard/test
```
**Returns**: Database statistics (total rows, orders, clients)

---

#### 2. Headline KPIs
```bash
POST /api/dashboard/headline
```
**Returns**: 4 main KPIs (Total Orders, Total Revenue, AOV, Distinct Brands)

**Request Body**:
```json
{
    "start_date": "2025-01-01",     // Optional
    "end_date": "2025-12-31",       // Optional
    "currency": "AED",               // Default: AED
    "clients": [],                   // Empty = all
    "countries": [],                 // Empty = all
    "product_types": [],            // Empty = all
    "brands": [],                    // Empty = all
    "suppliers": []                  // Empty = all
}
```

---

#### 3. Sales Trend (Line Chart)
```bash
POST /api/dashboard/trend?granularity=month
```
**Query Parameters**:
- `granularity`: `"day"` or `"month"` (default: `"month"`)

**Request Body**: Same as Headline KPIs (DashboardFilters)

**Returns**: Time series revenue data
```json
{
    "title": "Sales Trend (Month)",
    "chart_type": "line",
    "data": [
        {"label": "2025-01", "value": 450000},
        {"label": "2025-02", "value": 520000}
    ],
    "x_axis_label": "Date",
    "y_axis_label": "Revenue (AED)"
}
```

---

#### 4. Revenue Breakdown (Bar Chart)
```bash
POST /api/dashboard/breakdown?dimension=client_country
```
**Query Parameters**:
- `dimension`: One of:
  - `"client_country"` - By country
  - `"product_brand"` - By brand
  - `"order_type"` - By product type
  - `"client_name"` - By client

**Request Body**: Same as Headline KPIs (DashboardFilters)

**Returns**: Top 10 categories by revenue
```json
{
    "title": "Revenue by Client Country",
    "chart_type": "bar",
    "data": [
        {"label": "UAE", "value": 556706.03},
        {"label": "USA", "value": 385866.48}
    ],
    "x_axis_label": "Client Country",
    "y_axis_label": "Revenue (AED)"
}
```

---

#### 5. Top Products (Bar Chart)
```bash
POST /api/dashboard/top-products?limit=10
```
**Query Parameters**:
- `limit`: Number of products (default: `10`)

**Request Body**: Same as Headline KPIs (DashboardFilters)

**Returns**: Top N products ranked by revenue
```json
{
    "title": "Top 10 Products by Revenue",
    "chart_type": "bar",
    "data": [
        {"label": "Amazon.ae Gift Card", "value": 382868.92},
        {"label": "Apple Gift Card", "value": 221408.68}
    ],
    "x_axis_label": "Product",
    "y_axis_label": "Revenue (AED)"
}
```

---

## 🔍 Common Use Cases

### Get All Data (No Filters)
```bash
curl -X POST http://localhost:8000/api/dashboard/headline \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}'
```

### Filter by Date Range
```bash
curl -X POST http://localhost:8000/api/dashboard/headline \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-06-01",
    "end_date": "2025-06-30",
    "currency": "AED"
  }'
```

### Filter by Country
```bash
curl -X POST http://localhost:8000/api/dashboard/headline \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "AED",
    "countries": ["United Arab Emirates"]
  }'
```

### Filter by Brand
```bash
curl -X POST http://localhost:8000/api/dashboard/top-products \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "AED",
    "brands": ["Apple", "Samsung"]
  }'
```

### Multiple Filters Combined
```bash
curl -X POST http://localhost:8000/api/dashboard/trend \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "currency": "AED",
    "countries": ["United Arab Emirates"],
    "brands": ["Apple"],
    "product_types": ["Electronics"]
  }'
```

---

## 🧪 Quick Test Commands

### Test All Endpoints
```bash
cd munero-platform
./scripts/test_api.sh      # Tests KPI endpoints
./scripts/test_charts.sh   # Tests chart endpoints
```

### Test Individual Endpoint
```bash
# Health check
curl http://localhost:8000/health | python3 -m json.tool

# Dashboard test
curl http://localhost:8000/api/dashboard/test | python3 -m json.tool

# Headline KPIs
curl -X POST http://localhost:8000/api/dashboard/headline \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | python3 -m json.tool

# Sales trend
curl -X POST 'http://localhost:8000/api/dashboard/trend?granularity=month' \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | python3 -m json.tool

# Breakdown by brand
curl -X POST 'http://localhost:8000/api/dashboard/breakdown?dimension=product_brand' \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | python3 -m json.tool

# Top 5 products
curl -X POST 'http://localhost:8000/api/dashboard/top-products?limit=5' \
  -H "Content-Type: application/json" \
  -d '{"currency": "AED"}' | python3 -m json.tool
```

---

## 📊 Response Format

All chart endpoints return the same structure:
```typescript
interface ChartResponse {
    title: string;                    // Chart title
    chart_type: "bar" | "line" | "pie" | "scatter" | "dual_axis";
    data: ChartPoint[];               // Array of data points
    x_axis_label: string;             // X-axis label
    y_axis_label: string;             // Y-axis label
}

interface ChartPoint {
    label: string;                    // Category or date
    value: number;                    // Metric value
    series?: string | null;           // For multi-series charts
}
```

---

## 🎨 Frontend Integration

### TypeScript Types
```typescript
// Copy these to your frontend
type Currency = 'AED' | 'USD' | 'EUR';

interface DashboardFilters {
    start_date?: string;              // YYYY-MM-DD
    end_date?: string;                // YYYY-MM-DD
    currency: Currency;
    clients?: string[];
    countries?: string[];
    product_types?: string[];
    brands?: string[];
    suppliers?: string[];
}

interface KPIMetric {
    label: string;
    value: number;
    formatted: string;
    trend_pct?: number;
    trend_direction: 'up' | 'down' | 'flat' | 'neutral';
}

interface HeadlineStats {
    total_orders: KPIMetric;
    total_revenue: KPIMetric;
    avg_order_value: KPIMetric;
    distinct_brands: KPIMetric;
}
```

### API Client Example
```typescript
const API_BASE = 'http://localhost:8000';

export async function fetchHeadlineKPIs(filters: DashboardFilters): Promise<HeadlineStats> {
    const response = await fetch(`${API_BASE}/api/dashboard/headline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(filters)
    });
    return response.json();
}

export async function fetchSalesTrend(
    filters: DashboardFilters, 
    granularity: 'day' | 'month' = 'month'
): Promise<ChartResponse> {
    const response = await fetch(
        `${API_BASE}/api/dashboard/trend?granularity=${granularity}`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(filters)
        }
    );
    return response.json();
}
```

---

## 🔗 Resources

- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **API Info**: http://localhost:8000/

---

## 📝 Notes

1. **Empty Lists = Select All**: If you pass an empty array for filters like `countries: []`, it means "select all countries"
2. **Date Format**: Always use ISO format `YYYY-MM-DD` for dates
3. **Currency**: Currently only AED is used in the database (order_price_in_aed)
4. **Null Values**: Some records have `null` for country/brand - they appear as "None" in results
5. **SQL Injection Protection**: All queries use parameterized binding (safe from SQL injection)
6. **Timeout**: No timeout on endpoints (synchronous queries)
7. **Rate Limiting**: No rate limiting implemented (add if needed for production)

---

**Server**: http://localhost:8000  
**Status**: ✅ Running  
**Endpoints**: 6 total (1 test, 1 KPI, 3 charts, 2 system)  
**Documentation**: http://localhost:8000/docs
