'use client';

import { memo } from 'react';
import { ChatChartConfig } from '@/lib/types';
import {
    BarChart,
    Bar,
    ComposedChart,
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

type AugmentedScatterRow = Record<string, unknown> & { __rank: number; __label: string };

const TABLE_ROW_LIMIT = 10;
const DUAL_AXIS_BAR_CHART_LIMIT = 5;

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

function formatKeyLabel(value: string): string {
    return value
        .replace(/[_-]+/g, ' ')
        .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatCategoryLabel(value: unknown): string {
    const raw = String(value ?? '');
    if (!raw) return '';
    if (/^\d{4}-\d{2}(-\d{2})?$/.test(raw)) return raw;
    if (raw.toUpperCase() === raw) return raw;

    const spaced = raw.replace(/_/g, ' ');
    if (raw === raw.toLowerCase()) {
        return spaced.replace(/\b\w/g, (char) => char.toUpperCase());
    }
    return spaced;
}

function truncateLabel(value: string, maxLength: number): string {
    return value.length > maxLength ? value.slice(0, maxLength) + '...' : value;
}

function formatCellValue(value: unknown): string {
    if (typeof value === 'number') return formatNumber(value);
    return String(value ?? '');
}

function inferScatterLabelKey(
    rows: Record<string, unknown>[],
    xKey?: string,
    yKey?: string
): string | null {
    if (!rows.length) return null;

    const excluded = new Set([xKey, yKey].filter(Boolean) as string[]);
    const candidateKeys = Object.keys(rows[0] || {}).filter((key) => !excluded.has(key));

    const tokenWeights: Array<{ token: string; weight: number }> = [
        { token: 'client_name', weight: 120 },
        { token: 'product_name', weight: 115 },
        { token: 'supplier_name', weight: 110 },
        { token: 'brand_name', weight: 105 },
        { token: 'country', weight: 95 },
        { token: 'category', weight: 90 },
        { token: 'name', weight: 80 },
        { token: 'client', weight: 60 },
        { token: 'supplier', weight: 55 },
        { token: 'product', weight: 50 },
        { token: 'brand', weight: 45 },
    ];

    function hasUsableStringValues(key: string): boolean {
        for (let i = 0; i < Math.min(rows.length, 15); i++) {
            const value = rows[i]?.[key];
            if (typeof value === 'string' && value.trim().length > 0) return true;
        }
        return false;
    }

    function scoreKey(key: string): number {
        const name = key.toLowerCase();
        let score = 0;
        for (const { token, weight } of tokenWeights) {
            if (name.includes(token)) score += weight;
        }
        if (name.includes('id') || name.includes('uuid') || name.includes('code')) score -= 80;
        return score;
    }

    const scored = candidateKeys
        .filter(hasUsableStringValues)
        .map((key) => ({ key, score: scoreKey(key) }))
        .sort((a, b) => b.score - a.score);

    return scored[0]?.key ?? null;
}

function ScatterTooltip({
    active,
    payload,
    labelKey,
    xKey,
    yKey,
}: {
    active?: boolean;
    payload?: Array<{ payload?: Record<string, unknown> }>;
    labelKey: string | null;
    xKey: string;
    yKey: string;
}) {
    if (!active || !payload?.length) return null;
    const row = payload[0]?.payload;
    if (!row) return null;

    const rank = row.__rank;
    const labelValue = labelKey ? row[labelKey] : null;

    return (
        <div className="bg-background border border-border rounded-md shadow-lg p-2 text-xs">
            <div className="flex items-baseline justify-between gap-3 mb-1">
                {labelKey && labelValue != null && String(labelValue).trim() !== '' && (
                    <p className="font-medium">{formatCategoryLabel(labelValue)}</p>
                )}
                {typeof rank === 'number' && (
                    <p className="text-muted-foreground">#{rank}</p>
                )}
            </div>
            <p>{formatKeyLabel(xKey)}: {formatCellValue(row[xKey])}</p>
            <p>{formatKeyLabel(yKey)}: {formatCellValue(row[yKey])}</p>
        </div>
    );
}

function NumberedScatterDot({
    cx,
    cy,
    fill,
    payload,
}: {
    cx?: number;
    cy?: number;
    fill?: string;
    payload?: Record<string, unknown>;
}) {
    if (cx == null || cy == null) return null;
    const rank = payload?.__rank;
    const label = payload?.__label;
    const shouldShowNumber = typeof rank === 'number' && typeof label === 'string' && label.trim() !== '';

    const radius = shouldShowNumber ? 7 : 6;
    return (
        <g>
            <circle cx={cx} cy={cy} r={radius} fill={fill || '#3b82f6'} />
            {shouldShowNumber && (
                <text
                    x={cx}
                    y={cy}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize={9}
                    fontWeight={600}
                    fill="#ffffff"
                >
                    {String(rank)}
                </text>
            )}
        </g>
    );
}

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
    label?: unknown;
}) {
    if (!active || !payload?.length) return null;

    return (
        <div className="bg-background border border-border rounded-md shadow-lg p-2 text-xs">
            {label != null && label !== '' && (
                <p className="font-medium mb-1">{formatCategoryLabel(label)}</p>
            )}
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
        const displayData = data.slice(0, TABLE_ROW_LIMIT);

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
                {displayData.length === TABLE_ROW_LIMIT && (
                    <p className="text-xs text-muted-foreground text-center mt-2">
                        Showing {displayData.length} rows
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

        if (isHorizontal) {
            if (secondaryKey) {
                const chartData = data.slice(0, DUAL_AXIS_BAR_CHART_LIMIT);
                const tableData = data.slice(0, TABLE_ROW_LIMIT);
                const columns = Object.keys(data[0] || {});
                return (
                    <div className="space-y-3">
                        <ResponsiveContainer width="100%" height={200}>
                            <BarChart
                                data={chartData}
                                layout="vertical"
                                margin={{ top: 5, right: 10, left: 10, bottom: 5 }}
                            >
                                <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
                                <XAxis
                                    xAxisId="left"
                                    type="number"
                                    tickFormatter={formatNumber}
                                    tick={{ fontSize: 10 }}
                                />
                                <XAxis
                                    xAxisId="right"
                                    type="number"
                                    orientation="top"
                                    tickFormatter={formatNumber}
                                    tick={{ fontSize: 10 }}
                                />
                                <YAxis
                                    type="category"
                                    dataKey={config.x_column}
                                    width={100}
                                    tick={{ fontSize: 10 }}
                                    tickFormatter={(value: string) => truncateLabel(formatCategoryLabel(value), 15)}
                                />
                                <Tooltip content={<CustomTooltip />} />
                                <Legend />
                                <Bar
                                    xAxisId="left"
                                    dataKey={primaryKey}
                                    name={formatKeyLabel(primaryKey)}
                                    fill="#3b82f6"
                                    radius={[0, 4, 4, 0]}
                                />
                                <Bar
                                    xAxisId="right"
                                    dataKey={secondaryKey}
                                    name={formatKeyLabel(secondaryKey)}
                                    fill="#10b981"
                                    radius={[0, 4, 4, 0]}
                                />
                            </BarChart>
                        </ResponsiveContainer>

                        {data.length > DUAL_AXIS_BAR_CHART_LIMIT && (
                            <p className="text-xs text-muted-foreground text-center">
                                Chart shows top {chartData.length} for readability. Table shows {tableData.length} rows.
                            </p>
                        )}

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
                                    {tableData.map((row, idx) => (
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
                            {tableData.length === TABLE_ROW_LIMIT && (
                                <p className="text-xs text-muted-foreground text-center mt-2">
                                    Showing {tableData.length} rows
                                </p>
                            )}
                        </div>
                    </div>
                );
            }

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
                            tickFormatter={(value: string) => truncateLabel(formatCategoryLabel(value), 15)}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar
                            dataKey={primaryKey}
                            name={formatKeyLabel(primaryKey)}
                            fill="#3b82f6"
                            radius={[0, 4, 4, 0]}
                        />
                    </BarChart>
                </ResponsiveContainer>
            );
        }

        if (secondaryKey) {
            return (
                <ResponsiveContainer width="100%" height={200}>
                    <ComposedChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis
                            dataKey={config.x_column}
                            tick={{ fontSize: 10 }}
                            tickFormatter={(value: string) => truncateLabel(formatCategoryLabel(value), 10)}
                        />
                        <YAxis yAxisId="left" tickFormatter={formatNumber} tick={{ fontSize: 10 }} />
                        <YAxis
                            yAxisId="right"
                            orientation="right"
                            tickFormatter={formatNumber}
                            tick={{ fontSize: 10 }}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend />
                        <Bar
                            yAxisId="left"
                            dataKey={primaryKey}
                            name={formatKeyLabel(primaryKey)}
                            fill="#3b82f6"
                            radius={[4, 4, 0, 0]}
                        />
                        <Line
                            yAxisId="right"
                            type="monotone"
                            dataKey={secondaryKey}
                            name={formatKeyLabel(secondaryKey)}
                            stroke="#10b981"
                            strokeWidth={2}
                            dot={{ fill: '#10b981', r: 3 }}
                            activeDot={{ r: 5 }}
                        />
                    </ComposedChart>
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
                        tickFormatter={(value: string) => truncateLabel(formatCategoryLabel(value), 10)}
                    />
                    <YAxis tickFormatter={formatNumber} tick={{ fontSize: 10 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar
                        dataKey={primaryKey}
                        name={formatKeyLabel(primaryKey)}
                        fill="#3b82f6"
                        radius={[4, 4, 0, 0]}
                    />
                </BarChart>
            </ResponsiveContainer>
        );
    }

    // Line Chart
    if (config.type === 'line') {
        const primaryKey = config.y_column || 'value';
        const secondaryKey = config.secondary_y_column;
        return (
            <ResponsiveContainer width="100%" height={200}>
                <LineChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis
                        dataKey={config.x_column}
                        tick={{ fontSize: 10 }}
                        tickFormatter={(value: unknown) => truncateLabel(formatCategoryLabel(value), 10)}
                        interval="preserveStartEnd"
                        minTickGap={16}
                    />
                    <YAxis yAxisId="left" tickFormatter={formatNumber} tick={{ fontSize: 10 }} />
                    {secondaryKey && (
                        <YAxis
                            yAxisId="right"
                            orientation="right"
                            tickFormatter={formatNumber}
                            tick={{ fontSize: 10 }}
                        />
                    )}
                    <Tooltip content={<CustomTooltip />} />
                    {secondaryKey && <Legend />}
                    <Line
                        yAxisId="left"
                        type="monotone"
                        dataKey={primaryKey}
                        name={formatKeyLabel(primaryKey)}
                        stroke="#3b82f6"
                        strokeWidth={2}
                        dot={{ fill: '#3b82f6', r: 3 }}
                        activeDot={{ r: 5 }}
                    />
                    {secondaryKey && (
                        <Line
                            yAxisId="right"
                            type="monotone"
                            dataKey={secondaryKey}
                            name={formatKeyLabel(secondaryKey)}
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
        const xKey = config.x_column || 'x';
        const yKey = config.y_column || 'y';
        const labelKey = inferScatterLabelKey(data, xKey, yKey);
        const scatterData: AugmentedScatterRow[] = data.map((row, idx) => ({
            ...row,
            __rank: idx + 1,
            __label: labelKey ? String(row[labelKey] ?? '') : '',
        }));

        return (
            <div className="space-y-3">
                <ResponsiveContainer width="100%" height={200}>
                    <ScatterChart margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis
                            type="number"
                            dataKey={xKey}
                            name={xKey}
                            tickFormatter={formatNumber}
                            tick={{ fontSize: 10 }}
                        />
                        <YAxis
                            type="number"
                            dataKey={yKey}
                            name={yKey}
                            tickFormatter={formatNumber}
                            tick={{ fontSize: 10 }}
                        />
                        <Tooltip
                            cursor={{ strokeDasharray: '3 3' }}
                            content={<ScatterTooltip labelKey={labelKey} xKey={xKey} yKey={yKey} />}
                        />
                        <Scatter
                            data={scatterData}
                            fill="#3b82f6"
                            shape={(props: unknown) => {
                                const dot = props as unknown as {
                                    cx?: number;
                                    cy?: number;
                                    fill?: string;
                                    payload?: Record<string, unknown>;
                                };
                                return (
                                    <NumberedScatterDot
                                        cx={dot.cx}
                                        cy={dot.cy}
                                        fill={dot.fill}
                                        payload={dot.payload}
                                    />
                                );
                            }}
                        >
                            {scatterData.map((_, index) => (
                                <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                            ))}
                        </Scatter>
                    </ScatterChart>
                </ResponsiveContainer>

                {labelKey && (
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                            <thead>
                                <tr className="border-b">
                                    <th className="text-left p-2 font-medium text-muted-foreground">#</th>
                                    <th className="text-left p-2 font-medium text-muted-foreground">
                                        {formatKeyLabel(labelKey)}
                                    </th>
                                    <th className="text-left p-2 font-medium text-muted-foreground">
                                        {formatKeyLabel(xKey)}
                                    </th>
                                    <th className="text-left p-2 font-medium text-muted-foreground">
                                        {formatKeyLabel(yKey)}
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {scatterData.map((row, idx) => (
                                    <tr key={idx} className="border-b last:border-0">
                                        <td className="p-2 text-muted-foreground">
                                            {typeof row.__rank === 'number' ? row.__rank : idx + 1}
                                        </td>
                                        <td className="p-2">
                                            {formatCategoryLabel(row.__label)}
                                        </td>
                                        <td className="p-2">
                                            {formatCellValue(row[xKey])}
                                        </td>
                                        <td className="p-2">
                                            {formatCellValue(row[yKey])}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
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
