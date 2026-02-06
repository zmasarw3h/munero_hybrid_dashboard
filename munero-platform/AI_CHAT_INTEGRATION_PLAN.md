# AI Data Analyst Integration Plan

## Overview

This document outlines the complete integration of the Munero AI Data Analyst (currently a standalone Streamlit app) into the Munero Dashboard as a slide-over chat panel.

### Current State

| Component | Technology | Location |
|-----------|------------|----------|
| AI Analyst (Standalone) | Streamlit + Ollama + SQLite | `/app.py` |
| Dashboard Frontend | Next.js + React + Recharts | `/munero-platform/frontend/` |
| Dashboard Backend | FastAPI + SQLite | `/munero-platform/backend/` |

### Target State

- **Chat Slide-Over Panel**: 400px wide panel that slides in from the right
- **Trigger**: Button in dashboard header (top-right)
- **Context-Aware**: Reads current filters from `FilterContext`
- **Smart Visualizations**: Returns chart config, frontend renders with Recharts

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                    Dashboard Layout                             │    │
│  │  ┌──────────────────────────────────────────────────────────┐  │    │
│  │  │ Header: [Logo] [Nav Tabs] [Filters]        [🤖 Ask AI]   │  │    │
│  │  └──────────────────────────────────────────────────────────┘  │    │
│  │                                                                 │    │
│  │  ┌─────────────────────────────┐  ┌───────────────────────┐   │    │
│  │  │                             │  │   ChatSidebar         │   │    │
│  │  │    Dashboard Content        │  │   (Slide-Over)        │   │    │
│  │  │    (Overview/Market/        │  │                       │   │    │
│  │  │     Catalog pages)          │  │   - Context header    │   │    │
│  │  │                             │  │   - Message history   │   │    │
│  │  │    Width: ~66%              │  │   - Charts (Recharts) │   │    │
│  │  │                             │  │   - SQL display       │   │    │
│  │  │                             │  │   - Input field       │   │    │
│  │  │                             │  │                       │   │    │
│  │  │                             │  │   Width: 400px        │   │    │
│  │  └─────────────────────────────┘  └───────────────────────┘   │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                    │                                    │
└────────────────────────────────────┼────────────────────────────────────┘
                                     │ POST /api/chat
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                    POST /api/chat                               │    │
│  │                                                                 │    │
│  │  1. Receive: { message, filters, conversation_id }             │    │
│  │  2. Build context-aware SQL prompt (inject filters as WHERE)   │    │
│  │  3. Call Ollama (Qwen2.5-Coder) → generate SQL                 │    │
│  │  4. Execute SQL with timeout protection                        │    │
│  │  5. Run SmartRender logic → determine chart type               │    │
│  │  6. Return: { answer_text, sql_query, data, chart_config }     │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                              │                                          │
│                              ▼                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                    Services Layer                               │    │
│  │                                                                 │    │
│  │  llm_service.py:                                               │    │
│  │  - ChatOllama connection (Qwen2.5-Coder:7b)                    │    │
│  │  - SQL generation with schema + filter injection               │    │
│  │  - extract_sql_from_response()                                 │    │
│  │  - Timeout protection (60s LLM, 30s SQL)                       │    │
│  │                                                                 │    │
│  │  smart_render.py:                                              │    │
│  │  - Analyze DataFrame structure                                  │    │
│  │  - Determine best chart type (bar/line/pie/scatter/table)      │    │
│  │  - Return chart_config object (not rendered chart)             │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                              │                                          │
│                              ▼                                          │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                    SQLite Database                              │    │
│  │                    (munero.sqlite)                              │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Backend - LLM Service
### Phase 2: Backend - SmartRender Service  
### Phase 3: Backend - Chat Endpoint
### Phase 4: Frontend - Chat Components
### Phase 5: Frontend - Layout Integration
### Phase 6: Testing & Polish

---

# PHASE 1: Backend LLM Service

## Prompt for VS Code Agent

```
I need you to create a new LLM service for the Munero Dashboard backend that ports the AI functionality from app.py (Streamlit) to FastAPI.

## Context
- The existing Streamlit app at /app.py uses Ollama (Qwen2.5-Coder:7b) to convert natural language to SQL
- We need to port this to the FastAPI backend at /munero-platform/backend/
- The service should be context-aware (accept dashboard filters and inject them into SQL)

## Files to Create

### 1. backend/app/services/llm_service.py

Create a new service that:

1. **Connects to Ollama** using langchain-community:
   - Model: qwen2.5-coder:7b
   - Base URL: http://localhost:11434
   - Temperature: 0

2. **Has these functions**:

   a) `get_database_schema()` -> str
      - Return the schema info for fact_orders table
      - Include column descriptions and relationships
      - Note that fact_orders is DENORMALIZED (contains all data)

   b) `build_filter_clause(filters: DashboardFilters)` -> str
      - Convert FilterContext filters into SQL WHERE clause
      - Handle: date_range, countries, product_types, clients, brands, suppliers
      - Return "1=1" if no filters

   c) `generate_sql(question: str, filters: DashboardFilters)` -> str
      - Build the prompt with schema + filter context
      - Call Ollama with timeout protection (60 seconds)
      - Extract SQL from response (handle markdown, think tags, etc.)
      - Return clean SQL query

   d) `execute_sql(sql: str, conn)` -> pd.DataFrame
      - Execute with timeout protection (30 seconds)
      - Return DataFrame or raise exception

   e) `extract_sql_from_response(response: str)` -> str
      - Port from app.py
      - Remove <think> tags (DeepSeek-R1 specific)
      - Extract from ```sql blocks
      - Handle various LLM output formats

3. **Configuration**:
   ```python
   LLM_CONFIG = {
       "model": "qwen2.5-coder:7b",
       "base_url": "http://localhost:11434",
       "temperature": 0,
       "llm_timeout": 60,
       "sql_timeout": 30,
   }
   ```

4. **SQL Prompt Template** (port from app.py):
   - Include schema info
   - Add filter context as "ACTIVE FILTERS" section
   - Include terminology mapping (client, revenue, orders, etc.)
   - Include critical rules for SQL generation

### 2. backend/app/models.py (additions)

Add these Pydantic models:

```python
class ChatRequest(BaseModel):
    message: str
    filters: Optional[DashboardFilters] = None
    conversation_id: Optional[str] = None

class ChartConfig(BaseModel):
    type: Literal["bar", "line", "pie", "scatter", "table", "metric"]
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    secondary_y_column: Optional[str] = None
    orientation: Optional[Literal["horizontal", "vertical"]] = "vertical"
    title: Optional[str] = None

class ChatResponse(BaseModel):
    answer_text: str
    sql_query: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    chart_config: Optional[ChartConfig] = None
    row_count: int = 0
    warnings: List[str] = []
    error: Optional[str] = None
```

### 3. backend/requirements.txt (additions)

Add these dependencies:
```
langchain-community>=0.2.0
langchain-ollama>=0.1.0
```

## Reference Code

Port the following functions from /app.py:
- `get_llm()` → adapt for service pattern
- `get_enhanced_schema_info()` → `get_database_schema()`
- `get_sql_chain()` → `generate_sql()`
- `extract_sql_from_response()` → keep similar
- `remove_think_tags()` → keep similar
- `invoke_llm_with_timeout()` → adapt with ThreadPoolExecutor
- `execute_sql_with_timeout()` → `execute_sql()`

## Key Adaptations from app.py

1. **Filter Injection**: The dashboard has active filters. Inject them into the SQL prompt:
   ```
   ACTIVE DASHBOARD FILTERS (apply these to your query):
   - Date Range: 2025-12-01 to 2025-12-31
   - Countries: UAE, Saudi Arabia
   - Product Types: gift_cards
   
   Your SQL MUST include: WHERE order_date BETWEEN '2025-12-01' AND '2025-12-31' 
   AND client_country IN ('UAE', 'Saudi Arabia') AND order_type = 'gift_cards'
   ```

2. **No Streamlit Dependencies**: Remove all st.* calls, use pure Python

3. **Database Path**: Use `backend/data/munero.sqlite`

4. **Error Handling**: Return structured errors, don't raise exceptions to caller

## Testing

After creating the service, I should be able to:
```python
from app.services.llm_service import LLMService

service = LLMService()
result = service.generate_sql(
    "What are my top 5 products by revenue?",
    filters={"date_range": {"start": "2025-01-01", "end": "2025-12-31"}}
)
print(result)  # Should print valid SQL
```
```

---

# PHASE 2: Backend SmartRender Service

## Prompt for VS Code Agent

```
I need you to create a SmartRender service that determines the best visualization type for query results. This ports the smart_render() function from app.py.

## Context
- The Streamlit app has a SmartRender engine that auto-selects chart types
- We need to port this logic but return a CONFIG object instead of rendering
- The frontend (React/Recharts) will render based on the config

## Files to Create

### 1. backend/app/services/smart_render.py

Create a service with these functions:

1. **`determine_chart_type(df: pd.DataFrame, question: str)` -> ChartConfig**

   Logic to implement (port from app.py smart_render):

   a) **Single Value (KPI)**:
      - If 1 row × 1 column → type: "metric"
      - Return the value and formatted label

   b) **Single Column**:
      - If only 1 column → type: "table"

   c) **Too Many Columns (>3)**:
      - type: "table"

   d) **Two Numeric Columns (Scatter)**:
      - If 2+ numeric columns and user didn't specify chart type
      - type: "scatter", x_column, y_column

   e) **Time Series Detection**:
      - If label column contains: date, time, month, year, week, day
      - type: "line"

   f) **Category Detection**:
      - If ≤8 unique values → eligible for "pie"
      - If >8 values → "bar"

   g) **Long Labels**:
      - If max label length > 20 chars → orientation: "horizontal"

   h) **User Preference Override**:
      - Check question for: "pie chart", "bar chart", "line chart", "table", "scatter"
      - Override auto-detection

2. **`prepare_data_for_chart(df: pd.DataFrame, config: ChartConfig)` -> Tuple[List[Dict], List[str]]**

   - Limit to top 15 rows for display (preserve full data for warnings)
   - Aggregate if needed (raw transactions → grouped)
   - Sort appropriately
   - Return (data_list, warnings)

3. **`format_answer_text(df: pd.DataFrame, question: str, config: ChartConfig)` -> str**

   - Generate a brief natural language summary
   - Example: "Here are your top 5 products by revenue:"
   - Include total if single metric

### Configuration Constants

```python
SMART_RENDER_CONFIG = {
    "max_display_rows": 15,
    "long_label_threshold": 20,
    "pie_chart_max_slices": 8,
    "bar_chart_max_categories": 20,
}
```

### ChartConfig Examples

```python
# Bar chart
ChartConfig(
    type="bar",
    x_column="product_name",
    y_column="total_revenue",
    orientation="horizontal",
    title="Top Products by Revenue"
)

# Line chart (time series)
ChartConfig(
    type="line",
    x_column="month",
    y_column="revenue",
    title="Monthly Revenue Trend"
)

# Pie chart
ChartConfig(
    type="pie",
    x_column="order_type",  # names/labels
    y_column="revenue",     # values
    title="Revenue by Product Type"
)

# Scatter plot
ChartConfig(
    type="scatter",
    x_column="orders",
    y_column="revenue",
    title="Orders vs Revenue"
)

# Single metric
ChartConfig(
    type="metric",
    title="Total Revenue",
    # data will contain single value
)

# Table
ChartConfig(
    type="table",
    title="Query Results"
)
```

## Reference from app.py

Port the logic from `smart_render()` function:
- KPI card detection (1×1 result)
- Aggregation check (unique labels < total rows)
- Time series detection
- Long label detection
- Pie chart category limit with "Others" grouping
- LLM fallback for chart type decision (optional, can simplify to heuristics)

## Key Differences from app.py

1. **No Rendering**: Return ChartConfig, not Plotly figures
2. **No Streamlit**: No st.* calls
3. **Simplified**: Skip LLM chart selection, use heuristics only
4. **Data Format**: Return List[Dict] for JSON serialization

## Testing

```python
from app.services.smart_render import SmartRenderService
import pandas as pd

service = SmartRenderService()

# Test bar chart
df = pd.DataFrame({
    "product_name": ["Product A", "Product B", "Product C"],
    "revenue": [10000, 8000, 6000]
})
config = service.determine_chart_type(df, "top products")
print(config)  # type="bar", x_column="product_name", y_column="revenue"

# Test time series
df = pd.DataFrame({
    "month": ["2025-01", "2025-02", "2025-03"],
    "revenue": [10000, 12000, 11000]
})
config = service.determine_chart_type(df, "monthly trend")
print(config)  # type="line"
```
```

---

# PHASE 3: Backend Chat Endpoint

## Prompt for VS Code Agent

```
I need you to create the /api/chat endpoint that ties together the LLM service and SmartRender service.

## Context
- LLMService (Phase 1) generates SQL from natural language
- SmartRenderService (Phase 2) determines chart configuration
- This endpoint orchestrates both and returns a complete response

## Files to Create/Modify

### 1. backend/app/api/chat.py (NEW)

Create a new router:

```python
from fastapi import APIRouter, Depends
from app.models import ChatRequest, ChatResponse, ChartConfig
from app.services.llm_service import LLMService
from app.services.smart_render import SmartRenderService

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a natural language question and return data with visualization config.
    
    Flow:
    1. Generate SQL from question + filters
    2. Execute SQL query
    3. Determine best chart type
    4. Return structured response
    """
    pass  # Implement
```

### 2. Implementation Details

The endpoint should:

1. **Initialize Services**:
   ```python
   llm_service = LLMService()
   smart_render = SmartRenderService()
   ```

2. **Generate SQL**:
   ```python
   try:
       sql_query = llm_service.generate_sql(
           question=request.message,
           filters=request.filters
       )
   except TimeoutError:
       return ChatResponse(
           answer_text="The AI took too long to respond. Please try a simpler question.",
           error="LLM timeout"
       )
   ```

3. **Execute Query**:
   ```python
   try:
       df = llm_service.execute_sql(sql_query)
   except Exception as e:
       # Optionally: retry with error context
       return ChatResponse(
           answer_text=f"Query failed: {str(e)}",
           sql_query=sql_query,
           error=str(e)
       )
   ```

4. **Handle Empty Results**:
   ```python
   if df.empty:
       return ChatResponse(
           answer_text="No results found for your query with the current filters.",
           sql_query=sql_query,
           data=[],
           row_count=0
       )
   ```

5. **Determine Visualization**:
   ```python
   chart_config = smart_render.determine_chart_type(df, request.message)
   display_data, warnings = smart_render.prepare_data_for_chart(df, chart_config)
   answer_text = smart_render.format_answer_text(df, request.message, chart_config)
   ```

6. **Return Response**:
   ```python
   return ChatResponse(
       answer_text=answer_text,
       sql_query=sql_query,
       data=display_data,
       chart_config=chart_config,
       row_count=len(df),
       warnings=warnings
   )
   ```

### 3. backend/main.py (MODIFY)

Register the new router:

```python
from app.api.chat import router as chat_router

# Add after existing routers
app.include_router(chat_router)
```

### 4. Error Handling

Implement robust error handling:

```python
@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    warnings = []
    
    try:
        # ... main logic ...
    
    except TimeoutError as e:
        return ChatResponse(
            answer_text="Request timed out. Try a simpler question.",
            error="timeout",
            warnings=["LLM or SQL execution exceeded time limit"]
        )
    
    except sqlite3.OperationalError as e:
        return ChatResponse(
            answer_text="Database query failed. The AI may have generated invalid SQL.",
            sql_query=sql_query if 'sql_query' in locals() else None,
            error=str(e)
        )
    
    except Exception as e:
        return ChatResponse(
            answer_text=f"An error occurred: {str(e)}",
            error=str(e)
        )
```

### 5. Health Check for Ollama

Add a helper endpoint to check if Ollama is running:

```python
@router.get("/chat/health")
async def chat_health():
    """Check if the AI service is available."""
    try:
        # Quick ping to Ollama
        llm_service = LLMService()
        is_available = llm_service.check_connection()
        return {
            "status": "ok" if is_available else "unavailable",
            "model": "qwen2.5-coder:7b",
            "message": "AI service is ready" if is_available else "Ollama is not running. Start with: ollama serve"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
```

## Request/Response Examples

### Example 1: Top Products

**Request:**
```json
{
  "message": "What are my top 5 products by revenue?",
  "filters": {
    "date_range": {
      "start": "2025-01-01",
      "end": "2025-12-31"
    },
    "countries": ["UAE"]
  }
}
```

**Response:**
```json
{
  "answer_text": "Here are your top 5 products by revenue in UAE:",
  "sql_query": "SELECT product_name, SUM(sale_price * quantity) as total_revenue FROM fact_orders WHERE order_date BETWEEN '2025-01-01' AND '2025-12-31' AND client_country = 'UAE' GROUP BY product_name ORDER BY total_revenue DESC LIMIT 5;",
  "data": [
    {"product_name": "iTunes Gift Card $100", "total_revenue": 450000},
    {"product_name": "Google Play $50", "total_revenue": 380000},
    {"product_name": "Amazon Gift Card $25", "total_revenue": 290000},
    {"product_name": "Netflix Subscription", "total_revenue": 180000},
    {"product_name": "Spotify Premium", "total_revenue": 120000}
  ],
  "chart_config": {
    "type": "bar",
    "x_column": "product_name",
    "y_column": "total_revenue",
    "orientation": "horizontal",
    "title": "Top 5 Products by Revenue"
  },
  "row_count": 5,
  "warnings": [],
  "error": null
}
```

### Example 2: Monthly Trend

**Request:**
```json
{
  "message": "Show me the monthly revenue trend for 2025"
}
```

**Response:**
```json
{
  "answer_text": "Here's the monthly revenue trend for 2025:",
  "sql_query": "SELECT strftime('%Y-%m', order_date) as month, SUM(sale_price * quantity) as revenue FROM fact_orders WHERE order_date BETWEEN '2025-01-01' AND '2025-12-31' GROUP BY month ORDER BY month;",
  "data": [
    {"month": "2025-01", "revenue": 1200000},
    {"month": "2025-02", "revenue": 1350000},
    ...
  ],
  "chart_config": {
    "type": "line",
    "x_column": "month",
    "y_column": "revenue",
    "title": "Monthly Revenue Trend"
  },
  "row_count": 12,
  "warnings": [],
  "error": null
}
```

### Example 3: Single Metric

**Request:**
```json
{
  "message": "What is the total revenue?"
}
```

**Response:**
```json
{
  "answer_text": "Total Revenue: $4,567,890.00",
  "sql_query": "SELECT SUM(sale_price * quantity) as total_revenue FROM fact_orders;",
  "data": [{"total_revenue": 4567890.00}],
  "chart_config": {
    "type": "metric",
    "title": "Total Revenue"
  },
  "row_count": 1,
  "warnings": [],
  "error": null
}
```

## Testing

After implementation, test with curl:

```bash
# Test basic query
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are my top 5 customers?",
    "filters": {}
  }'

# Test with filters
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me monthly revenue",
    "filters": {
      "date_range": {"start": "2025-01-01", "end": "2025-06-30"},
      "countries": ["UAE", "Saudi Arabia"]
    }
  }'

# Test health check
curl http://localhost:8000/api/chat/health
```
```

---

# PHASE 4: Frontend Chat Components

## Prompt for VS Code Agent

```
I need you to create the frontend chat components for the AI slide-over panel.

## Context
- Backend /api/chat endpoint returns: { answer_text, sql_query, data, chart_config, warnings }
- Frontend should render the chat UI and visualizations using Recharts
- The slide-over is 400px wide, slides from right

## Files to Create

### 1. frontend/lib/types.ts (additions)

Add these types:

```typescript
// Chat types
export interface ChatRequest {
  message: string;
  filters?: DashboardFilters;
  conversation_id?: string;
}

export interface ChartConfig {
  type: 'bar' | 'line' | 'pie' | 'scatter' | 'table' | 'metric';
  x_column?: string;
  y_column?: string;
  secondary_y_column?: string;
  orientation?: 'horizontal' | 'vertical';
  title?: string;
}

export interface ChatResponse {
  answer_text: string;
  sql_query?: string;
  data?: Record<string, any>[];
  chart_config?: ChartConfig;
  row_count: number;
  warnings: string[];
  error?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  response?: ChatResponse;  // Only for assistant messages
}
```

### 2. frontend/lib/api-client.ts (additions)

Add chat API method:

```typescript
async sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${this.baseUrl}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.statusText}`);
  }
  
  return response.json();
}

async checkChatHealth(): Promise<{ status: string; message: string }> {
  const response = await fetch(`${this.baseUrl}/api/chat/health`);
  return response.json();
}
```

### 3. frontend/components/chat/ChatInput.tsx (NEW)

```tsx
'use client';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({ onSend, disabled, placeholder }: ChatInputProps) {
  // Input field with send button
  // Handle Enter key
  // Clear input after send
  // Disable while loading
}
```

Features:
- Text input with placeholder "Ask a question about your data..."
- Send button (icon or text)
- Enter key to send
- Disabled state while AI is responding
- Clear input after sending

### 4. frontend/components/chat/ChatMessage.tsx (NEW)

```tsx
'use client';

import { ChatMessage as ChatMessageType } from '@/lib/types';

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  // Render user or assistant message
  // For assistant: include chart, SQL, warnings
}
```

Features:
- Different styling for user vs assistant messages
- User: right-aligned, blue background
- Assistant: left-aligned, gray background
- Render markdown in answer_text (bold, bullet points)
- Include ChatChart component for visualizations
- Collapsible SQL display
- Show warnings if present

### 5. frontend/components/chat/ChatChart.tsx (NEW)

```tsx
'use client';

import { ChartConfig } from '@/lib/types';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie,
  ScatterChart, Scatter, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts';

interface ChatChartProps {
  config: ChartConfig;
  data: Record<string, any>[];
}

export function ChatChart({ config, data }: ChatChartProps) {
  // Render appropriate chart based on config.type
}
```

Implement chart types:

1. **Bar Chart**:
   ```tsx
   if (config.type === 'bar') {
     return (
       <ResponsiveContainer width="100%" height={200}>
         <BarChart 
           data={data} 
           layout={config.orientation === 'horizontal' ? 'vertical' : 'horizontal'}
         >
           <XAxis dataKey={config.x_column} />
           <YAxis />
           <Tooltip />
           <Bar dataKey={config.y_column} fill="#3b82f6" />
         </BarChart>
       </ResponsiveContainer>
     );
   }
   ```

2. **Line Chart**:
   - Use LineChart with Line component
   - Format X axis for dates if needed

3. **Pie Chart**:
   - Use PieChart with Pie component
   - Add labels and colors

4. **Scatter Chart**:
   - Use ScatterChart with Scatter component

5. **Metric (KPI)**:
   ```tsx
   if (config.type === 'metric') {
     const value = data[0]?.[Object.keys(data[0])[0]];
     return (
       <div className="text-center py-4">
         <div className="text-3xl font-bold text-blue-600">
           {typeof value === 'number' ? value.toLocaleString() : value}
         </div>
         <div className="text-sm text-muted-foreground">{config.title}</div>
       </div>
     );
   }
   ```

6. **Table**:
   - Use a simple HTML table or existing DataTable component
   - Show first 10 rows

### 6. frontend/components/chat/ChatSidebar.tsx (NEW)

```tsx
'use client';

import { useState, useRef, useEffect } from 'react';
import { X, Send, Copy, Check, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useFilters } from '@/components/dashboard/FilterContext';
import { apiClient } from '@/lib/api-client';
import { ChatMessage, ChatResponse } from '@/lib/types';
import { ChatInput } from './ChatInput';
import { ChatMessage as ChatMessageComponent } from './ChatMessage';

interface ChatSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ChatSidebar({ isOpen, onClose }: ChatSidebarProps) {
  const { filters } = useFilters();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (message: string) => {
    // Add user message
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Call API with current filters
      const response = await apiClient.sendChatMessage({
        message,
        filters,
      });

      // Add assistant message
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.answer_text,
        timestamp: new Date(),
        response,
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      // Handle error
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error.message}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Render slide-over panel
  return (
    <div className={cn(
      "fixed inset-y-0 right-0 w-[400px] bg-background border-l shadow-lg transform transition-transform duration-300 z-50",
      isOpen ? "translate-x-0" : "translate-x-full"
    )}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <span className="text-lg">🤖</span>
          <span className="font-semibold">AI Assistant</span>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Context indicator */}
      <div className="px-4 py-2 bg-muted/50 text-xs text-muted-foreground">
        Context: {formatFilterContext(filters)}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4" style={{ height: 'calc(100vh - 180px)' }}>
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground py-8">
            <p className="mb-4">👋 Hi! Ask me anything about your data.</p>
            <div className="space-y-2 text-sm">
              <p className="text-blue-600 cursor-pointer hover:underline" onClick={() => handleSend("What are my top 5 products?")}>
                "What are my top 5 products?"
              </p>
              <p className="text-blue-600 cursor-pointer hover:underline" onClick={() => handleSend("Show me monthly revenue trend")}>
                "Show me monthly revenue trend"
              </p>
              <p className="text-blue-600 cursor-pointer hover:underline" onClick={() => handleSend("Which clients have the highest order volume?")}>
                "Which clients have the highest order volume?"
              </p>
            </div>
          </div>
        )}
        
        {messages.map(msg => (
          <ChatMessageComponent key={msg.id} message={msg} />
        ))}
        
        {isLoading && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <div className="animate-pulse">🤖</div>
            <span>Thinking...</span>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t">
        <ChatInput onSend={handleSend} disabled={isLoading} />
      </div>
    </div>
  );
}

function formatFilterContext(filters: DashboardFilters): string {
  const parts = [];
  if (filters.dateRange) {
    parts.push(`${filters.dateRange.start} to ${filters.dateRange.end}`);
  }
  if (filters.countries?.length) {
    parts.push(filters.countries.join(', '));
  }
  return parts.length > 0 ? parts.join(' | ') : 'All data';
}
```

### 7. frontend/components/chat/index.ts (NEW)

```typescript
export { ChatSidebar } from './ChatSidebar';
export { ChatMessage } from './ChatMessage';
export { ChatInput } from './ChatInput';
export { ChatChart } from './ChatChart';
```

## Styling Requirements

- Use Tailwind CSS classes
- Match existing dashboard styling
- Smooth slide-in animation (300ms)
- Scrollable message area
- Fixed header and input

## Component Behavior

1. **ChatSidebar**:
   - Controlled by isOpen prop
   - Reads filters from FilterContext
   - Manages message history in state
   - Auto-scrolls to latest message

2. **ChatMessage**:
   - Different styles for user/assistant
   - Renders chart if response has chart_config
   - Collapsible SQL with copy button
   - Shows warnings as yellow alerts

3. **ChatChart**:
   - Responsive width, fixed height (200px in sidebar)
   - Handles all chart types from backend
   - Proper axis labels and tooltips

4. **ChatInput**:
   - Disabled while loading
   - Enter to send, Shift+Enter for newline
   - Clear after send

## Testing

After creating components:
1. Import ChatSidebar in layout
2. Add state for isOpen
3. Add toggle button
4. Test with various questions
```

---

# PHASE 5: Frontend Layout Integration

## Prompt for VS Code Agent

```
I need you to integrate the ChatSidebar into the dashboard layout with a toggle button.

## Context
- ChatSidebar component exists from Phase 4
- Need to add toggle button to the dashboard header
- Button should be visible on all dashboard pages

## Files to Modify

### 1. frontend/app/dashboard/layout.tsx

Add the chat toggle button and ChatSidebar to the layout:

```tsx
'use client';

import { useState } from 'react';
import { MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ChatSidebar } from '@/components/chat';
// ... existing imports

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [isChatOpen, setIsChatOpen] = useState(false);

  return (
    <FilterProvider>
      <div className="min-h-screen bg-background">
        {/* Header */}
        <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
          <div className="container flex h-14 items-center justify-between">
            {/* Left: Logo/Brand */}
            <div className="flex items-center gap-4">
              <h1 className="font-bold text-lg">Munero</h1>
              {/* Nav tabs */}
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-2">
              {/* Existing items... */}
              
              {/* AI Chat Toggle Button */}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsChatOpen(true)}
                className="gap-2"
              >
                <MessageSquare className="h-4 w-4" />
                <span className="hidden sm:inline">Ask AI</span>
              </Button>
            </div>
          </div>
        </header>

        {/* Filter Bar */}
        <FilterBar />

        {/* Main Content */}
        <main className="container py-6">
          {children}
        </main>

        {/* Chat Sidebar (Slide-over) */}
        <ChatSidebar 
          isOpen={isChatOpen} 
          onClose={() => setIsChatOpen(false)} 
        />

        {/* Backdrop when chat is open */}
        {isChatOpen && (
          <div 
            className="fixed inset-0 bg-black/20 z-40"
            onClick={() => setIsChatOpen(false)}
          />
        )}
      </div>
    </FilterProvider>
  );
}
```

### 2. Button Styling Options

Option A: Outline button (subtle)
```tsx
<Button variant="outline" size="sm" className="gap-2">
  <MessageSquare className="h-4 w-4" />
  Ask AI
</Button>
```

Option B: Primary button (prominent)
```tsx
<Button size="sm" className="gap-2 bg-blue-600 hover:bg-blue-700">
  <Sparkles className="h-4 w-4" />
  Ask AI
</Button>
```

Option C: Ghost button with badge
```tsx
<Button variant="ghost" size="icon" className="relative">
  <MessageSquare className="h-5 w-5" />
  <span className="absolute -top-1 -right-1 h-3 w-3 bg-blue-600 rounded-full" />
</Button>
```

### 3. Keyboard Shortcut (Optional Enhancement)

Add keyboard shortcut to toggle chat:

```tsx
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    // Cmd+K or Ctrl+K to toggle chat
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      setIsChatOpen(prev => !prev);
    }
    // Escape to close
    if (e.key === 'Escape' && isChatOpen) {
      setIsChatOpen(false);
    }
  };

  document.addEventListener('keydown', handleKeyDown);
  return () => document.removeEventListener('keydown', handleKeyDown);
}, [isChatOpen]);
```

Add tooltip to button showing shortcut:
```tsx
<Button ... title="Ask AI (⌘K)">
```

### 4. Z-Index Management

Ensure proper layering:
- Header: z-40
- Backdrop: z-40
- ChatSidebar: z-50
- Tooltips/Dropdowns: z-50+

### 5. Mobile Responsiveness

On mobile, make chat full-width:
```tsx
<div className={cn(
  "fixed inset-y-0 right-0 bg-background border-l shadow-lg transform transition-transform duration-300 z-50",
  "w-full sm:w-[400px]",  // Full width on mobile
  isOpen ? "translate-x-0" : "translate-x-full"
)}>
```

## Testing Checklist

- [ ] Button visible in header on all pages
- [ ] Click opens slide-over
- [ ] Backdrop click closes
- [ ] X button closes
- [ ] Escape key closes
- [ ] Chat persists while navigating pages
- [ ] Filters are passed to chat
- [ ] Mobile: full-width chat

## Optional: Floating Action Button Alternative

If you prefer a floating button instead of header button:

```tsx
{/* Floating Action Button */}
<Button
  onClick={() => setIsChatOpen(true)}
  className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg z-30"
  size="icon"
>
  <MessageSquare className="h-6 w-6" />
</Button>
```
```

---

# PHASE 6: Testing & Polish

## Prompt for VS Code Agent

```
I need you to test the AI chat integration end-to-end and add polish.

## Testing Checklist

### 1. Backend Tests

Create test script: `scripts/test_chat_integration.sh`

```bash
#!/bin/bash

echo "=== Testing Chat Integration ==="

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

echo -e "\n=== Tests Complete ==="
```

### 2. Frontend Manual Testing

Test these scenarios:

1. **Open/Close Chat**:
   - Click "Ask AI" button → chat opens
   - Click X → chat closes
   - Click backdrop → chat closes
   - Press Escape → chat closes

2. **Send Messages**:
   - Type message, press Enter → message sent
   - Type message, click Send → message sent
   - Empty message → nothing happens

3. **Responses**:
   - "Top 5 products" → Bar chart appears
   - "Monthly revenue trend" → Line chart appears
   - "Total revenue" → Single metric displays
   - "List all clients" → Table displays

4. **SQL Display**:
   - Click "View SQL" → SQL expands
   - Click copy button → SQL copied to clipboard

5. **Filter Context**:
   - Set date filter → ask question → filters applied
   - Set country filter → ask question → filters applied

6. **Error States**:
   - Turn off Ollama → send message → error displayed
   - Send gibberish → graceful error

7. **Loading States**:
   - Send message → loading indicator shows
   - Input disabled while loading

### 3. Polish Items

#### A. Loading States

Add skeleton loaders:
```tsx
{isLoading && (
  <div className="space-y-3 animate-pulse">
    <div className="h-4 bg-muted rounded w-3/4" />
    <div className="h-4 bg-muted rounded w-1/2" />
    <div className="h-32 bg-muted rounded" />
  </div>
)}
```

#### B. Copy SQL Button Feedback

```tsx
const [copied, setCopied] = useState(false);

const handleCopy = async () => {
  await navigator.clipboard.writeText(sql);
  setCopied(true);
  setTimeout(() => setCopied(false), 2000);
};

<Button variant="ghost" size="sm" onClick={handleCopy}>
  {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
</Button>
```

#### C. Message Timestamps

```tsx
<span className="text-xs text-muted-foreground">
  {format(message.timestamp, 'h:mm a')}
</span>
```

#### D. Suggested Questions

After assistant response, show follow-up suggestions:
```tsx
<div className="flex flex-wrap gap-2 mt-2">
  <Button variant="outline" size="sm" onClick={() => handleSend("Show me the trend")}>
    📈 Show trend
  </Button>
  <Button variant="outline" size="sm" onClick={() => handleSend("Break down by category")}>
    📊 By category
  </Button>
</div>
```

#### E. Error Recovery

```tsx
{response?.error && (
  <div className="bg-red-50 border border-red-200 rounded p-3 mt-2">
    <p className="text-red-800 text-sm">{response.error}</p>
    <Button variant="outline" size="sm" className="mt-2" onClick={() => handleRetry()}>
      Try Again
    </Button>
  </div>
)}
```

#### F. Empty State

```tsx
{messages.length === 0 && (
  <div className="flex flex-col items-center justify-center h-full text-center p-8">
    <div className="text-4xl mb-4">🤖</div>
    <h3 className="font-semibold mb-2">AI Data Assistant</h3>
    <p className="text-muted-foreground text-sm mb-6">
      Ask questions about your sales data in plain English.
    </p>
    <div className="space-y-2 w-full max-w-[280px]">
      <SuggestedQuestion onClick={handleSend}>
        What are my top selling products?
      </SuggestedQuestion>
      <SuggestedQuestion onClick={handleSend}>
        Show me revenue by country
      </SuggestedQuestion>
      <SuggestedQuestion onClick={handleSend}>
        Monthly sales trend for 2025
      </SuggestedQuestion>
    </div>
  </div>
)}
```

#### G. Ollama Not Running Warning

Check on mount:
```tsx
useEffect(() => {
  const checkHealth = async () => {
    const health = await apiClient.checkChatHealth();
    if (health.status !== 'ok') {
      setOllamaWarning(health.message);
    }
  };
  checkHealth();
}, []);

{ollamaWarning && (
  <div className="bg-yellow-50 border-b border-yellow-200 px-4 py-2 text-sm text-yellow-800">
    ⚠️ {ollamaWarning}
  </div>
)}
```

### 4. Performance Optimizations

1. **Debounce Input** (if implementing auto-complete):
   ```tsx
   const debouncedSend = useMemo(
     () => debounce(handleSend, 300),
     []
   );
   ```

2. **Virtualize Long Conversations** (if needed):
   ```tsx
   import { FixedSizeList } from 'react-window';
   ```

3. **Memoize Chart Components**:
   ```tsx
   const MemoizedChart = memo(ChatChart);
   ```

### 5. Accessibility

1. **Focus Management**:
   - Focus input when chat opens
   - Return focus to trigger when chat closes

2. **Keyboard Navigation**:
   - Tab through messages
   - Enter to expand/collapse SQL

3. **Screen Reader**:
   - aria-label on buttons
   - aria-live for new messages

```tsx
<div 
  role="log" 
  aria-label="Chat messages" 
  aria-live="polite"
>
  {messages.map(...)}
</div>
```

## Final Verification

Run through complete flow:
1. Start backend: `cd backend && uvicorn main:app --reload`
2. Start Ollama: `ollama serve`
3. Start frontend: `cd frontend && npm run dev`
4. Open dashboard, click "Ask AI"
5. Ask "What are my top products?"
6. Verify chart renders correctly
7. Check SQL display works
8. Test with various question types
```

---

# Quick Reference

## Files Created/Modified Summary

### Backend
| File | Action | Phase |
|------|--------|-------|
| `backend/app/services/llm_service.py` | CREATE | 1 |
| `backend/app/services/smart_render.py` | CREATE | 2 |
| `backend/app/api/chat.py` | CREATE | 3 |
| `backend/app/models.py` | MODIFY | 1, 3 |
| `backend/main.py` | MODIFY | 3 |
| `backend/requirements.txt` | MODIFY | 1 |

### Frontend
| File | Action | Phase |
|------|--------|-------|
| `frontend/lib/types.ts` | MODIFY | 4 |
| `frontend/lib/api-client.ts` | MODIFY | 4 |
| `frontend/components/chat/ChatInput.tsx` | CREATE | 4 |
| `frontend/components/chat/ChatMessage.tsx` | CREATE | 4 |
| `frontend/components/chat/ChatChart.tsx` | CREATE | 4 |
| `frontend/components/chat/ChatSidebar.tsx` | CREATE | 4 |
| `frontend/components/chat/index.ts` | CREATE | 4 |
| `frontend/app/dashboard/layout.tsx` | MODIFY | 5 |

### Scripts
| File | Action | Phase |
|------|--------|-------|
| `scripts/test_chat_integration.sh` | CREATE | 6 |

---

## Dependencies

### Backend (requirements.txt additions)
```
langchain-community>=0.2.0
langchain-ollama>=0.1.0
```

### Frontend
No new npm packages required (uses existing Recharts)

---

## Ollama Setup Reminder

Before testing, ensure Ollama is running with the required model:

```bash
# Start Ollama server
ollama serve

# Pull the model (if not already)
ollama pull qwen2.5-coder:7b

# Verify model is available
ollama list
```
