'use client';

/**
 * MiniSparkline - Tiny inline chart for KPI cards
 * 
 * A minimal sparkline visualization designed to fit inside KPI cards.
 * Shows trends without axes, grid, or detailed tooltips.
 */

import { AreaChart, Area, LineChart, Line, ResponsiveContainer } from 'recharts';
import { useId } from 'react';

interface MiniSparklineProps {
    /** Array of values to display */
    data: number[];
    /** Chart type - area (filled) or line */
    type?: 'area' | 'line';
    /** Primary color for the chart */
    color?: string;
    /** Chart width in pixels (if not responsive) */
    width?: number;
    /** Chart height in pixels */
    height?: number;
    /** Whether to show gradient fill for area chart */
    showGradient?: boolean;
}

export function MiniSparkline({
    data,
    type = 'area',
    color = '#3b82f6', // Default blue
    width,
    height = 32,
    showGradient = true,
}: MiniSparklineProps) {
    const sparklineId = useId();

    // Convert number array to chart data format
    const chartData = data.map((value, index) => ({
        index,
        value,
    }));

    // Don't render if no data
    if (!data || data.length === 0) {
        return (
            <div
                className="flex items-center justify-center text-muted-foreground text-xs"
                style={{ height }}
            >
                No data
            </div>
        );
    }

    const gradientId = `sparkline-gradient-${sparklineId.replace(/:/g, '')}`;

    if (type === 'line') {
        return (
            <div style={{ width: width || '100%', height }}>
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
                        <Line
                            type="monotone"
                            dataKey="value"
                            stroke={color}
                            strokeWidth={1.5}
                            dot={false}
                            isAnimationActive={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        );
    }

    // Area chart (default)
    return (
        <div style={{ width: width || '100%', height }}>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
                    {showGradient && (
                        <defs>
                            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor={color} stopOpacity={0.3} />
                                <stop offset="100%" stopColor={color} stopOpacity={0.05} />
                            </linearGradient>
                        </defs>
                    )}
                    <Area
                        type="monotone"
                        dataKey="value"
                        stroke={color}
                        strokeWidth={1.5}
                        fill={showGradient ? `url(#${gradientId})` : color}
                        fillOpacity={showGradient ? 1 : 0.1}
                        isAnimationActive={false}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}

export default MiniSparkline;
