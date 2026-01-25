"""
LLM Engine for AI-powered SQL generation and analysis.
Handles natural language to SQL conversion, query execution, and visualization recommendations.
Also includes intent detection for routing to Driver Analysis endpoint.
"""
import re
import pandas as pd
import httpx
from typing import Tuple, Optional, Literal, cast, Dict, Any
from datetime import date, timedelta
from langchain_ollama import ChatOllama
from app.core.database import get_data
from app.models import DashboardFilters, ChartResponse, ChartPoint, AIAnalysisResponse

# Configuration
LLM_MODEL = "qwen2.5-coder:7b"  # Or your preferred local model
BASE_URL = "http://localhost:11434"
LLM_TEMPERATURE = 0

# Intent Detection Patterns
DIAGNOSTIC_PATTERNS = [
    r"why did",
    r"why is",
    r"why are",
    r"why was",
    r"why were",
    r"what caused",
    r"what's causing",
    r"explain the",
    r"explain why",
    r"reason for",
    r"reasons for",
    r"what happened to",
    r"what drove",
    r"what's driving",
    r"what is driving",
    r"analyze the change",
    r"analyze the drop",
    r"analyze the increase",
    r"understand the",
]


def detect_intent(question: str) -> Literal["data_query", "driver_analysis"]:
    """
    Detects whether a question is a data query or a diagnostic "why" question.

    Args:
        question: User's natural language question

    Returns:
        "driver_analysis" if the question is asking "why did X change?"
        "data_query" for regular data retrieval questions

    Examples:
        "Why did revenue drop this month?" -> "driver_analysis"
        "Show me top 10 clients by revenue" -> "data_query"
        "What caused the spike in December?" -> "driver_analysis"
        "What is total revenue?" -> "data_query"
    """
    question_lower = question.lower().strip()

    for pattern in DIAGNOSTIC_PATTERNS:
        if re.search(pattern, question_lower):
            print(f"🎯 Intent detected: driver_analysis (matched: '{pattern}')")
            return "driver_analysis"

    print(f"🎯 Intent detected: data_query")
    return "data_query"


def extract_metric_from_question(question: str) -> Literal["revenue", "orders", "margin", "aov"]:
    """
    Extracts the metric being asked about from a diagnostic question.

    Args:
        question: User's question

    Returns:
        The metric type: revenue, orders, margin, or aov
    """
    question_lower = question.lower()

    # Check for specific metrics
    if any(term in question_lower for term in ["order", "orders", "volume"]):
        return "orders"
    elif any(term in question_lower for term in ["margin", "profit", "profitability"]):
        return "margin"
    elif any(term in question_lower for term in ["aov", "average order value", "order value"]):
        return "aov"
    else:
        # Default to revenue for sales, revenue, income, etc.
        return "revenue"


def get_comparison_periods(filters: DashboardFilters) -> tuple[dict, dict]:
    """
    Determines the current and prior periods for driver analysis based on filters.

    If user has a date range in filters, uses that as current period
    and calculates a comparable prior period.

    Returns:
        tuple of (current_period, prior_period) dicts with start/end dates
    """
    today = date.today()

    if filters.start_date and filters.end_date:
        # Use filter dates as current period
        current_start = filters.start_date
        current_end = filters.end_date

        # Calculate period length
        period_length = (current_end - current_start).days

        # Prior period is same length, immediately before current
        prior_end = current_start - timedelta(days=1)
        prior_start = prior_end - timedelta(days=period_length)
    else:
        # Default: Current month vs prior month
        current_start = today.replace(day=1)
        current_end = today

        # Prior month
        prior_end = current_start - timedelta(days=1)
        prior_start = prior_end.replace(day=1)

    return (
        {"start": str(current_start), "end": str(current_end)},
        {"start": str(prior_start), "end": str(prior_end)}
    )


async def call_driver_analysis(
    metric: str,
    current_period: dict,
    prior_period: dict,
    filters: Optional[DashboardFilters] = None
) -> Dict[str, Any]:
    """
    Calls the driver analysis endpoint.

    Args:
        metric: The metric to analyze (revenue, orders, margin, aov)
        current_period: Dict with start/end dates
        prior_period: Dict with start/end dates
        filters: Optional dashboard filters

    Returns:
        Driver analysis response as a dictionary
    """
    request_body = {
        "metric": metric,
        "current_period": current_period,
        "prior_period": prior_period,
        "dimensions": ["client_name", "product_brand", "client_country", "order_type"],
        "top_n": 5
    }

    if filters:
        request_body["filters"] = filters.model_dump()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/analyze/drivers",
            json=request_body,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


def generate_driver_narration(analysis: Dict[str, Any], question: str) -> str:
    """
    Generates a natural language explanation of the driver analysis results.
    Uses the LLM to create a clear, actionable narrative.

    Args:
        analysis: Driver analysis response dictionary
        question: Original user question

    Returns:
        Natural language explanation of the analysis
    """
    llm = get_llm()

    # Build driver summary text
    drivers_text = []
    for dim_key, drivers in analysis.get("drivers", {}).items():
        dim_name = dim_key.replace("by_", "").replace("_", " ").title()
        if drivers:
            top_driver = drivers[0]
            drivers_text.append(
                f"- {dim_name}: {top_driver['name']} ({top_driver['contribution_to_total_change']:.1f}% of change, delta: {top_driver['delta']:+,.2f})"
            )

    drivers_summary = "\n".join(drivers_text) if drivers_text else "No significant drivers identified."

    # Get primary and secondary drivers
    summary = analysis.get("summary", {})
    primary = summary.get("primary_driver", {})
    secondary = summary.get("secondary_driver", {})

    prompt = f"""You are a business analyst. Convert this variance analysis into a clear, actionable explanation.

USER QUESTION: "{question}"

VARIANCE ANALYSIS RESULTS:
- Metric: {analysis['metric']}
- Current Period Total: {analysis['current_total']:,.2f}
- Prior Period Total: {analysis['prior_total']:,.2f}
- Total Change: {analysis['total_change']:+,.2f} ({analysis['total_change_pct']:+.1f}%)
- Direction: {analysis['direction']}

TOP DRIVERS BY DIMENSION:
{drivers_summary}

PRIMARY DRIVER: {primary.get('entity', 'N/A')} ({primary.get('dimension', 'N/A')}) - {primary.get('contribution', 0):.1f}% of change
SECONDARY DRIVER: {secondary.get('entity', 'N/A')} ({secondary.get('dimension', 'N/A')}) - {secondary.get('contribution', 0):.1f}% of change

GUIDELINES:
1. Start with the headline: what changed and by how much
2. Identify the #1 driver (highest contribution %)
3. Mention 2-3 secondary drivers if significant (>10% contribution)
4. Note any positive offsetting factors
5. If one dimension dominates (e.g., single client = 80%), emphasize this
6. Keep it under 150 words
7. Use bullet points for clarity
8. Do NOT speculate on business reasons - stick to the data

Provide a clear summary:"""

    try:
        response = llm.invoke(prompt).content
        if isinstance(response, list):
            response = str(response[0]) if response else ""
        return str(response).strip()
    except Exception as e:
        # Fallback to simple summary
        return (
            f"{analysis['metric'].title()} {analysis['direction']}d by {analysis['total_change']:+,.2f} "
            f"({analysis['total_change_pct']:+.1f}%). "
            f"Primary driver: {primary.get('entity', 'Unknown')} "
            f"(contributed {primary.get('contribution', 0):.1f}% of the change)."
        )


def get_llm():
    """
    Initialize and return ChatOllama instance.
    """
    return ChatOllama(model=LLM_MODEL, base_url=BASE_URL, temperature=LLM_TEMPERATURE)


def get_sql_prompt(question: str, filters: DashboardFilters) -> str:
    """
    Constructs the prompt with Schema info AND Current Dashboard Context.
    
    Args:
        question: User's natural language question
        filters: Current dashboard filter state
        
    Returns:
        str: Complete prompt for SQL generation
    """
    # Convert active filters to text description AND SQL WHERE clauses
    context_parts = []
    where_clauses = ["is_test = 0"]  # Always filter out test data
    
    if filters.start_date:
        end_date_str = str(filters.end_date) if filters.end_date else 'present'
        context_parts.append(f"- Date range: {filters.start_date} to {end_date_str}")
        if filters.end_date:
            where_clauses.append(f"order_date BETWEEN '{filters.start_date}' AND '{filters.end_date}'")
        else:
            where_clauses.append(f"order_date >= '{filters.start_date}'")
    
    if filters.countries:
        context_parts.append(f"- Countries: {', '.join(filters.countries)}")
        country_list = "', '".join(filters.countries)
        where_clauses.append(f"client_country IN ('{country_list}')")
    
    if filters.brands:
        context_parts.append(f"- Brands: {', '.join(filters.brands)}")
        brand_list = "', '".join(filters.brands)
        where_clauses.append(f"product_brand IN ('{brand_list}')")
    
    if filters.clients:
        context_parts.append(f"- Clients: {', '.join(filters.clients)}")
        client_list = "', '".join(filters.clients)
        where_clauses.append(f"client_name IN ('{client_list}')")
    
    if filters.product_types:
        context_parts.append(f"- Product types: {', '.join(filters.product_types)}")
        type_list = "', '".join(filters.product_types)
        where_clauses.append(f"order_type IN ('{type_list}')")
    
    if filters.suppliers:
        context_parts.append(f"- Suppliers: {', '.join(filters.suppliers)}")
        supplier_list = "', '".join(filters.suppliers)
        where_clauses.append(f"supplier_name IN ('{supplier_list}')")
    
    context_str = "\n".join(context_parts) if context_parts else "- No active filters (analyzing all data)"
    where_clause_sql = " AND ".join(where_clauses)

    return f"""You are a SQLite expert for the 'Munero' sales database.

CURRENT DASHBOARD CONTEXT (User has these filters active):
{context_str}

REQUIRED WHERE CLAUSE (Include this in your query):
WHERE {where_clause_sql}

DATABASE SCHEMA:
- Table: fact_orders (denormalized - contains ALL transaction data)

KEY COLUMNS:
- order_number: Unique order ID (TEXT)
- order_date: Transaction date (TEXT, format: YYYY-MM-DD)
- order_price_in_aed: Revenue in AED (REAL)
- cogs_in_aed: Cost of goods sold in AED (REAL)
- quantity: Quantity ordered (INTEGER)
- client_name: Customer name (TEXT)
- client_country: Customer country code (TEXT, e.g., 'AE', 'SA')
- client_balance: Customer balance (REAL)
- product_name: Product name (TEXT)
- product_brand: Product brand (TEXT, e.g., 'Apple', 'Amazon', 'Google')
- product_sku: Product SKU (TEXT)
- order_type: Product category/type (TEXT, e.g., 'gift_cards', 'vouchers')
- supplier_name: Supplier name (TEXT)
- is_test: Test flag (INTEGER: 0=real, 1=test)

MUNERO BUSINESS LOGIC (Critical definitions):
1. 'Revenue' or 'Sales' = SUM(order_price_in_aed)
2. 'Profit' or 'Gross Profit' = SUM(order_price_in_aed - cogs_in_aed)
3. 'Margin' or 'Profit Margin' = (Revenue - COGS) / Revenue * 100
   - Formula: (SUM(order_price_in_aed) - SUM(cogs_in_aed)) / SUM(order_price_in_aed) * 100
   - Interpretation: >20% = High margin, 0-20% = Medium, <0% = Unprofitable
4. 'AOV' or 'Average Order Value' = Total Revenue / COUNT(DISTINCT order_number)
5. 'Market Share' = Entity Revenue / Total Revenue * 100
6. 'Product Type' or 'Category' = order_type column
7. 'Brand' = product_brand column
8. 'Client' or 'Customer' = client_name column

QUERY CONSTRUCTION RULES:
1. ALWAYS include: WHERE is_test = 0 (filter out test data)
2. ALWAYS include the dashboard filter WHERE clause shown above
3. For date grouping:
   - Daily: strftime('%Y-%m-%d', order_date)
   - Monthly: strftime('%Y-%m', order_date)
   - Yearly: strftime('%Y', order_date)
4. For aggregations, use COUNT(DISTINCT order_number) for order counts
5. For top N queries, use ORDER BY revenue DESC LIMIT N
6. Handle NULL COGS: Use COALESCE(cogs_in_aed, 0) if calculating profit
7. Round currency values: ROUND(SUM(order_price_in_aed), 2)

EXAMPLE QUERIES:
Q: "What's the total revenue?"
A: SELECT ROUND(SUM(order_price_in_aed), 2) as total_revenue FROM fact_orders WHERE {where_clause_sql}

Q: "Show top 5 clients by revenue"
A: SELECT client_name, ROUND(SUM(order_price_in_aed), 2) as revenue FROM fact_orders WHERE {where_clause_sql} GROUP BY client_name ORDER BY revenue DESC LIMIT 5

Q: "Which brands have negative margins?"
A: SELECT product_brand, ROUND(SUM(order_price_in_aed), 2) as revenue, ROUND(SUM(cogs_in_aed), 2) as cogs, ROUND((SUM(order_price_in_aed) - SUM(cogs_in_aed)) / SUM(order_price_in_aed) * 100, 2) as margin_pct FROM fact_orders WHERE {where_clause_sql} GROUP BY product_brand HAVING margin_pct < 0 ORDER BY margin_pct ASC

QUESTION: {question}

Return ONLY the raw SQL query. No markdown code blocks. No explanations. No extra text.

SQL:"""


def clean_sql_response(raw_response: str) -> str:
    """
    Clean LLM response to extract pure SQL.
    Removes markdown blocks, think tags, and extra text.
    
    Args:
        raw_response: Raw LLM output
        
    Returns:
        str: Cleaned SQL query
    """
    # Remove markdown code blocks
    sql = re.sub(r'```sql\s*', '', raw_response, flags=re.IGNORECASE)
    sql = re.sub(r'```\s*', '', sql)
    
    # Remove DeepSeek-R1 style <think> tags
    sql = re.sub(r'<think>.*?</think>', '', sql, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove common prefixes
    sql = re.sub(r'^(SQL:|Query:|SELECT)', 'SELECT', sql, flags=re.IGNORECASE)
    
    return sql.strip()


def determine_viz_type(df: pd.DataFrame, question: str = "") -> Tuple[str, str, str]:
    """
    Simplified port of 'smart_render' from app.py.
    Determines the best visualization type based on data characteristics.
    
    Args:
        df: Query result dataframe
        question: Original user question (for context)
        
    Returns:
        tuple: (chart_type, x_axis_column, y_axis_column)
    """
    if df.empty or len(df.columns) < 2:
        return "table", "", ""
    
    # Auto-detect column types
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    cat_cols = df.select_dtypes(exclude=['number']).columns.tolist()
    
    if not num_cols:
        return "table", "", ""
    
    # Determine label and value columns
    x_col = cat_cols[0] if cat_cols else df.columns[0]
    y_col = num_cols[0]
    
    # Data characteristics
    row_count = len(df)
    is_time_series = any(keyword in x_col.lower() for keyword in ['date', 'year', 'month', 'day', 'week'])
    
    # Check if question mentions specific chart types
    question_lower = question.lower()
    if 'pie' in question_lower or 'proportion' in question_lower:
        if row_count <= 10:
            return "pie", x_col, y_col
    
    # Decision logic
    if is_time_series:
        # Time series data → Line chart
        return "line", x_col, y_col
    elif row_count > 10 and len(num_cols) >= 2:
        # Multiple metrics with many rows → Scatter plot
        return "scatter", num_cols[0], num_cols[1]
    elif row_count <= 15:
        # Few categories → Bar chart
        return "bar", x_col, y_col
    else:
        # Too many rows → Table
        return "table", x_col, y_col


async def process_chat_query_async(question: str, filters: DashboardFilters) -> AIAnalysisResponse:
    """
    Async version of the main AI processing pipeline.
    Routes to either Driver Analysis or SQL generation based on intent detection.

    Args:
        question: User's natural language question
        filters: Current dashboard filter state

    Returns:
        AIAnalysisResponse: Complete AI analysis with answer, optional SQL, and visualization
    """
    print(f"🤖 AI Query: '{question}'")
    print(f"📊 Active Filters: {filters.model_dump()}")

    # Step 0: Intent Detection - Route to appropriate handler
    intent = detect_intent(question)

    if intent == "driver_analysis":
        print("🔍 Routing to Driver Analysis...")
        return await _handle_driver_analysis(question, filters)
    else:
        print("📝 Routing to SQL Generation...")
        return _handle_data_query(question, filters)


async def _handle_driver_analysis(question: str, filters: DashboardFilters) -> AIAnalysisResponse:
    """
    Handles diagnostic "why" questions using the Driver Analysis endpoint.

    Args:
        question: User's diagnostic question
        filters: Current dashboard filter state

    Returns:
        AIAnalysisResponse with narrated explanation of variance drivers
    """
    try:
        # Extract the metric being asked about
        metric = extract_metric_from_question(question)
        print(f"📊 Detected metric: {metric}")

        # Determine comparison periods
        current_period, prior_period = get_comparison_periods(filters)
        print(f"📅 Current period: {current_period}")
        print(f"📅 Prior period: {prior_period}")

        # Call the driver analysis endpoint
        analysis = await call_driver_analysis(
            metric=metric,
            current_period=current_period,
            prior_period=prior_period,
            filters=filters
        )
        print(f"✅ Driver analysis complete: {analysis['direction']} of {analysis['total_change_pct']:.1f}%")

        # Generate natural language narration
        narration = generate_driver_narration(analysis, question)

        # Build a summary for the response
        summary_parts = [narration]

        # Add period context
        period_note = f"\n\n*Analysis period: {current_period['start']} to {current_period['end']} vs {prior_period['start']} to {prior_period['end']}*"
        summary_parts.append(period_note)

        return AIAnalysisResponse(
            answer_text="\n".join(summary_parts),
            sql_generated=f"-- Driver Analysis (not SQL-based)\n-- Metric: {metric}\n-- Current: {current_period}\n-- Prior: {prior_period}",
            related_chart=None  # TODO: Add waterfall chart in future
        )

    except httpx.HTTPStatusError as e:
        print(f"❌ Driver Analysis API Error: {e}")
        return AIAnalysisResponse(
            answer_text=f"I tried to analyze the variance but encountered an API error: {str(e)}. Please ensure the backend is running and try again.",
            sql_generated="",
            related_chart=None
        )
    except Exception as e:
        print(f"❌ Driver Analysis Error: {e}")
        return AIAnalysisResponse(
            answer_text=f"I encountered an error while analyzing the drivers: {str(e)}",
            sql_generated="",
            related_chart=None
        )


def _handle_data_query(question: str, filters: DashboardFilters) -> AIAnalysisResponse:
    """
    Handles regular data queries using SQL generation.

    Args:
        question: User's data query question
        filters: Current dashboard filter state

    Returns:
        AIAnalysisResponse with SQL query results and visualization
    """
    llm = get_llm()
    
    # Step 1: Generate SQL
    print("⚙️  Step 1: Generating SQL...")
    prompt = get_sql_prompt(question, filters)
    
    try:
        raw_response = llm.invoke(prompt).content
        # Handle both string and list responses
        if isinstance(raw_response, list):
            raw_response = str(raw_response[0]) if raw_response else ""
        sql_query = clean_sql_response(str(raw_response))
        print(f"✅ Generated SQL: {sql_query[:100]}...")
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return AIAnalysisResponse(
            answer_text=f"I encountered an error generating the SQL query: {str(e)}",
            sql_generated="",
            related_chart=None
        )
    
    # Step 2: Execute SQL
    print("⚙️  Step 2: Executing SQL...")
    try:
        df = get_data(sql_query)
        print(f"✅ Query returned {len(df)} rows, {len(df.columns)} columns")
    except Exception as e:
        print(f"❌ SQL Execution Error: {e}")
        return AIAnalysisResponse(
            answer_text=f"I generated this SQL query but it failed to execute: ```sql\n{sql_query}\n```\n\nError: {str(e)}",
            sql_generated=sql_query,
            related_chart=None
        )

    if df.empty:
        print("⚠️  No data returned")
        return AIAnalysisResponse(
            answer_text="I couldn't find any data matching your request. Try adjusting your filters or rephrasing the question.",
            sql_generated=sql_query,
            related_chart=None
        )

    # Step 3: Determine Visualization
    print("⚙️  Step 3: Determining visualization type...")
    viz_type, x_axis, y_axis = determine_viz_type(df, question)
    print(f"✅ Visualization: {viz_type} (x={x_axis}, y={y_axis})")
    
    chart_resp = None
    if viz_type != "table":
        # Convert DataFrame to ChartPoints
        points = []
        try:
            for _, row in df.iterrows():
                label_val = str(row[x_axis]) if x_axis in df.columns else str(row.iloc[0])
                value_val = float(row[y_axis]) if y_axis in df.columns else float(row.iloc[1])
                points.append(ChartPoint(label=label_val, value=value_val))
            
            # Ensure viz_type is a valid literal
            valid_chart_types: list[Literal['bar', 'line', 'pie', 'scatter', 'dual_axis']] = ['bar', 'line', 'pie', 'scatter', 'dual_axis']
            chart_type: Literal['bar', 'line', 'pie', 'scatter', 'dual_axis'] = cast(
                Literal['bar', 'line', 'pie', 'scatter', 'dual_axis'],
                viz_type if viz_type in valid_chart_types else 'bar'
            )
            
            chart_resp = ChartResponse(
                title=f"Analysis: {question}",
                chart_type=chart_type,
                data=points[:50],  # Limit to 50 points for performance
                x_axis_label=x_axis.replace('_', ' ').title(),
                y_axis_label=y_axis.replace('_', ' ').title()
            )
            print(f"✅ Created chart with {len(points)} data points")
        except Exception as e:
            print(f"⚠️  Chart creation failed: {e}, falling back to table")
            viz_type = "table"

    # Step 4: Generate Natural Language Summary
    print("⚙️  Step 4: Generating natural language summary...")
    try:
        # Build filter context string for summary
        filter_context_parts = []
        if filters.start_date:
            filter_context_parts.append(f"Date: {filters.start_date} to {filters.end_date or 'present'}")
        if filters.countries:
            filter_context_parts.append(f"Countries: {', '.join(filters.countries)}")
        if filters.brands:
            filter_context_parts.append(f"Brands: {', '.join(filters.brands)}")
        if filters.clients:
            filter_context_parts.append(f"Clients: {', '.join(filters.clients)}")
        if filters.product_types:
            filter_context_parts.append(f"Product Types: {', '.join(filters.product_types)}")
        if filters.suppliers:
            filter_context_parts.append(f"Suppliers: {', '.join(filters.suppliers)}")
        
        filter_context = " | ".join(filter_context_parts) if filter_context_parts else "All data (no filters active)"
        
        # Prepare data summary for the LLM
        data_preview = df.head(5).to_markdown(index=False) if len(df) <= 5 else df.head(5).to_string(index=False)
        
        # Calculate key statistics for context
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        stats_context = ""
        if numeric_cols:
            main_metric = numeric_cols[0]
            total = df[main_metric].sum()
            avg = df[main_metric].mean()
            stats_context = f"\nKey Stats: Total {main_metric} = {total:,.2f}, Average = {avg:,.2f}"
        
        summary_prompt = f"""You are a business analyst for Munero, a B2B gift card and voucher platform.

USER QUESTION: "{question}"

ACTIVE DASHBOARD FILTERS: {filter_context}

SQL QUERY EXECUTED:
{sql_query}

DATA RESULT (first 5 rows):
{data_preview}

Total Rows: {len(df)}{stats_context}

TASK: Provide a clear, actionable 2-3 sentence summary for an executive. Focus on:
1. The key finding or pattern
2. Business implications (profitability, growth opportunities, risks)
3. Reference the active filters if relevant to context

MUNERO BUSINESS CONTEXT:
- Negative margins indicate unprofitable client/supplier relationships
- AOV (Average Order Value) patterns reveal client purchasing behavior
- Market share concentration shows dependency risks
- Product types: gift_cards, vouchers, etc.

Summary:"""
        
        summary_response = llm.invoke(summary_prompt).content
        # Handle both string and list responses
        if isinstance(summary_response, list):
            summary_response = str(summary_response[0]) if summary_response else ""
        summary = str(summary_response).strip()
        print(f"✅ Summary generated: {summary[:100]}...")
    except Exception as e:
        print(f"⚠️  Summary generation failed: {e}")
        summary = f"Analysis complete. Query returned {len(df)} results."

    print("🎉 AI processing complete!")
    return AIAnalysisResponse(
        answer_text=summary,
        sql_generated=sql_query,
        related_chart=chart_resp
    )


def process_chat_query(question: str, filters: DashboardFilters) -> AIAnalysisResponse:
    """
    Synchronous wrapper for backward compatibility.
    Routes data queries synchronously, but diagnostic queries need async context.

    For full functionality including driver analysis, use process_chat_query_async.

    Args:
        question: User's natural language question
        filters: Current dashboard filter state

    Returns:
        AIAnalysisResponse: Complete AI analysis with SQL, data, and visualization
    """
    intent = detect_intent(question)

    if intent == "driver_analysis":
        # For synchronous calls, we can't use the async driver analysis
        # Return a message directing to use async endpoint
        print("⚠️ Driver analysis requires async context. Falling back to sync data query.")
        # Try to handle it as a data query instead
        return _handle_data_query(question, filters)
    else:
        return _handle_data_query(question, filters)
