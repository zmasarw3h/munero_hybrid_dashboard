'use client';

import { memo } from 'react';
import { ChatChartConfig } from '@/lib/types';
import {
    BarChart,
    Bar,
    LineChart,
    Line,
    PieChart,
    Pie,
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell,
    Legend,
} from 'recharts';

interface ChatChartProps {
    config: ChatChartConfig;
    data: Record<string, unknown>[];
}

// Color palette for pie chart slices
const CHART_COLORS = [
    '#3b82f6', // blue-500
    '#10b981', // emerald-500
    '#f59e0b', // amber-500
    '#ef4444', // red-500
    '#8b5cf6', // violet-500
    '#ec4899', // pink-500
    '#06b6d4', // cyan-500
    '#84cc16', // lime-500
];

// Format large numbers
function formatNumber(value: number): string {
    if (Math.abs(value) >= 1000000) {
        return (value / 1000000).toFixed(1) + 'M';
    }
    if (Math.abs(value) >= 1000) {
        return (value / 1000).toFixed(1) + 'K';
    }
    return value.toLocaleString();
}

// Custom tooltip formatter
function CustomTooltip({ active, payload, label }: {
    active?: boolean;
    payload?: Array<{ value: number; name: string; color: string }>;
    label?: string;
}) {
    if (!active || !payload?.length) return null;

    return (
        <div className="bg-background border border-border rounded-md shadow-lg p-2 text-xs">
            {label && <p className="font-medium mb-1">{label}</p>}
            {payload.map((entry, index) => (
                <p key={index} style={{ color: entry.color }}>
                    {entry.name}: {typeof entry.value === 'number' ? formatNumber(entry.value) : entry.value}
                </p>
            ))}
        </div>
    );
}

export function ChatChart({ config, data }: ChatChartProps) {
    if (!data || data.length === 0) {
        return (
            <div className="h-[200px] flex items-center justify-center text-muted-foreground text-sm">
                No data to display
            </div>
        );
    }

    // Metric (KPI) display
    if (config.type === 'metric') {
        const firstRow = data[0];
        const keys = Object.keys(firstRow);
        const valueKey = config.y_column || keys[0];
        const value = firstRow[valueKey];

        return (
            <div className="text-center py-6">
                <div className="text-3xl font-bold text-blue-600">
                    {typeof value === 'number' ? formatNumber(value) : String(value)}
                </div>
                {config.title && (
                    <div className="text-sm text-muted-foreground mt-1">{config.title}</div>
                )}
            </div>
        );
    }

    // Table display
    if (config.type === 'table') {
        const columns = Object.keys(data[0] || {});
        const displayData = data.slice(0, 10); // Show first 10 rows

        return (
            <div className="overflow-x-auto">
                <table className="w-full text-xs">
                    <thead>
                        <tr className="border-b">
                            {columns.map((col) => (
                                <th key={col} className="text-left p-2 font-medium text-muted-foreground">
                                    {col.replace(/_/g, ' ')}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {displayData.map((row, idx) => (
                            <tr key={idx} className="border-b last:border-0">
                                {columns.map((col) => (
                                    <td key={col} className="p-2">
                                        {typeof row[col] === 'number'
                                            ? formatNumber(row[col] as number)
                                            : String(row[col] ?? '')}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
                {data.length > 10 && (
                    <p className="text-xs text-muted-foreground text-center mt-2">
                        Showing 10 of {data.length} rows
                    </p>
                )}
            </div>
        );
    }

    // Bar Chart
    if (config.type === 'bar') {
        const isHorizontal = config.orientation === 'horizontal';
        const primaryKey = config.y_column || 'value';
        const secondaryKey = config.secondary_y_column;
        const showLegend = Boolean(secondaryKey);

        if (isHorizontal) {
            return (
                <ResponsiveContainer width="100%" height={200}>
                    <BarChart
                        data={data}
                        layout="vertical"
                        margin={{ top: 5, right: 10, left: 10, bottom: 5 }}
                    >
                        <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                        <XAxis type="number" tickFormatter={formatNumber} tick={{ fontSize: 10 }} />
                        <YAxis
                            type="category"
                            dataKey={config.x_column}
                            width={100}
                            tick={{ fontSize: 10 }}
                            tickFormatter={(value: string) => value.length > 15 ? value.slice(0, 15) + '...' : value}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        {showLegend && <Legend />}
                        <Bar dataKey={primaryKey} fill="#3b82f6" radius={[0, 4, 4, 0]} />
                        {secondaryKey && (
                            <Bar dataKey={secondaryKey} fill="#10b981" radius={[0, 4, 4, 0]} />
                        )}
                    </BarChart>
                </ResponsiveContainer>
            );
        }

        return (
            <ResponsiveContainer width="100%" height={200}>
                <BarChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis
                        dataKey={config.x_column}
                        tick={{ fontSize: 10 }}
                        tickFormatter={(value: string) => value.length > 10 ? value.slice(0, 10) + '...' : value}
                    />
                    <YAxis tickFormatter={formatNumber} tick={{ fontSize: 10 }} />
                    <Tooltip content={<CustomTooltip />} />
                    {showLegend && <Legend />}
                    <Bar dataKey={primaryKey} fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    {secondaryKey && (
                        <Bar dataKey={secondaryKey} fill="#10b981" radius={[4, 4, 0, 0]} />
                    )}
                </BarChart>
            </ResponsiveContainer>
        );
    }

    // Line Chart
    if (config.type === 'line') {
        return (
            <ResponsiveContainer width="100%" height={200}>
                <LineChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis
                        dataKey={config.x_column}
                        tick={{ fontSize: 10 }}
                    />
                    <YAxis tickFormatter={formatNumber} tick={{ fontSize: 10 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Line
                        type="monotone"
                        dataKey={config.y_column || 'value'}
                        stroke="#3b82f6"
                        strokeWidth={2}
                        dot={{ fill: '#3b82f6', r: 3 }}
                        activeDot={{ r: 5 }}
                    />
                    {config.secondary_y_column && (
                        <Line
                            type="monotone"
                            dataKey={config.secondary_y_column}
                            stroke="#10b981"
                            strokeWidth={2}
                            dot={{ fill: '#10b981', r: 3 }}
                        />
                    )}
                </LineChart>
            </ResponsiveContainer>
        );
    }

    // Pie Chart
    if (config.type === 'pie') {
        return (
            <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                    <Pie
                        data={data}
                        dataKey={config.y_column || 'value'}
                        nameKey={config.x_column || 'name'}
                        cx="50%"
                        cy="50%"
                        outerRadius={70}
                        label={({ name, percent }) => {
                            const displayName = String(name || '');
                            const truncated = displayName.length > 10 ? displayName.slice(0, 10) + '...' : displayName;
                            return `${truncated} (${((percent || 0) * 100).toFixed(0)}%)`;
                        }}
                        labelLine={false}
                    >
                        {data.map((_, index) => (
                            <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                        ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                </PieChart>
            </ResponsiveContainer>
        );
    }

    // Scatter Chart
    if (config.type === 'scatter') {
        return (
            <ResponsiveContainer width="100%" height={200}>
                <ScatterChart margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                        type="number"
                        dataKey={config.x_column}
                        name={config.x_column}
                        tickFormatter={formatNumber}
                        tick={{ fontSize: 10 }}
                    />
                    <YAxis
                        type="number"
                        dataKey={config.y_column}
                        name={config.y_column}
                        tickFormatter={formatNumber}
                        tick={{ fontSize: 10 }}
                    />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }} content={<CustomTooltip />} />
                    <Scatter data={data} fill="#3b82f6">
                        {data.map((_, index) => (
                            <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                        ))}
                    </Scatter>
                </ScatterChart>
            </ResponsiveContainer>
        );
    }

    // Fallback for unknown chart type
    return (
        <div className="h-[200px] flex items-center justify-center text-muted-foreground text-sm">
            Unsupported chart type: {config.type}
        </div>
    );
}

// Memoized version for performance
export const MemoizedChatChart = memo(ChatChart);
