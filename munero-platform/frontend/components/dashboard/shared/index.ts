/**
 * Shared leaderboard components and utilities
 * Use these for consistent leaderboard/table experiences across all dashboard pages
 */

// Base leaderboard component
export { BaseLeaderboard } from './BaseLeaderboard';
export type { BaseLeaderboardProps } from './BaseLeaderboard';

// Badge components
export {
    LeaderboardBadge,
    ProductTypeBadge,
    SegmentBadge,
    StatusBadge,
} from './LeaderboardBadge';
export type { LeaderboardBadgeProps } from './LeaderboardBadge';

// Utilities and types
export {
    // Formatting
    formatCurrency,
    formatNumber,
    formatPercentage,
    formatGrowth,
    truncateText,
    // Sorting
    getNextSortDirection,
    sortData,
    // Column helpers
    createColumn,
    // Style constants
    LEADERBOARD_STYLES,
} from './leaderboard-utils';

export type {
    SortDirection,
    SortConfig,
    ColumnDef,
} from './leaderboard-utils';
