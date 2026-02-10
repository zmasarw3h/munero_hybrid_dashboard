"""
Pydantic models for API request/response schemas.
These serve as data contracts between frontend and backend.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, date


# ============================================================================
# HEALTH & SYSTEM MODELS
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    database_connected: bool
    llm_available: bool


# ============================================================================
# DASHBOARD MODELS (Phase 2)
# ============================================================================

class DashboardFilters(BaseModel):
    """
    Global filters passed from Frontend -> Backend.
    """
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    currency: str = 'AED'  # Changed from Literal to string to support dynamic currencies
    comparison_mode: Literal['yoy', 'prev_period', 'none'] = 'yoy'
    anomaly_threshold: float = 3.0
    # Optional List Filters (Empty list = Select All)
    clients: List[str] = Field(default_factory=list)
    countries: List[str] = Field(default_factory=list)
    product_types: List[str] = Field(default_factory=list) 
    brands: List[str] = Field(default_factory=list)
    suppliers: List[str] = Field(default_factory=list)


class KPIMetric(BaseModel):
    label: str            # e.g., "Total Revenue"
    value: float          # e.g., 125000.00
    formatted: str        # e.g., "AED 125,000"
    trend_pct: Optional[float] = None      # e.g., +12.5
    trend_direction: Literal['up', 'down', 'flat', 'neutral'] = 'neutral'


class HeadlineStats(BaseModel):
    """
    The top row of the dashboard.
    """
    total_orders: KPIMetric
    total_revenue: KPIMetric
    avg_order_value: KPIMetric
    orders_per_client: KPIMetric
    distinct_brands: KPIMetric


class ChartPoint(BaseModel):
    label: str  # x-axis value (date or category)
    value: float
    series: Optional[str] = None # For multi-line charts


class ChartResponse(BaseModel):
    title: str
    chart_type: Literal['bar', 'line', 'pie', 'scatter', 'dual_axis']
    data: List[ChartPoint]
    x_axis_label: str
    y_axis_label: str


# ============================================================================
# TREND CHART MODELS (Phase 4 - Executive Overview)
# ============================================================================

class TrendPoint(BaseModel):
    """
    Enhanced data point for dual-axis trend charts with anomaly detection.
    Used by the Executive Overview dashboard's main trend widget.
    """
    date_label: str       # x-axis label (e.g., "2025-01" or "2025-01-15")
    revenue: float        # Bar metric - total revenue
    orders: int           # Line metric - total orders
    revenue_growth: Optional[float] = 0.0  # % change vs previous point
    orders_growth: Optional[float] = 0.0   # % change vs previous point
    is_revenue_anomaly: bool = False  # Z-score based anomaly flag
    is_order_anomaly: bool = False    # Z-score based anomaly flag


class TrendResponse(BaseModel):
    """
    Response model for the enhanced trend endpoint.
    Contains dual-axis data (revenue + orders) with growth metrics and anomaly flags.
    """
    title: str
    data: List[TrendPoint]


# ============================================================================
# SCATTER CHART MODELS (Phase 1 Part 2 - Market Analysis)
# ============================================================================

class ScatterPoint(BaseModel):
    """
    Data point for client scatter plot analysis.
    Used by the Market Analysis page to visualize client behavior patterns.
    """
    client_name: str
    country: Optional[str] = "Unknown"
    total_revenue: float
    total_orders: int
    aov: float                  # Average Order Value (revenue / orders)
    dominant_type: str          # Product type with highest revenue for this client


class ScatterResponse(BaseModel):
    """
    Response model for the client scatter endpoint.
    Returns client-level aggregations with dominant product type.

    Includes metadata about the full dataset for accurate KPIs:
    - total_clients: Full count before limiting to top 500
    - median_orders: Median order count from ALL clients (for market-wide thresholds)
    - median_revenue: Median revenue from ALL clients (for market-wide thresholds)
    """
    data: List[ScatterPoint]
    total_clients: int = 0
    median_orders: int = 0
    median_revenue: float = 0.0


# ============================================================================
# LEADERBOARD MODELS (Phase 1 Part 3 - Top Performers)
# ============================================================================

class LeaderboardRow(BaseModel):
    """
    Standardized row for leaderboard/ranking tables.
    Used for Top Clients, Top Brands, Top Suppliers, Top Products widgets.
    """
    label: str                          # Entity name (client, brand, supplier, product)
    revenue: float                      # Total revenue generated
    orders: int                         # Number of distinct orders
    margin_pct: Optional[float] = None  # Profit margin: (Revenue - COGS) / Revenue * 100
    share_pct: float                    # Market share: % of total revenue in this view
    growth_pct: float = 0.0            # YoY or period-over-period growth percentage
    trend: Optional[List[float]] = None  # 6 monthly revenue values for sparkline visualization
    failure_rate: Optional[float] = None  # Mock failure rate for products (0.1-3.0%)


class LeaderboardResponse(BaseModel):
    """
    Response model for leaderboard/ranking endpoints.
    Contains top N entities with performance metrics.
    """
    title: str
    dimension: str
    data: List[LeaderboardRow]


class FilterOptionsResponse(BaseModel):
    """
    Response model for filter options endpoint.
    Returns distinct values for dropdown selectors.
    """
    clients: List[str]
    brands: List[str]
    suppliers: List[str]
    countries: List[str]
    currencies: List[str]


# ============================================================================
# AI QUERY MODELS (Phase 3 - Future)
# ============================================================================

class ChatRequest(BaseModel):
    """Request schema for AI chat endpoint"""
    message: str = Field(..., min_length=1, max_length=500, description="Natural language question")
    filters: Optional[DashboardFilters] = Field(default=None, description="Current dashboard filter state")
    conversation_id: Optional[str] = Field(default=None, description="Optional conversation ID for context")


class ChartConfig(BaseModel):
    """
    Configuration for rendering charts on the frontend.
    Returned by the SmartRender service to tell the frontend how to visualize data.
    """
    type: Literal["bar", "line", "pie", "scatter", "table", "metric"] = Field(
        ..., description="Type of visualization to render"
    )
    x_column: Optional[str] = Field(None, description="Column name for x-axis")
    y_column: Optional[str] = Field(None, description="Column name for y-axis (primary)")
    secondary_y_column: Optional[str] = Field(None, description="Column name for secondary y-axis")
    orientation: Optional[Literal["horizontal", "vertical"]] = Field(
        "vertical", description="Chart orientation (for bar charts)"
    )
    title: Optional[str] = Field(None, description="Chart title")


class ChatResponse(BaseModel):
    """
    Complete response from the AI chat endpoint.
    Contains answer text, generated SQL, data, and visualization configuration.
    """
    answer_text: str = Field(..., description="Natural language summary/answer")
    sql_query: Optional[str] = Field(None, description="The SQL query that was generated and executed")
    export_token: Optional[str] = Field(
        None,
        description="Signed short-lived token required for /api/chat/export-csv (hosted hardening).",
    )
    data: Optional[List[Dict[str, Any]]] = Field(None, description="Query result data as list of dicts")
    chart_config: Optional[ChartConfig] = Field(None, description="Visualization configuration")
    row_count: int = Field(default=0, description="Number of rows returned")
    warnings: List[str] = Field(default_factory=list, description="Any warnings generated during processing")
    error: Optional[str] = Field(None, description="Error message if query failed")


class AIAnalysisResponse(BaseModel):
    """
    Response from AI Copilot after processing a natural language query.
    Contains the answer text, generated SQL, and visualization config.
    """
    answer_text: str = Field(..., description="Natural language summary of findings")
    sql_generated: str = Field(..., description="The SQL query that was executed")
    related_chart: Optional[ChartResponse] = Field(None, description="Chart configuration if data is visualizable")


class QueryRequest(BaseModel):
    """Request schema for natural language queries"""
    question: str = Field(..., min_length=1, max_length=1000, description="Natural language question")
    include_sql: bool = Field(default=True, description="Whether to return the generated SQL")
    max_rows: int = Field(default=1000, ge=1, le=10000, description="Maximum rows to return")


class QueryResponse(BaseModel):
    """Response schema for query results"""
    success: bool
    question: str
    sql_query: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[str]] = None
    row_count: Optional[int] = None
    visualization_type: Optional[str] = None
    visualization_config: Optional[Dict[str, Any]] = None
    warning: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


class TableInfo(BaseModel):
    """Schema information for a database table"""
    name: str
    row_count: int
    columns: List[str]
    sample_data: Optional[List[Dict[str, Any]]] = None


class DatabaseSchema(BaseModel):
    """Complete database schema information"""
    tables: List[TableInfo]
    foreign_keys: Optional[Dict[str, List[str]]] = None


class ChatMessage(BaseModel):
    """Chat message in conversation history"""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    sql_query: Optional[str] = None
    has_data: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)


class ConversationHistory(BaseModel):
    """Conversation history management"""
    session_id: str
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime


# ============================================================================
# DRIVER ANALYSIS MODELS (Phase 0 - Why Did X Change?)
# ============================================================================

class DateRange(BaseModel):
    """Date range for period comparison"""
    start: date
    end: date


class DriverAnalysisRequest(BaseModel):
    """
    Request model for driver analysis endpoint.
    Used to answer "why did X change?" questions with mathematical precision.
    """
    metric: Literal["revenue", "orders", "margin", "aov"] = Field(
        ...,
        description="The metric to analyze"
    )
    current_period: DateRange = Field(
        ...,
        description="The current period to analyze"
    )
    prior_period: DateRange = Field(
        ...,
        description="The comparison period"
    )
    filters: Optional[DashboardFilters] = Field(
        default=None,
        description="Optional dashboard filters to apply"
    )
    dimensions: List[str] = Field(
        default=["client_name", "product_brand", "client_country", "order_type"],
        description="Dimensions to analyze for drivers"
    )
    top_n: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of top drivers to return per dimension"
    )


class DriverEntity(BaseModel):
    """Individual driver entity with impact metrics"""
    name: str
    current_value: float
    prior_value: float
    delta: float
    delta_pct: Optional[float] = None  # Percentage change
    contribution_to_total_change: float  # % of total change explained by this entity


class DriverSummary(BaseModel):
    """Summary of the primary and secondary drivers"""
    dimension: str
    entity: str
    contribution: float


class DriverAnalysisResponse(BaseModel):
    """
    Response model for driver analysis.
    Contains mathematically computed variance drivers across dimensions.
    """
    metric: str
    current_total: float
    prior_total: float
    total_change: float
    total_change_pct: float
    direction: Literal["increase", "decrease", "flat"]
    drivers: Dict[str, List[DriverEntity]]  # Keyed by dimension (e.g., "by_client_name")
    summary: Dict[str, DriverSummary]  # Primary and secondary drivers


# ============================================================================
# META / DATA FRESHNESS MODELS
# ============================================================================

class MetaResponse(BaseModel):
    """Response model for data freshness and metadata endpoint"""
    last_updated: Optional[datetime] = None
    data_source: str = "database"
    refresh_schedule: str = "Daily at 2:00 AM UTC"
    total_records: Optional[int] = None


# ============================================================================
# OVERVIEW V2 MODELS (Executive Dashboard Enhancements)
# ============================================================================

class StuckOrder(BaseModel):
    """Individual stuck/failed order for operational alerts"""
    order_number: str
    order_date: str
    status: Literal['stuck', 'failed', 'pending']
    age_days: int
    product_name: str
    client_name: str
    amount: float


class StuckOrdersResponse(BaseModel):
    """Response for stuck orders endpoint"""
    total_count: int
    orders: List[StuckOrder]
    is_mock: bool = False  # True when using mock data (no order_status in DB)


class SparklinePoint(BaseModel):
    """Single data point for sparkline visualization"""
    date: str
    value: float


class SparklineResponse(BaseModel):
    """Response for sparkline data endpoint"""
    metric: str
    data: List[SparklinePoint]


class CountryData(BaseModel):
    """Country-level aggregation for geography map"""
    country_code: str  # ISO 3166-1 alpha-2 (e.g., "AE", "SA")
    country_name: str
    revenue: float
    orders: int
    clients: int


class GeographyResponse(BaseModel):
    """Response for geography endpoint"""
    data: List[CountryData]


class ProductByStatus(BaseModel):
    """Product with revenue breakdown by order status"""
    product_name: str
    product_sku: Optional[str] = None
    brand: str
    total_revenue: float
    completed_revenue: float
    failed_revenue: float
    stuck_revenue: float
    completed_count: int
    failed_count: int
    stuck_count: int


class TopProductsByStatusResponse(BaseModel):
    """Response for top products by status endpoint"""
    data: List[ProductByStatus]
    is_mock: bool = False  # True when status breakdown is simulated


class BrandByType(BaseModel):
    """Brand with revenue breakdown by product type"""
    brand_name: str
    total_revenue: float
    gift_card_revenue: float
    merchandise_revenue: float
    gift_card_orders: int
    merchandise_orders: int


class TopBrandsByTypeResponse(BaseModel):
    """Response for top brands by type endpoint"""
    data: List[BrandByType]


# ============================================================================
# CATALOG ANALYSIS MODELS (Catalog Page Endpoints)
# ============================================================================

class CatalogKPIs(BaseModel):
    """KPI metrics for the Catalog Analysis page"""
    active_skus: int
    active_skus_change: Optional[float] = None
    currency_count: int
    currency_count_change: Optional[int] = None
    avg_margin: Optional[float] = None
    avg_margin_change: Optional[float] = None
    supplier_health: float
    at_risk_suppliers: int


class ProductScatterPoint(BaseModel):
    """Data point for product scatter plot analysis"""
    product_name: str
    product_type: Literal['gift_card', 'merchandise']
    quantity: float
    revenue: float
    margin: Optional[float] = None
    quadrant: Literal['cash_cow', 'premium_niche', 'penny_stock', 'dead_stock']


class ProductScatterResponse(BaseModel):
    """Response model for product scatter endpoint"""
    data: List[ProductScatterPoint]
    median_revenue: float
    median_quantity: float
    total_products: int


class TrendItem(BaseModel):
    """Individual product trend data for movers endpoint"""
    product_name: str
    growth_pct: float
    current_revenue: float
    prior_revenue: float


class ProductMoversResponse(BaseModel):
    """Response model for product movers endpoint (risers and fallers)"""
    risers: List[TrendItem]
    fallers: List[TrendItem]
