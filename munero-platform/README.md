# Munero AI Platform 🚀

Production-grade AI-powered data analytics platform with natural language querying capabilities.

**Status**: ✅ Phase 3 Complete - Backend operational with AI Copilot

## 🎯 Overview

The Munero AI Platform transforms sales data analysis through:
- 📊 **Interactive Dashboards** - Real-time KPIs and charts
- 🤖 **AI Copilot** - Natural language to SQL queries
- 🔍 **Smart Visualizations** - Auto-detected chart types
- 📈 **Business Intelligence** - Actionable insights

## Tech Stack

- **Backend**: FastAPI 0.115.0 (Python 3.13) ✅
- **Database**: SQLite (66,563 rows) ✅
- **AI/LLM**: LangChain 0.3.0 + Ollama (qwen2.5-coder:7b) ✅
- **Frontend**: Next.js 14 (TypeScript, App Router, Shadcn UI) - *Phase 4*

## Project Structure

```
munero-platform/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/         # API route handlers
│   │   ├── core/        # Configuration and settings
│   │   ├── services/    # Business logic (AI, SmartRender)
│   │   └── models.py    # Pydantic data contracts
│   ├── main.py          # FastAPI entry point
│   └── requirements.txt
├── frontend/            # Next.js application (TBD)
├── data/                # SQLite database storage
└── scripts/             # ETL and setup utilities
    └── ingest_data.py   # CSV to SQLite ingestion
```

## Quick Start

### 1. Set Up the Database

First, run the data ingestion script to create the SQLite database from your CSV files:

```bash
cd munero-platform
python scripts/ingest_data.py
```

This will:
- Read CSV files from `/Users/zmasarweh/Documents/Munero_CSV_Data/`
- Clean column names (lowercase, snake_case)
- Convert date columns to ISO format (YYYY-MM-DD)
- Create `data/munero.sqlite` with 4 tables:
  - `dim_customer`
  - `dim_products`
  - `dim_suppliers`
  - `fact_orders`

### 2. Install Backend Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Start Ollama (Required for AI features)

Make sure Ollama is running with the required model:

```bash
ollama serve
ollama pull qwen2.5-coder:7b
```

### 4. Run the Backend Server

```bash
# Start the backend server
./scripts/start_backend.sh

# Or manually:
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📊 API Endpoints

### Dashboard API (Phase 2) ✅
- `POST /api/dashboard/headline` - KPI metrics (orders, revenue, AOV, brands)
- `POST /api/dashboard/trend` - Time series charts
- `POST /api/dashboard/breakdown` - Category breakdowns
- `POST /api/dashboard/top-products` - Product rankings
- `GET /api/dashboard/test` - Database connectivity test

### AI Copilot API (Phase 3) ✅
- `POST /api/chat/` - Natural language query processing
- `GET /api/chat/test` - LLM connectivity check

### System
- `GET /` - API welcome message
- `GET /health` - Health check with database and LLM status

**Total**: 9 operational endpoints

## 🧪 Testing

```bash
# Test dashboard endpoints
./scripts/test_api.sh        # 5 KPI test scenarios
./scripts/test_charts.sh     # 9 chart test scenarios

# Test AI copilot
./scripts/test_chat.sh       # 7 AI query scenarios
```

## 🤖 AI Copilot Examples

Ask questions in natural language:

```bash
# Top products
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the top 5 products by revenue?", "filters": {"currency": "AED"}}'

# Revenue trend
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me revenue trend by month for 2025", "filters": {"start_date": "2025-01-01", "end_date": "2025-12-31"}}'

# Brand comparison
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{"message": "Compare Apple vs Samsung revenue", "filters": {"brands": ["Apple", "Samsung"]}}'
```

## ⚙️ Configuration

Edit `backend/app/core/config.py` or use environment variables:

```env
# .env file (create in backend/ directory)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
LLM_TEMPERATURE=0.0
LLM_TIMEOUT=60
SQL_TIMEOUT=30
MAX_DISPLAY_ROWS=1000
DEBUG=True
```

## 📈 Development Roadmap

### Phase 1: Foundation ✅
- [x] Project structure setup
- [x] Data ingestion script (66,563 rows)
- [x] FastAPI backend foundation
- [x] Pydantic models (data contracts)
- [x] Configuration management

### Phase 2: Dashboard API ✅
- [x] KPI metrics endpoint
- [x] Time series charts endpoint
- [x] Category breakdown endpoint
- [x] Product rankings endpoint
- [x] Dynamic filter system

### Phase 3: AI Copilot ✅
- [x] LLM service integration (LangChain + Ollama)
- [x] SQL generation from natural language
- [x] Smart visualization detection
- [x] Natural language summaries
- [x] Context-aware prompting

### Phase 4: Frontend (Next) 🚧
- [ ] Next.js 14 setup with App Router
- [ ] Dashboard UI with Shadcn components
- [ ] Interactive charts (Recharts)
- [ ] AI chat interface
- [ ] Global filter controls
- [ ] Real-time query execution

### Phase 5: Advanced Features 📋
- [ ] Query history & favorites
- [ ] Export to PDF/Excel
- [ ] User authentication
- [ ] Scheduled reports
- [ ] Email alerts
- [ ] Query API endpoints
- [ ] Frontend Next.js setup
- [ ] Frontend UI components (Shadcn)
- [ ] Frontend-backend integration

## License

Proprietary - Munero AI Platform
