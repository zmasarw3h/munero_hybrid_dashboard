'use client';

import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { ArrowUpDown, TrendingUp, TrendingDown } from 'lucide-react';
import { useState, type ReactNode } from 'react';

export interface ColumnDef<T = unknown> {
    key: string;
    header: string;
    accessor: (row: T) => unknown;
    sortable?: boolean;
    align?: 'left' | 'center' | 'right';
    format?: (value: unknown) => ReactNode;
    className?: string;
}

interface DataTableProps<T = unknown> {
    columns: ColumnDef<T>[];
    data: T[];
    onRowClick?: (row: T) => void;
    emptyMessage?: string;
    highlightedRowId?: string;
    getRowId?: (row: T) => string;
}

export function DataTable<T = unknown>({
    columns,
    data,
    onRowClick,
    emptyMessage = 'No data available',
    highlightedRowId,
    getRowId,
}: DataTableProps<T>) {
    const [sortConfig, setSortConfig] = useState<{
        key: string;
        direction: 'asc' | 'desc';
    } | null>(null);

    // Sort data
    const sortedData = [...data].sort((a, b) => {
        if (!sortConfig) return 0;

        const column = columns.find((col) => col.key === sortConfig.key);
        if (!column) return 0;

        const aValue = column.accessor(a);
        const bValue = column.accessor(b);

        if (aValue === bValue) return 0;

        const comparison =
            (aValue as string | number) > (bValue as string | number) ? 1 : -1;
        return sortConfig.direction === 'asc' ? comparison : -comparison;
    });

    const handleSort = (key: string) => {
        const column = columns.find((col) => col.key === key);
        if (!column?.sortable) return;

        setSortConfig((current) => {
            if (!current || current.key !== key) {
                return { key, direction: 'desc' };
            }
            if (current.direction === 'desc') {
                return { key, direction: 'asc' };
            }
            return null;
        });
    };

    if (data.length === 0) {
        return (
            <div className="w-full py-12 text-center text-muted-foreground">
                <p className="text-sm">{emptyMessage}</p>
            </div>
        );
    }

    return (
        <div className="w-full overflow-auto rounded-lg border border-gray-200 dark:border-gray-800">
            <Table>
                <TableHeader>
                    <TableRow className="bg-gray-50 dark:bg-gray-900">
                        {columns.map((column) => (
                            <TableHead
                                key={column.key}
                                className={`font-semibold ${column.align === 'right' ? 'text-right' : column.align === 'center' ? 'text-center' : 'text-left'} ${column.sortable ? 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800' : ''
                                    } ${column.className || ''}`}
                                onClick={() => handleSort(column.key)}
                            >
                                <div className="flex items-center gap-2 justify-between">
                                    <span>{column.header}</span>
                                    {column.sortable && (
                                        <div className="flex flex-col">
                                            {sortConfig?.key === column.key ? (
                                                sortConfig.direction === 'asc' ? (
                                                    <TrendingUp className="h-3 w-3 text-blue-600" />
                                                ) : (
                                                    <TrendingDown className="h-3 w-3 text-blue-600" />
                                                )
                                            ) : (
                                                <ArrowUpDown className="h-3 w-3 text-gray-400" />
                                            )}
                                        </div>
                                    )}
                                </div>
                            </TableHead>
                        ))}
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {sortedData.map((row, index) => {
                        const rowId = getRowId?.(row) || index.toString();
                        const isHighlighted = rowId === highlightedRowId;

                        return (
                            <TableRow
                                key={rowId}
                                onClick={() => onRowClick?.(row)}
                                className={`
                  ${onRowClick ? 'cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-950' : ''}
                  ${isHighlighted ? 'bg-blue-100 dark:bg-blue-900' : ''}
                  transition-colors
                `}
                            >
                                {columns.map((column) => {
                                    const value = column.accessor(row);
                                    const formattedValue = column.format
                                        ? column.format(value)
                                        : (value as ReactNode);

                                    return (
                                        <TableCell
                                            key={`${rowId}-${column.key}`}
                                            className={`${column.align === 'right'
                                                    ? 'text-right'
                                                    : column.align === 'center'
                                                        ? 'text-center'
                                                        : 'text-left'
                                                } ${column.className || ''}`}
                                        >
                                            {formattedValue}
                                        </TableCell>
                                    );
                                })}
                            </TableRow>
                        );
                    })}
                </TableBody>
            </Table>
        </div>
    );
}

// Helper function for common column formatters
export const formatters = {
    currency: (value: number, currency = 'AED') =>
        `${currency} ${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,

    number: (value: number) => value.toLocaleString(),

    percentage: (value: number) => `${value.toFixed(1)}%`,

    date: (value: string | Date) => {
        const date = typeof value === 'string' ? new Date(value) : value;
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    },

    badge: (value: string, colorMap?: Record<string, string>) => {
        const color = colorMap?.[value] || 'gray';
        return (
            <span
                className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-${color}-100 text-${color}-700`}
            >
                {value}
            </span>
        );
    },
};
