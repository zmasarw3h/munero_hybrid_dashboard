// API client for backend communication

import {
    DashboardFilters,
    HeadlineStats,
    ChartResponse,
    AIAnalysisResponse,
    TrendResponse,
    ScatterResponse,
    LeaderboardResponse,
    FilterOptionsResponse,
    MetaResponse,
    // Catalog Types
    CatalogKPIs,
    ProductScatterResponse,
    ProductMoversResponse,
    // Overview V2 Types
    StuckOrdersResponse,
    SparklineResponse,
    GeographyResponse,
    TopProductsByStatusResponse,
    TopBrandsByTypeResponse,
    // Chat Types
    ChatRequest,
    ChatResponse,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class APIClient {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`;

        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options?.headers,
                },
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                // Handle various error response formats
                let message = `API Error: ${response.status}`;
                if (typeof error === 'object' && error !== null) {
                    message = error.detail || error.message || (Object.keys(error).length > 0 ? JSON.stringify(error) : message);
                }
                throw new Error(message);
            }

            return response.json();
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    }

    // Dashboard APIs
    async getHeadlineStats(filters: DashboardFilters): Promise<HeadlineStats> {
        return this.request<HeadlineStats>('/api/dashboard/headline', {
            method: 'POST',
            body: JSON.stringify(filters),
        });
    }

    async getTrend(
        filters: DashboardFilters,
        granularity: 'day' | 'month' | 'year' = 'month'
    ): Promise<TrendResponse> {
        const params = new URLSearchParams({ granularity });
        return this.request<TrendResponse>(`/api/dashboard/trend?${params.toString()}`, {
            method: 'POST',
            body: JSON.stringify(filters),
        });
    }

    async getLeaderboard(
        filters: DashboardFilters,
        dimension: 'client' | 'brand' | 'supplier' | 'product' | 'order_type',
        includeTrend: boolean = false
    ): Promise<LeaderboardResponse> {
        const params = new URLSearchParams({
            dimension,
            include_trend: includeTrend.toString()
        });
        return this.request<LeaderboardResponse>(`/api/dashboard/breakdown?${params.toString()}`, {
            method: 'POST',
            body: JSON.stringify(filters),
        });
    }

    async getTopProducts(filters: DashboardFilters, limit: number = 10): Promise<ChartResponse> {
        const params = new URLSearchParams({ limit: limit.toString() });
        return this.request<ChartResponse>(`/api/dashboard/top-products?${params.toString()}`, {
            method: 'POST',
            body: JSON.stringify(filters),
        });
    }

    async getScatter(filters: DashboardFilters): Promise<ScatterResponse> {
        return this.request<ScatterResponse>('/api/dashboard/scatter', {
            method: 'POST',
            body: JSON.stringify(filters),
        });
    }

    // Get filter options for multi-select dropdowns
    async getFilterOptions(): Promise<FilterOptionsResponse> {
        return this.request<FilterOptionsResponse>('/api/dashboard/filter-options');
    }

    // AI Chat API
    async chat(message: string, filters: DashboardFilters): Promise<AIAnalysisResponse> {
        return this.request<AIAnalysisResponse>('/api/chat/', {
            method: 'POST',
            body: JSON.stringify({ message, filters }),
        });
    }

    // Health check
    async healthCheck(): Promise<{ status: string; database_connected: boolean; llm_available: boolean }> {
        return this.request('/health');
    }

    // Data freshness / metadata
    async getMeta(): Promise<MetaResponse> {
        return this.request<MetaResponse>('/api/analyze/meta');
    }

    // ========================================================================
    // OVERVIEW V2 ENDPOINTS
    // ========================================================================

    /**
     * Get stuck/failed orders for operational alerts panel
     * Note: Returns mock data as order_status is not in the database
     */
    async getStuckOrders(limit: number = 10): Promise<StuckOrdersResponse> {
        const params = new URLSearchParams({ limit: limit.toString() });
        return this.request<StuckOrdersResponse>(`/api/dashboard/stuck-orders?${params.toString()}`);
    }

    /**
     * Get sparkline data for KPI cards
     * @param metric 'orders' or 'revenue'
     * @param days Number of days of data (default 30)
     */
    async getSparklineData(metric: 'orders' | 'revenue', days: number = 30): Promise<SparklineResponse> {
        const params = new URLSearchParams({ days: days.toString() });
        return this.request<SparklineResponse>(`/api/dashboard/sparkline/${metric}?${params.toString()}`);
    }

    /**
     * Get revenue/orders aggregated by country for geography map
     */
    async getGeographyData(filters: DashboardFilters): Promise<GeographyResponse> {
        return this.request<GeographyResponse>('/api/dashboard/geography', {
            method: 'POST',
            body: JSON.stringify(filters),
        });
    }

    /**
     * Get top products with revenue breakdown by order status
     * Note: Status breakdown is simulated (mock) as order_status is not in DB
     */
    async getTopProductsByStatus(filters: DashboardFilters, limit: number = 10): Promise<TopProductsByStatusResponse> {
        const params = new URLSearchParams({ limit: limit.toString() });
        return this.request<TopProductsByStatusResponse>(`/api/dashboard/top-products-by-status?${params.toString()}`, {
            method: 'POST',
            body: JSON.stringify(filters),
        });
    }

    /**
     * Get top brands with revenue breakdown by product type (gift_card vs merchandise)
     */
    async getTopBrandsByType(filters: DashboardFilters, limit: number = 10): Promise<TopBrandsByTypeResponse> {
        const params = new URLSearchParams({ limit: limit.toString() });
        return this.request<TopBrandsByTypeResponse>(`/api/dashboard/top-brands-by-type?${params.toString()}`, {
            method: 'POST',
            body: JSON.stringify(filters),
        });
    }

    // ========================================================================
    // CATALOG ANALYSIS ENDPOINTS
    // ========================================================================

    /**
     * Get catalog KPIs (active SKUs, currency count, avg margin, supplier health)
     */
    async getCatalogKPIs(filters: DashboardFilters): Promise<CatalogKPIs> {
        return this.request<CatalogKPIs>('/api/dashboard/catalog/kpis', {
            method: 'POST',
            body: JSON.stringify(filters),
        });
    }

    /**
     * Get product scatter data for performance matrix
     * Returns top 500 products by revenue with quantity, margin, and quadrant assignment
     */
    async getProductScatter(filters: DashboardFilters): Promise<ProductScatterResponse> {
        return this.request<ProductScatterResponse>('/api/dashboard/catalog/scatter', {
            method: 'POST',
            body: JSON.stringify(filters),
        });
    }

    /**
     * Get top risers and fallers (movers & shakers)
     * Compares current period vs prior period revenue growth
     */
    async getProductMovers(filters: DashboardFilters): Promise<ProductMoversResponse> {
        return this.request<ProductMoversResponse>('/api/dashboard/catalog/movers', {
            method: 'POST',
            body: JSON.stringify(filters),
        });
    }

    // ========================================================================
    // AI CHAT ENDPOINTS
    // ========================================================================

    /**
     * Send a chat message to the AI assistant
     * Returns answer with optional visualization config
     */
    async sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
        return this.request<ChatResponse>('/api/chat/', {
            method: 'POST',
            body: JSON.stringify(request),
        });
    }

    /**
     * Check if the AI chat service is available
     */
    async checkChatHealth(): Promise<{ status: string; provider?: string; model?: string; message: string; hint?: string }> {
        return this.request('/api/chat/health');
    }

    /**
     * Export chat query results as CSV
     * Downloads full results (up to 10,000 rows) without LIMIT constraint
     */
    async exportChatCSV(sqlQuery: string, filters?: DashboardFilters, filename?: string): Promise<void> {
        const response = await fetch(`${this.baseUrl}/api/chat/export-csv`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sql_query: sqlQuery,
                filters,
                filename: filename || 'chat-export.csv'
            }),
        });

        if (!response.ok) {
            throw new Error('Failed to export CSV');
        }

        // Trigger browser download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename || 'chat-export.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }
}

export const apiClient = new APIClient();
