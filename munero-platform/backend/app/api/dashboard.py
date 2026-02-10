"""
Dashboard API endpoints.
Provides KPI metrics and chart data for the dashboard frontend.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Literal, Optional
import logging
from app.models import (
    DashboardFilters, HeadlineStats, KPIMetric,
    ChartResponse, ChartPoint,
    TrendResponse, TrendPoint,
    ScatterResponse, ScatterPoint,
    LeaderboardResponse, LeaderboardRow,
    FilterOptionsResponse,
    # Overview V2 Models
    StuckOrder, StuckOrdersResponse,
    SparklinePoint, SparklineResponse,
    CountryData, GeographyResponse,
    ProductByStatus, TopProductsByStatusResponse,
    BrandByType, TopBrandsByTypeResponse,
    # Catalog Analysis Models
    CatalogKPIs, ProductScatterPoint, ProductScatterResponse,
    TrendItem, ProductMoversResponse
)
from app.core.database import get_data
from app.core.config import settings
from app.core.logging_utils import redact_filter_values_for_log
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import hashlib

router = APIRouter()
logger = logging.getLogger(__name__)


def _log_filters_debug(label: str, filters: DashboardFilters) -> None:
    if settings.DEBUG:
        logger.debug("%s filters=%s", label, redact_filter_values_for_log(filters))

def _sql_numeric_expr(column: str) -> str:
    """
    Return a SQL expression that coerces numeric-like values in hosted Postgres.

    This helps when ingested datasets store numeric fields as TEXT.
    """
    if settings.db_dialect == "postgresql":
        # Coerce to float while tolerating blank strings and common formatting.
        # - `::text` works for both TEXT and numeric column types.
        # - `regexp_replace` strips commas/currency symbols if present.
        # - NULLIF avoids casting empty strings.
        return (
            "NULLIF("
            f"regexp_replace({column}::text, '[^0-9.+-]', '', 'g')"
            ", '')::double precision"
        )
    return column


def _sql_date_cast_expr(date_column: str) -> str:
    """
    Return a SQL expression that evaluates to a DATE (dialect-aware).
    """
    if settings.db_dialect == "postgresql":
        # Avoid casting blank strings which would raise an error in Postgres.
        return f"NULLIF({date_column}::text, '')::date"
    return date_column


def _sql_date_label_expr(date_column: str, granularity: Literal["day", "month", "year"]) -> str:
    """
    Build a SQL expression that formats a date column into a string label.
    Supports SQLite and PostgreSQL based on current settings.
    """
    if settings.db_dialect == "postgresql":
        fmt = {"day": "YYYY-MM-DD", "month": "YYYY-MM", "year": "YYYY"}[granularity]
        return f"to_char({_sql_date_cast_expr(date_column)}, '{fmt}')"

    # SQLite default (dates stored as TEXT in YYYY-MM-DD format)
    fmt = {"day": "%Y-%m-%d", "month": "%Y-%m", "year": "%Y"}[granularity]
    return f"strftime('{fmt}', {date_column})"


def _sql_cutoff_from_max_date(date_column: str, *, days: int | None = None, months: int | None = None) -> str:
    """
    Returns a SQL subquery expression that computes a cutoff date relative to MAX(date_column).
    """
    if (days is None) == (months is None):
        raise ValueError("Provide exactly one of days or months")

    if settings.db_dialect == "postgresql":
        date_expr = _sql_date_cast_expr(date_column)
        if months is not None:
            return f"(SELECT (MAX({date_expr}) - INTERVAL '{months} months')::date FROM fact_orders)"
        return f"(SELECT (MAX({date_expr}) - INTERVAL '{days} days')::date FROM fact_orders)"

    # SQLite
    if months is not None:
        return f"(SELECT date(MAX({date_column}), '-{months} months') FROM fact_orders)"
    return f"(SELECT date(MAX({date_column}), '-{days} days') FROM fact_orders)"


def build_where_clause(filters: DashboardFilters) -> tuple[str, dict]:
    """
    Constructs dynamic SQL WHERE clause from filters.
    
    Args:
        filters: DashboardFilters object with optional filter criteria
        
    Returns:
        tuple: (sql_string, params_dict) for safe parameterized queries
        
    Example:
        >>> filters = DashboardFilters(start_date="2025-01-01", countries=["UAE"])
        >>> sql, params = build_where_clause(filters)
        >>> sql
        '1=1 AND order_date >= :start_date AND client_country IN (:country_0)'
        >>> params
        {'start_date': '2025-01-01', 'country_0': 'UAE'}
    """
    conditions = ["1=1"]  # Default always true - simplifies AND chaining
    params = {}
    order_date_expr = _sql_date_cast_expr("order_date")

    # Date Range Filters
    if filters.start_date:
        conditions.append(f"{order_date_expr} >= :start_date")
        params["start_date"] = str(filters.start_date)
    
    if filters.end_date:
        conditions.append(f"{order_date_expr} <= :end_date")
        params["end_date"] = str(filters.end_date)
    
    # List Filters - Only apply if list is not empty (empty = select all)
    if filters.countries:
        # SQL "IN" clause with parameterized values for SQL injection protection
        placeholders = [f":country_{i}" for i in range(len(filters.countries))]
        conditions.append(f"client_country IN ({','.join(placeholders)})")
        for i, val in enumerate(filters.countries):
            params[f"country_{i}"] = val
    
    if filters.clients:
        placeholders = [f":client_{i}" for i in range(len(filters.clients))]
        conditions.append(f"client_name IN ({','.join(placeholders)})")
        for i, val in enumerate(filters.clients):
            params[f"client_{i}"] = val
    
    if filters.product_types:
        placeholders = [f":type_{i}" for i in range(len(filters.product_types))]
        conditions.append(f"order_type IN ({','.join(placeholders)})")
        for i, val in enumerate(filters.product_types):
            params[f"type_{i}"] = val
    
    if filters.brands:
        placeholders = [f":brand_{i}" for i in range(len(filters.brands))]
        conditions.append(f"product_brand IN ({','.join(placeholders)})")
        for i, val in enumerate(filters.brands):
            params[f"brand_{i}"] = val
    
    if filters.suppliers:
        placeholders = [f":supplier_{i}" for i in range(len(filters.suppliers))]
        conditions.append(f"supplier_name IN ({','.join(placeholders)})")
        for i, val in enumerate(filters.suppliers):
            params[f"supplier_{i}"] = val

    return " AND ".join(conditions), params


@router.post("/headline", response_model=HeadlineStats)
def get_headline_stats(filters: DashboardFilters):
    """
    Calculates the 4 top-level KPIs for the dashboard.
    
    **Metrics:**
    - Total Orders: Count of distinct order numbers
    - Total Revenue: Sum of order_price_in_aed (standard currency)
    - Avg Order Value: Total Revenue / Total Orders
    - Distinct Brands: Count of unique product brands sold
    
    **Request Body:**
    ```json
    {
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "currency": "AED",
        "countries": ["UAE", "Saudi Arabia"],
        "brands": [],
        "clients": [],
        "product_types": [],
        "suppliers": []
    }
    ```
    
    **Response:**
    ```json
    {
        "total_orders": {
            "label": "Total Orders",
            "value": 1234,
            "formatted": "1,234",
            "trend_direction": "neutral"
        },
        "total_revenue": { ... },
        "avg_order_value": { ... },
        "distinct_brands": { ... }
    }
    ```
    """
    where_sql, params = build_where_clause(filters)
    
    # Query: Aggregated metrics
    # Note: Using order_price_in_aed as the standard 'Revenue'
    query = f"""
        SELECT
            COUNT(DISTINCT order_number) as total_orders,
            SUM({_sql_numeric_expr("order_price_in_aed")}) as total_revenue,
            COUNT(DISTINCT product_brand) as distinct_brands,
            COUNT(DISTINCT client_name) as distinct_clients
        FROM fact_orders
        WHERE {where_sql}
    """
    
    logger.info("🔍 Executing Headline KPI Query")
    _log_filters_debug("🔍 Headline KPI Query", filters)
    df = get_data(query, params)
    
    if df.empty:
        # Return zeroed stats if no data
        logger.info("⚠️ No data found for the given filters - returning zero metrics")
        zero = KPIMetric(label="", value=0, formatted="0", trend_direction="neutral")
        return HeadlineStats(
            total_orders=KPIMetric(label="Total Orders", value=0, formatted="0", trend_direction="neutral"),
            total_revenue=KPIMetric(label="Total Revenue", value=0, formatted="AED 0.00", trend_direction="neutral"),
            avg_order_value=KPIMetric(label="Avg Order Value", value=0, formatted="AED 0.00", trend_direction="neutral"),
            orders_per_client=KPIMetric(label="Orders per Client", value=0, formatted="0.00", trend_direction="neutral"),
            distinct_brands=KPIMetric(label="Active Brands", value=0, formatted="0", trend_direction="neutral")
        )

    # Extract values
    row = df.iloc[0]
    total_rev = row.get("total_revenue", 0) or 0
    total_ord = row.get("total_orders", 0) or 0
    brands = row.get("distinct_brands", 0) or 0
    clients = row.get("distinct_clients", 0) or 0
    
    # Calculate derived metrics
    aov = total_rev / total_ord if total_ord > 0 else 0  # Average Order Value
    orders_per_client = total_ord / clients if clients > 0 else 0  # Orders per Client

    logger.info(
        "✅ Headline KPIs calculated (orders=%s, revenue=%s, aov=%s, orders_per_client=%s, brands=%s)",
        total_ord,
        round(float(total_rev), 2),
        round(float(aov), 2),
        round(float(orders_per_client), 2),
        brands,
    )

    return HeadlineStats(
        total_orders=KPIMetric(
            label="Total Orders",
            value=total_ord,
            formatted=f"{total_ord:,.0f}",
            trend_pct=0.0,  # Hardcoded until comparison logic is implemented
            trend_direction="neutral" 
        ),
        total_revenue=KPIMetric(
            label="Total Revenue (AED)",
            value=total_rev,
            formatted=f"AED {total_rev:,.2f}",
            trend_pct=0.0,  # Hardcoded until comparison logic is implemented
            trend_direction="neutral"
        ),
        avg_order_value=KPIMetric(
            label="Avg Order Value",
            value=aov,
            formatted=f"AED {aov:,.2f}",
            trend_pct=0.0,  # Hardcoded until comparison logic is implemented
            trend_direction="neutral"
        ),
        orders_per_client=KPIMetric(
            label="Orders per Client",
            value=orders_per_client,
            formatted=f"{orders_per_client:.2f}",
            trend_pct=0.0,  # Hardcoded until comparison logic is implemented
            trend_direction="neutral"
        ),
        distinct_brands=KPIMetric(
            label="Brands Sold",
            value=brands,
            formatted=str(int(brands)),
            trend_pct=0.0,  # Hardcoded until comparison logic is implemented
            trend_direction="neutral"
        )
    )


@router.get("/test")
def test_dashboard():
    """
    Simple test endpoint to verify the dashboard API is working.
    
    Returns a sample query result from the database.
    """
    query = """
        SELECT 
            COUNT(*) as total_rows,
            COUNT(DISTINCT order_number) as total_orders,
            COUNT(DISTINCT client_name) as total_clients
        FROM fact_orders
    """
    df = get_data(query)
    
    if df.empty:
        raise HTTPException(status_code=500, detail="Database query failed")
    
    return {
        "status": "ok",
        "database": "connected",
        "stats": df.to_dict(orient="records")[0]
    }


@router.post("/trend", response_model=TrendResponse)
def get_sales_trend(filters: DashboardFilters, granularity: Literal['day', 'month', 'year'] = 'month'):
    """
    Returns dual-axis sales trend (Revenue + Orders) with anomaly detection.
    
    **Enhanced Features (Phase 4)**:
    - Dual-axis plotting: Revenue (bar) + Orders (line)
    - Growth calculation: Period-over-period % change for both metrics
    - Anomaly detection: Z-score based flagging (configurable threshold)
    
    **Granularity Options**:
    - `day`: Daily aggregation (YYYY-MM-DD)
    - `month`: Monthly aggregation (YYYY-MM)
    - `year`: Yearly aggregation (YYYY)
    
    **Request Body**:
    ```json
    {
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "currency": "AED",
        "anomaly_threshold": 3.0,
        "countries": []
    }
    ```
    
    **Query Parameters**:
    - `granularity`: "day" or "month" (default: "month")
    
    **Response**: Dual-axis chart data with anomaly flags and growth metrics
    """
    where_sql, params = build_where_clause(filters)
    date_label_expr = _sql_date_label_expr("order_date", granularity)
    
    # 1. Fetch Aggregated Data
    query = f"""
        SELECT
            {date_label_expr} as date_label,
            SUM({_sql_numeric_expr("order_price_in_aed")}) as revenue,
            COUNT(DISTINCT order_number) as orders
        FROM fact_orders
        WHERE {where_sql}
        GROUP BY 1
        ORDER BY 1 ASC
    """
    
    logger.info("🔍 Executing Enhanced Trend Query (granularity=%s)", granularity)
    _log_filters_debug("🔍 Enhanced Trend Query", filters)
    df = get_data(query, params)
    
    if df.empty:
        logger.info("⚠️ No trend data found for the given filters")
        return TrendResponse(title=f"Sales & Volume Trend ({granularity.title()})", data=[])

    # 2. Calculate Growth (Period over Period)
    df['revenue_growth'] = df['revenue'].pct_change().fillna(0) * 100
    df['orders_growth'] = df['orders'].pct_change().fillna(0) * 100

    # 3. Anomaly Detection (Z-Score)
    # Helper to calculate anomalies safely
    def detect_anomalies(series, threshold):
        """Detect anomalies using Z-score method"""
        if len(series) < 5 or series.std() == 0:
            return [False] * len(series)
        z_scores = (series - series.mean()) / series.std()
        return abs(z_scores) > threshold

    threshold = getattr(filters, 'anomaly_threshold', 3.0)  # Default to 3.0 if missing
    df['is_revenue_anomaly'] = detect_anomalies(df['revenue'], threshold)
    df['is_order_anomaly'] = detect_anomalies(df['orders'], threshold)

    # Count anomalies for logging
    revenue_anomalies = df['is_revenue_anomaly'].sum()
    order_anomalies = df['is_order_anomaly'].sum()
    logger.info(
        "✅ Trend Analysis (points=%s, revenue_anomalies=%s, order_anomalies=%s)",
        len(df),
        int(revenue_anomalies),
        int(order_anomalies),
    )

    # 4. Map to Response Model
    data_points = []
    for _, row in df.iterrows():
        data_points.append(TrendPoint(
            date_label=str(row['date_label']),
            revenue=float(row['revenue']),
            orders=int(row['orders']),
            revenue_growth=float(row['revenue_growth']),
            orders_growth=float(row['orders_growth']),
            is_revenue_anomaly=bool(row['is_revenue_anomaly']),
            is_order_anomaly=bool(row['is_order_anomaly'])
        ))
        
    return TrendResponse(
        title=f"Sales & Volume Trend ({granularity.title()})",
        data=data_points
    )


@router.post("/breakdown", response_model=LeaderboardResponse)
def get_leaderboard(
    filters: DashboardFilters,
    dimension: Literal['client', 'brand', 'supplier', 'product', 'order_type'],
    include_trend: bool = False,
    include_growth: bool = False
):
    """
    Returns top performers by specified dimension with profitability metrics.

    **Enhanced Leaderboard Endpoint (Phase 1 Part 3)**
    - Powers "Top Clients," "Top Brands," "Top Suppliers," "Top Products" widgets
    - Calculates profit margin: (Revenue - COGS) / Revenue
    - Calculates market share: % of total revenue in filtered view
    - Optionally includes 6-month sparkline trend data
    - Optionally includes growth_pct for period-over-period comparison

    **Dimension Options**:
    - `client`: Top clients by revenue
    - `brand`: Top brands by revenue
    - `supplier`: Top suppliers by revenue
    - `product`: Top products by revenue (includes failure_rate when include_growth=True)
    - `order_type`: Revenue by product type (Gift Card, Merchandise, etc.)

    **Request Body**:
    ```json
    {
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "currency": "AED",
        "countries": []
    }
    ```

    **Query Parameters**:
    - `dimension`: Grouping dimension (client/brand/supplier/product)
    - `include_trend`: If true, include 6-month revenue trend for sparklines (default: false)
    - `include_growth`: If true and dimension='product', calculate period-over-period growth_pct (default: false)

    **Response**: Top 50 entities with revenue, orders, margin %, market share %, and optional trend
    """
    where_sql, params = build_where_clause(filters)

    # 1. Map API dimension to DB Column
    dim_map = {
        'client': 'client_name',
        'brand': 'product_brand',
        'supplier': 'supplier_name',
        'product': 'product_name',
        'order_type': 'order_type'
    }
    db_col = dim_map.get(dimension, 'product_brand')

    # 2. Aggregation Query
    query = f"""
        SELECT
            {db_col} as label,
            SUM({_sql_numeric_expr("order_price_in_aed")}) as revenue,
            COUNT(DISTINCT order_number) as orders,
            SUM({_sql_numeric_expr("cogs_in_aed")}) as total_cogs
        FROM fact_orders
        WHERE {where_sql}
        GROUP BY 1
        HAVING SUM({_sql_numeric_expr("order_price_in_aed")}) > 0
        ORDER BY 2 DESC
        LIMIT 50
    """

    logger.info(
        "🔍 Executing Leaderboard Query (dimension=%s, include_trend=%s, include_growth=%s)",
        dimension,
        include_trend,
        include_growth,
    )
    _log_filters_debug("🔍 Leaderboard Query", filters)
    df = get_data(query, params)

    if df.empty:
        logger.info("⚠️ No leaderboard data found for the given filters")
        return LeaderboardResponse(title=f"Top {dimension.title()}s", dimension=dimension, data=[])

    # 3. Process Metrics in Pandas

    # A. Calculate Market Share
    total_view_revenue = df['revenue'].sum()
    df['share_pct'] = (df['revenue'] / total_view_revenue * 100).fillna(0)

    # B. Calculate Margin %
    # Safe division: if revenue is 0, margin is None. If COGS is missing (NaN), result is NaN.
    df['gross_profit'] = df['revenue'] - df['total_cogs']
    df['margin_pct'] = (df['gross_profit'] / df['revenue'] * 100).round(2)

    logger.info(
        "✅ Leaderboard analyzed (dimension=%s, rows=%s, total_revenue=%s)",
        dimension,
        len(df),
        round(float(total_view_revenue), 2),
    )

    # 4. Fetch Trend Data (if requested)
    trend_data = {}
    if include_trend and not df.empty:
        # Get the list of entities (top 50 from leaderboard)
        entities = df['label'].tolist()

        # Build placeholders for IN clause
        entity_placeholders = [f":entity_{i}" for i in range(len(entities))]
        for i, entity in enumerate(entities):
            params[f"entity_{i}"] = entity

        # Query for last 6 months of monthly revenue per entity
        trend_query = f"""
            SELECT
                {db_col} as label,
                {_sql_date_label_expr("order_date", "month")} as month,
                SUM({_sql_numeric_expr("order_price_in_aed")}) as monthly_revenue
            FROM fact_orders
            WHERE {_sql_date_cast_expr("order_date")} >= {_sql_cutoff_from_max_date("order_date", months=6)}
              AND {db_col} IN ({','.join(entity_placeholders)})
            GROUP BY 1, 2
            ORDER BY 1, 2 ASC
        """

        trend_df = get_data(trend_query, params)

        if not trend_df.empty:
            # Get sorted unique months for consistent ordering
            all_months = sorted(trend_df['month'].unique())

            # Group by entity and create trend arrays
            for entity in entities:
                entity_trends = trend_df[trend_df['label'] == entity]
                # Create month-value mapping
                month_values = dict(zip(entity_trends['month'], entity_trends['monthly_revenue']))
                # Build trend array with 0 for missing months
                trend_data[entity] = [float(month_values.get(m, 0)) for m in all_months]

            logger.info(
                "📈 Trend data fetched (entities=%s, months=%s)",
                len(trend_data),
                len(all_months),
            )

    # 5. Calculate Growth Data (if requested and dimension is 'product')
    growth_data = {}
    if include_growth and dimension == 'product' and filters.start_date and filters.end_date:
        # Calculate prior period
        date_range_days = (filters.end_date - filters.start_date).days
        prior_start = filters.start_date - timedelta(days=date_range_days + 1)
        prior_end = filters.start_date - timedelta(days=1)

        entities = df['label'].tolist()
        entity_placeholders = [f":growth_entity_{i}" for i in range(len(entities))]
        growth_params = {
            "current_start": str(filters.start_date),
            "current_end": str(filters.end_date),
            "prior_start": str(prior_start),
            "prior_end": str(prior_end)
        }
        for i, entity in enumerate(entities):
            growth_params[f"growth_entity_{i}"] = entity

        growth_query = f"""
            WITH current_period AS (
                SELECT product_name, SUM({_sql_numeric_expr("order_price_in_aed")}) as revenue
                FROM fact_orders
                WHERE {_sql_date_cast_expr("order_date")} >= :current_start AND {_sql_date_cast_expr("order_date")} <= :current_end
                  AND product_name IN ({','.join(entity_placeholders)})
                GROUP BY product_name
            ),
            prior_period AS (
                SELECT product_name, SUM({_sql_numeric_expr("order_price_in_aed")}) as revenue
                FROM fact_orders
                WHERE {_sql_date_cast_expr("order_date")} >= :prior_start AND {_sql_date_cast_expr("order_date")} <= :prior_end
                  AND product_name IN ({','.join(entity_placeholders)})
                GROUP BY product_name
            )
            SELECT
                c.product_name,
                c.revenue as current_revenue,
                COALESCE(p.revenue, 0) as prior_revenue,
                CASE WHEN p.revenue > 0
                    THEN ((c.revenue - p.revenue) / p.revenue * 100)
                    ELSE NULL
                END as growth_pct
            FROM current_period c
            LEFT JOIN prior_period p ON c.product_name = p.product_name
        """

        growth_df = get_data(growth_query, growth_params)
        if not growth_df.empty:
            for _, row in growth_df.iterrows():
                if row['growth_pct'] is not None:
                    growth_data[row['product_name']] = round(float(row['growth_pct']), 2)
            logger.info("📈 Growth data calculated (products=%s)", len(growth_data))

    # 6. Map to Response
    data_points = []
    for _, row in df.iterrows():
        # Handle Margin edge cases (Infinity or NaN)
        margin = row['margin_pct']
        if pd.isna(margin) or margin == float('inf') or margin == float('-inf'):
            margin = None

        # Get trend for this entity (if available)
        entity_trend = trend_data.get(str(row['label']), None) if include_trend else None

        # Get growth percentage (if calculated)
        entity_growth = growth_data.get(str(row['label']), 0.0) if include_growth and dimension == 'product' else 0.0

        # Calculate failure rate for products (mock data)
        failure_rate = None
        if dimension == 'product' and include_growth:
            failure_rate = mock_failure_rate(str(row['label']))

        data_points.append(LeaderboardRow(
            label=str(row['label']),
            revenue=float(row['revenue']),
            orders=int(row['orders']),
            margin_pct=margin,
            share_pct=float(row['share_pct']),
            growth_pct=entity_growth,
            trend=entity_trend,
            failure_rate=failure_rate
        ))

    # Log insights
    if data_points:
        top_entity = data_points[0]
        avg_margin = sum(p.margin_pct for p in data_points if p.margin_pct is not None) / max(len([p for p in data_points if p.margin_pct is not None]), 1)
        logger.info(
            "📊 Top entity (dimension=%s, label=%s, revenue=%s, share_pct=%s, avg_margin=%s)",
            dimension,
            top_entity.label,
            round(float(top_entity.revenue), 2),
            round(float(top_entity.share_pct), 1),
            round(float(avg_margin), 1),
        )

    return LeaderboardResponse(
        title=f"Top {dimension.title()}s",
        dimension=dimension,
        data=data_points
    )


@router.post("/top-products", response_model=ChartResponse)
def get_top_products(filters: DashboardFilters, limit: int = 10):
    """
    Returns top N products by revenue.
    
    **Request Body**:
    ```json
    {
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "currency": "AED",
        "brands": ["Apple", "Samsung"]
    }
    ```
    
    **Query Parameters**:
    - `limit`: Number of top products to return (default: 10)
    
    **Response**: Bar chart data with product names (truncated to 30 chars) and revenue
    """
    where_sql, params = build_where_clause(filters)
    
    query = f"""
        SELECT 
            product_name,
            SUM({_sql_numeric_expr("order_price_in_aed")}) as total_revenue
        FROM fact_orders
        WHERE {where_sql}
        GROUP BY product_name
        ORDER BY total_revenue DESC
        LIMIT {limit}
    """
    
    logger.info("🔍 Executing Top Products Query (limit=%s)", limit)
    _log_filters_debug("🔍 Top Products Query", filters)
    df = get_data(query, params)
    
    data_points = []
    if not df.empty:
        data_points = [
            ChartPoint(
                label=str(row['product_name'])[:30] + ("..." if len(str(row['product_name'])) > 30 else ""), 
                value=float(row['total_revenue'])
            ) 
            for _, row in df.iterrows()
        ]
        logger.info("✅ Top Products returned (count=%s)", len(data_points))
    else:
        logger.info("⚠️ No product data found for the given filters")

    return ChartResponse(
        title=f"Top {limit} Products by Revenue",
        chart_type="bar",
        data=data_points,
        x_axis_label="Product",
        y_axis_label="Revenue (AED)"
    )


@router.post("/scatter", response_model=ScatterResponse)
def get_client_scatter(filters: DashboardFilters):
    """
    Returns client-level scatter plot data for Market Analysis.
    
    **Analysis Focus:**
    - Visualizes client behavior patterns (high-volume vs high-value)
    - Color-codes clients by their dominant product type
    - Calculates Average Order Value (AOV) for each client
    
    **Metrics Per Client:**
    - Total Revenue: Sum of all orders
    - Total Orders: Count of distinct orders
    - AOV: Revenue / Orders
    - Dominant Type: Product type generating most revenue
    
    **Request Body:**
    ```json
    {
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "currency": "AED",
        "countries": ["UAE"],
        "product_types": []
    }
    ```
    
    **Response**: List of client data points with behavior metrics
    """
    where_sql, params = build_where_clause(filters)
    
    # 1. Fetch Granular Data (Client + Type level)
    # We group by Type here to determine the "Dominant" category later in Pandas
    query = f"""
        SELECT 
            client_name,
            client_country,
            order_type,
            SUM({_sql_numeric_expr("order_price_in_aed")}) as type_revenue,
            COUNT(DISTINCT order_number) as type_orders
        FROM fact_orders
        WHERE {where_sql}
        GROUP BY client_name, order_type
    """
    
    logger.info("🔍 Executing Client Scatter Query")
    _log_filters_debug("🔍 Client Scatter Query", filters)
    raw_df = get_data(query, params)
    
    if raw_df.empty:
        logger.info("⚠️ No client data found for the given filters")
        return ScatterResponse(data=[])

    # 2. Process in Pandas to find Totals + Dominant Type
    
    # A. Calculate Totals per Client
    # Group by client_name to get sum of revenue and orders across all types
    client_totals = raw_df.groupby('client_name').agg({
        'type_revenue': 'sum',
        'type_orders': 'sum',
        'client_country': 'first'  # Take the first country found
    }).rename(columns={'type_revenue': 'total_revenue', 'type_orders': 'total_orders'})
    
    # B. Find Dominant Type (The type with max revenue for that client)
    # Sort by revenue desc, then drop duplicates to keep top entry per client
    dominant_types = raw_df.sort_values('type_revenue', ascending=False).drop_duplicates('client_name')[['client_name', 'order_type']]
    
    # C. Merge
    final_df = client_totals.merge(dominant_types, on='client_name', how='left')
    
    # D. Calculate AOV
    final_df['aov'] = final_df['total_revenue'] / final_df['total_orders']
    
    # Reset index to make client_name a regular column
    final_df = final_df.reset_index()

    # Calculate medians from FULL dataset (before limiting to top 500)
    # These represent true market-wide thresholds for segmentation
    total_clients = len(final_df)
    median_orders = int(np.median(final_df['total_orders'].values)) if total_clients > 0 else 0
    median_revenue = float(np.median(final_df['total_revenue'].values)) if total_clients > 0 else 0.0
    logger.info(
        "📊 Full dataset medians (clients=%s, median_orders=%s, median_revenue=%s)",
        total_clients,
        median_orders,
        round(float(median_revenue), 2),
    )

    # Limit to top 500 clients by revenue for performance (avoids rendering thousands of SVG elements)
    if total_clients > 500:
        final_df = final_df.nlargest(500, 'total_revenue')
        logger.info(
            "✅ Client Scatter returning top 500 (total_clients=%s)",
            total_clients,
        )
    else:
        logger.info("✅ Client Scatter analyzed (clients=%s)", total_clients)
    
    # 3. Map to Response
    data_points = []
    for _, row in final_df.iterrows():
        # Handle potential NaNs safely
        country = row['client_country'] if pd.notna(row['client_country']) else "Unknown"
        dom_type = row['order_type'] if pd.notna(row['order_type']) else "Unknown"
        
        data_points.append(ScatterPoint(
            client_name=str(row['client_name']),
            country=str(country),
            total_revenue=float(row['total_revenue']),
            total_orders=int(row['total_orders']),
            aov=float(row['aov']),
            dominant_type=str(dom_type)
        ))
    
    # Log summary stats
    if data_points:
        avg_aov = sum(p.aov for p in data_points) / len(data_points)
        max_revenue_client = max(data_points, key=lambda p: p.total_revenue)
        logger.info(
            "📊 Client Insights calculated (avg_aov=%s, top_client_revenue=%s)",
            round(float(avg_aov), 2),
            round(float(max_revenue_client.total_revenue), 2),
        )
        if settings.DEBUG:
            logger.debug(
                "📊 Client Insights top_client=%s",
                max_revenue_client.client_name,
            )

    return ScatterResponse(
        data=data_points,
        total_clients=total_clients,
        median_orders=median_orders,
        median_revenue=median_revenue
    )


@router.get("/filter-options", response_model=FilterOptionsResponse)
def get_filter_options():
    """
    Returns distinct values for all filter dropdowns.
    
    **Purpose**: Populate multi-select dropdowns in the filter UI
    
    **Queries**:
    - Clients: Distinct client names
    - Brands: Distinct product brands
    - Suppliers: Distinct supplier names
    - Countries: Distinct client countries
    
    **Response**: Lists of unique string values for each dimension
    """
    logger.info("🔍 Fetching filter options from database")
    
    # Query 1: Get distinct clients
    clients_query = """
        SELECT DISTINCT client_name 
        FROM fact_orders 
        WHERE client_name IS NOT NULL
        ORDER BY client_name
    """
    clients_df = get_data(clients_query)
    clients = clients_df['client_name'].tolist() if not clients_df.empty else []
    
    # Query 2: Get distinct brands
    brands_query = """
        SELECT DISTINCT product_brand 
        FROM fact_orders 
        WHERE product_brand IS NOT NULL
        ORDER BY product_brand
    """
    brands_df = get_data(brands_query)
    brands = brands_df['product_brand'].tolist() if not brands_df.empty else []
    
    # Query 3: Get distinct suppliers
    suppliers_query = """
        SELECT DISTINCT supplier_name 
        FROM fact_orders 
        WHERE supplier_name IS NOT NULL
        ORDER BY supplier_name
    """
    suppliers_df = get_data(suppliers_query)
    suppliers = suppliers_df['supplier_name'].tolist() if not suppliers_df.empty else []
    
    # Query 4: Get distinct countries
    countries_query = """
        SELECT DISTINCT client_country 
        FROM fact_orders 
        WHERE client_country IS NOT NULL
        ORDER BY client_country
    """
    countries_df = get_data(countries_query)
    countries = countries_df['client_country'].tolist() if not countries_df.empty else []
    
    # Query 5: Get distinct currencies
    currencies_query = """
        SELECT DISTINCT currency 
        FROM fact_orders 
        WHERE currency IS NOT NULL
        ORDER BY currency
    """
    currencies_df = get_data(currencies_query)
    currencies = currencies_df['currency'].tolist() if not currencies_df.empty else []
    
    logger.info(
        "✅ Filter options loaded (clients=%s, brands=%s, suppliers=%s, countries=%s, currencies=%s)",
        len(clients),
        len(brands),
        len(suppliers),
        len(countries),
        len(currencies),
    )
    
    return FilterOptionsResponse(
        clients=clients,
        brands=brands,
        suppliers=suppliers,
        countries=countries,
        currencies=currencies
    )


# ============================================================================
# OVERVIEW V2 ENDPOINTS (Executive Dashboard Enhancements)
# ============================================================================

# Country code mapping for geography map
COUNTRY_CODE_MAP = {
    "United Arab Emirates": "AE",
    "UAE": "AE",
    "Saudi Arabia": "SA",
    "KSA": "SA",
    "Kuwait": "KW",
    "Qatar": "QA",
    "Bahrain": "BH",
    "Oman": "OM",
    "Egypt": "EG",
    "Jordan": "JO",
    "Lebanon": "LB",
    "Iraq": "IQ",
    "Morocco": "MA",
    "Tunisia": "TN",
    "Algeria": "DZ",
    "United Kingdom": "GB",
    "UK": "GB",
    "United States": "US",
    "United States of America": "US",
    "USA": "US",
    "Germany": "DE",
    "France": "FR",
    "India": "IN",
    "Pakistan": "PK",
    "Philippines": "PH",
    "Bangladesh": "BD",
    "Sri Lanka": "LK",
    "Nepal": "NP",
    "Canada": "CA",
    "Australia": "AU",
    "China": "CN",
    "Japan": "JP",
    "South Korea": "KR",
    "Singapore": "SG",
    "Malaysia": "MY",
    "Indonesia": "ID",
    "Thailand": "TH",
    "Vietnam": "VN",
    "Turkey": "TR",
    "Russia": "RU",
    "Brazil": "BR",
    "Mexico": "MX",
    "South Africa": "ZA",
    "Nigeria": "NG",
    "Kenya": "KE",
}


@router.get("/stuck-orders", response_model=StuckOrdersResponse)
def get_stuck_orders(limit: int = 10):
    """
    Returns MOCK stuck/failed/pending orders for demo purposes.
    
    ⚠️ MOCK DATA: The database does not have an order_status column.
    This endpoint returns realistic mock data for development/demo purposes.
    
    When real order_status data becomes available, replace with actual SQL query.
    
    **Response:**
    ```json
    {
        "total_count": 5,
        "orders": [
            {
                "order_number": "ORD-99200",
                "order_date": "2026-01-01",
                "status": "stuck",
                "age_days": 4,
                "product_name": "Amazon Gift Card $50",
                "client_name": "Acme Corp",
                "amount": 250.00
            }
        ],
        "is_mock": true
    }
    ```
    """
    logger.info("📋 Generating mock stuck orders (limit=%s)", limit)
    
    # Generate realistic mock data
    mock_statuses: list[Literal['stuck', 'failed', 'pending']] = ['stuck', 'failed', 'pending']
    mock_products = [
        'Amazon Gift Card $50', 
        'iTunes Gift Card $25', 
        'Google Play $100', 
        'Netflix Subscription', 
        'Spotify Premium', 
        'PlayStation Store $50',
        'Xbox Gift Card $25',
        'Steam Wallet $100'
    ]
    mock_clients = [
        'Acme Corporation', 
        'Global Trade LLC', 
        'Tech Solutions Inc', 
        'MediaBuy International',
        'Digital Ventures Ltd'
    ]
    
    orders = []
    num_orders = min(limit, random.randint(3, 6))  # Random 3-6 mock orders
    
    for i in range(num_orders):
        age = random.randint(1, 7)
        orders.append(StuckOrder(
            order_number=f"ORD-{99200 + i}",
            order_date=(datetime.now() - timedelta(days=age)).strftime("%Y-%m-%d"),
            status=mock_statuses[i % 3],
            age_days=age,
            product_name=mock_products[i % len(mock_products)],
            client_name=mock_clients[i % len(mock_clients)],
            amount=round(random.uniform(50, 500), 2)
        ))
    
    # Sort by age descending (oldest first)
    orders.sort(key=lambda x: x.age_days, reverse=True)
    
    logger.info("✅ Generated mock stuck orders (count=%s)", len(orders))
    
    return StuckOrdersResponse(
        total_count=len(orders),
        orders=orders,
        is_mock=True
    )


@router.get("/sparkline/{metric}", response_model=SparklineResponse)
def get_sparkline_data(metric: str, days: int = 30):
    """
    Returns daily aggregated data for sparkline visualization in KPI cards.
    
    **Path Parameters:**
    - metric: 'orders' | 'revenue'
    
    **Query Parameters:**
    - days: Number of days of data (default: 30)
    
    **Response:**
    ```json
    {
        "metric": "revenue",
        "data": [
            {"date": "2025-12-06", "value": 125000},
            {"date": "2025-12-07", "value": 132000},
            ...
        ]
    }
    ```
    """
    if metric not in ['orders', 'revenue']:
        raise HTTPException(status_code=400, detail=f"Invalid metric '{metric}'. Must be 'orders' or 'revenue'")
    
    logger.info("📊 Fetching sparkline data (metric=%s, days=%s)", metric, days)
    
    # Build aggregation expression based on metric
    if metric == "orders":
        agg_expr = "COUNT(DISTINCT order_number)"
    else:  # revenue
        agg_expr = f"SUM({_sql_numeric_expr('order_price_in_aed')})"

    # Get the most recent date in the database and work backwards from there
    # This handles cases where data is historical (e.g., June 2025 only)
    cutoff_expr = _sql_cutoff_from_max_date("order_date", days=days)
    order_date_expr = _sql_date_cast_expr("order_date")
    query = f"""
        SELECT
            {order_date_expr} as date,
            {agg_expr} as value
        FROM fact_orders
        WHERE {order_date_expr} >= {cutoff_expr}
        GROUP BY 1
        ORDER BY 1
    """
    
    df = get_data(query)
    
    if df.empty:
        logger.info("⚠️ No sparkline data found (metric=%s)", metric)
        return SparklineResponse(metric=metric, data=[])
    
    data = [
        SparklinePoint(date=str(row['date']), value=float(row['value'] or 0))
        for _, row in df.iterrows()
    ]
    
    logger.info("✅ Retrieved sparkline points (metric=%s, count=%s)", metric, len(data))
    
    return SparklineResponse(metric=metric, data=data)


@router.post("/geography", response_model=GeographyResponse)
def get_geography_data(filters: DashboardFilters):
    """
    Returns revenue and order metrics aggregated by country.
    Used for the interactive choropleth map in Zone 4.
    
    **Response:**
    ```json
    {
        "data": [
            {
                "country_code": "AE",
                "country_name": "United Arab Emirates",
                "revenue": 3100000.00,
                "orders": 18234,
                "clients": 45
            }
        ]
    }
    ```
    """
    where_sql, params = build_where_clause(filters)
    
    logger.info("🌍 Fetching geography data")
    _log_filters_debug("🌍 Geography Query", filters)
    
    query = f"""
        SELECT 
            client_country as country_name,
            SUM({_sql_numeric_expr("order_price_in_aed")}) as revenue,
            COUNT(DISTINCT order_number) as orders,
            COUNT(DISTINCT client_name) as clients
        FROM fact_orders
        WHERE {where_sql}
          AND client_country IS NOT NULL
        GROUP BY client_country
        ORDER BY revenue DESC
    """
    
    df = get_data(query, params)
    
    if df.empty:
        logger.info("⚠️ No geography data found")
        return GeographyResponse(data=[])
    
    data = []
    for _, row in df.iterrows():
        country_name = row['country_name']
        # Map country name to ISO code
        country_code = COUNTRY_CODE_MAP.get(country_name, country_name[:2].upper() if country_name else "XX")
        
        data.append(CountryData(
            country_code=country_code,
            country_name=country_name,
            revenue=float(row['revenue'] or 0),
            orders=int(row['orders'] or 0),
            clients=int(row['clients'] or 0)
        ))
    
    logger.info("✅ Retrieved geography data (countries=%s)", len(data))
    
    return GeographyResponse(data=data)


@router.post("/top-products-by-status", response_model=TopProductsByStatusResponse)
def get_top_products_by_status(filters: DashboardFilters, limit: int = 10):
    """
    Returns top products with revenue breakdown by order status.
    
    ⚠️ MOCK STATUS DATA: The database does not have an order_status column.
    This endpoint queries real product totals but applies a mock 95%/5% split
    for completed vs failed/stuck revenue.
    
    **Query Parameters:**
    - limit: Number of top products to return (default: 10)
    
    **Response:**
    ```json
    {
        "data": [
            {
                "product_name": "Amazon Gift Card $50",
                "product_sku": "AMZN-GC-50",
                "brand": "Amazon",
                "total_revenue": 400000,
                "completed_revenue": 380000,
                "failed_revenue": 12000,
                "stuck_revenue": 8000,
                "completed_count": 2340,
                "failed_count": 70,
                "stuck_count": 47
            }
        ],
        "is_mock": true
    }
    ```
    """
    where_sql, params = build_where_clause(filters)
    params['limit'] = limit
    
    logger.info("📦 Fetching top products by status (limit=%s)", limit)
    _log_filters_debug("📦 Top Products by Status", filters)
    
    # Query real product totals
    query = f"""
        SELECT 
            product_name,
            product_sku,
            product_brand as brand,
            SUM({_sql_numeric_expr("order_price_in_aed")}) as total_revenue,
            COUNT(DISTINCT order_number) as total_count
        FROM fact_orders
        WHERE {where_sql}
          AND product_name IS NOT NULL
        GROUP BY product_name, product_sku, product_brand
        ORDER BY total_revenue DESC
        LIMIT :limit
    """
    
    df = get_data(query, params)
    
    if df.empty:
        logger.info("⚠️ No product data found")
        return TopProductsByStatusResponse(data=[], is_mock=True)
    
    # Apply mock status distribution to real totals
    # Vary the completion rate slightly per product for realism
    data = []
    for _, row in df.iterrows():
        total_rev = float(row['total_revenue'] or 0)
        total_count = int(row['total_count'] or 0)
        sku_value = row.get("product_sku")
        sku = None if pd.isna(sku_value) else str(sku_value)
        
        # Vary completion rate between 92-98% for realism
        completion_rate = random.uniform(0.92, 0.98)
        failed_rate = random.uniform(0.01, 0.05)
        stuck_rate = 1.0 - completion_rate - failed_rate
        
        data.append(ProductByStatus(
            product_name=row['product_name'],
            product_sku=sku,
            brand=row['brand'] or "Unknown",
            total_revenue=total_rev,
            completed_revenue=round(total_rev * completion_rate, 2),
            failed_revenue=round(total_rev * failed_rate, 2),
            stuck_revenue=round(total_rev * stuck_rate, 2),
            completed_count=int(total_count * completion_rate),
            failed_count=max(1, int(total_count * failed_rate)),
            stuck_count=max(0, int(total_count * stuck_rate))
        ))
    
    logger.info("✅ Retrieved top products with status breakdown (count=%s)", len(data))
    
    return TopProductsByStatusResponse(data=data, is_mock=True)


@router.post("/top-brands-by-type", response_model=TopBrandsByTypeResponse)
def get_top_brands_by_type(filters: DashboardFilters, limit: int = 10):
    """
    Returns top brands with revenue breakdown by product type (gift_card vs merchandise).
    Uses real data from the order_type column.
    
    **Query Parameters:**
    - limit: Number of top brands to return (default: 10)
    
    **Response:**
    ```json
    {
        "data": [
            {
                "brand_name": "Amazon",
                "total_revenue": 500000,
                "gift_card_revenue": 400000,
                "merchandise_revenue": 100000,
                "gift_card_orders": 2000,
                "merchandise_orders": 500
            }
        ]
    }
    ```
    """
    where_sql, params = build_where_clause(filters)
    params['limit'] = limit
    
    logger.info("🏷️ Fetching top brands by type (limit=%s)", limit)
    _log_filters_debug("🏷️ Top Brands by Type", filters)
    
    query = f"""
        SELECT 
            product_brand as brand_name,
            SUM({_sql_numeric_expr("order_price_in_aed")}) as total_revenue,
            SUM(CASE WHEN order_type = 'gift_card' THEN {_sql_numeric_expr("order_price_in_aed")} ELSE 0 END) as gift_card_revenue,
            SUM(CASE WHEN order_type = 'merchandise' THEN {_sql_numeric_expr("order_price_in_aed")} ELSE 0 END) as merchandise_revenue,
            COUNT(DISTINCT CASE WHEN order_type = 'gift_card' THEN order_number END) as gift_card_orders,
            COUNT(DISTINCT CASE WHEN order_type = 'merchandise' THEN order_number END) as merchandise_orders
        FROM fact_orders
        WHERE {where_sql}
          AND product_brand IS NOT NULL
        GROUP BY product_brand
        ORDER BY total_revenue DESC
        LIMIT :limit
    """
    
    df = get_data(query, params)
    
    if df.empty:
        logger.info("⚠️ No brand data found")
        return TopBrandsByTypeResponse(data=[])
    
    data = [
        BrandByType(
            brand_name=row['brand_name'],
            total_revenue=float(row['total_revenue'] or 0),
            gift_card_revenue=float(row['gift_card_revenue'] or 0),
            merchandise_revenue=float(row['merchandise_revenue'] or 0),
            gift_card_orders=int(row['gift_card_orders'] or 0),
            merchandise_orders=int(row['merchandise_orders'] or 0)
        )
        for _, row in df.iterrows()
    ]
    
    logger.info("✅ Retrieved top brands by type (count=%s)", len(data))

    return TopBrandsByTypeResponse(data=data)


# ============================================================================
# CATALOG ANALYSIS ENDPOINTS (Product Performance Analysis)
# ============================================================================

def mock_failure_rate(product_name: str) -> float:
    """Returns consistent failure rate (0.1-3.0%) for same product."""
    hash_val = int(hashlib.md5(product_name.encode()).hexdigest(), 16)
    return round(0.1 + (hash_val % 30) / 10.0, 2)


@router.post("/catalog/kpis", response_model=CatalogKPIs)
def get_catalog_kpis(filters: DashboardFilters):
    """
    Returns catalog-specific KPIs with period-over-period comparison.

    **Metrics:**
    - Active SKUs: Count of distinct product SKUs with quantity > 0
    - Currency Count: Number of distinct currencies used
    - Avg Margin: Average profit margin percentage (with COGS check)
    - Supplier Health: % of suppliers with < 30% revenue concentration

    **Request Body:**
    ```json
    {
        "start_date": "2025-06-01",
        "end_date": "2025-06-30",
        "brands": [],
        "countries": []
    }
    ```
    """
    where_sql, params = build_where_clause(filters)

    logger.info("📦 Executing Catalog KPIs Query")
    _log_filters_debug("📦 Catalog KPIs Query", filters)

    # Calculate prior period for comparison
    if filters.start_date and filters.end_date:
        date_range_days = (filters.end_date - filters.start_date).days
        prior_start = filters.start_date - timedelta(days=date_range_days + 1)
        prior_end = filters.start_date - timedelta(days=1)
        prior_params = params.copy()
        prior_params["start_date"] = str(prior_start)
        prior_params["end_date"] = str(prior_end)
        prior_where_sql = where_sql.replace(f":start_date", f"'{prior_start}'").replace(f":end_date", f"'{prior_end}'")
    else:
        prior_start = None
        prior_end = None

    # Query 1: Active SKUs
    sku_query = f"""
        SELECT COUNT(DISTINCT product_sku) as active_skus
        FROM fact_orders
        WHERE {where_sql} AND product_sku IS NOT NULL AND {_sql_numeric_expr("quantity")} > 0
    """
    sku_df = get_data(sku_query, params)
    active_skus = int(sku_df.iloc[0]['active_skus']) if not sku_df.empty else 0

    # Query 2: Currency count
    currency_query = f"""
        SELECT COUNT(DISTINCT currency) as currency_count
        FROM fact_orders
        WHERE {where_sql}
    """
    currency_df = get_data(currency_query, params)
    currency_count = int(currency_df.iloc[0]['currency_count']) if not currency_df.empty else 0

    # Query 3: Average margin (only where COGS exists)
    margin_query = f"""
        SELECT AVG(
            ({_sql_numeric_expr("order_price_in_aed")} - COALESCE({_sql_numeric_expr("cogs_in_aed")}, 0)) / NULLIF({_sql_numeric_expr("order_price_in_aed")}, 0) * 100
        ) as avg_margin
        FROM fact_orders
        WHERE {where_sql} AND {_sql_numeric_expr("cogs_in_aed")} > 0 AND {_sql_numeric_expr("order_price_in_aed")} > 0
    """
    margin_df = get_data(margin_query, params)
    avg_margin = float(margin_df.iloc[0]['avg_margin']) if not margin_df.empty and margin_df.iloc[0]['avg_margin'] is not None else None

    # Query 4: Supplier health (% with < 30% concentration)
    # SQLite doesn't support FILTER, so we use CASE expressions
    supplier_query = f"""
        WITH total_revenue AS (
            SELECT SUM({_sql_numeric_expr("order_price_in_aed")}) as total
            FROM fact_orders
            WHERE {where_sql}
        ),
        supplier_shares AS (
            SELECT
                supplier_name,
                SUM({_sql_numeric_expr("order_price_in_aed")}) * 100.0 / (SELECT total FROM total_revenue) as share_pct
            FROM fact_orders
            WHERE {where_sql}
            GROUP BY supplier_name
        )
        SELECT
            CAST(SUM(CASE WHEN share_pct < 30 THEN 1 ELSE 0 END) AS FLOAT) * 100.0 /
                NULLIF(COUNT(*), 0) as health_pct,
            SUM(CASE WHEN share_pct >= 30 THEN 1 ELSE 0 END) as at_risk_count
        FROM supplier_shares
    """
    supplier_df = get_data(supplier_query, params)

    if not supplier_df.empty and supplier_df.iloc[0]['health_pct'] is not None:
        supplier_health = float(supplier_df.iloc[0]['health_pct'])
        at_risk_suppliers = int(supplier_df.iloc[0]['at_risk_count'] or 0)
    else:
        supplier_health = 100.0
        at_risk_suppliers = 0

    # Calculate prior period values for comparison
    active_skus_change = None
    currency_count_change = None
    avg_margin_change = None

    if prior_start and prior_end:
        # Prior SKUs
        prior_sku_query = f"""
            SELECT COUNT(DISTINCT product_sku) as active_skus
            FROM fact_orders
            WHERE {_sql_date_cast_expr("order_date")} >= :prior_start AND {_sql_date_cast_expr("order_date")} <= :prior_end
              AND product_sku IS NOT NULL AND {_sql_numeric_expr("quantity")} > 0
        """
        prior_sku_params = {"prior_start": str(prior_start), "prior_end": str(prior_end)}

        # Add other filters (excluding date filters which we override)
        if filters.countries:
            for i, val in enumerate(filters.countries):
                prior_sku_params[f"country_{i}"] = val
        if filters.brands:
            for i, val in enumerate(filters.brands):
                prior_sku_params[f"brand_{i}"] = val
        if filters.suppliers:
            for i, val in enumerate(filters.suppliers):
                prior_sku_params[f"supplier_{i}"] = val

        prior_sku_df = get_data(prior_sku_query, prior_sku_params)
        if not prior_sku_df.empty:
            prior_skus = int(prior_sku_df.iloc[0]['active_skus'] or 0)
            if prior_skus > 0:
                active_skus_change = round((active_skus - prior_skus) / prior_skus * 100, 2)

        # Prior currency count
        prior_currency_query = f"""
            SELECT COUNT(DISTINCT currency) as currency_count
            FROM fact_orders
            WHERE {_sql_date_cast_expr("order_date")} >= :prior_start AND {_sql_date_cast_expr("order_date")} <= :prior_end
        """
        prior_currency_df = get_data(prior_currency_query, prior_sku_params)
        if not prior_currency_df.empty:
            prior_currencies = int(prior_currency_df.iloc[0]['currency_count'] or 0)
            currency_count_change = currency_count - prior_currencies

        # Prior avg margin
        prior_margin_query = f"""
            SELECT AVG(
                ({_sql_numeric_expr("order_price_in_aed")} - COALESCE({_sql_numeric_expr("cogs_in_aed")}, 0)) / NULLIF({_sql_numeric_expr("order_price_in_aed")}, 0) * 100
            ) as avg_margin
            FROM fact_orders
            WHERE {_sql_date_cast_expr("order_date")} >= :prior_start AND {_sql_date_cast_expr("order_date")} <= :prior_end
              AND {_sql_numeric_expr("cogs_in_aed")} > 0 AND {_sql_numeric_expr("order_price_in_aed")} > 0
        """
        prior_margin_df = get_data(prior_margin_query, prior_sku_params)
        if not prior_margin_df.empty and prior_margin_df.iloc[0]['avg_margin'] is not None and avg_margin is not None:
            prior_margin = float(prior_margin_df.iloc[0]['avg_margin'])
            avg_margin_change = round(avg_margin - prior_margin, 2)

    avg_margin_display = f"{avg_margin:.1f}%" if avg_margin is not None else "N/A"
    logger.info(
        "✅ Catalog KPIs calculated (active_skus=%s, currencies=%s, avg_margin=%s, supplier_health=%s)",
        active_skus,
        currency_count,
        avg_margin_display,
        round(float(supplier_health), 1),
    )

    return CatalogKPIs(
        active_skus=active_skus,
        active_skus_change=active_skus_change,
        currency_count=currency_count,
        currency_count_change=currency_count_change,
        avg_margin=round(avg_margin, 2) if avg_margin is not None else None,
        avg_margin_change=avg_margin_change,
        supplier_health=round(supplier_health, 2),
        at_risk_suppliers=at_risk_suppliers
    )


@router.post("/catalog/scatter", response_model=ProductScatterResponse)
def get_product_scatter(filters: DashboardFilters):
    """
    Returns product-level scatter plot data for Catalog Analysis.

    **Analysis Focus:**
    - Visualizes product performance (revenue vs quantity)
    - Assigns quadrants: cash_cow, premium_niche, penny_stock, dead_stock
    - Returns top 500 products by revenue for performance

    **Quadrant Logic:**
    - High Revenue + High Quantity = Cash Cow
    - High Revenue + Low Quantity = Premium Niche
    - Low Revenue + High Quantity = Penny Stock
    - Low Revenue + Low Quantity = Dead Stock

    **Request Body:**
    ```json
    {
        "start_date": "2025-06-01",
        "end_date": "2025-06-30",
        "brands": [],
        "countries": []
    }
    ```
    """
    where_sql, params = build_where_clause(filters)

    logger.info("📊 Executing Product Scatter Query")
    _log_filters_debug("📊 Product Scatter Query", filters)

    query = f"""
        SELECT
            product_name,
            product_sku,
            order_type,
            SUM({_sql_numeric_expr("order_price_in_aed")}) as total_revenue,
            SUM({_sql_numeric_expr("quantity")}) as total_quantity,
            COUNT(DISTINCT order_number) as total_orders,
            AVG(
                CASE WHEN {_sql_numeric_expr("order_price_in_aed")} > 0 AND {_sql_numeric_expr("cogs_in_aed")} > 0
                THEN ({_sql_numeric_expr("order_price_in_aed")} - COALESCE({_sql_numeric_expr("cogs_in_aed")}, 0)) / {_sql_numeric_expr("order_price_in_aed")} * 100
                ELSE NULL END
            ) as avg_margin
        FROM fact_orders
        WHERE {where_sql}
        GROUP BY product_name, product_sku, order_type
        HAVING SUM({_sql_numeric_expr("order_price_in_aed")}) > 0
    """

    df = get_data(query, params)

    if df.empty:
        logger.info("⚠️ No product scatter data found")
        return ProductScatterResponse(
            data=[],
            median_revenue=0.0,
            median_quantity=0.0,
            total_products=0
        )

    # Store total count before limiting
    total_products = len(df)

    # Limit to top 500 by revenue
    df = df.nlargest(500, 'total_revenue')

    # Calculate medians from limited dataset
    median_revenue = float(df['total_revenue'].median())
    median_quantity = float(df['total_quantity'].median())

    logger.info(
        "📊 Product Scatter prepared (total_products=%s, returned=%s, median_revenue=%s, median_quantity=%s)",
        total_products,
        len(df),
        round(float(median_revenue), 2),
        round(float(median_quantity), 2),
    )

    # Assign quadrants
    def assign_quadrant(row):
        if row['total_revenue'] > median_revenue:
            return 'cash_cow' if row['total_quantity'] > median_quantity else 'premium_niche'
        else:
            return 'penny_stock' if row['total_quantity'] > median_quantity else 'dead_stock'

    df['quadrant'] = df.apply(assign_quadrant, axis=1)

    # Map to response model
    data_points = []
    for _, row in df.iterrows():
        # Determine product type
        order_type = row['order_type']
        if pd.isna(order_type):
            product_type = 'merchandise'
        elif 'gift' in str(order_type).lower() or order_type == 'gift_card':
            product_type = 'gift_card'
        else:
            product_type = 'merchandise'

        # Handle margin
        margin = row['avg_margin']
        if pd.isna(margin) or margin == float('inf') or margin == float('-inf'):
            margin = None
        else:
            margin = round(float(margin), 2)

        data_points.append(ProductScatterPoint(
            product_name=str(row['product_name']),
            product_type=product_type,
            quantity=float(row['total_quantity']),
            revenue=float(row['total_revenue']),
            margin=margin,
            quadrant=row['quadrant']
        ))

    # Log summary
    quadrant_counts = df['quadrant'].value_counts().to_dict()
    logger.info("📈 Quadrant distribution: %s", quadrant_counts)

    return ProductScatterResponse(
        data=data_points,
        median_revenue=round(median_revenue, 2),
        median_quantity=round(median_quantity, 2),
        total_products=total_products
    )


@router.post("/catalog/movers", response_model=ProductMoversResponse)
def get_product_movers(filters: DashboardFilters):
    """
    Returns top 5 risers and fallers based on revenue growth %.

    **Analysis:**
    - Compares current period vs prior period (same duration)
    - Excludes products with zero prior revenue (avoids infinity)
    - Returns products with highest positive and negative growth

    **Request Body:**
    ```json
    {
        "start_date": "2025-06-01",
        "end_date": "2025-06-30",
        "brands": [],
        "countries": []
    }
    ```
    """
    logger.info("📈 Executing Product Movers Query")
    _log_filters_debug("📈 Product Movers Query", filters)

    # Calculate prior period
    if not filters.start_date or not filters.end_date:
        logger.info("⚠️ Date range required for movers calculation")
        return ProductMoversResponse(risers=[], fallers=[])

    date_range_days = (filters.end_date - filters.start_date).days
    prior_start = filters.start_date - timedelta(days=date_range_days + 1)
    prior_end = filters.start_date - timedelta(days=1)

    # Build filter conditions (excluding date)
    filter_conditions = []
    filter_params = {}

    if filters.countries:
        placeholders = [f":country_{i}" for i in range(len(filters.countries))]
        filter_conditions.append(f"client_country IN ({','.join(placeholders)})")
        for i, val in enumerate(filters.countries):
            filter_params[f"country_{i}"] = val

    if filters.brands:
        placeholders = [f":brand_{i}" for i in range(len(filters.brands))]
        filter_conditions.append(f"product_brand IN ({','.join(placeholders)})")
        for i, val in enumerate(filters.brands):
            filter_params[f"brand_{i}"] = val

    if filters.suppliers:
        placeholders = [f":supplier_{i}" for i in range(len(filters.suppliers))]
        filter_conditions.append(f"supplier_name IN ({','.join(placeholders)})")
        for i, val in enumerate(filters.suppliers):
            filter_params[f"supplier_{i}"] = val

    extra_filters = " AND " + " AND ".join(filter_conditions) if filter_conditions else ""

    # Query for risers (top 5 by growth DESC)
    params = {
        "current_start": str(filters.start_date),
        "current_end": str(filters.end_date),
        "prior_start": str(prior_start),
        "prior_end": str(prior_end),
        **filter_params
    }

    movers_query = f"""
        WITH current_period AS (
            SELECT product_name, SUM({_sql_numeric_expr("order_price_in_aed")}) as revenue
            FROM fact_orders
            WHERE {_sql_date_cast_expr("order_date")} >= :current_start AND {_sql_date_cast_expr("order_date")} <= :current_end
              {extra_filters}
            GROUP BY product_name
        ),
        prior_period AS (
            SELECT product_name, SUM({_sql_numeric_expr("order_price_in_aed")}) as revenue
            FROM fact_orders
            WHERE {_sql_date_cast_expr("order_date")} >= :prior_start AND {_sql_date_cast_expr("order_date")} <= :prior_end
              {extra_filters}
            GROUP BY product_name
        )
        SELECT
            c.product_name,
            c.revenue as current_revenue,
            COALESCE(p.revenue, 0) as prior_revenue,
            ((c.revenue - COALESCE(p.revenue, 0)) / NULLIF(p.revenue, 0) * 100) as growth_pct
        FROM current_period c
        LEFT JOIN prior_period p ON c.product_name = p.product_name
        WHERE p.revenue > 0
        ORDER BY growth_pct DESC
        LIMIT 5
    """

    risers_df = get_data(movers_query, params)

    # Query for fallers (bottom 5 by growth ASC)
    fallers_query = f"""
        WITH current_period AS (
            SELECT product_name, SUM({_sql_numeric_expr("order_price_in_aed")}) as revenue
            FROM fact_orders
            WHERE {_sql_date_cast_expr("order_date")} >= :current_start AND {_sql_date_cast_expr("order_date")} <= :current_end
              {extra_filters}
            GROUP BY product_name
        ),
        prior_period AS (
            SELECT product_name, SUM({_sql_numeric_expr("order_price_in_aed")}) as revenue
            FROM fact_orders
            WHERE {_sql_date_cast_expr("order_date")} >= :prior_start AND {_sql_date_cast_expr("order_date")} <= :prior_end
              {extra_filters}
            GROUP BY product_name
        )
        SELECT
            c.product_name,
            c.revenue as current_revenue,
            COALESCE(p.revenue, 0) as prior_revenue,
            ((c.revenue - COALESCE(p.revenue, 0)) / NULLIF(p.revenue, 0) * 100) as growth_pct
        FROM current_period c
        LEFT JOIN prior_period p ON c.product_name = p.product_name
        WHERE p.revenue > 0
        ORDER BY growth_pct ASC
        LIMIT 5
    """

    fallers_df = get_data(fallers_query, params)

    # Map to response
    risers = []
    if not risers_df.empty:
        for _, row in risers_df.iterrows():
            if row['growth_pct'] is not None:
                risers.append(TrendItem(
                    product_name=str(row['product_name']),
                    growth_pct=round(float(row['growth_pct']), 2),
                    current_revenue=float(row['current_revenue']),
                    prior_revenue=float(row['prior_revenue'])
                ))

    fallers = []
    if not fallers_df.empty:
        for _, row in fallers_df.iterrows():
            if row['growth_pct'] is not None:
                fallers.append(TrendItem(
                    product_name=str(row['product_name']),
                    growth_pct=round(float(row['growth_pct']), 2),
                    current_revenue=float(row['current_revenue']),
                    prior_revenue=float(row['prior_revenue'])
                ))

    logger.info("✅ Product Movers calculated (risers=%s, fallers=%s)", len(risers), len(fallers))
    if risers:
        if settings.DEBUG:
            logger.debug(
                "   Top riser: %s (+%s%%)",
                risers[0].product_name,
                round(float(risers[0].growth_pct), 1),
            )
    if fallers:
        if settings.DEBUG:
            logger.debug(
                "   Top faller: %s (%s%%)",
                fallers[0].product_name,
                round(float(fallers[0].growth_pct), 1),
            )

    return ProductMoversResponse(risers=risers, fallers=fallers)
