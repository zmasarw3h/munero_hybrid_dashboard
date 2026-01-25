"""
Chat API endpoints for AI-powered data analysis.
Orchestrates LLM Service (SQL generation) + SmartRender Service (visualization selection).
Returns complete ChatResponse with answer text, SQL, data, and chart configuration.
"""
import sqlite3
import re
import csv
import io
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import pandas as pd

from pydantic import BaseModel

from app.models import (
    ChatRequest, 
    ChatResponse, 
    ChartConfig, 
    DashboardFilters
)
from app.services.llm_service import LLMService, LLM_CONFIG, DB_PATH
from app.services.smart_render import SmartRenderService


router = APIRouter()


# ============================================================================
# EXPORT CSV REQUEST MODEL
# ============================================================================

class ExportCSVRequest(BaseModel):
    """Request model for CSV export endpoint."""
    sql_query: str
    filename: Optional[str] = "export.csv"

# Initialize services (singleton-like pattern)
_llm_service: Optional[LLMService] = None
_smart_render_service: Optional[SmartRenderService] = None


def get_llm_service() -> LLMService:
    """Get or create LLMService instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def get_smart_render_service() -> SmartRenderService:
    """Get or create SmartRenderService instance."""
    global _smart_render_service
    if _smart_render_service is None:
        _smart_render_service = SmartRenderService()
    return _smart_render_service


@router.post("/", response_model=ChatResponse)
async def chat_with_data(request: ChatRequest):
    """
    AI-powered natural language data analysis.
    
    **Process**:
    1. Takes user's question + current dashboard filters
    2. LLM Service: Generates SQL from natural language with filter injection
    3. Executes SQL against the database
    4. SmartRender Service: Determines optimal visualization
    5. Returns complete response with answer, SQL, data, and chart config

    **Request Body**:
    ```json
    {
        "message": "What are the top 5 products by revenue?",
        "filters": {
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "currency": "AED",
            "countries": ["United Arab Emirates"]
        },
        "conversation_id": "optional-session-id"
    }
    ```

    **Response**:
    ```json
    {
        "answer_text": "Here are your top 5 results:",
        "sql_query": "SELECT product_name, SUM(order_price_in_aed) as revenue FROM fact_orders...",
        "data": [{"product_name": "Gift Card", "revenue": 382868.92}, ...],
        "chart_config": {
            "type": "bar",
            "x_column": "product_name",
            "y_column": "revenue",
            "orientation": "horizontal",
            "title": "Top 5 Products by Revenue"
        },
        "row_count": 5,
        "warnings": [],
        "error": null
    }
    ```

    **Example Queries**:
    - "What are the top 5 products by revenue?"
    - "Show monthly revenue trend"
    - "Which country has the highest sales?"
    - "What is total revenue?"
    - "Compare Apple vs Samsung by orders"
    """
    start_time = datetime.now()
    warnings: list[str] = []
    
    print(f"\n{'='*60}")
    print(f"📨 Chat Request: '{request.message}'")
    print(f"   Timestamp: {start_time.isoformat()}")
    print(f"{'='*60}")
    
    llm_service = get_llm_service()
    smart_render_service = get_smart_render_service()
    
    # Get filters (use defaults if None)
    filters = request.filters or DashboardFilters()
    
    try:
        # =====================================================================
        # STEP 1: Generate SQL using LLM Service
        # =====================================================================
        print("🤖 Step 1: Generating SQL from natural language...")
        
        try:
            sql_query = llm_service.generate_sql(request.message, filters)
            print(f"   ✅ SQL generated: {sql_query[:100]}...")
        except TimeoutError as e:
            print(f"   ⏱️ LLM timeout: {e}")
            return ChatResponse(
                answer_text="The AI took too long to respond. Please try a simpler question.",
                sql_query=None,
                data=None,
                chart_config=None,
                row_count=0,
                warnings=["LLM request timed out"],
                error=str(e)
            )
        except Exception as e:
            print(f"   ❌ LLM error: {e}")
            return ChatResponse(
                answer_text="I couldn't understand your question. Please try rephrasing it.",
                sql_query=None,
                data=None,
                chart_config=None,
                row_count=0,
                warnings=[],
                error=f"SQL generation failed: {str(e)}"
            )
        
        # =====================================================================
        # STEP 2: Execute SQL Query
        # =====================================================================
        print("🔍 Step 2: Executing SQL query...")
        
        try:
            df = llm_service.execute_sql(sql_query)
            row_count = len(df)
            print(f"   ✅ Query returned {row_count} rows, {len(df.columns)} columns")
        except TimeoutError as e:
            print(f"   ⏱️ SQL timeout: {e}")
            return ChatResponse(
                answer_text="The query took too long to execute. Try narrowing your date range or adding filters.",
                sql_query=sql_query,
                data=None,
                chart_config=None,
                row_count=0,
                warnings=["SQL query timed out"],
                error=str(e)
            )
        except sqlite3.OperationalError as e:
            print(f"   ❌ SQL error: {e}")
            error_msg = str(e)
            # Provide helpful feedback for common errors
            if "no such column" in error_msg.lower():
                hint = "The query referenced a column that doesn't exist."
            elif "no such table" in error_msg.lower():
                hint = "The query referenced a table that doesn't exist."
            else:
                hint = "There was an issue with the generated query."
            
            return ChatResponse(
                answer_text=f"I generated a query but it had an error. {hint} Please try rephrasing your question.",
                sql_query=sql_query,
                data=None,
                chart_config=None,
                row_count=0,
                warnings=[],
                error=f"SQL execution failed: {error_msg}"
            )
        except Exception as e:
            print(f"   ❌ Unexpected SQL error: {e}")
            return ChatResponse(
                answer_text="Something went wrong while running the query. Please try again.",
                sql_query=sql_query,
                data=None,
                chart_config=None,
                row_count=0,
                warnings=[],
                error=f"SQL execution failed: {str(e)}"
            )
        
        # =====================================================================
        # STEP 3: Determine Visualization with SmartRender
        # =====================================================================
        print("📊 Step 3: Determining optimal visualization...")
        
        chart_config = smart_render_service.determine_chart_type(df, request.message)
        print(f"   ✅ Chart type: {chart_config.type} (orientation: {chart_config.orientation})")
        
        # =====================================================================
        # STEP 4: Prepare Data for JSON Response
        # =====================================================================
        print("📦 Step 4: Preparing data for response...")
        
        data_list, render_warnings = smart_render_service.prepare_data_for_chart(df, chart_config)
        warnings.extend(render_warnings)
        
        if render_warnings:
            print(f"   ⚠️ Warnings: {render_warnings}")
        
        # =====================================================================
        # STEP 5: Generate Answer Text
        # =====================================================================
        print("💬 Step 5: Generating answer text...")
        
        answer_text = smart_render_service.format_answer_text(df, request.message, chart_config)
        print(f"   ✅ Answer: {answer_text}")
        
        # =====================================================================
        # STEP 6: Return Complete Response
        # =====================================================================
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        print(f"{'='*60}")
        print(f"✅ Chat completed in {elapsed_ms:.0f}ms")
        print(f"{'='*60}\n")
        
        return ChatResponse(
            answer_text=answer_text,
            sql_query=sql_query,
            data=data_list,
            chart_config=chart_config,
            row_count=row_count,
            warnings=warnings,
            error=None
        )
        
    except Exception as e:
        print(f"❌ Unexpected error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        
        return ChatResponse(
            answer_text="An unexpected error occurred. Please try again.",
            sql_query=None,
            data=None,
            chart_config=None,
            row_count=0,
            warnings=[],
            error=str(e)
        )


@router.get("/health")
async def chat_health():
    """
    Health check endpoint for AI chat service.
    Checks Ollama connectivity and LLM model availability.
    
    **Response**:
    ```json
    {
        "status": "healthy",
        "llm_available": true,
        "model": "qwen2.5-coder:7b",
        "base_url": "http://localhost:11434",
        "message": "Ollama is running and model is available"
    }
    ```
    """
    llm_service = get_llm_service()
    
    try:
        is_connected = llm_service.check_connection()
        
        if is_connected:
            return {
                "status": "healthy",
                "llm_available": True,
                "model": llm_service.model,
                "base_url": llm_service.base_url,
                "message": "Ollama is running and model is available"
            }
        else:
            return {
                "status": "degraded",
                "llm_available": False,
                "model": llm_service.model,
                "base_url": llm_service.base_url,
                "message": f"Ollama is running but model '{llm_service.model}' may not be loaded",
                "hint": f"Run: ollama pull {llm_service.model}"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "llm_available": False,
            "model": llm_service.model,
            "base_url": llm_service.base_url,
            "error": str(e),
            "message": "Cannot connect to Ollama",
            "hint": "Make sure Ollama is running: ollama serve"
        }


@router.get("/test")
def test_chat():
    """
    Quick test endpoint to verify the chat API is working.
    Makes a simple query to test the full pipeline.
    """
    llm_service = get_llm_service()
    
    try:
        # Check connection first
        if not llm_service.check_connection():
            return {
                "status": "error",
                "llm_available": False,
                "error": "Ollama not available",
                "hint": "Make sure Ollama is running: ollama serve"
            }
        
        return {
            "status": "ok",
            "llm_available": True,
            "model": llm_service.model,
            "base_url": llm_service.base_url,
            "message": "Chat API is ready"
        }
    except Exception as e:
        return {
            "status": "error",
            "llm_available": False,
            "error": str(e),
            "hint": "Make sure Ollama is running: ollama serve"
        }


@router.post("/export-csv")
async def export_csv(request: ExportCSVRequest):
    """
    Export SQL query results as CSV.
    
    Removes any existing LIMIT clause and adds a safety cap of 10,000 rows.
    Returns streaming CSV response for download.
    
    **Request Body**:
    ```json
    {
        "sql_query": "SELECT product_name, SUM(revenue) as revenue FROM fact_orders GROUP BY product_name",
        "filename": "export.csv"
    }
    ```
    
    **Response**: CSV file download
    """
    try:
        # 1. Remove existing LIMIT clause
        sql_query = re.sub(r'\bLIMIT\s+\d+\b', '', request.sql_query, flags=re.IGNORECASE)
        
        # 2. Add safety LIMIT of 10000
        sql_query = sql_query.strip().rstrip(';')
        sql_query = f"{sql_query} LIMIT 10000"
        
        # 3. Execute query
        conn = sqlite3.connect(str(DB_PATH))
        df = pd.read_sql_query(sql_query, conn)
        conn.close()
        
        # 4. Generate CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(df.columns.tolist())
        
        # Write data rows
        for _, row in df.iterrows():
            writer.writerow(row.tolist())
        
        csv_content = output.getvalue()
        output.close()
        
        # 5. Return as streaming response
        filename = request.filename or "export.csv"
        
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "text/csv"
            }
        )
        
    except sqlite3.OperationalError as e:
        raise HTTPException(status_code=400, detail=f"SQL execution failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
