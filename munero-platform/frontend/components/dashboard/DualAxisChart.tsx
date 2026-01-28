'use client';

import React from 'react';
import {
    ResponsiveContainer,
    ComposedChart,
    Bar,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    Cell,
} from 'recharts';
import type { LegendPayload } from 'recharts';
import { ArrowLeftRight, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';

/**
 * Data point type for the chart - supports any key-value pairs
 */
export type ChartDataPoint = Record<string, string | number | boolean | null | undefined> & {
    is_revenue_anomaly?: boolean;
    is_order_anomaly?: boolean;
};

/**
 * DualAxisChart Props Interface
 * For Executive Overview page - visualizes Revenue and Order Volume on the same timeline
 */
export interface DualAxisChartProps {
    data: ChartDataPoint[];
    barKey: string;
    lineKey: string;
    xKey: string;
    title: string;
    height?: number;
    onMetricToggle?: () => void;
    anomalyThreshold?: number;
    granularity?: 'day' | 'month' | 'year';
    onGranularityChange?: (granularity: 'day' | 'month' | 'year') => void;
}

/**
 * Custom Tooltip Component
 * Displays metric values and anomaly indicators
 */
type TooltipPayloadItem = {
    name?: string | number;
    value?: string | number;
    color?: string;
    payload?: ChartDataPoint;
};

type DualAxisTooltipProps = {
    active?: boolean;
    payload?: TooltipPayloadItem[];
    label?: string | number;
};

const CustomTooltip = ({ active, payload, label }: DualAxisTooltipProps) => {
    if (!active || !payload || !payload.length) {
        return null;
    }

    const data = payload[0]?.payload;

    return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
            <p className="font-semibold text-sm text-gray-900 dark:text-gray-100 mb-2">
                {label}
            </p>
            {payload.map((entry, index) => (
                <div key={index} className="flex items-center gap-2 text-xs mb-1">
                    <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: entry.color }}
                    />
                    <span className="text-gray-700 dark:text-gray-300">
                        {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
                    </span>
                </div>
            ))}
            {/* Show anomaly indicators if present */}
            {data?.is_revenue_anomaly && (
                <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-600 flex items-center gap-1 text-xs text-red-600 dark:text-red-400 font-medium">
                    <AlertCircle className="h-3 w-3" />
                    Revenue Anomaly Detected
                </div>
            )}
            {data?.is_order_anomaly && (
                <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-600 flex items-center gap-1 text-xs text-red-600 dark:text-red-400 font-medium">
                    <AlertCircle className="h-3 w-3" />
                    Order Anomaly Detected
                </div>
            )}
        </div>
    );
};

/**
 * Format Y-axis labels for better readability
 */
const formatYAxis = (value: number) => {
    if (value >= 1000000) {
        return `${(value / 1000000).toFixed(1)}M`;
    }
    if (value >= 1000) {
        return `${(value / 1000).toFixed(1)}K`;
    }
    return value.toString();
};

/**
 * Custom Legend Component
 */
type LegendContentProps = {
    payload?: ReadonlyArray<LegendPayload>;
};

const renderLegend = ({ payload }: LegendContentProps, anomalyCount: number) => {
    if (!payload?.length) return null;
    return (
        <div className="flex flex-wrap justify-center gap-6 mt-3">
            {payload.map((entry, index) => (
                <div key={index} className="flex items-center gap-2">
                    <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: entry.color }}
                    />
                    <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
                        {entry.value}
                    </span>
                </div>
            ))}
            {/* Add anomaly indicator to legend */}
            {anomalyCount > 0 && (
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500" />
                    <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
                        Anomalies ({anomalyCount})
                    </span>
                </div>
            )}
        </div>
    );
};

/**
 * DualAxisChart Component
 * 
 * A sophisticated chart component for the Executive Overview page that visualizes
 * both Revenue and Order Volume on the same timeline using dual Y-axes.
 * 
 * Features:
 * - Bar chart for primary metric (Blue #3b82f6)
 * - Line chart for secondary metric (Orange #f97316, 2px stroke)
 * - Scatter overlay for anomaly detection (Red #ef4444 dots)
 * - Interactive "Swap Axis" button to toggle bar/line assignment
 * - Responsive design with proper axis formatting
 * - Custom tooltips for enhanced UX
 * - Legend for metric identification
 * 
 * @example
 * ```tsx
 * <DualAxisChart
 *   data={revenueData}
 *   barKey="revenue"
 *   lineKey="order_count"
 *   xKey="month"
 *   title="Revenue & Order Volume Trends"
 *   onMetricToggle={() => handleSwapMetrics()}
 * />
 * ```
 */
export function DualAxisChart({
    data,
    barKey,
    lineKey,
    xKey,
    title,
    height = 400,
    onMetricToggle,
    anomalyThreshold,
    granularity = 'month',
    onGranularityChange,
}: DualAxisChartProps) {
    /**
     * Count anomaly points for legend display
     */
    const anomalyCount = data.filter(
        (point) => point.is_revenue_anomaly === true || point.is_order_anomaly === true
    ).length;

    /**
     * Format metric names for display
     */
    const formatMetricName = (key: string) => {
        return key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
    };

    return (
        <Card className="w-full">
            {/* Header with Title and Controls */}
            <CardHeader className="flex flex-row items-center justify-between space-y-0 py-2 px-4">
                {/* Title and threshold on the left */}
                <div>
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                        {title}
                    </h3>
                    {anomalyThreshold !== undefined && (
                        <p className="text-xs text-gray-500">
                            Anomalies: Z &gt; {anomalyThreshold}
                        </p>
                    )}
                </div>

                {/* Controls on the right */}
                <div className="flex items-center gap-2">
                    {/* Granularity Selector */}
                    {onGranularityChange && (
                        <div className="flex rounded-lg border border-gray-200 overflow-hidden">
                            {(['day', 'month', 'year'] as const).map((g) => (
                                <button
                                    key={g}
                                    onClick={() => onGranularityChange(g)}
                                    className={`px-3 py-1.5 text-xs font-medium transition-colors ${granularity === g
                                        ? 'bg-blue-500 text-white'
                                        : 'bg-white text-gray-600 hover:bg-gray-50'
                                        }`}
                                >
                                    {g.charAt(0).toUpperCase() + g.slice(1)}
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Swap Axis Button */}
                    {onMetricToggle && (
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onMetricToggle}
                            className="gap-2 hover:bg-gray-100 dark:hover:bg-gray-800"
                        >
                            <ArrowLeftRight className="h-4 w-4" />
                            Swap Axis
                        </Button>
                    )}
                </div>
            </CardHeader>

            <CardContent className="p-3 pt-0">
                {/* Empty State */}
                {(!data || data.length === 0) ? (
                    <div className="flex items-center justify-center text-gray-500 dark:text-gray-400" style={{ height: height - 60 }}>
                        <div className="text-center">
                            <p className="text-lg font-medium">No data available</p>
                            <p className="text-sm mt-2">Adjust filters to view chart data</p>
                        </div>
                    </div>
                ) : (
                    /* Chart Container */
                    <ResponsiveContainer width="100%" height={height - 60}>
                        <ComposedChart
                            data={data}
                            margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                        >
                            {/* Grid */}
                            <CartesianGrid
                                strokeDasharray="3 3"
                                stroke="#e5e7eb"
                                className="dark:stroke-gray-700"
                            />

                            {/* X-Axis */}
                            <XAxis
                                dataKey={xKey}
                                tick={{ fill: '#6b7280', fontSize: 12 }}
                                tickLine={{ stroke: '#d1d5db' }}
                                axisLine={{ stroke: '#d1d5db' }}
                            />

                            {/* Left Y-Axis (Bar) */}
                            <YAxis
                                yAxisId="left"
                                tick={{ fill: '#6b7280', fontSize: 12 }}
                                tickLine={{ stroke: '#d1d5db' }}
                                axisLine={{ stroke: '#d1d5db' }}
                                tickFormatter={formatYAxis}
                            />

                            {/* Right Y-Axis (Line) */}
                            <YAxis
                                yAxisId="right"
                                orientation="right"
                                tick={{ fill: '#6b7280', fontSize: 12 }}
                                tickLine={{ stroke: '#d1d5db' }}
                                axisLine={{ stroke: '#d1d5db' }}
                                tickFormatter={formatYAxis}
                            />

                            {/* Tooltip */}
                            <Tooltip content={<CustomTooltip />} />

                            {/* Legend */}
                            <Legend content={(props) => renderLegend(props, anomalyCount)} />

                            {/* Bar Chart (Primary Metric) - Blue #3b82f6, Red #ef4444 for anomalies */}
                            <Bar
                                yAxisId="left"
                                dataKey={barKey}
                                name={formatMetricName(barKey)}
                                radius={[4, 4, 0, 0]}
                                maxBarSize={60}
                            >
                                {data.map((entry, index) => {
                                    const isAnomaly = entry.is_revenue_anomaly || entry.is_order_anomaly;
                                    return (
                                        <Cell
                                            key={`cell-${index}`}
                                            fill={isAnomaly ? '#ef4444' : '#3b82f6'}
                                        />
                                    );
                                })}
                            </Bar>

                            {/* Line Chart (Secondary Metric) - Orange #f97316, 2px stroke */}
                            <Line
                                yAxisId="right"
                                type="monotone"
                                dataKey={lineKey}
                                stroke="#f97316"
                                strokeWidth={2}
                                name={formatMetricName(lineKey)}
                                dot={{ fill: '#f97316', r: 4 }}
                                activeDot={{ r: 6 }}
                            />
                        </ComposedChart>
                    </ResponsiveContainer>
                )}
            </CardContent>
        </Card>
    );
}
