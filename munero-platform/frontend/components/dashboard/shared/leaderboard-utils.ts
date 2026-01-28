/**
 * Shared utilities for leaderboard components
 * Provides consistent formatting, styling, and behavior across all leaderboards
 */

import { ReactNode } from 'react';

// ============================================================================
// CURRENCY FORMATTING
// ============================================================================

/**
 * Format currency with optional compact notation
 * @param value - The numeric value to format
 * @param currency - Currency code (default: 'AED')
 * @param compact - Use compact notation (K, M) for large numbers
 */
export function formatCurrency(
    value: number,
    currency: string = 'AED',
    compact: boolean = true
): string {
    if (compact) {
        if (value >= 1_000_000) {
            return `${currency} ${(value / 1_000_000).toFixed(2)}M`;
        }
        if (value >= 1_000) {
            return `${currency} ${(value / 1_000).toFixed(1)}K`;
        }
    }
    return `${currency} ${value.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    })}`;
}

// ============================================================================
// NUMBER FORMATTING
// ============================================================================

/**
 * Format a number with locale-specific separators
 */
export function formatNumber(value: number): string {
    return value.toLocaleString();
}

/**
 * Format a percentage value
 * @param value - The percentage value
 * @param decimals - Number of decimal places (default: 1)
 */
export function formatPercentage(value: number | null, decimals: number = 1): string {
    if (value === null || value === undefined) return 'N/A';
    return `${value.toFixed(decimals)}%`;
}

/**
 * Format growth percentage with arrow indicator
 * @param value - The growth percentage
 * @param showArrow - Whether to show up/down arrow
 */
export function formatGrowth(value: number | null, showArrow: boolean = true): {
    text: string;
    color: string;
    isPositive: boolean | null;
} {
    if (value === null || value === undefined) {
        return { text: 'N/A', color: 'text-gray-400', isPositive: null };
    }

    const isPositive = value >= 0;
    const arrow = showArrow ? (isPositive ? '↑ ' : '↓ ') : '';
    const color = isPositive ? 'text-green-600' : 'text-red-600';

    return {
        text: `${arrow}${Math.abs(value).toFixed(1)}%`,
        color,
        isPositive,
    };
}

// ============================================================================
// TEXT UTILITIES
// ============================================================================

/**
 * Truncate text to a maximum length
 * @param text - The text to truncate
 * @param maxLength - Maximum length before truncation
 */
export function truncateText(text: string, maxLength: number = 30): string {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

// ============================================================================
// SORTING UTILITIES
// ============================================================================

export type SortDirection = 'asc' | 'desc' | null;

export interface SortConfig<K extends string = string> {
    key: K;
    direction: SortDirection;
}

/**
 * Get the next sort direction in the tri-state cycle
 * null -> desc -> asc -> null
 */
export function getNextSortDirection(currentDirection: SortDirection): SortDirection {
    if (currentDirection === null) return 'desc';
    if (currentDirection === 'desc') return 'asc';
    return null;
}

/**
 * Generic sort function for leaderboard data
 */
export function sortData<T>(
    data: T[],
    sortConfig: SortConfig | null,
    accessor: (item: T, key: string) => unknown
): T[] {
    if (!sortConfig || !sortConfig.direction) return data;

    return [...data].sort((a, b) => {
        const aValue = accessor(a, sortConfig.key);
        const bValue = accessor(b, sortConfig.key);

        // Handle null/undefined values
        if (aValue == null && bValue == null) return 0;
        if (aValue == null) return 1;
        if (bValue == null) return -1;

        // Compare values
        if (aValue === bValue) return 0;
        const comparison = aValue > bValue ? 1 : -1;
        return sortConfig.direction === 'asc' ? comparison : -comparison;
    });
}

// ============================================================================
// STYLE CONSTANTS
// ============================================================================

export const LEADERBOARD_STYLES = {
    // Table container
    tableContainer: 'w-full overflow-auto rounded-lg border border-gray-200 dark:border-gray-800',

    // Header row
    headerRow: 'bg-gray-50 dark:bg-gray-900',
    headerCell: 'font-semibold',
    headerCellSortable: 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800',

    // Body rows
    row: 'transition-colors',
    rowHover: 'hover:bg-gray-50 dark:hover:bg-gray-800',
    rowClickable: 'cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-950',
    rowSelected: 'bg-blue-100 dark:bg-blue-900',

    // Cells
    cellNumeric: 'text-right tabular-nums',

    // Loading skeleton
    skeletonRow: 'h-12 bg-gray-100 dark:bg-gray-800 animate-pulse rounded',

    // Empty state
    emptyContainer: 'flex items-center justify-center py-12 text-muted-foreground',
    emptyIcon: 'h-10 w-10 mx-auto mb-2 opacity-50',
    emptyText: 'text-sm',
} as const;

// ============================================================================
// COLUMN DEFINITION TYPES
// ============================================================================

export interface ColumnDef<T = unknown> {
    key: string;
    header: string;
    accessor: (row: T) => unknown;
    sortable?: boolean;
    align?: 'left' | 'center' | 'right';
    width?: string;
    className?: string;
    render?: (value: unknown, row: T) => ReactNode;
}

/**
 * Create a standard column definition with sensible defaults
 */
export function createColumn<T>(
    key: string,
    header: string,
    accessor: (row: T) => unknown,
    options: Partial<Omit<ColumnDef<T>, 'key' | 'header' | 'accessor'>> = {}
): ColumnDef<T> {
    return {
        key,
        header,
        accessor,
        sortable: true,
        align: 'left',
        ...options,
    };
}
