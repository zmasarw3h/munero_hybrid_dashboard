'use client';

import { useState, useEffect, useCallback } from 'react';
import { useFilters, transformFiltersForAPI } from '@/components/dashboard/FilterContext';
import { apiClient } from '@/lib/api-client';
import {
    HeadlineStats,
    TrendResponse,
    MetaResponse,
    SparklineResponse,
    StuckOrder,
    LeaderboardRow
} from '@/lib/types';
import {
    DualAxisChart,
    EnhancedKPICard,
    CompactDonut,
    StuckOrdersList,
    TopPerformersChart,
    GeographyMap,
    AnomalyTicker,
} from '@/components/dashboard';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, Clock, BarChart3 } from 'lucide-react';

export default function OverviewPage() {
    const { filters } = useFilters();
    const [stats, setStats] = useState<HeadlineStats | null>(null);
    const [trendData, setTrendData] = useState<TrendResponse | null>(null);
    const [meta, setMeta] = useState<MetaResponse | null>(null);
    const [ordersSparkline, setOrdersSparkline] = useState<number[]>([]);
    const [revenueSparkline, setRevenueSparkline] = useState<number[]>([]);
    const [stuckOrdersCount, setStuckOrdersCount] = useState(0);
    const [maxStuckAge, setMaxStuckAge] = useState(0);
    const [stuckOrders, setStuckOrders] = useState<StuckOrder[]>([]);
    const [stuckOrdersMock, setStuckOrdersMock] = useState(false);
    const [typeData, setTypeData] = useState<{ name: string; value: number; color: string }[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // State for chart controls
    const [swapAxes, setSwapAxes] = useState(false);
    const [granularity, setGranularity] = useState<'day' | 'month' | 'year'>('day');

    const fetchData = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const apiFilters = transformFiltersForAPI(filters);

            // Fetch all data in parallel
            const [
                statsData,
                trendResult,
                metaResult,
                ordersSparklineData,
                revenueSparklineData,
                stuckOrdersData,
                typeBreakdownData,
            ] = await Promise.all([
                apiClient.getHeadlineStats(apiFilters),
                apiClient.getTrend(apiFilters, granularity),
                apiClient.getMeta().catch(() => null),
                apiClient.getSparklineData(apiFilters, 'orders', 30),
                apiClient.getSparklineData(apiFilters, 'revenue', 30),
                apiClient.getStuckOrders(5),
                apiClient.getLeaderboard(apiFilters, 'order_type'),
            ]);

            setStats(statsData);
            setTrendData(trendResult);
            setMeta(metaResult);

            // Extract sparkline values
            setOrdersSparkline(ordersSparklineData.data.map(p => p.value));
            setRevenueSparkline(revenueSparklineData.data.map(p => p.value));

            // Extract stuck orders summary and full list
            setStuckOrdersCount(stuckOrdersData.total_count);
            setStuckOrders(stuckOrdersData.orders);
            setStuckOrdersMock(stuckOrdersData.is_mock);
            if (stuckOrdersData.orders.length > 0) {
                setMaxStuckAge(Math.max(...stuckOrdersData.orders.map(o => o.age_days)));
            }

            // Transform type breakdown for donut chart
            const TYPE_COLORS: Record<string, string> = {
                'gift_card': '#3b82f6',
                'Gift Card': '#3b82f6',
                'merchandise': '#8b5cf6',
                'Merchandise': '#8b5cf6',
            };
            const donutData = typeBreakdownData.data.map((row: LeaderboardRow) => {
                const displayName = row.label
                    .split('_')
                    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                    .join(' ');
                return {
                    name: displayName,
                    value: row.revenue,
                    color: TYPE_COLORS[row.label] || TYPE_COLORS[displayName] || '#6b7280',
                };
            });
            setTypeData(donutData);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch data');
            console.error('Error fetching dashboard data:', err);
        } finally {
            setLoading(false);
        }
    }, [filters, granularity]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    // Format the last updated date
    const formatLastUpdated = (dateString: string | null) => {
        if (!dateString) return 'Unknown';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            });
        } catch {
            return dateString;
        }
    };

    // Handle stuck orders card action
    const handleViewStuckOrders = () => {
        // Scroll to operational health panel or open modal
        const panel = document.getElementById('operational-health-panel');
        panel?.scrollIntoView({ behavior: 'smooth' });
    };

    // Handle country click from map
    const handleCountryFilter = (countryName: string) => {
        console.log('Filter by country:', countryName);
        // TODO: Update filter context with country
    };

    if (error) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Card className="w-full max-w-md">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-red-600">
                            <AlertCircle className="h-5 w-5" />
                            Error Loading Data
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-sm text-gray-600">{error}</p>
                        <p className="text-xs text-gray-500 mt-2">
                            Make sure the backend is reachable and `NEXT_PUBLIC_API_URL` is set correctly.
                        </p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="space-y-2">
            {/* Page Header with Data Freshness */}
            <div className="flex justify-between items-start">
                <div>
                    <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Executive Overview</h2>
                    <p className="text-gray-600 dark:text-gray-400 text-xs mt-0.5">
                        Key performance indicators and business metrics at a glance
                    </p>
                </div>
                {meta && (
                    <div className="flex items-center gap-2 text-sm text-gray-500 bg-gray-50 dark:bg-gray-800 px-3 py-2 rounded-lg">
                        <Clock className="h-4 w-4" />
                        <span>Updated: {formatLastUpdated(meta.last_updated)}</span>
                    </div>
                )}
            </div>

            {/* ZONE 2: Enhanced KPI Cards */}
            <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-5">
                <EnhancedKPICard
                    label="Total Orders"
                    value={stats?.total_orders.formatted || '—'}
                    trendPct={stats?.total_orders.trend_pct}
                    trendDirection={stats?.total_orders.trend_direction}
                    sparklineData={ordersSparkline}
                    sparklineType="area"
                    isLoading={loading}
                />
                <EnhancedKPICard
                    label="Total Revenue"
                    value={stats?.total_revenue.formatted || '—'}
                    trendPct={stats?.total_revenue.trend_pct}
                    trendDirection={stats?.total_revenue.trend_direction}
                    sparklineData={revenueSparkline}
                    sparklineType="line"
                    sparklineColor="#22c55e"
                    isLoading={loading}
                />
                <EnhancedKPICard
                    label="Avg Order Value"
                    value={stats?.avg_order_value.formatted || '—'}
                    trendPct={stats?.avg_order_value.trend_pct}
                    trendDirection={stats?.avg_order_value.trend_direction}
                    isLoading={loading}
                />
                <EnhancedKPICard
                    label="Orders / Client"
                    value={stats?.orders_per_client.formatted || '—'}
                    trendPct={stats?.orders_per_client.trend_pct}
                    trendDirection={stats?.orders_per_client.trend_direction}
                    isLoading={loading}
                />
                <EnhancedKPICard
                    label="Stuck Orders"
                    value={`${stuckOrdersCount} orders`}
                    secondaryText={stuckOrdersCount > 0 ? `Max: ${maxStuckAge}d` : undefined}
                    actionText="View"
                    onAction={handleViewStuckOrders}
                    isAlert={stuckOrdersCount > 0}
                    isLoading={loading}
                />
            </div>

            {/* ZONE 3: DualAxisChart (8 cols) + StuckOrdersList (4 cols) */}
            <div className="grid gap-2 lg:grid-cols-12">
                {/* Sales & Volume Trend Chart (8 cols) */}
                <div className="lg:col-span-8">
                    {trendData && trendData.data.length > 0 ? (
                        <DualAxisChart
                            data={trendData.data}
                            barKey={swapAxes ? 'orders' : 'revenue'}
                            lineKey={swapAxes ? 'revenue' : 'orders'}
                            xKey="date_label"
                            title={trendData.title || 'Sales & Volume Trend'}
                            height={320}
                            onMetricToggle={() => setSwapAxes(!swapAxes)}
                            anomalyThreshold={filters.anomalyThreshold}
                            granularity={granularity}
                            onGranularityChange={setGranularity}
                        />
                    ) : loading ? (
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-lg">Sales & Volume Trend</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="bg-gray-100 dark:bg-gray-800 animate-pulse rounded-lg" style={{ height: 200 }}></div>
                            </CardContent>
                        </Card>
                    ) : (
                        <Card>
                            <CardHeader className="pb-2">
                                <CardTitle className="text-lg">Sales & Volume Trend</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex items-center justify-center text-gray-400" style={{ height: 200 }}>
                                    <div className="text-center">
                                        <BarChart3 className="h-10 w-10 mx-auto mb-2 opacity-50" />
                                        <p className="text-sm">No trend data available</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>

                {/* Stuck Orders List (4 cols) */}
                <div className="lg:col-span-4" id="operational-health-panel">
                    <StuckOrdersList
                        orders={stuckOrders}
                        isMock={stuckOrdersMock}
                        maxDisplay={5}
                        totalCount={stuckOrders.length}
                        isLoading={loading}
                        onRetry={(order) => console.log('Retry order:', order.order_number)}
                        onViewDetails={(order) => console.log('View details:', order.order_number)}
                        onViewAll={stuckOrders.length > 5 ? () => console.log('View all stuck orders') : undefined}
                    />
                </div>
            </div>

            {/* ZONE 4: GeographyMap (4 cols) + TopPerformers (6 cols) + CompactDonut (2 cols) */}
            <div className="grid gap-2 lg:grid-cols-12">
                {/* Revenue by Geography */}
                <div className="lg:col-span-4">
                    <GeographyMap
                        height={320}
                        onCountryClick={handleCountryFilter}
                    />
                </div>

                {/* Top Performers (Products/Brands toggle) */}
                <div className="lg:col-span-6">
                    <TopPerformersChart
                        limit={10}
                        height={320}
                    />
                </div>

                {/* Revenue by Type Donut */}
                <div className="lg:col-span-2">
                    <CompactDonut
                        title="Revenue by Type"
                        data={typeData}
                        size={70}
                        currency={filters.currency}
                        height={410}
                        onSegmentClick={(segment) => console.log('Filter by type:', segment.name)}
                    />
                </div>
            </div>

            {/* ZONE 5: Anomaly Ticker */}
            <AnomalyTicker
                trendData={trendData?.data || []}
                onAnomalyClick={(anomaly) => {
                    console.log('Anomaly clicked:', anomaly);
                    // TODO: Filter dashboard to anomaly date or open AI chat
                }}
            />
        </div>
    );
}
