// API Types matching backend Pydantic models

export type ComparisonMode = 'yoy' | 'prev_period' | 'none';
export type TrendDirection = 'up' | 'down' | 'flat' | 'neutral';
export type Currency = string;  // Dynamic currency support

export interface DashboardFilters {
    start_date?: string;
    end_date?: string;
    currency: string;  // Changed from Currency literal to string for dynamic currencies
    comparison_mode: ComparisonMode;
    anomaly_threshold: number;
    clients: string[];
    countries: string[];
    product_types: string[];
    brands: string[];
    suppliers: string[];
}

export interface KPIMetric {
    label: string;
    value: number;
    formatted: string;
    trend_pct?: number;
    trend_direction: TrendDirection;
}

export interface HeadlineStats {
    total_orders: KPIMetric;
    total_revenue: KPIMetric;
    avg_order_value: KPIMetric;
    orders_per_client: KPIMetric;
    distinct_brands: KPIMetric;
}

export interface ChartPoint {
    label: string;
    value: number;
    series?: string;
}

export interface ChartResponse {
    title: string;
    chart_type: 'bar' | 'line' | 'pie' | 'scatter' | 'dual_axis';
    data: ChartPoint[];
    x_axis_label: string;
    y_axis_label: string;
}

// ============================================================================
// TREND CHART TYPES (Phase 4 - Enhanced Trend API)
// ============================================================================

export interface TrendPoint {
    [key: string]: string | number | boolean | null | undefined;  // Index signature for chart compatibility
    date_label: string;       // x-axis label (e.g., "2025-01" or "2025-06-15")
    revenue: number;          // Bar metric - total revenue
    orders: number;           // Line metric - total orders
    revenue_growth: number;   // % change vs previous point
    orders_growth: number;    // % change vs previous point
    is_revenue_anomaly: boolean;  // Z-score based anomaly flag
    is_order_anomaly: boolean;    // Z-score based anomaly flag
}

export interface TrendResponse {
    title: string;
    data: TrendPoint[];
}

// ============================================================================
// SCATTER CHART TYPES (Phase 1 Part 2 - Market Analysis)
// ============================================================================

export interface ScatterPoint {
    client_name: string;
    country: string;
    total_revenue: number;
    total_orders: number;
    aov: number;              // Average Order Value
    dominant_type: string;    // Product type with highest revenue
}

export interface ScatterResponse {
    data: ScatterPoint[];
    // Metadata about full dataset (for accurate KPIs when scatter is limited to top 500)
    total_clients: number;      // Full count before limiting
    median_orders: number;      // Median from ALL clients (for market-wide thresholds)
    median_revenue: number;     // Median from ALL clients (for market-wide thresholds)
}

// ============================================================================
// LEADERBOARD TYPES (Phase 1 Part 3 - Top Performers)
// ============================================================================

export interface LeaderboardRow {
    label: string;                      // Entity name (client, brand, supplier, product)
    revenue: number;                    // Total revenue generated
    orders: number;                     // Number of distinct orders
    margin_pct: number | null;          // Profit margin: (Revenue - COGS) / Revenue * 100
    share_pct: number;                  // Market share: % of total revenue
    growth_pct?: number;                // YoY growth (placeholder)
    trend?: number[];                   // 6 monthly revenue values for sparkline
    failure_rate?: number | null;       // Mock failure rate for products
}

export interface LeaderboardResponse {
    title: string;
    dimension: string;
    data: LeaderboardRow[];
}

export interface FilterOptionsResponse {
    clients: string[];
    brands: string[];
    suppliers: string[];
    countries: string[];
    currencies: string[];
}

export interface AIAnalysisResponse {
    answer_text: string;
    sql_generated: string;
    related_chart?: ChartResponse;
}

// ============================================================================
// META / DATA FRESHNESS TYPES
// ============================================================================

export interface MetaResponse {
    last_updated: string | null;        // ISO datetime string
    data_source: string;
    refresh_schedule: string;
    total_records: number | null;
}

// ============================================================================
// OVERVIEW V2 TYPES (Executive Dashboard Enhancements)
// ============================================================================

export type StuckOrderStatus = 'stuck' | 'failed' | 'pending';

export interface StuckOrder {
    order_number: string;
    order_date: string;
    status: StuckOrderStatus;
    age_days: number;
    product_name: string;
    client_name: string;
    amount: number;
}

export interface StuckOrdersResponse {
    total_count: number;
    orders: StuckOrder[];
    is_mock: boolean;
}

export interface SparklinePoint {
    date: string;
    value: number;
}

export interface SparklineResponse {
    metric: string;
    data: SparklinePoint[];
}

export interface CountryData {
    country_code: string;  // ISO 3166-1 alpha-2 (e.g., "AE", "SA")
    country_name: string;
    revenue: number;
    orders: number;
    clients: number;
}

export interface GeographyResponse {
    data: CountryData[];
}

export interface ProductByStatus {
    product_name: string;
    product_sku: string | null;
    brand: string;
    total_revenue: number;
    completed_revenue: number;
    failed_revenue: number;
    stuck_revenue: number;
    completed_count: number;
    failed_count: number;
    stuck_count: number;
}

export interface TopProductsByStatusResponse {
    data: ProductByStatus[];
    is_mock: boolean;
}

export interface BrandByType {
    brand_name: string;
    total_revenue: number;
    gift_card_revenue: number;
    merchandise_revenue: number;
    gift_card_orders: number;
    merchandise_orders: number;
}

export interface TopBrandsByTypeResponse {
    data: BrandByType[];
}

// Anomaly item for the ticker (derived from TrendPoint)
export interface AnomalyItem {
    date: string;
    metric: 'revenue' | 'orders';
    change_pct: number;
    z_score: number;
    direction: 'positive' | 'negative';
}

// ============================================================================
// MARKET ANALYSIS / CLIENT SEGMENTATION TYPES
// ============================================================================

export type ClientSegment = 'champion' | 'whale' | 'loyalist' | 'developing';

export interface SegmentThresholds {
    minOrdersForHighFrequency: number;  // Median orders by default
    minRevenueForHighValue: number;     // Median revenue by default
}

export interface SegmentedClient extends ScatterPoint {
    segment: ClientSegment;
}

export interface SegmentSummary {
    segment: ClientSegment;
    count: number;
    totalRevenue: number;
    avgRevenue: number;
    avgOrders: number;
    color: string;
    label: string;
}

export interface MarketKPIs {
    activeClients: number;
    avgRevenuePerClient: number;
    topClientName: string;
    topClientRevenue: number;
    topClientSharePct: number;
    isConcentrationRisk: boolean;  // true if >25%
}

export interface ConcentrationDataPoint {
    clientName: string;
    revenue: number;
    cumulativeRevenue: number;
    cumulativePercent: number;
    rank: number;
}

// ============================================================================
// CATALOG ANALYSIS TYPES (Product Performance Analysis)
// ============================================================================

export interface CatalogKPIs {
    active_skus: number;
    active_skus_change?: number;
    currency_count: number;
    currency_count_change?: number;
    avg_margin: number | null;
    avg_margin_change?: number;
    supplier_health: number;
    at_risk_suppliers: number;
}

export type ProductQuadrant = 'cash_cow' | 'premium_niche' | 'penny_stock' | 'dead_stock';
export type ProductType = 'gift_card' | 'merchandise';

export interface ProductScatterPoint {
    product_name: string;
    product_type: ProductType;
    quantity: number;
    revenue: number;
    margin: number | null;
    quadrant: ProductQuadrant;
}

export interface ProductScatterResponse {
    data: ProductScatterPoint[];
    median_revenue: number;
    median_quantity: number;
    total_products: number;
}

export interface ProductMoverItem {
    product_name: string;
    growth_pct: number;
    current_revenue: number;
    prior_revenue: number;
}

export interface ProductMoversResponse {
    risers: ProductMoverItem[];
    fallers: ProductMoverItem[];
}

// ============================================================================
// AI CHAT TYPES (Phase 4 - Chat Integration)
// ============================================================================

export interface ChatRequest {
    message: string;
    filters?: DashboardFilters;
    conversation_id?: string;
}

export interface ChatChartConfig {
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
    export_token?: string;
    data?: Record<string, unknown>[];
    chart_config?: ChatChartConfig;
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
    requestFilters?: DashboardFilters; // Stored for assistant messages (CSV export)
}
