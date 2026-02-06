import {
    ScatterPoint,
    ClientSegment,
    SegmentedClient,
    SegmentThresholds,
    SegmentSummary,
    MarketKPIs,
    ConcentrationDataPoint,
} from './types';

// ============================================================================
// SEGMENT CONFIGURATION
// ============================================================================

export const SEGMENT_CONFIG: Record<
    ClientSegment,
    { label: string; color: string; bgColor: string; description: string }
> = {
    champion: {
        label: 'Champions',
        color: '#22c55e',
        bgColor: 'rgba(34, 197, 94, 0.1)',
        description: 'High Spend, High Frequency',
    },
    whale: {
        label: 'Whales',
        color: '#3b82f6',
        bgColor: 'rgba(59, 130, 246, 0.1)',
        description: 'High Spend, Low Frequency',
    },
    loyalist: {
        label: 'Loyalists',
        color: '#eab308',
        bgColor: 'rgba(234, 179, 8, 0.1)',
        description: 'Low Spend, High Frequency',
    },
    developing: {
        label: 'Developing',
        color: '#6b7280',
        bgColor: 'rgba(107, 114, 128, 0.1)',
        description: 'Low Spend, Low Frequency',
    },
};

// ============================================================================
// STATISTICAL UTILITIES
// ============================================================================

/**
 * Calculate median value from array of numbers
 */
export function calculateMedian(values: number[]): number {
    if (values.length === 0) return 0;
    const sorted = [...values].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 !== 0
        ? sorted[mid]
        : (sorted[mid - 1] + sorted[mid]) / 2;
}

/**
 * Determine if an axis should use logarithmic scale
 * Uses log scale when data has extreme outliers (max/min ratio > 100x)
 */
export function shouldUseLogScale(values: number[]): boolean {
    if (values.length < 2) return false;

    // Filter to positive values only (log scale can't include 0)
    const positiveValues = values.filter((v) => v > 0);
    if (positiveValues.length < 2) return false;

    const max = Math.max(...positiveValues);
    const min = Math.min(...positiveValues);

    // Use log scale if max/min ratio exceeds 100x
    return max / min > 100;
}

/**
 * Calculate smart axis minimum to remove empty space below data points.
 * Returns a "nice" rounded value below the minimum data point.
 *
 * @param values - Array of data values
 * @param threshold - The segmentation threshold (optional - only include if close to data)
 * @returns Optimized minimum value for the axis
 */
export function calculateSmartAxisMin(values: number[], threshold: number): number {
    if (values.length === 0) return 0;

    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);

    // If minimum data is close to zero (within 10% of max), start at 0
    if (minValue < maxValue * 0.1) return 0;

    // Only include threshold if it's reasonably close to the data range
    // (within 50% of the min value). Otherwise, focus on showing the data well.
    const thresholdIsRelevant = threshold >= minValue * 0.5;
    const effectiveMin = thresholdIsRelevant ? Math.min(minValue, threshold) : minValue;

    // Round down to a "nice" number for clean axis labels
    // Use order of magnitude to determine rounding
    if (effectiveMin <= 0) return 0;

    const magnitude = Math.pow(10, Math.floor(Math.log10(effectiveMin)));
    const niceMin = Math.floor(effectiveMin / magnitude) * magnitude;

    // Apply a small buffer (reduce by 20%) for visual breathing room
    // but ensure we don't go below a reasonable fraction of the min
    const bufferedMin = niceMin * 0.8;

    return Math.max(0, bufferedMin);
}

/**
 * Calculate default thresholds based on median values
 *
 * When backend-provided medians are available (calculated from ALL clients),
 * use those for accurate market-wide segmentation thresholds.
 * Otherwise, fall back to calculating from the visible client data.
 *
 * @param clients - Array of scatter points (may be limited to top 500)
 * @param medianOrders - Optional: Median orders from ALL clients (backend-provided)
 * @param medianRevenue - Optional: Median revenue from ALL clients (backend-provided)
 */
export function calculateDefaultThresholds(
    clients: ScatterPoint[],
    medianOrders?: number,
    medianRevenue?: number
): SegmentThresholds {
    if (clients.length === 0) {
        return {
            minOrdersForHighFrequency: 0,
            minRevenueForHighValue: 0,
        };
    }

    // Use backend-provided medians if available (calculated from ALL clients)
    if (medianOrders !== undefined && medianRevenue !== undefined) {
        return {
            minOrdersForHighFrequency: medianOrders,
            minRevenueForHighValue: Math.round(medianRevenue),
        };
    }

    // Fallback: calculate from visible data (may be biased if limited to top 500)
    const orders = clients.map((c) => c.total_orders);
    const revenues = clients.map((c) => c.total_revenue);

    return {
        minOrdersForHighFrequency: Math.round(calculateMedian(orders)),
        minRevenueForHighValue: Math.round(calculateMedian(revenues)),
    };
}

// ============================================================================
// SEGMENTATION LOGIC
// ============================================================================

/**
 * Classify a client into a segment based on thresholds
 *
 * Quadrant Layout:
 *   High Revenue | Whales (top-left)    | Champions (top-right)
 *   Low Revenue  | Developing (bot-left)| Loyalists (bot-right)
 *                | Low Orders           | High Orders
 */
export function classifyClient(
    client: ScatterPoint,
    thresholds: SegmentThresholds
): ClientSegment {
    const isHighValue = client.total_revenue >= thresholds.minRevenueForHighValue;
    const isHighFrequency = client.total_orders >= thresholds.minOrdersForHighFrequency;

    if (isHighValue && isHighFrequency) return 'champion';
    if (isHighValue && !isHighFrequency) return 'whale';
    if (!isHighValue && isHighFrequency) return 'loyalist';
    return 'developing';
}

/**
 * Segment all clients and return enriched data
 */
export function segmentClients(
    clients: ScatterPoint[],
    thresholds: SegmentThresholds
): SegmentedClient[] {
    return clients.map((client) => ({
        ...client,
        segment: classifyClient(client, thresholds),
    }));
}

/**
 * Calculate segment summaries for the donut chart
 * Optimized: Single-pass O(n) algorithm instead of 4 separate filters
 */
export function calculateSegmentSummaries(clients: SegmentedClient[]): SegmentSummary[] {
    // Initialize accumulators for each segment
    const accumulators: Record<ClientSegment, { count: number; totalRevenue: number; totalOrders: number }> = {
        champion: { count: 0, totalRevenue: 0, totalOrders: 0 },
        whale: { count: 0, totalRevenue: 0, totalOrders: 0 },
        loyalist: { count: 0, totalRevenue: 0, totalOrders: 0 },
        developing: { count: 0, totalRevenue: 0, totalOrders: 0 },
    };

    // Single pass through all clients
    for (const client of clients) {
        const acc = accumulators[client.segment];
        acc.count++;
        acc.totalRevenue += client.total_revenue;
        acc.totalOrders += client.total_orders;
    }

    // Build result array
    const segments: ClientSegment[] = ['champion', 'whale', 'loyalist', 'developing'];
    return segments.map((segment) => {
        const acc = accumulators[segment];
        return {
            segment,
            count: acc.count,
            totalRevenue: acc.totalRevenue,
            avgRevenue: acc.count > 0 ? acc.totalRevenue / acc.count : 0,
            avgOrders: acc.count > 0 ? acc.totalOrders / acc.count : 0,
            color: SEGMENT_CONFIG[segment].color,
            label: SEGMENT_CONFIG[segment].label,
        };
    });
}

// ============================================================================
// MARKET KPI CALCULATIONS
// ============================================================================

/**
 * Calculate Market KPIs from client data
 *
 * @param clients - Array of scatter points (may be limited to top 500)
 * @param totalClientCount - Optional: Total count from ALL clients (backend-provided)
 *                           Used to show accurate "Active Clients" KPI
 */
export function calculateMarketKPIs(
    clients: ScatterPoint[],
    totalClientCount?: number
): MarketKPIs {
    if (clients.length === 0) {
        return {
            activeClients: totalClientCount ?? 0,
            avgRevenuePerClient: 0,
            topClientName: 'N/A',
            topClientRevenue: 0,
            topClientSharePct: 0,
            isConcentrationRisk: false,
        };
    }

    // Use full client count if provided, otherwise fall back to visible data length
    const activeClients = totalClientCount ?? clients.length;
    const totalRevenue = clients.reduce((sum, c) => sum + c.total_revenue, 0);
    // Avg revenue is calculated from visible data (which may be top 500)
    const avgRevenuePerClient = clients.length > 0 ? totalRevenue / clients.length : 0;

    // Find top client
    const topClient = clients.reduce(
        (top, c) => (c.total_revenue > top.total_revenue ? c : top),
        clients[0]
    );

    const topClientSharePct =
        totalRevenue > 0 ? (topClient.total_revenue / totalRevenue) * 100 : 0;

    return {
        activeClients,
        avgRevenuePerClient,
        topClientName: topClient.client_name,
        topClientRevenue: topClient.total_revenue,
        topClientSharePct,
        isConcentrationRisk: topClientSharePct > 25,
    };
}

// ============================================================================
// CONCENTRATION / PARETO ANALYSIS
// ============================================================================

/**
 * Calculate concentration data for Pareto chart
 * Shows cumulative revenue percentage by client rank
 */
export function calculateConcentrationData(
    clients: ScatterPoint[],
    topN: number = 10
): ConcentrationDataPoint[] {
    if (clients.length === 0) return [];

    // Sort by revenue descending
    const sorted = [...clients].sort((a, b) => b.total_revenue - a.total_revenue);
    const totalRevenue = sorted.reduce((sum, c) => sum + c.total_revenue, 0);

    // Take top N clients
    const topClients = sorted.slice(0, topN);

    let cumulativeRevenue = 0;
    return topClients.map((client, index) => {
        cumulativeRevenue += client.total_revenue;
        return {
            clientName: client.client_name,
            revenue: client.total_revenue,
            cumulativeRevenue,
            cumulativePercent: totalRevenue > 0 ? (cumulativeRevenue / totalRevenue) * 100 : 0,
            rank: index + 1,
        };
    });
}

/**
 * Find the number of clients that account for a target percentage of revenue
 * Useful for insights like "Top 5 clients = 60% of revenue"
 */
export function findClientsForRevenuePercent(
    clients: ScatterPoint[],
    targetPercent: number = 80
): { count: number; actualPercent: number } {
    if (clients.length === 0) return { count: 0, actualPercent: 0 };

    const sorted = [...clients].sort((a, b) => b.total_revenue - a.total_revenue);
    const totalRevenue = sorted.reduce((sum, c) => sum + c.total_revenue, 0);

    let cumulativeRevenue = 0;
    for (let i = 0; i < sorted.length; i++) {
        cumulativeRevenue += sorted[i].total_revenue;
        const percent = (cumulativeRevenue / totalRevenue) * 100;
        if (percent >= targetPercent) {
            return { count: i + 1, actualPercent: percent };
        }
    }

    return { count: sorted.length, actualPercent: 100 };
}

// ============================================================================
// FORMATTING UTILITIES
// ============================================================================

/**
 * Format currency value with appropriate suffix (K, M)
 */
export function formatCurrencyCompact(value: number, currency: string = 'AED'): string {
    if (value >= 1000000) {
        return `${currency} ${(value / 1000000).toFixed(1)}M`;
    }
    if (value >= 1000) {
        return `${currency} ${(value / 1000).toFixed(1)}K`;
    }
    return `${currency} ${value.toFixed(0)}`;
}

/**
 * Format percentage with appropriate decimal places
 */
export function formatPercent(value: number, decimals: number = 1): string {
    return `${value.toFixed(decimals)}%`;
}
