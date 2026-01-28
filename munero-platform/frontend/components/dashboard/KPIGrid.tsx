'use client';

import { HeadlineStats } from '@/lib/types';
import { MetricCard } from './MetricCard';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { useFilters } from './FilterContext';

interface KPIGridProps {
    stats: HeadlineStats;
    loading?: boolean;
}

/**
 * Helper function to get dynamic comparison label based on mode
 * CRITICAL: This ensures the label reflects the actual comparison being shown
 */
const getComparisonLabel = (mode: 'yoy' | 'prev_period' | 'none'): string => {
    switch (mode) {
        case 'yoy':
            return 'vs Same Period Last Year';
        case 'prev_period':
            return 'vs Previous Period';
        case 'none':
            return '';
        default:
            return 'vs Previous Period';
    }
};

export function KPIGrid({ stats, loading }: KPIGridProps) {
    const { filters, setFilter } = useFilters();

    if (loading) {
        return (
            <div className="space-y-4">
                <div className="flex justify-end">
                    <div className="h-10 w-48 bg-gray-200 animate-pulse rounded-md"></div>
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
                    {[...Array(5)].map((_, i) => (
                        <MetricCard key={i} label="" value="" isLoading={true} />
                    ))}
                </div>
            </div>
        );
    }

    const handleComparisonToggle = (mode: 'yoy' | 'prev_period' | 'none') => {
        setFilter('comparisonMode', mode);
    };

    // Get dynamic comparison label
    const comparisonLabel = getComparisonLabel(filters.comparisonMode);

    return (
        <div className="space-y-4">
            {/* Comparison Mode Dropdown */}
            <div className="flex justify-end">
                <Select
                    value={filters.comparisonMode}
                    onValueChange={(value) => setFilter('comparisonMode', value as 'yoy' | 'prev_period' | 'none')}
                >
                    <SelectTrigger className="w-[200px]">
                        <SelectValue placeholder="Comparison Mode" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="yoy">Year over Year</SelectItem>
                        <SelectItem value="prev_period">Previous Period</SelectItem>
                        <SelectItem value="none">No Comparison</SelectItem>
                    </SelectContent>
                </Select>
            </div>

            {/* KPI Metrics Grid */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
                {/* Total Orders */}
                <MetricCard
                    label={stats.total_orders.label}
                    value={stats.total_orders.formatted}
                    trend={stats.total_orders.trend_pct}
                    trendDirection={stats.total_orders.trend_direction}
                    comparisonLabel={comparisonLabel}
                    onToggleComparison={handleComparisonToggle}
                />

                {/* Total Revenue */}
                <MetricCard
                    label={stats.total_revenue.label}
                    value={stats.total_revenue.formatted}
                    trend={stats.total_revenue.trend_pct}
                    trendDirection={stats.total_revenue.trend_direction}
                    comparisonLabel={comparisonLabel}
                    onToggleComparison={handleComparisonToggle}
                />

                {/* Avg Order Value */}
                <MetricCard
                    label={stats.avg_order_value.label}
                    value={stats.avg_order_value.formatted}
                    trend={stats.avg_order_value.trend_pct}
                    trendDirection={stats.avg_order_value.trend_direction}
                    comparisonLabel={comparisonLabel}
                    onToggleComparison={handleComparisonToggle}
                />

                {/* Orders per Client */}
                <MetricCard
                    label={stats.orders_per_client.label}
                    value={stats.orders_per_client.formatted}
                    trend={stats.orders_per_client.trend_pct}
                    trendDirection={stats.orders_per_client.trend_direction}
                    comparisonLabel={comparisonLabel}
                    onToggleComparison={handleComparisonToggle}
                />

                {/* Distinct Brands */}
                <MetricCard
                    label={stats.distinct_brands.label}
                    value={stats.distinct_brands.formatted}
                    trend={stats.distinct_brands.trend_pct}
                    trendDirection={stats.distinct_brands.trend_direction}
                    comparisonLabel={comparisonLabel}
                    onToggleComparison={handleComparisonToggle}
                />
            </div>
        </div>
    );
}
