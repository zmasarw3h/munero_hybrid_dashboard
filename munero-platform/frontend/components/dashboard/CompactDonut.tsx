'use client';

/**
 * CompactDonut - Small donut chart with legend table
 * 
 * Designed for the Operational Health Panel to show revenue by type breakdown.
 * Features a compact donut with a table legend below.
 */

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface DonutSegment {
    name: string;
    value: number;
    color: string;
    [key: string]: string | number;  // Index signature for Recharts compatibility
}

interface CompactDonutProps {
    /** Chart title */
    title: string;
    /** Data segments */
    data: DonutSegment[];
    /** Donut size in pixels */
    size?: number;
    /** Inner radius ratio (0-1) */
    innerRadiusRatio?: number;
    /** Click handler for segments */
    onSegmentClick?: (segment: DonutSegment) => void;
    /** Optional className */
    className?: string;
    /** Currency for formatting (only used when valueFormat is 'currency') */
    currency?: string;
    /** Fixed height for the card (optional) */
    height?: number;
    /** Value format: 'currency' (default) or 'count' */
    valueFormat?: 'currency' | 'count';
}

function formatValue(value: number, currency: string = 'AED', format: 'currency' | 'count' = 'currency'): string {
    if (format === 'count') {
        return value.toLocaleString();
    }
    if (value >= 1000000) {
        return `${currency} ${(value / 1000000).toFixed(1)}M`;
    }
    if (value >= 1000) {
        return `${currency} ${(value / 1000).toFixed(0)}K`;
    }
    return `${currency} ${value.toFixed(0)}`;
}

function formatPercent(value: number, total: number): string {
    if (total === 0) return '0%';
    return `${((value / total) * 100).toFixed(0)}%`;
}

export function CompactDonut({
    title,
    data,
    size = 120,
    innerRadiusRatio = 0.6,
    onSegmentClick,
    className,
    currency = 'AED',
    height,
    valueFormat = 'currency',
}: CompactDonutProps) {
    const total = data.reduce((sum, d) => sum + d.value, 0);

    // Empty state
    if (!data || data.length === 0 || total === 0) {
        return (
            <Card className={className}>
                <CardHeader className="py-2 px-3">
                    <CardTitle className="text-sm font-medium">{title}</CardTitle>
                </CardHeader>
                <CardContent className="pb-3 px-3">
                    <div className="flex items-center justify-center h-20 text-sm text-muted-foreground">
                        No data available
                    </div>
                </CardContent>
            </Card>
        );
    }

    // Use height for fixed card sizing and internal calculations
    // Calculate chart size to fill available space while leaving room for legend
    const chartSize = height ? Math.min(height - 200, 140) : size;
    const chartOuterRadius = chartSize / 2 - 5;
    const chartInnerRadius = chartOuterRadius * innerRadiusRatio;

    return (
        <Card className={cn('overflow-hidden', className)} style={height ? { height } : undefined}>
            <CardHeader className="py-2 px-3">
                <CardTitle className="text-sm font-medium">{title}</CardTitle>
            </CardHeader>
            <CardContent className="pb-3 px-3 flex flex-col">
                {/* Donut Chart */}
                <div className="flex justify-center items-center">
                    <div style={{ width: chartSize, height: chartSize }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={data}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={chartInnerRadius}
                                    outerRadius={chartOuterRadius}
                                    paddingAngle={2}
                                    dataKey="value"
                                    onClick={(_, index) => onSegmentClick?.(data[index])}
                                    style={{ cursor: onSegmentClick ? 'pointer' : 'default' }}
                                >
                                    {data.map((entry, index) => (
                                        <Cell
                                            key={`cell-${index}`}
                                            fill={entry.color}
                                            stroke="none"
                                        />
                                    ))}
                                </Pie>
                                <Tooltip
                                    formatter={(value) => formatValue(Number(value) || 0, currency, valueFormat)}
                                    contentStyle={{
                                        backgroundColor: 'hsl(var(--background))',
                                        border: '1px solid hsl(var(--border))',
                                        borderRadius: '6px',
                                        fontSize: '12px',
                                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                                        zIndex: 50,
                                    }}
                                    wrapperStyle={{ zIndex: 50 }}
                                    position={{ x: 0, y: -60 }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Legend Table - compact for narrow layouts */}
                <div className="space-y-2 mt-3">
                    {data.map((segment, index) => (
                        <div
                            key={index}
                            className={cn(
                                'flex flex-col text-sm',
                                onSegmentClick && 'cursor-pointer hover:bg-muted/50 rounded px-1 -mx-1 py-0.5'
                            )}
                            onClick={() => onSegmentClick?.(segment)}
                        >
                            <div className="flex items-center gap-2">
                                <div
                                    className="w-3 h-3 rounded-full flex-shrink-0"
                                    style={{ backgroundColor: segment.color }}
                                />
                                <span className="text-foreground font-medium truncate">{segment.name}</span>
                            </div>
                            <div className="flex items-center justify-between pl-5">
                                <span className="font-semibold tabular-nums text-foreground">
                                    {formatPercent(segment.value, total)}
                                </span>
                                <span className="text-muted-foreground tabular-nums">
                                    {formatValue(segment.value, currency, valueFormat)}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}

export default CompactDonut;
