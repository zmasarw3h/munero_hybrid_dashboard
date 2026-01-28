'use client';

import { useMemo } from 'react';
import {
    ResponsiveContainer,
    ComposedChart,
    Bar,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ReferenceLine,
    Cell,
} from 'recharts';
import type { BarRectangleItem } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ScatterPoint, ConcentrationDataPoint } from '@/lib/types';
import { calculateConcentrationData, findClientsForRevenuePercent } from '@/lib/market-utils';

export interface RevenueConcentrationChartProps {
    data: ScatterPoint[];
    topN?: number;
    height?: number;
    className?: string;
    onClientClick?: (clientName: string) => void;
}

type TooltipPayloadItem<TPayload> = {
    payload?: TPayload;
};

type BasicTooltipProps<TPayload> = {
    active?: boolean;
    payload?: ReadonlyArray<TooltipPayloadItem<TPayload>>;
    label?: string | number;
};

// Custom Tooltip
const ConcentrationTooltip = ({ active, payload }: BasicTooltipProps<ConcentrationDataPoint>) => {
    if (!active || !payload || !payload.length) return null;

    const data = payload[0]?.payload;
    if (!data) return null;

    return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 z-50">
            <p className="font-semibold text-sm text-gray-900 dark:text-gray-100 mb-2">
                #{data.rank}: {data.clientName}
            </p>
            <div className="space-y-1 text-xs">
                <div className="flex justify-between gap-4">
                    <span className="text-muted-foreground">Revenue:</span>
                    <span className="font-medium">
                        AED {data.revenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                </div>
                <div className="flex justify-between gap-4">
                    <span className="text-muted-foreground">Cumulative:</span>
                    <span className="font-medium">
                        AED {data.cumulativeRevenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                </div>
                <div className="flex justify-between gap-4 pt-1 border-t border-gray-200 dark:border-gray-600">
                    <span className="text-muted-foreground">% of Total:</span>
                    <span className="font-semibold text-blue-600">
                        {data.cumulativePercent.toFixed(1)}%
                    </span>
                </div>
            </div>
        </div>
    );
};

// Format Y-axis labels
const formatYAxis = (value: number) => {
    if (value >= 1000000) {
        return `${(value / 1000000).toFixed(1)}M`;
    }
    if (value >= 1000) {
        return `${(value / 1000).toFixed(0)}K`;
    }
    return value.toString();
};

export function RevenueConcentrationChart({
    data,
    topN = 10,
    height = 350,
    className,
    onClientClick,
}: RevenueConcentrationChartProps) {
    // Calculate concentration data
    const concentrationData = useMemo(
        () => calculateConcentrationData(data, topN),
        [data, topN]
    );

    // Find clients for 80% revenue (Pareto insight)
    const paretoInsight = useMemo(
        () => findClientsForRevenuePercent(data, 80),
        [data]
    );

    // Calculate max revenue for Y-axis domain
    const maxRevenue = useMemo(() => {
        if (concentrationData.length === 0) return 100000;
        return Math.max(...concentrationData.map((d) => d.revenue)) * 1.1;
    }, [concentrationData]);

    if (!data || data.length === 0) {
        return (
            <Card className={cn('overflow-hidden', className)} style={{ height }}>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base">Revenue Concentration</CardTitle>
                </CardHeader>
                <CardContent>
                    <div
                        className="flex items-center justify-center bg-gray-50 dark:bg-gray-900 rounded-lg"
                        style={{ height: height - 80 }}
                    >
                        <div className="text-center text-muted-foreground">
                            <TrendingUp className="h-12 w-12 mx-auto mb-2 opacity-50" />
                            <p className="text-sm">No data available</p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className={cn('overflow-hidden', className)} style={{ height }}>
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-base">Revenue Concentration</CardTitle>
                </div>
                {/* Pareto Insight */}
                <p className="text-xs text-muted-foreground mt-1">
                    Top {paretoInsight.count}{' '}
                    {data.length >= 500 ? 'of 500 shown' : `client${paretoInsight.count !== 1 ? 's' : ''}`} ={' '}
                    <span className="font-semibold text-blue-600">
                        {paretoInsight.actualPercent.toFixed(0)}%
                    </span>{' '}
                    of {data.length >= 500 ? 'shown' : ''} revenue
                </p>
            </CardHeader>

            <CardContent className="pt-0">
                <ResponsiveContainer width="100%" height={height - 140}>
                    <ComposedChart
                        data={concentrationData}
                        margin={{ top: 10, right: 30, left: 10, bottom: 40 }}
                    >
                        <CartesianGrid
                            strokeDasharray="3 3"
                            className="stroke-gray-200 dark:stroke-gray-700"
                        />

                        <XAxis
                            dataKey="rank"
                            tick={{ fontSize: 11 }}
                            tickFormatter={(v) => `#${v}`}
                            label={{
                                value: 'Client Rank',
                                position: 'insideBottom',
                                offset: -20,
                                style: { fontSize: 11, fill: '#6b7280' },
                            }}
                        />

                        {/* Left Y-Axis: Revenue */}
                        <YAxis
                            yAxisId="left"
                            orientation="left"
                            tick={{ fontSize: 11 }}
                            tickFormatter={formatYAxis}
                            domain={[0, maxRevenue]}
                            label={{
                                value: 'Revenue',
                                angle: -90,
                                position: 'insideLeft',
                                offset: 10,
                                style: { fontSize: 11, fill: '#6b7280' },
                            }}
                        />

                        {/* Right Y-Axis: Cumulative Percentage */}
                        <YAxis
                            yAxisId="right"
                            orientation="right"
                            tick={{ fontSize: 11 }}
                            tickFormatter={(v) => `${v}%`}
                            domain={[0, 100]}
                        />

                        {/* 80% Reference Line (Pareto Principle) */}
                        <ReferenceLine
                            yAxisId="right"
                            y={80}
                            stroke="#ef4444"
                            strokeDasharray="5 5"
                            strokeWidth={1}
                            label={{
                                value: '80%',
                                position: 'right',
                                fill: '#ef4444',
                                fontSize: 10,
                            }}
                        />

                        <Tooltip content={<ConcentrationTooltip />} />

                        {/* Revenue Bars */}
                        <Bar
                            yAxisId="left"
                            dataKey="revenue"
                            name="Revenue"
                            fill="#3b82f6"
                            radius={[4, 4, 0, 0]}
                            cursor="pointer"
                            onClick={(bar: BarRectangleItem) => {
                                const point = bar.payload as ConcentrationDataPoint | undefined;
                                if (point?.clientName) onClientClick?.(point.clientName);
                            }}
                        >
                            {concentrationData.map((entry, index) => (
                                <Cell
                                    key={`cell-${index}`}
                                    fill={entry.cumulativePercent <= 80 ? '#3b82f6' : '#93c5fd'}
                                />
                            ))}
                        </Bar>

                        {/* Cumulative Percentage Line */}
                        <Line
                            yAxisId="right"
                            type="monotone"
                            dataKey="cumulativePercent"
                            name="Cumulative %"
                            stroke="#f97316"
                            strokeWidth={2}
                            dot={{ fill: '#f97316', strokeWidth: 0, r: 4 }}
                            activeDot={{ r: 6, stroke: '#f97316', strokeWidth: 2, fill: '#fff' }}
                        />
                    </ComposedChart>
                </ResponsiveContainer>

                {/* Legend */}
                <div className="flex justify-center gap-6 mt-1 text-xs">
                    <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded bg-blue-500" />
                        <span className="text-muted-foreground">Client Revenue</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <div className="w-3 h-3 rounded-full bg-orange-500" />
                        <span className="text-muted-foreground">Cumulative %</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <div className="w-4 h-0.5 bg-red-500" style={{ borderTop: '2px dashed' }} />
                        <span className="text-muted-foreground">80% Threshold</span>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
