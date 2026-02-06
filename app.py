import streamlit as st
import pandas as pd
import sqlite3
import os
import re
import plotly.express as px
from plotly.subplots import make_subplots
from langchain_community.chat_models import ChatOllama
from langchain_community.utilities import SQLDatabase
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Optional, Tuple
import time
import plotly.graph_objects as go

# --- CONFIGURATION ---
CONFIG = {
    "DB_FILE": "munero_pilot.sqlite",
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "OLLAMA_MODEL": "qwen2.5-coder:7b",
    "LLM_TEMPERATURE": 0,
    "MAX_DISPLAY_ROWS": 1000,
    "SHOW_SQL_DEFAULT": True,
    "LLM_TIMEOUT": 60,  # Timeout for LLM requests in seconds
    "SQL_TIMEOUT": 30,  # Timeout for SQL execution in seconds
}

FILES = {
    "dim_customer": "/Users/zmasarweh/Documents/Munero_CSV_Data/dim_customer_rows.csv",
    "dim_products": "/Users/zmasarweh/Documents/Munero_CSV_Data/dim_products_rows.csv",
    "dim_suppliers": "/Users/zmasarweh/Documents/Munero_CSV_Data/dim_suppliers_rows.csv",
    "fact_orders": "/Users/zmasarweh/Documents/Munero_CSV_Data/fact_orders_rows_converted.csv"
}

# --- PAGE SETUP ---
st.set_page_config(page_title="Munero AI Analyst", layout="wide")

# --- DATA LOADING FUNCTIONS ---
@st.cache_resource
def setup_database():
    """
    Loads CSVs into SQLite with proper date formatting.
    """
    conn = sqlite3.connect(CONFIG["DB_FILE"], check_same_thread=False)
    
    for table_name, path in FILES.items():
        if not os.path.exists(path):
            st.error(f"File not found: {path}")
            return None
        
        df = pd.read_csv(path)
        
        # Clean column names
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        
        # FIX: Convert ALL date columns to ISO format (YYYY-MM-DD)
        date_columns = [col for col in df.columns if 'date' in col.lower()]
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')
        
        # Load to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
    
    return conn

# --- LLM SETUP ---
@st.cache_resource
def get_llm():
    """Initialize ChatOllama."""
    return ChatOllama(
        model=CONFIG["OLLAMA_MODEL"],
        base_url=CONFIG["OLLAMA_BASE_URL"],
        temperature=CONFIG["LLM_TEMPERATURE"],
    )

@st.cache_resource
def get_sql_database():
    """Wrap SQLite DB for LangChain."""
    return SQLDatabase.from_uri(
        f"sqlite:///{CONFIG['DB_FILE']}",
        include_tables=['dim_customer', 'dim_products', 'dim_suppliers', 'fact_orders'],
        sample_rows_in_table_info=5
    )

def get_enhanced_schema_info(_db):
    """
    Get enhanced schema information with explicit foreign key relationships.
    """
    # Get base schema from SQLDatabase
    base_schema = _db.get_table_info()
    
    # Add explicit foreign key documentation
    fk_info = """

FOREIGN KEY RELATIONSHIPS:
- fact_orders.customer_id → dim_customer.customer_id (PK)
- fact_orders.product_id → dim_products.product_id (PK)
- fact_orders.supplier_id → dim_suppliers.supplier_id (PK)
"""
    
    return base_schema + fk_info

@st.cache_resource
def get_sql_chain(_llm, _db):
    """Create SQL generation function using direct LLM calls."""
    
    def generate_sql(question: str) -> str:
        """Generate SQL query from natural language question."""
        
        # Get enhanced database schema with FK relationships
        table_info = get_enhanced_schema_info(_db)
        
        sql_prompt = f"""You are a SQLite expert. Write a SQL query to answer the question below.

Database Schema:
{table_info}

⚠️ IMPORTANT: fact_orders is a DENORMALIZED table - it contains ALL data including names.
NO JOINS ARE NEEDED for most queries - everything is in fact_orders!

WHERE TO FIND DATA (all in fact_orders table):
- Customer/Client names: fact_orders.client_name
- Customer country: fact_orders.client_country
- Customer balance: fact_orders.client_balance
- Product names: fact_orders.product_name
- Product SKU: fact_orders.product_sku
- Product brand: fact_orders.product_brand
- Product categories: fact_orders.order_type
- Supplier names: fact_orders.supplier_name
- Transaction data: fact_orders.order_date, fact_orders.quantity, fact_orders.sale_price, fact_orders.order_number

TERMINOLOGY MAPPING:
- User says "client" or "customer" → Use fact_orders.client_name
- User says "product category" → Use fact_orders.order_type
- User says "supplier" → Use fact_orders.supplier_name
- User says "revenue" or "sales" → Calculate as (fact_orders.sale_price * fact_orders.quantity)
- User says "orders" → Count distinct fact_orders.order_number
- User says "quantity sold" → SUM(fact_orders.quantity)

FILTERING BY NAMES:
When user mentions a specific name (like "Loylogic", "TechCorp", etc.):
- Use LIKE with % wildcard for flexible matching
- Example: WHERE fact_orders.client_name LIKE 'Loylogic%'

EXAMPLE (for reference only - do NOT copy this unless user asks about Loylogic):
Question: "Total revenue from Loylogic"
SQL: SELECT SUM(sale_price * quantity) AS total_revenue FROM fact_orders WHERE client_name LIKE 'Loylogic%';

NOW ANSWER THE ACTUAL USER QUESTION BELOW:
Question: {question}

CRITICAL RULES:
1. You can use <think> tags for your reasoning, then output ONLY the SQL query
2. Dates in order_date column are in YYYY-MM-DD format
3. Use BETWEEN for date ranges: WHERE order_date BETWEEN '2025-06-01' AND '2025-06-07'
4. For monthly queries: WHERE strftime('%Y-%m', order_date) = '2025-06'
5. Today's date is 2024-12-24
6. Always use table aliases for joins
7. ORDER BY can ONLY reference columns in SELECT or use aggregate functions that are in SELECT
8. For "Top N" queries: Use ORDER BY with the aggregate column (e.g., ORDER BY total_revenue DESC) then LIMIT N
9. End with semicolon
8. No markdown formatting in the final SQL output

SQL Query:"""
        
        try:
            response = invoke_llm_with_timeout(_llm, sql_prompt)
            return response
        except TimeoutError as e:
            raise TimeoutError(f"SQL generation timed out: {str(e)}")
    
    return generate_sql

# --- UTILITY FUNCTIONS ---
def invoke_llm_with_timeout(llm, prompt: str, timeout: Optional[int] = None) -> str:
    """
    Invoke LLM with timeout protection.
    Raises TimeoutError if the request takes longer than specified timeout.
    """
    if timeout is None:
        timeout = CONFIG["LLM_TIMEOUT"]
    
    def _invoke():
        response = llm.invoke(prompt)
        return response.content
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_invoke)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            raise TimeoutError(f"LLM request timed out after {timeout} seconds")

def execute_sql_with_timeout(sql_query: str, conn, timeout: Optional[int] = None) -> pd.DataFrame:
    """
    Execute SQL query with timeout protection.
    Raises TimeoutError if the query takes longer than specified timeout.
    """
    if timeout is None:
        timeout = CONFIG["SQL_TIMEOUT"]
    
    def _execute():
        return pd.read_sql_query(sql_query, conn)
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_execute)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            raise TimeoutError(f"SQL query timed out after {timeout} seconds")

def remove_think_tags(response: str) -> str:
    """
    Remove DeepSeek-R1's <think>...</think> reasoning tags from response.
    Must be called BEFORE any other parsing.
    """
    # Remove all <think> blocks (case-insensitive, multiline, greedy)
    cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()

def extract_sql_from_response(response: str) -> str:
    """
    Robust SQL extraction from LLM response.
    Handles markdown blocks, explanatory text, and DeepSeek-R1 <think> tags.
    """
    # STEP 0: Remove <think> tags FIRST (DeepSeek-R1 specific)
    response = remove_think_tags(response)
    response = response.strip()
    
    # Method 1: Extract from ```sql code block
    match = re.search(r'```sql\s+(.*?)\s+```', response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Method 2: Extract from generic ``` code block
    match = re.search(r'```\s+(.*?)\s+```', response, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Method 3: Find SELECT/WITH statement
    match = re.search(
        r'((?:WITH|SELECT|INSERT|UPDATE|DELETE)\s+.*?)(?:;|\n\n|$)',
        response,
        re.DOTALL | re.IGNORECASE
    )
    if match:
        return match.group(1).strip()
    
    # Method 4: Return as-is (will fail in pd.read_sql, triggering retry)
    return response.strip()

def smart_render(df: pd.DataFrame, question: str, llm, key_suffix: str = "") -> tuple:
    """
    Unified SmartRender Engine - Intelligent visualization with automatic optimization.
    
    Handles all data presentation logic in one place:
    1. Detects if data needs aggregation (raw transactions vs aggregated)
    2. Limits data to top N for readability
    3. Detects long labels and forces horizontal orientation
    4. Decides best visualization type (user preference > LLM decision)
    5. Applies heuristic overrides (e.g., too many categories for pie)
    6. Renders final visualization
    
    Returns:
        tuple: (figure_or_None, warning_message_or_None)
    """
    if df.empty:
        st.info("Query returned no results.")
        return None, None
    
    # Check if dataframe only contains NULL/None values (aggregate with no matches)
    # This happens when SQL aggregate functions (SUM, COUNT, etc.) have no matching rows
    if len(df) == 1 and df.isnull().all().all():
        st.info("Query returned no results.")
        return None, None
    
    # --- KPI CARD CHECK: Single-value results ---
    # Display as metric card for 1 row x 1 column (e.g., "Total Revenue: $1,234,567.89")
    if len(df) == 1 and len(df.columns) == 1:
        # Extract column name and clean it up
        col_name = df.columns[0]
        label = col_name.replace("_", " ").title()
        
        # Extract the single value
        value = df.iloc[0, 0]
        
        # Format the value
        if isinstance(value, (int, float)) and not pd.isna(value):
            formatted_value = f"{value:,.2f}"
        elif pd.isna(value):
            formatted_value = "No Data"
        else:
            formatted_value = str(value)
        
        # Display as KPI card
        st.metric(label=label, value=formatted_value)
        return None, None
    
    # Configuration
    MAX_CATEGORIES = 15  # Maximum categories to display in charts
    LONG_LABEL_THRESHOLD = 20  # Character length to trigger horizontal bars
    PIE_CHART_MAX = 8  # Maximum slices for readable pie chart
    
    warnings = []
    original_row_count = len(df)
    
    # If single column, always use table
    if len(df.columns) == 1:
        st.dataframe(df, use_container_width=True, key=f"dataframe_{key_suffix}")
        return None, None
    
    # Detect numeric columns for multi-metric support (scatter plots)
    numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    
    # If >3 columns or no numeric columns, use table
    if len(df.columns) > 3 or len(numeric_cols) == 0:
        st.dataframe(df, use_container_width=True, key=f"dataframe_{key_suffix}")
        return None, None
    
    # Determine label and value columns
    if len(numeric_cols) >= 1:
        # Assume first non-numeric column is label (or first column if all numeric)
        non_numeric_cols = [col for col in df.columns if col not in numeric_cols]
        label_col = non_numeric_cols[0] if non_numeric_cols else df.columns[0]
        value_col = numeric_cols[0]
        secondary_value_col = numeric_cols[1] if len(numeric_cols) >= 2 else None
    else:
        # Fallback to original logic
        label_col = df.columns[0]
        value_col = df.columns[1]
        secondary_value_col = None
    
    # --- STEP 1: Aggregation Check ---
    # If every row has a unique label, data is NOT aggregated (raw transactions)
    unique_labels = df[label_col].nunique()
    is_aggregated = unique_labels < len(df)
    
    df_viz = df.copy()
    
    if not is_aggregated and pd.api.types.is_numeric_dtype(df[value_col]):
        # Data needs aggregation - likely raw transactions
        warnings.append(f"Auto-aggregated {len(df)} raw transactions")
        
        # Aggregate all numeric columns (for scatter plots with multiple metrics)
        agg_cols = [value_col]
        if secondary_value_col is not None:
            agg_cols.append(secondary_value_col)
        
        df_viz = df.groupby(label_col, as_index=False)[agg_cols].sum()
        df_viz = df_viz.sort_values(by=value_col, ascending=False)
        unique_labels = len(df_viz)
    
    # --- STEP 2: Detect Time Series (before limiting) ---
    # Time series should NEVER be limited - we need all data points for temporal continuity
    is_time_series = (
        'date' in label_col.lower() or 
        'time' in label_col.lower() or
        'month' in label_col.lower() or
        'year' in label_col.lower() or
        'day' in label_col.lower() or
        'week' in label_col.lower() or
        pd.api.types.is_datetime64_any_dtype(df_viz[label_col])
    )
    
    # --- STEP 3: Limit to Top N (skip for time series) ---
    if is_time_series:
        # Time series: keep all points, sort by date
        try:
            # Try to sort chronologically
            df_viz[label_col] = pd.to_datetime(df_viz[label_col], errors='coerce')
            df_viz = df_viz.sort_values(by=label_col)
        except:
            # If conversion fails, keep as-is
            pass
    elif len(df_viz) > MAX_CATEGORIES:
        warnings.append(f"Showing top {MAX_CATEGORIES} of {len(df_viz)} items")
        df_viz = df_viz.nlargest(MAX_CATEGORIES, value_col)
    
    # --- STEP 4: Detect Long Labels ---
    max_label_length = df_viz[label_col].astype(str).str.len().max()
    force_horizontal = max_label_length > LONG_LABEL_THRESHOLD
    
    if force_horizontal:
        warnings.append("Using horizontal layout for long category names")
    
    # --- STEP 5: Decide Visualization Type ---
    # First check if user explicitly requested a chart type
    question_lower = question.lower()
    viz_type = None
    
    if any(word in question_lower for word in ['pie chart', 'pie graph', 'use pie', 'as pie', 'show pie']):
        viz_type = "PIE"
    elif any(word in question_lower for word in ['bar chart', 'bar graph', 'use bar', 'as bar', 'show bar']):
        viz_type = "BAR"
    elif any(word in question_lower for word in ['line chart', 'line graph', 'use line', 'as line', 'show line', 'trend']):
        viz_type = "LINE"
    elif any(word in question_lower for word in ['table', 'show table', 'as table', 'list']):
        viz_type = "TABLE"
    elif any(word in question_lower for word in ['scatter', 'scatter plot', 'correlation', 'relationship']):
        viz_type = "SCATTER"
    
    # Heuristic: If we have two numeric metrics, use scatter plot to show relationship
    if viz_type is None and secondary_value_col is not None and len(df_viz) > 1:
        viz_type = "SCATTER"
        warnings.append(f"Detected two metrics: Using Scatter Plot to show relationship between {value_col} and {secondary_value_col}")
    
    # If no explicit request and not scatter, ask LLM to decide
    if viz_type is None:
        viz_prompt = f"""You are a data visualization expert. Analyze this query result and recommend the best visualization.

Original Question: {question}

Data Characteristics:
- Total rows in result: {original_row_count}
- Unique categories: {unique_labels}
- Columns: {df.columns.tolist()}
- Value range: {df_viz[value_col].min():.2f} to {df_viz[value_col].max():.2f}
- Long labels: {'Yes' if force_horizontal else 'No'}

First 3 rows (after processing):
{df_viz.head(3).to_string()}

Choose the BEST visualization type:
- BAR: For comparing categories (e.g., top N customers, sales by product)
- LINE: For trends over time (dates on x-axis)
- PIE: For proportions/percentages (ONLY if ≤8 categories)
- TABLE: For detailed listings, text data, or when charts won't be clear

Respond with EXACTLY: VIZ: <BAR|LINE|PIE|TABLE>

VIZ:"""
        
        try:
            response = invoke_llm_with_timeout(llm, viz_prompt, timeout=30)
            response = remove_think_tags(response)
            match = re.search(r'VIZ:\s*(BAR|LINE|PIE|TABLE)', response, re.IGNORECASE)
            if match:
                viz_type = match.group(1).upper()
            else:
                viz_type = "TABLE"
        except TimeoutError:
            warnings.append("Visualization selection timed out, using table")
            viz_type = "TABLE"
    
    # --- STEP 6: Apply Heuristic Overrides ---
    # Override LLM decision if data characteristics make it inappropriate
    
    # Heuristic 1: Pie chart with too many categories - use "Top 9 + Others" grouping
    if viz_type == "PIE" and len(df_viz) > 10:
        # Keep it as PIE but group small slices into "Others"
        top_9 = df_viz.nlargest(9, value_col)
        remaining = df_viz.iloc[9:]
        
        if len(remaining) > 0:
            # Sum all remaining values
            others_value = remaining[value_col].sum()
            
            # Create "Others" row
            others_row = pd.DataFrame({
                label_col: ["Others"],
                value_col: [others_value]
            })
            
            # Combine top 9 + Others
            df_viz = pd.concat([top_9, others_row], ignore_index=True)
            unique_labels = len(df_viz)  # Update cardinality to 10
            
            warnings.append(f"⚠️ Too many categories for Pie chart. Showing Top 9 + 'Others' for readability")
    
    # Heuristic 2: Bar chart with too many categories - switch to table
    if viz_type == "BAR" and len(df_viz) > 20:
        warnings.append(f"Too many categories ({len(df_viz)}) for readable chart - using table")
        viz_type = "TABLE"
    
    # --- STEP 7: Render Visualization ---
    warning_message = " | ".join(warnings) if warnings else None
    
    # Show warnings to user if any
    if warning_message:
        st.info(f"ℹ️ {warning_message}")
    
    # Wrap rendering in try-except for error handling
    try:
        if viz_type == "TABLE":
            st.dataframe(df_viz, use_container_width=True, key=f"dataframe_{key_suffix}")
            return None, warning_message
        
        elif viz_type == "BAR":
            # Clean data before charting - drop rows with null in EITHER column
            df_viz_clean = df_viz.dropna(subset=[label_col, value_col])
            
            if len(df_viz_clean) == 0:
                st.warning("All values are null/NaN - displaying as table")
                st.dataframe(df_viz, use_container_width=True, key=f"dataframe_{key_suffix}")
                return None, f"{warning_message} | All values null"
            
            if force_horizontal:
                # Horizontal bar chart for long labels
                fig = px.bar(
                    df_viz_clean,
                    y=label_col,
                    x=value_col,
                    orientation='h',
                    title=f"{value_col} by {label_col}"
                )
                fig.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    height=max(400, len(df_viz_clean) * 30)  # Dynamic height
                )
            else:
                # Standard vertical bar chart
                fig = px.bar(
                    df_viz_clean,
                    x=label_col,
                    y=value_col,
                    title=f"{value_col} by {label_col}"
                )
            
            st.plotly_chart(fig, use_container_width=True, key=f"bar_chart_{key_suffix}")
            return fig, warning_message
        
        elif viz_type == "LINE":
            df_viz_clean = df_viz.dropna(subset=[label_col, value_col])
            
            fig = px.line(
                df_viz_clean,
                x=label_col,
                y=value_col,
                title=f"{value_col} over {label_col}"
            )
            st.plotly_chart(fig, use_container_width=True, key=f"line_chart_{key_suffix}")
            return fig, warning_message
        
        elif viz_type == "PIE":
            df_viz_clean = df_viz.dropna(subset=[label_col, value_col])
            
            fig = px.pie(
                df_viz_clean,
                names=label_col,
                values=value_col,
                title=f"Distribution of {value_col}"
            )
            st.plotly_chart(fig, use_container_width=True, key=f"pie_chart_{key_suffix}")
            return fig, warning_message
        
        elif viz_type == "SCATTER":
            # Scatter plot for two numeric metrics (correlation/relationship)
            if secondary_value_col is None:
                # Fallback if scatter was requested but no secondary metric
                st.warning("Scatter plot requires two numeric metrics - displaying as table")
                st.dataframe(df_viz, use_container_width=True, key=f"dataframe_{key_suffix}")
                return None, f"{warning_message} | Missing secondary metric"
            
            # Clean data - drop rows with null in any of the three columns
            df_viz_clean = df_viz.dropna(subset=[label_col, value_col, secondary_value_col])
            
            if len(df_viz_clean) == 0:
                st.warning("All values are null/NaN - displaying as table")
                st.dataframe(df_viz, use_container_width=True, key=f"dataframe_{key_suffix}")
                return None, f"{warning_message} | All values null"
            
            # --- DYNAMIC SCALE DETECTION ---
            # Determine if log scale is needed for each axis independently
            # This prevents unnecessary distortion when metrics don't have extreme ranges
            
            def needs_log_scale(df, col):
                """
                Detect if a column needs logarithmic scaling.
                Heuristic: If max/min ratio > 1000 (3+ orders of magnitude), use log scale.
                """
                # Filter out non-positive values (log requires > 0)
                valid_data = df[col][df[col] > 0]
                
                if valid_data.empty or len(valid_data) < 2:
                    return False
                
                max_val = valid_data.max()
                min_val = valid_data.min()
                
                # Avoid division by zero
                if min_val == 0:
                    return False
                
                # If spread is > 1000x (3 orders of magnitude), use log scale
                ratio = max_val / min_val
                return ratio > 1000
            
            # Check each axis independently
            use_log_x = needs_log_scale(df_viz_clean, value_col)
            use_log_y = needs_log_scale(df_viz_clean, secondary_value_col)
            
            # Build dynamic scale note for user
            scale_info = []
            if use_log_x:
                scale_info.append(f"{value_col} (X-axis)")
            if use_log_y:
                scale_info.append(f"{secondary_value_col} (Y-axis)")
            
            if scale_info:
                scale_note = f"Note: Log scale applied to {', '.join(scale_info)} due to large value range"
            else:
                scale_note = "Note: Using linear scale for both axes"
            
            # Build dynamic title
            scale_suffix = ""
            if use_log_x and use_log_y:
                scale_suffix = " (Log-Log Scale)"
            elif use_log_x:
                scale_suffix = " (Log X-axis)"
            elif use_log_y:
                scale_suffix = " (Log Y-axis)"
            # else: linear scale, no suffix needed
            
            # --- CONDITIONAL RENDERING BASED ON DATA VOLUME ---
            
            # CONDITION A: High Volume (> 10 rows) → Log-Scale Scatter Only
            if len(df_viz_clean) > 10:
                # For large datasets, use dynamic log-scale to handle scale differences
                # Only applies log scale to axes that need it (ratio > 1000x)
                fig = px.scatter(
                    df_viz_clean,
                    x=value_col,
                    y=secondary_value_col,
                    hover_data=[label_col],
                    log_x=use_log_x,  # Dynamic: only if X-axis has >1000x range
                    log_y=use_log_y,  # Dynamic: only if Y-axis has >1000x range
                    title=f"{value_col} vs {secondary_value_col}{scale_suffix}"
                )
                
                # Customize appearance
                fig.update_traces(marker=dict(size=10, opacity=0.7))
                
                # Add annotation about scale choice (only if log scale is used)
                if use_log_x or use_log_y:
                    fig.add_annotation(
                        text=scale_note,
                        xref="paper", yref="paper",
                        x=0.5, y=-0.15,
                        showarrow=False,
                        font=dict(size=10, color="gray")
                    )
                
                st.plotly_chart(fig, use_container_width=True, key=f"scatter_chart_{key_suffix}")
                return fig, warning_message
            
            # CONDITION B: Low Volume (<= 10 rows) → Show Tabs with Dual-Axis + Scatter
            else:
                # For small datasets (executive summaries), offer both views
                tab1, tab2 = st.tabs(["📊 Dual Axis (Bar + Line)", "🔍 Scatter Plot (Log Scale)"])
                
                with tab1:
                    # TAB 1: Dual-Axis Chart (Bar + Line)
                    # This gives detailed view with two separate Y-axes for different scales
                    
                    # Create figure with secondary y-axis
                    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
                    
                    # Add bar chart for first metric (primary y-axis)
                    fig_dual.add_trace(
                        go.Bar(
                            x=df_viz_clean[label_col],
                            y=df_viz_clean[value_col],
                            name=value_col,
                            marker_color='lightblue'
                        ),
                        secondary_y=False
                    )
                    
                    # Add line chart for second metric (secondary y-axis)
                    fig_dual.add_trace(
                        go.Scatter(
                            x=df_viz_clean[label_col],
                            y=df_viz_clean[secondary_value_col],
                            name=secondary_value_col,
                            mode='lines+markers',
                            line=dict(color='orange', width=3),
                            marker=dict(size=8)
                        ),
                        secondary_y=True
                    )
                    
                    # Update layout
                    fig_dual.update_layout(
                        title=f"{value_col} & {secondary_value_col} by {label_col}",
                        xaxis_title=label_col,
                        hovermode='x unified',
                        height=500
                    )
                    
                    # Set y-axes titles
                    fig_dual.update_yaxes(title_text=value_col, secondary_y=False)
                    fig_dual.update_yaxes(title_text=secondary_value_col, secondary_y=True)
                    
                    st.plotly_chart(fig_dual, use_container_width=True, key=f"dual_axis_{key_suffix}")
                    st.caption("💡 **Dual Axis View**: Bar chart (left axis) + Line chart (right axis) for comparing metrics with different scales")
                
                with tab2:
                    # TAB 2: Log-Scale Scatter Plot (if needed)
                    # Uses dynamic scale detection - same logic as high-volume view
                    
                    fig_scatter = px.scatter(
                        df_viz_clean,
                        x=value_col,
                        y=secondary_value_col,
                        hover_data=[label_col],
                        log_x=use_log_x,  # Dynamic: only if X-axis has >1000x range
                        log_y=use_log_y,  # Dynamic: only if Y-axis has >1000x range
                        title=f"{value_col} vs {secondary_value_col}{scale_suffix}"
                    )
                    
                    # Customize appearance
                    fig_scatter.update_traces(marker=dict(size=12, opacity=0.8))
                    
                    # Add labels to each point for small datasets
                    fig_scatter.update_traces(
                        text=df_viz_clean[label_col],
                        textposition='top center',
                        textfont=dict(size=9)
                    )
                    
                    st.plotly_chart(fig_scatter, use_container_width=True, key=f"scatter_tab_{key_suffix}")
                    
                    # Dynamic caption based on scale choice
                    if use_log_x or use_log_y:
                        st.caption(f"💡 **Scatter View**: {scale_note}")
                    else:
                        st.caption("💡 **Scatter View**: Linear scale for both axes - data has moderate ranges")
                
                # Return the dual-axis figure as primary
                return fig_dual, warning_message
        
        else:  # Fallback to table
            st.dataframe(df_viz, use_container_width=True, key=f"dataframe_{key_suffix}")
            return None, warning_message
            
    except Exception as e:
        # If rendering fails, fall back to table with error message
        st.error(f"⚠️ Chart rendering failed: {str(e)}")
        st.markdown("**Displaying as table instead:**")
        st.dataframe(df_viz, use_container_width=True, key=f"dataframe_fallback_{key_suffix}")
        return None, f"{warning_message} | Rendering error: {str(e)}"

# --- QUERY PROCESSING ---
def process_question(question: str, llm, sql_chain, conn) -> dict:
    """
    Complete pipeline: Question → SQL → DataFrame → SmartRender
    """
    result = {
        "success": False,
        "sql": None,
        "df": None,
        "viz_warning": None,
        "error": None
    }
    
    try:
        # STEP 1: Generate SQL
        with st.spinner("🧠 Generating SQL query..."):
            raw_response = sql_chain(question)  # Direct function call
            sql_query = extract_sql_from_response(raw_response)
            result["sql"] = sql_query
        
        # STEP 2: Execute SQL
        with st.spinner("🔍 Executing query..."):
            try:
                df = execute_sql_with_timeout(sql_query, conn)
                result["df"] = df
                
                # Check if results are empty (query succeeded but returned no rows)
                if df.empty and len(df.columns) > 0:
                    st.warning("Query returned no results. Analyzing query for missing JOINs...")
                    
                    empty_fix_prompt = f"""This SQL query executed successfully but returned ZERO rows:
{sql_query}

Original question: {question}

COMMON CAUSES OF EMPTY RESULTS:
1. Incorrect LIKE pattern or exact match when data has variations
2. Wrong column name
3. Case sensitivity issues
4. Missing data for that filter value

CRITICAL FACTS ABOUT THE DATABASE:
- fact_orders is DENORMALIZED - all data is in ONE table
- NO JOINS needed - client_name, product_name, supplier_name are directly in fact_orders
- Use LIKE 'value%' for name matching

REQUIRED FIX:
1. Make sure you're querying fact_orders table directly (no joins)
2. Use LIKE with % wildcard: WHERE fact_orders.client_name LIKE 'Name%'
3. Check column names: client_name, product_name, supplier_name, order_type

Example correct query:
SELECT client_name, SUM(sale_price * quantity) AS total_revenue
FROM fact_orders
WHERE client_name LIKE 'Loylogic%'
GROUP BY client_name;

Rewrite the query to fix the issue.
Return ONLY the corrected SQL query.

SQL:"""
                    
                    try:
                        fixed_response = invoke_llm_with_timeout(llm, empty_fix_prompt)
                        fixed_sql = extract_sql_from_response(fixed_response)
                        result["sql"] = fixed_sql
                        
                        df = execute_sql_with_timeout(fixed_sql, conn)
                        result["df"] = df
                        
                        if not df.empty:
                            st.success("✅ Query fixed! Found results after adding proper JOINs.")
                    except TimeoutError:
                        st.warning("Retry attempt timed out. Displaying original empty results.")
                    except Exception as retry_error:
                        st.warning(f"Retry failed: {str(retry_error)}. Displaying original empty results.")
                
            except TimeoutError as e:
                raise TimeoutError(f"SQL query execution timed out: {str(e)}")
            except Exception as e:
                # Retry with error context
                st.warning("Query failed, attempting to fix...")
                fix_prompt = f"""The following SQL query failed:
{sql_query}

Error: {str(e)}

Fix the query. Remember dates are YYYY-MM-DD format.
Return ONLY the corrected SQL query.

SQL:"""
                try:
                    fixed_response = invoke_llm_with_timeout(llm, fix_prompt)
                    fixed_sql = extract_sql_from_response(fixed_response)
                    result["sql"] = fixed_sql
                    df = execute_sql_with_timeout(fixed_sql, conn)
                    result["df"] = df
                except TimeoutError:
                    raise Exception("Query retry timed out after attempting to fix the SQL")
        
        result["success"] = True
        
    except TimeoutError as e:
        result["error"] = f"⏱️ Request timed out: {str(e)}"
    except Exception as e:
        result["error"] = str(e)
    
    return result

# --- MAIN APP ---
st.title("🤖 Munero AI Data Analyst")
st.markdown("Ask questions about your sales, customers, products, and suppliers in natural language!")

# Initialize database
if "conn" not in st.session_state:
    with st.spinner("📦 Loading database..."):
        conn = setup_database()
        if conn:
            st.session_state["conn"] = conn
            st.success("✅ Database loaded successfully!")
        else:
            st.error("Failed to load database. Please check file paths.")
            st.stop()

# Initialize LLM components
if "llm" not in st.session_state:
    with st.spinner("🤖 Initializing AI..."):
        try:
            st.session_state["llm"] = get_llm()
            st.session_state["db"] = get_sql_database()
            st.session_state["sql_chain"] = get_sql_chain(
                st.session_state["llm"],
                st.session_state["db"]
            )
            st.success("✅ AI ready!")
        except Exception as e:
            st.error(f"Failed to initialize AI: {e}")
            st.info("Make sure Ollama is running: `ollama serve`")
            st.stop()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "👋 Hello! I'm your AI data analyst. Ask me anything about your sales data!\n\n**Example questions:**\n- Top 10 customers by sales in June 2025\n- Total revenue by product category\n- Sales trend over the last 3 months\n- Which suppliers have the most orders?"
    }]

# --- CHAT INTERFACE ---
st.divider()

# Display chat history
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        if "df" in message and message["df"] is not None and isinstance(message["df"], pd.DataFrame):
            # Show visualization with smart render
            # For historical messages, we need to get question from previous user message
            question = ""
            if idx > 0 and st.session_state.messages[idx-1]["role"] == "user":
                question = st.session_state.messages[idx-1]["content"]
            
            fig, viz_warning = smart_render(
                message["df"], 
                question, 
                st.session_state["llm"],
                key_suffix=f"msg_{idx}"
            )
            # Warning is already displayed inside smart_render()
        
        if "sql" in message and message["sql"]:
            with st.expander("🔍 View SQL Query"):
                st.code(message["sql"], language="sql")
        
        if "df" in message and message["df"] is not None and isinstance(message["df"], pd.DataFrame) and not message["df"].empty:
            # Download button - use FULL original dataframe
            csv = message["df"].to_csv(index=False)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name="query_results.csv",
                mime="text/csv",
                key=f"download_{idx}"
            )

# Chat input
if prompt := st.chat_input("Ask me about your data..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Process query
    with st.chat_message("assistant"):
        result = process_question(
            prompt, 
            st.session_state["llm"],
            st.session_state["sql_chain"],
            st.session_state["conn"]
        )
        
        if result["success"]:
            response_text = "Here's what I found:"
            st.markdown(response_text)
            
            # Use SmartRender for intelligent visualization
            fig, viz_warning = smart_render(
                result["df"], 
                prompt, 
                st.session_state["llm"],
                key_suffix=f"current_{len(st.session_state.messages)}"
            )
            # Warning is already displayed inside smart_render()
            
            # Show SQL
            with st.expander("🔍 View SQL Query"):
                st.code(result["sql"], language="sql")
            
            # Download button with unique key - FULL original dataframe
            if not result["df"].empty:
                csv = result["df"].to_csv(index=False)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv,
                    file_name="query_results.csv",
                    mime="text/csv",
                    key=f"download_current_{len(st.session_state.messages)}"
                )
            
            # Save to history
            st.session_state.messages.append({
                "role": "assistant",
                "content": response_text,
                "df": result["df"],
                "sql": result["sql"]
            })
        else:
            error_msg = f"❌ I encountered an error: {result['error']}"
            st.error(error_msg)
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg
            })

# --- SIDEBAR: DATABASE EXPLORER ---
with st.sidebar:
    st.header("📊 Database Info")
    
    try:
        tables = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table'",
            st.session_state["conn"]
        )
        st.write("**Tables:**", ", ".join(tables['name'].tolist()))
        
        # Table viewer
        with st.expander("View Tables"):
            selected_table = st.selectbox(
                "Select table:",
                tables['name'].tolist()
            )
            if selected_table:
                df = pd.read_sql_query(
                    f"SELECT * FROM {selected_table} LIMIT 5",
                    st.session_state["conn"]
                )
                st.dataframe(df, use_container_width=True)
                st.caption(f"Showing first 5 rows of {selected_table}")
    except Exception as e:
        st.error(f"Error loading database info: {e}")
    
    st.divider()
    st.markdown("**Status:**")
    st.success("🟢 Database Connected")
    st.success("🟢 AI Ready")
    
    st.divider()
    st.markdown("**Configuration:**")
    st.info(f"⏱️ LLM Timeout: {CONFIG['LLM_TIMEOUT']}s")
    st.info(f"⏱️ SQL Timeout: {CONFIG['SQL_TIMEOUT']}s")
    st.caption("Requests exceeding these limits will be cancelled automatically")