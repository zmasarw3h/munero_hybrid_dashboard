// Dashboard Components Index
// Export all dashboard components for easy importing

export { MetricCard } from './MetricCard';
export { DualAxisChart } from './DualAxisChart';
export { ClientScatter } from './ClientScatter';
export { DataTable, formatters } from './DataTable';
export { KPIGrid } from './KPIGrid';
export { FilterBar } from './FilterBar';
export { NavTabs } from './NavTabs';
export { FilterProvider, useFilters, transformFiltersForAPI } from './FilterContext';
export { ProductTypeChart } from './ProductTypeChart';
export { AnomalyCard } from './AnomalyCard';

// Overview V2 Components
export { MiniSparkline } from './MiniSparkline';
export { EnhancedKPICard } from './EnhancedKPICard';
export { CompactDonut } from './CompactDonut';
export { StuckOrdersList } from './StuckOrdersList';
export { OperationalHealthPanel } from './OperationalHealthPanel';
export { TopPerformersChart } from './TopPerformersChart';
export { AnomalyTicker } from './AnomalyTicker';
export { GeographyMap } from './GeographyMap';

// Market Analysis Components
export { ClientSegmentationMatrix } from './ClientSegmentationMatrix';
export { RevenueConcentrationChart } from './RevenueConcentrationChart';
export { ClientLeaderboard } from './ClientLeaderboard';

// Catalog Analysis Components
export { ProductPerformanceMatrix } from './catalog';
export type { ProductScatterPoint, ProductPerformanceMatrixProps } from './catalog';

// Shared Leaderboard Components
export {
    BaseLeaderboard,
    LeaderboardBadge,
    ProductTypeBadge,
    SegmentBadge,
    StatusBadge,
    formatCurrency,
    formatNumber,
    formatPercentage,
    formatGrowth,
    truncateText,
    createColumn,
    LEADERBOARD_STYLES,
} from './shared';
export type {
    BaseLeaderboardProps,
    LeaderboardBadgeProps,
    SortDirection,
    SortConfig,
    ColumnDef as LeaderboardColumnDef,
} from './shared';

// Re-export types from DataTable
export type { ColumnDef } from './DataTable';

// Export types from other components if needed
export type { MetricCardProps } from './MetricCard';
export type { DualAxisChartProps, ChartDataPoint } from './DualAxisChart';
export type { ClientData, ClientScatterProps } from './ClientScatter';
export type { DashboardFilters } from './FilterContext';
