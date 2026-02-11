"""
Chat API endpoints for AI-powered data analysis.
Orchestrates LLM Service (SQL generation) + SmartRender Service (visualization selection).
Returns complete ChatResponse with answer text, SQL, data, and chart configuration.
"""
import re
import csv
import io
import logging
import traceback
import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

from pydantic import BaseModel

from app.models import (
    ChatRequest, 
    ChatResponse, 
    ChartConfig, 
    DashboardFilters
)
from app.services.llm_service import LLMService, FILTER_PLACEHOLDER_TOKEN
from app.services.sql_safety import SQLSafetyError, validate_sql_safety
from app.services.smart_render import SmartRenderService
from app.core.config import settings
from app.core.logging_utils import (
    redact_filter_values_for_log,
    redact_params_for_log,
    redact_sql_for_log,
    short_sha256,
)
from app.core.export_tokens import ExportTokenError, make_export_token, verify_export_token
from app.core.database import engine, execute_query_df
from app.sql_rewrite import maybe_broaden_client_name_equals_to_contains, rewrite_order_type_literals


router = APIRouter()
logger = logging.getLogger(__name__)

_REDACTION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-]+"), r"\1 <redacted>"),
    (re.compile(r"(?i)\b(api[_-]?key)\s*[:=]\s*[^\s,;\]\)\}\"']+"), r"\1=<redacted>"),
    (re.compile(r"(?i)\b(authorization)\s*[:=]\s*[^\s,;\]\)\}\"']+"), r"\1=<redacted>"),
    (re.compile(r"(?i)\b(token)\s*[:=]\s*[^\s,;\]\)\}\"']+"), r"\1=<redacted>"),
    (re.compile(r"(?i)\b(secret)\s*[:=]\s*[^\s,;\]\)\}\"']+"), r"\1=<redacted>"),
    (re.compile(r"(?i)\b(password)\s*[:=]\s*[^\s,;\]\)\}\"']+"), r"\1=<redacted>"),
    (re.compile(r'(?is)("(?:prompt|message|input|sql_query)"\s*:\s*")[^"]*(")'), r'\1<redacted>\2'),
    (re.compile(r"(?is)\b(prompt|message|input|sql_query)\s*=\s*'[^']*'"), r"\1='<redacted>'"),
    (re.compile(r'(?is)\b(prompt|message|input|sql_query)\s*=\s*"[^"]*"'), r'\1="<redacted>"'),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "sk-<redacted>"),
]


def _new_correlation_id() -> str:
    return uuid.uuid4().hex[:8]


def _redact_log_text(text: str) -> str:
    if not text:
        return text
    redacted = text
    for pattern, replacement in _REDACTION_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def _log_exception(
    *,
    correlation_id: str,
    label: str,
    exc: Exception,
    prompt_text: Optional[str] = None,
    sql_text: Optional[str] = None,
    prompt_len: Optional[int] = None,
    prompt_sha: Optional[str] = None,
    sql_len: Optional[int] = None,
    sql_sha: Optional[str] = None,
) -> None:
    context_parts: list[str] = []
    if prompt_len is not None:
        context_parts.append(f"prompt_len={prompt_len}")
    if prompt_sha:
        context_parts.append(f"prompt_sha={prompt_sha}")
    if sql_len is not None:
        context_parts.append(f"sql_len={sql_len}")
    if sql_sha:
        context_parts.append(f"sql_sha={sql_sha}")
    context_str = f" ({', '.join(context_parts)})" if context_parts else ""

    logger.exception(
        "❌ [%s] %s%s exc_type=%s",
        correlation_id,
        label,
        context_str,
        type(exc).__name__,
        exc_info=False,
    )
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    if prompt_text:
        tb = tb.replace(prompt_text, "<prompt_redacted>")
    if sql_text:
        tb = tb.replace(sql_text, "<sql_redacted>")
    if settings.DEBUG:
        logger.debug("❌ [%s] traceback=%s", correlation_id, _redact_log_text(tb))


def _extract_dbapi_details(exc: Exception) -> tuple[str | None, str | None, str | None]:
    orig = getattr(exc, "orig", None)
    if isinstance(orig, Exception):
        orig_type = type(orig).__name__
        orig_sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
        orig_message = str(orig)
    else:
        orig_type = None
        orig_sqlstate = None
        orig_message = None

    if isinstance(orig_message, str) and len(orig_message) > 500:
        orig_message = orig_message[:500] + "…"

    return orig_type, orig_sqlstate, orig_message


# ============================================================================
# EXPORT CSV REQUEST MODEL
# ============================================================================

class ExportCSVRequest(BaseModel):
    """Request model for CSV export endpoint."""
    sql_query: str
    filters: Optional[DashboardFilters] = None
    export_token: Optional[str] = None
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
def chat_with_data(request: ChatRequest):
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
    correlation_id = _new_correlation_id()
    prompt_text = request.message or ""
    prompt_len = len(prompt_text)
    prompt_sha = short_sha256(prompt_text)
    debug_enabled = bool(settings.DEBUG)
    debug_log_prompts = bool(settings.DEBUG and settings.DEBUG_LOG_PROMPTS)
    
    logger.info(
        "📨 Chat request received (id=%s, prompt_len=%s, prompt_sha=%s, conversation_id=%s)",
        correlation_id,
        prompt_len,
        prompt_sha,
        request.conversation_id,
    )
    
    llm_service = get_llm_service()
    smart_render_service = get_smart_render_service()
    
    # Get filters (use defaults if None)
    filters = request.filters or DashboardFilters()
    if debug_enabled:
        logger.debug("📨 [%s] filters=%s", correlation_id, redact_filter_values_for_log(filters))
        if debug_log_prompts:
            logger.debug("📨 [%s] prompt=%s", correlation_id, _redact_log_text(prompt_text))
    
    try:
        # =====================================================================
        # STEP 1: Generate SQL using LLM Service
        # =====================================================================
        if debug_enabled:
            logger.debug("🤖 [%s] Step 1: generating SQL from natural language", correlation_id)
        
        try:
            sql_template = llm_service.generate_sql(request.message, filters)
            sql_query, sql_params = llm_service.inject_filters_into_sql(sql_template, filters)
            sql_query, norm_warnings = rewrite_order_type_literals(sql_query)
            warnings.extend(norm_warnings)
            logger.info("✅ [%s] SQL generated (%s)", correlation_id, redact_sql_for_log(sql_query))
            if debug_log_prompts:
                logger.debug(
                    "✅ [%s] sql=%s params=%s",
                    correlation_id,
                    redact_sql_for_log(sql_query, include_prefix=True),
                    redact_params_for_log(sql_params),
                )
        except ValueError as e:
            _log_exception(
                correlation_id=correlation_id,
                label="Filter injection error",
                exc=e,
                prompt_text=prompt_text,
                prompt_len=prompt_len,
                prompt_sha=prompt_sha,
            )
            return ChatResponse(
                answer_text="I couldn't generate a safe query for your request. Please try rephrasing it.",
                sql_query=None,
                data=None,
                chart_config=None,
                row_count=0,
                warnings=[],
                error="Invalid request.",
            )
        except TimeoutError as e:
            _log_exception(
                correlation_id=correlation_id,
                label="LLM timeout",
                exc=e,
                prompt_text=prompt_text,
                prompt_len=prompt_len,
                prompt_sha=prompt_sha,
            )
            return ChatResponse(
                answer_text="The AI took too long to respond. Please try a simpler question.",
                sql_query=None,
                data=None,
                chart_config=None,
                row_count=0,
                warnings=["LLM request timed out"],
                error="Request timed out.",
            )
        except Exception as e:
            _log_exception(
                correlation_id=correlation_id,
                label="LLM error",
                exc=e,
                prompt_text=prompt_text,
                prompt_len=prompt_len,
                prompt_sha=prompt_sha,
            )
            return ChatResponse(
                answer_text="I couldn't understand your question. Please try rephrasing it.",
                sql_query=None,
                data=None,
                chart_config=None,
                row_count=0,
                warnings=[],
                error="SQL generation failed."
            )

        # =====================================================================
        # SQL SAFETY VALIDATION
        # =====================================================================
        try:
            validate_sql_safety(sql_query)
        except SQLSafetyError as e:
            _log_exception(
                correlation_id=correlation_id,
                label="Unsafe SQL blocked",
                exc=e,
                prompt_text=prompt_text,
                sql_text=sql_query,
                prompt_len=prompt_len,
                prompt_sha=prompt_sha,
                sql_len=len(sql_query) if sql_query else 0,
                sql_sha=short_sha256(sql_query) if sql_query else None,
            )
            logger.warning("🚫 [%s] Unsafe SQL blocked (reason=%s)", correlation_id, str(e))
            return ChatResponse(
                answer_text="I couldn't generate a safe read-only query for your request. Please try rephrasing it.",
                sql_query=None,
                data=None,
                chart_config=None,
                row_count=0,
                warnings=["Unsafe SQL blocked"],
                error="Unsafe SQL blocked.",
            )
        
        # =====================================================================
        # STEP 2: Execute SQL Query
        # =====================================================================
        if debug_enabled:
            logger.debug("🔍 [%s] Step 2: executing SQL query (%s)", correlation_id, redact_sql_for_log(sql_query))
        
        try:
            df = llm_service.execute_sql(sql_query, params=sql_params)
            row_count = len(df)
            logger.info("✅ [%s] SQL executed (rows=%s, cols=%s)", correlation_id, row_count, len(df.columns))
            if getattr(df, "attrs", {}).get("truncated"):
                warnings.append(f"Results truncated to {settings.MAX_DISPLAY_ROWS} rows")

            if df.empty:
                rewritten = maybe_broaden_client_name_equals_to_contains(
                    sql_query,
                    db_dialect=settings.db_dialect,
                    params=sql_params,
                )
                if rewritten is not None:
                    rewritten_sql, rewritten_params, rewritten_warning = rewritten
                    try:
                        validate_sql_safety(rewritten_sql)
                        df_retry = llm_service.execute_sql(rewritten_sql, params=rewritten_params)
                        if not df_retry.empty:
                            df = df_retry
                            sql_query = rewritten_sql
                            sql_params = rewritten_params
                            row_count = len(df)
                            warnings.append(rewritten_warning)
                            logger.info(
                                "✅ [%s] SQL re-executed after broadening client match (rows=%s, cols=%s, sql=%s)",
                                correlation_id,
                                row_count,
                                len(df.columns),
                                redact_sql_for_log(sql_query),
                            )
                            if getattr(df, "attrs", {}).get("truncated"):
                                warnings.append(f"Results truncated to {settings.MAX_DISPLAY_ROWS} rows")
                    except SQLSafetyError as rewrite_exc:
                        logger.warning(
                            "🚫 [%s] Client match rewrite blocked by safety (reason=%s)",
                            correlation_id,
                            str(rewrite_exc),
                        )
                    except Exception as rewrite_exc:
                        logger.warning(
                            "⚠️ [%s] Client match rewrite failed (exc_type=%s)",
                            correlation_id,
                            type(rewrite_exc).__name__,
                        )
        except TimeoutError as e:
            _log_exception(
                correlation_id=correlation_id,
                label="SQL timeout",
                exc=e,
                prompt_text=prompt_text,
                sql_text=sql_query,
                prompt_len=prompt_len,
                prompt_sha=prompt_sha,
                sql_len=len(sql_query) if sql_query else 0,
                sql_sha=short_sha256(sql_query) if sql_query else None,
            )
            return ChatResponse(
                answer_text="The query took too long to execute. Try narrowing your date range or adding filters.",
                sql_query=sql_query,
                data=None,
                chart_config=None,
                row_count=0,
                warnings=["SQL query timed out"],
                error="Request timed out.",
            )
        except SQLAlchemyError as e:
            _log_exception(
                correlation_id=correlation_id,
                label="SQL execution error",
                exc=e,
                prompt_text=prompt_text,
                sql_text=sql_query,
                prompt_len=prompt_len,
                prompt_sha=prompt_sha,
                sql_len=len(sql_query) if sql_query else 0,
                sql_sha=short_sha256(sql_query) if sql_query else None,
            )
            dbapi_type, sqlstate, dbapi_message = _extract_dbapi_details(e)
            logger.error(
                "❌ [%s] SQL execution failed (dbapi_type=%s, sqlstate=%s, message=%s, sql=%s, params=%s)",
                correlation_id,
                dbapi_type,
                sqlstate,
                dbapi_message,
                redact_sql_for_log(sql_query),
                redact_params_for_log(sql_params or {}),
            )

            error_msg = dbapi_message or str(getattr(e, "orig", e))
            error_lower = error_msg.lower()

            # Detect Postgres server-side statement timeout (distinct from our client-side TimeoutError)
            if "statement timeout" in error_lower or "canceling statement due to statement timeout" in error_lower:
                return ChatResponse(
                    answer_text="The query took too long to execute. Try narrowing your date range or adding filters.",
                    sql_query=sql_query,
                    data=None,
                    chart_config=None,
                    row_count=0,
                    warnings=["SQL query timed out"],
                    error="Request timed out.",
                )

            repair_max = max(0, int(getattr(settings, "LLM_SQL_REPAIR_MAX_ATTEMPTS", 0) or 0))
            repair_succeeded = False
            if repair_max > 0:
                for attempt in range(1, repair_max + 1):
                    try:
                        injected_predicate, _ = llm_service.build_filter_predicate(filters)
                        repaired_template = llm_service.repair_sql_template(
                            question=request.message,
                            filters=filters,
                            failed_sql_template=sql_template,
                            injected_predicate=injected_predicate,
                            db_error=(dbapi_message or "Database execution error"),
                        )
                        repaired_query, repaired_params = llm_service.inject_filters_into_sql(repaired_template, filters)
                        repaired_query, norm_warnings = rewrite_order_type_literals(repaired_query)
                        warnings.extend(norm_warnings)
                        validate_sql_safety(repaired_query)

                        sql_query = repaired_query
                        sql_params = repaired_params
                        df = llm_service.execute_sql(repaired_query, params=repaired_params)
                        row_count = len(df)
                        warnings.append("Auto-repaired SQL after initial failure")
                        if getattr(df, "attrs", {}).get("truncated"):
                            warnings.append(f"Results truncated to {settings.MAX_DISPLAY_ROWS} rows")
                        logger.info(
                            "✅ [%s] SQL auto-repair succeeded (attempt=%s, rows=%s, cols=%s)",
                            correlation_id,
                            attempt,
                            row_count,
                            len(df.columns),
                        )
                        repair_succeeded = True
                        break
                    except SQLSafetyError as repair_exc:
                        _log_exception(
                            correlation_id=correlation_id,
                            label="SQL auto-repair blocked by safety",
                            exc=repair_exc,
                            prompt_text=prompt_text,
                            sql_text=sql_query,
                            prompt_len=prompt_len,
                            prompt_sha=prompt_sha,
                            sql_len=len(sql_query) if sql_query else 0,
                            sql_sha=short_sha256(sql_query) if sql_query else None,
                        )
                        logger.warning(
                            "🚫 [%s] SQL auto-repair blocked by safety (reason=%s)",
                            correlation_id,
                            str(repair_exc),
                        )
                        break
                    except TimeoutError as repair_exc:
                        _log_exception(
                            correlation_id=correlation_id,
                            label="SQL auto-repair timed out",
                            exc=repair_exc,
                            prompt_text=prompt_text,
                            sql_text=sql_query,
                            prompt_len=prompt_len,
                            prompt_sha=prompt_sha,
                            sql_len=len(sql_query) if sql_query else 0,
                            sql_sha=short_sha256(sql_query) if sql_query else None,
                        )
                        break
                    except Exception as repair_exc:
                        _log_exception(
                            correlation_id=correlation_id,
                            label="SQL auto-repair attempt failed",
                            exc=repair_exc,
                            prompt_text=prompt_text,
                            sql_text=sql_query,
                            prompt_len=prompt_len,
                            prompt_sha=prompt_sha,
                            sql_len=len(sql_query) if sql_query else 0,
                            sql_sha=short_sha256(sql_query) if sql_query else None,
                        )
                        logger.warning(
                            "⚠️ [%s] SQL auto-repair attempt failed (attempt=%s, exc_type=%s)",
                            correlation_id,
                            attempt,
                            type(repair_exc).__name__,
                        )

            if repair_succeeded:
                # Proceed to Step 3 using the repaired SQL results.
                pass
            else:
                # Provide helpful feedback for common errors
                if "no such column" in error_lower or ("column" in error_lower and "does not exist" in error_lower):
                    hint = "The query referenced a column that doesn't exist."
                elif "no such table" in error_lower or ("relation" in error_lower and "does not exist" in error_lower):
                    hint = "The query referenced a table that doesn't exist."
                elif (
                    "function round" in error_lower and "double precision" in error_lower
                ) or "round(double precision, integer)" in error_lower:
                    hint = (
                        "Postgres requires numeric for ROUND(x, 2). Cast the SUM to numeric, e.g. "
                        "ROUND(SUM(...)::numeric, 2)."
                    )
                elif (
                    "operator does not exist" in error_lower
                    or "function sum" in error_lower
                    or "could not cast" in error_lower
                ):
                    hint = (
                        "There was a type mismatch in the query. Some numeric/date fields may be stored as text "
                        "and require casting."
                    )
                elif "syntax error" in error_lower:
                    hint = "There was a syntax error in the generated SQL."
                else:
                    hint = "There was an issue with the generated query."

                return ChatResponse(
                    answer_text=f"I generated a query but it had an error. {hint} Please try rephrasing your question.",
                    sql_query=sql_query,
                    data=None,
                    chart_config=None,
                    row_count=0,
                    warnings=warnings,
                    error="SQL execution failed.",
                )
        except Exception as e:
            _log_exception(
                correlation_id=correlation_id,
                label="Unexpected SQL execution error",
                exc=e,
                prompt_text=prompt_text,
                sql_text=sql_query,
                prompt_len=prompt_len,
                prompt_sha=prompt_sha,
                sql_len=len(sql_query) if sql_query else 0,
                sql_sha=short_sha256(sql_query) if sql_query else None,
            )
            return ChatResponse(
                answer_text="Something went wrong while running the query. Please try again.",
                sql_query=sql_query,
                data=None,
                chart_config=None,
                row_count=0,
                warnings=[],
                error="SQL execution failed."
            )
        
        # =====================================================================
        # STEP 3: Determine Visualization with SmartRender
        # =====================================================================
        if debug_enabled:
            logger.debug("📊 [%s] Step 3: determining optimal visualization", correlation_id)
        
        chart_config = smart_render_service.determine_chart_type(df, request.message)
        if debug_enabled:
            logger.debug(
                "✅ [%s] chart type=%s orientation=%s",
                correlation_id,
                chart_config.type,
                chart_config.orientation,
            )
        
        # =====================================================================
        # STEP 4: Prepare Data for JSON Response
        # =====================================================================
        if debug_enabled:
            logger.debug("📦 [%s] Step 4: preparing data for response", correlation_id)
        
        data_list, render_warnings = smart_render_service.prepare_data_for_chart(
            df, chart_config, request.message
        )
        warnings.extend(render_warnings)
        
        if render_warnings:
            logger.warning("⚠️ [%s] render warnings=%s", correlation_id, render_warnings)
        
        # =====================================================================
        # STEP 5: Generate Answer Text
        # =====================================================================
        if debug_enabled:
            logger.debug("💬 [%s] Step 5: generating answer text", correlation_id)
        
        answer_text = smart_render_service.format_answer_text(df, request.message, chart_config)
        logger.info(
            "✅ [%s] answer generated (answer_len=%s, answer_sha=%s)",
            correlation_id,
            len(answer_text or ""),
            short_sha256(answer_text or ""),
        )
        if debug_log_prompts:
            logger.debug("✅ [%s] answer=%s", correlation_id, _redact_log_text(answer_text))
        
        # =====================================================================
        # STEP 6: Return Complete Response
        # =====================================================================
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info("✅ [%s] chat completed in %sms", correlation_id, round(elapsed_ms, 0))

        export_token: str | None = None
        signing_secret = (settings.EXPORT_SIGNING_SECRET or "").strip()
        if signing_secret:
            try:
                export_token = make_export_token(
                    secret=signing_secret,
                    sql_query=sql_query,
                    filters=filters.model_dump(mode="json"),
                    ttl_s=int(settings.EXPORT_TOKEN_TTL_S),
                )
            except Exception as token_exc:
                logger.warning(
                    "⚠️ [%s] Failed to generate export token (exc_type=%s)",
                    correlation_id,
                    type(token_exc).__name__,
                )
        
        return ChatResponse(
            answer_text=answer_text,
            sql_query=sql_query,
            export_token=export_token,
            data=data_list,
            chart_config=chart_config,
            row_count=row_count,
            warnings=warnings,
            error=None
        )
        
    except Exception as e:
        _log_exception(
            correlation_id=correlation_id,
            label="Unexpected error in chat endpoint",
            exc=e,
            prompt_text=prompt_text,
            prompt_len=prompt_len,
            prompt_sha=prompt_sha,
        )
        
        return ChatResponse(
            answer_text="An unexpected error occurred. Please try again.",
            sql_query=None,
            data=None,
            chart_config=None,
            row_count=0,
            warnings=[],
            error="Unexpected error."
        )


@router.get("/health")
async def chat_health():
    """
    Health check endpoint for AI chat service.
    Checks hosted LLM connectivity and model availability.
    
    **Response**:
    ```json
    {
        "status": "healthy",
        "llm_available": true,
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "message": "LLM is reachable and model is available"
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
                "provider": llm_service.provider,
                "model": llm_service.model,
                "base_url": llm_service.base_url,
                "message": "LLM is reachable and model is available"
            }
        else:
            return {
                "status": "degraded",
                "llm_available": False,
                "provider": llm_service.provider,
                "model": llm_service.model,
                "base_url": llm_service.base_url,
                "message": "LLM is not reachable or is not configured.",
                "hint": "Set LLM_API_KEY (or GEMINI_API_KEY) and confirm outbound HTTPS is allowed."
            }
    except Exception as e:
        correlation_id = _new_correlation_id()
        _log_exception(
            correlation_id=correlation_id,
            label="Health check error",
            exc=e,
        )
        return {
            "status": "unhealthy",
            "llm_available": False,
            "provider": llm_service.provider,
            "model": llm_service.model,
            "base_url": llm_service.base_url,
            "error": "Health check failed.",
            "message": "Cannot reach LLM provider.",
            "hint": "Confirm LLM_API_KEY is set and the service can reach the LLM API."
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
                "error": "LLM not available",
                "hint": "Set LLM_API_KEY (or GEMINI_API_KEY) and confirm outbound HTTPS is allowed."
            }
        
        return {
            "status": "ok",
            "llm_available": True,
            "provider": llm_service.provider,
            "model": llm_service.model,
            "base_url": llm_service.base_url,
            "message": "Chat API is ready"
        }
    except Exception as e:
        correlation_id = _new_correlation_id()
        _log_exception(
            correlation_id=correlation_id,
            label="Test endpoint error",
            exc=e,
        )
        return {
            "status": "error",
            "llm_available": False,
            "error": "Test failed.",
            "hint": "Confirm LLM_API_KEY is set and the LLM API is reachable."
        }


@router.post("/export-csv")
def export_csv(request: ExportCSVRequest):
    """
    Export SQL query results as CSV.
    
    Removes any existing LIMIT clause and adds a safety cap of 10,000 rows.
    Returns streaming CSV response for download.
    
    **Request Body**:
    ```json
    {
        "sql_query": "SELECT product_name, SUM(revenue) as revenue FROM fact_orders GROUP BY product_name",
        "filters": { "start_date": "2025-01-01", "end_date": "2025-12-31", "countries": [] },
        "filename": "export.csv"
    }
    ```
    
    **Response**: CSV file download
    """
    try:
        correlation_id = _new_correlation_id()
        llm_service = get_llm_service()
        filters = request.filters or DashboardFilters()
        debug_enabled = bool(settings.DEBUG)
        debug_log_prompts = bool(settings.DEBUG and settings.DEBUG_LOG_PROMPTS)
        signing_secret = (settings.EXPORT_SIGNING_SECRET or "").strip()

        logger.info(
            "📤 Export CSV request received (id=%s, sql=%s)",
            correlation_id,
            redact_sql_for_log(request.sql_query),
        )
        if debug_enabled:
            logger.debug("📤 [%s] filters=%s", correlation_id, redact_filter_values_for_log(filters))
            if debug_log_prompts:
                logger.debug(
                    "📤 [%s] sql=%s",
                    correlation_id,
                    redact_sql_for_log(request.sql_query, include_prefix=True),
                )

        if not signing_secret:
            if not settings.DEBUG:
                raise HTTPException(
                    status_code=503,
                    detail="CSV export is not configured.",
                )
        else:
            try:
                verify_export_token(
                    secret=signing_secret,
                    token=request.export_token or "",
                    sql_query=request.sql_query,
                    filters=filters.model_dump(mode="json"),
                )
            except ExportTokenError as token_exc:
                logger.warning(
                    "🚫 Export CSV rejected (id=%s, reason=%s)",
                    correlation_id,
                    str(token_exc),
                )
                raise HTTPException(
                    status_code=403,
                    detail="Unauthorized export request.",
                )

        # 1. Remove existing LIMIT clause
        sql_query = re.sub(r'\bLIMIT\s+\d+\b', '', request.sql_query, flags=re.IGNORECASE)
        sql_query = sql_query.strip().rstrip(';')

        # 2. Ensure we have params for the injected placeholders
        placeholder_count = sql_query.count(FILTER_PLACEHOLDER_TOKEN)
        if placeholder_count == 1:
            try:
                sql_query, params = llm_service.inject_filters_into_sql(sql_query, filters)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        elif placeholder_count > 1:
            raise HTTPException(
                status_code=400,
                detail="Invalid SQL query: filters placeholder appears multiple times.",
            )
        else:
            _, params = llm_service.build_filter_predicate(filters)
            used_keys = set(re.findall(r'(?<!:):([A-Za-z_][A-Za-z0-9_]*)', sql_query))
            params = {k: v for k, v in params.items() if k in used_keys}
            missing = used_keys - set(params.keys())
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail="Missing required parameters to export this query.",
                )

        # 3. Add safety LIMIT of 10000
        sql_query = f"{sql_query} LIMIT 10000"

        # 4. Validate query safety (read-only, single statement)
        try:
            validate_sql_safety(sql_query)
        except SQLSafetyError as e:
            _log_exception(
                correlation_id=correlation_id,
                label="Unsafe SQL blocked in export-csv",
                exc=e,
                sql_text=sql_query,
                sql_len=len(sql_query) if sql_query else 0,
                sql_sha=short_sha256(sql_query) if sql_query else None,
            )
            raise HTTPException(status_code=400, detail="Unsafe SQL query.")

        # 5. Execute query
        df = execute_query_df(sql_query, conn=engine, params=params or None, max_rows=10000)
        
        # 6. Generate CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(df.columns.tolist())
        
        # Write data rows
        for _, row in df.iterrows():
            writer.writerow(row.tolist())
        
        csv_content = output.getvalue()
        output.close()
        
        # 7. Return as streaming response
        filename = request.filename or "export.csv"
        
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "text/csv"
            }
        )
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        _log_exception(
            correlation_id=correlation_id,
            label="SQL execution failed in export-csv",
            exc=e,
            sql_text=sql_query if "sql_query" in locals() else None,
            sql_len=len(sql_query) if "sql_query" in locals() else None,
            sql_sha=short_sha256(sql_query) if "sql_query" in locals() and sql_query else None,
        )
        raise HTTPException(status_code=400, detail="SQL execution failed.")
    except Exception as e:
        _log_exception(
            correlation_id=correlation_id,
            label="Export failed",
            exc=e,
        )
        raise HTTPException(status_code=500, detail="Export failed.")
