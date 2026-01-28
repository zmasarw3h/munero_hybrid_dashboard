'use client';

import { useMemo, useState, ReactNode } from 'react';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowUpDown, TrendingUp, TrendingDown, X, Loader2 } from 'lucide-react';
import {
    ColumnDef,
    SortConfig,
    SortDirection,
    getNextSortDirection,
    sortData,
    LEADERBOARD_STYLES,
} from './leaderboard-utils';

// ============================================================================
// TYPES
// ============================================================================

export interface BaseLeaderboardProps<T = unknown> {
    /** Title displayed in card header */
    title: string;
    /** Optional description below title */
    description?: string;
    /** Column definitions */
    columns: ColumnDef<T>[];
    /** Data rows */
    data: T[];
    /** Loading state */
    loading?: boolean;
    /** Number of skeleton rows to show when loading */
    loadingRows?: number;
    /** Unique identifier for each row */
    getRowId: (row: T) => string;
    /** Callback when a row is clicked */
    onRowClick?: (row: T) => void;
    /** Currently selected row ID */
    selectedRowId?: string | null;
    /** Active filter info to display */
    activeFilter?: {
        label: string;
        badge?: ReactNode;
    };
    /** Callback to clear the active filter */
    onClearFilter?: () => void;
    /** Count info to display (e.g., "5 of 100 clients") */
    countInfo?: string;
    /** Message to show when no data */
    emptyMessage?: string;
    /** Icon to show in empty state */
    emptyIcon?: ReactNode;
    /** Default sort configuration */
    defaultSort?: SortConfig;
    /** Additional class for the card */
    className?: string;
}

// ============================================================================
// SORT ICON COMPONENT
// ============================================================================

function SortIcon({
    columnKey,
    sortConfig
}: {
    columnKey: string;
    sortConfig: SortConfig | null;
}) {
    if (!sortConfig || sortConfig.key !== columnKey || !sortConfig.direction) {
        return <ArrowUpDown className="h-3 w-3 text-gray-400" />;
    }
    return sortConfig.direction === 'asc' ? (
        <TrendingUp className="h-3 w-3 text-blue-600" />
    ) : (
        <TrendingDown className="h-3 w-3 text-blue-600" />
    );
}

// ============================================================================
// LOADING SKELETON
// ============================================================================

function LoadingSkeleton({
    rows = 5,
    title
}: {
    rows?: number;
    title: string;
}) {
    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="text-base">{title}</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="space-y-2">
                    {[...Array(rows)].map((_, i) => (
                        <div
                            key={i}
                            className={LEADERBOARD_STYLES.skeletonRow}
                        />
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}

// ============================================================================
// EMPTY STATE
// ============================================================================

function EmptyState({
    message,
    icon
}: {
    message: string;
    icon?: ReactNode;
}) {
    return (
        <div className={LEADERBOARD_STYLES.emptyContainer}>
            <div className="text-center">
                {icon && <div className={LEADERBOARD_STYLES.emptyIcon}>{icon}</div>}
                <p className={LEADERBOARD_STYLES.emptyText}>{message}</p>
            </div>
        </div>
    );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function BaseLeaderboard<T>({
    title,
    description,
    columns,
    data,
    loading = false,
    loadingRows = 5,
    getRowId,
    onRowClick,
    selectedRowId,
    activeFilter,
    onClearFilter,
    countInfo,
    emptyMessage = 'No data available',
    emptyIcon,
    defaultSort,
    className,
}: BaseLeaderboardProps<T>) {
    // Sort state
    const [sortConfig, setSortConfig] = useState<SortConfig | null>(defaultSort || null);

    // Sort data
    const sortedData = useMemo(() => {
        return sortData(data, sortConfig, (item, key) => {
            const column = columns.find((col) => col.key === key);
            return column ? column.accessor(item) : null;
        });
    }, [data, sortConfig, columns]);

    // Handle column sort
    const handleSort = (key: string) => {
        const column = columns.find((col) => col.key === key);
        if (!column?.sortable) return;

        setSortConfig((current) => {
            if (!current || current.key !== key) {
                return { key, direction: 'desc' };
            }
            const nextDirection = getNextSortDirection(current.direction);
            if (nextDirection === null) {
                return null;
            }
            return { key, direction: nextDirection };
        });
    };

    // Loading state
    if (loading) {
        return <LoadingSkeleton rows={loadingRows} title={title} />;
    }

    return (
        <Card className={className}>
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-base">{title}</CardTitle>
                    {activeFilter && onClearFilter && (
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onClearFilter}
                            className="text-xs h-7 px-2"
                        >
                            <X className="h-3 w-3 mr-1" />
                            Clear Filter
                            {activeFilter.badge && (
                                <span className="ml-2">{activeFilter.badge}</span>
                            )}
                            {!activeFilter.badge && activeFilter.label && (
                                <span className="ml-2 font-medium">{activeFilter.label}</span>
                            )}
                        </Button>
                    )}
                </div>
                {(description || countInfo) && (
                    <CardDescription className="text-xs">
                        {countInfo || description}
                    </CardDescription>
                )}
            </CardHeader>
            <CardContent>
                {data.length === 0 ? (
                    <EmptyState message={emptyMessage} icon={emptyIcon} />
                ) : (
                    <div className={LEADERBOARD_STYLES.tableContainer}>
                        <Table>
                            <TableHeader>
                                <TableRow className={LEADERBOARD_STYLES.headerRow}>
                                    {columns.map((column) => (
                                        <TableHead
                                            key={column.key}
                                            className={`
                        ${LEADERBOARD_STYLES.headerCell}
                        ${column.sortable ? LEADERBOARD_STYLES.headerCellSortable : ''}
                        ${column.align === 'right' ? 'text-right' : column.align === 'center' ? 'text-center' : 'text-left'}
                        ${column.className || ''}
                      `}
                                            style={column.width ? { width: column.width } : undefined}
                                            onClick={() => column.sortable && handleSort(column.key)}
                                        >
                                            <div className={`flex items-center gap-2 ${column.align === 'right' ? 'justify-end' : column.align === 'center' ? 'justify-center' : 'justify-between'}`}>
                                                <span>{column.header}</span>
                                                {column.sortable && (
                                                    <SortIcon columnKey={column.key} sortConfig={sortConfig} />
                                                )}
                                            </div>
                                        </TableHead>
                                    ))}
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {sortedData.map((row) => {
                                    const rowId = getRowId(row);
                                    const isSelected = rowId === selectedRowId;
                                    const isClickable = !!onRowClick;

                                    return (
                                        <TableRow
                                            key={rowId}
                                            onClick={() => onRowClick?.(row)}
                                            className={`
                        ${LEADERBOARD_STYLES.row}
                        ${isClickable ? LEADERBOARD_STYLES.rowClickable : LEADERBOARD_STYLES.rowHover}
                        ${isSelected ? LEADERBOARD_STYLES.rowSelected : ''}
                      `}
                                        >
                                            {columns.map((column) => {
                                                const value = column.accessor(row);
                                                const content = column.render
                                                    ? column.render(value, row)
                                                    : String(value ?? '');

                                                return (
                                                    <TableCell
                                                        key={`${rowId}-${column.key}`}
                                                        className={`
                              ${column.align === 'right' ? LEADERBOARD_STYLES.cellNumeric : ''}
                              ${column.align === 'center' ? 'text-center' : ''}
                              ${column.className || ''}
                            `}
                                                    >
                                                        {content}
                                                    </TableCell>
                                                );
                                            })}
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

export default BaseLeaderboard;
