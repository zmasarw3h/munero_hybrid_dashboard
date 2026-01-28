'use client';

import {
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell,
} from 'recharts';
import type { ScatterPointItem } from 'recharts/types/cartesian/Scatter';
import { Users } from 'lucide-react';

export interface ClientData {
    client_id: string;
    client_name: string;
    client_country: string;
    total_orders: number;
    total_revenue: number;
    [key: string]: unknown;
}

export interface ClientScatterProps {
    data: ClientData[];
    onClientClick?: (clientId: string) => void;
    title?: string;
    highlightedClient?: string;
}

type TooltipPayloadItem<TPayload> = {
    payload?: TPayload;
};

type BasicTooltipProps<TPayload> = {
    active?: boolean;
    payload?: ReadonlyArray<TooltipPayloadItem<TPayload>>;
};

// Custom Tooltip
const CustomTooltip = ({ active, payload }: BasicTooltipProps<ClientData>) => {
    if (!active || !payload || !payload.length) return null;

    const data = payload[0]?.payload;
    if (!data) return null;

    return (
        <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-2 mb-2">
                <Users className="h-4 w-4 text-blue-500" />
                <p className="font-semibold text-sm">{data.client_name}</p>
            </div>

            <div className="space-y-1 text-xs">
                <div className="flex justify-between gap-4">
                    <span className="text-muted-foreground">Country:</span>
                    <span className="font-medium">{data.client_country}</span>
                </div>
                <div className="flex justify-between gap-4">
                    <span className="text-muted-foreground">Total Orders:</span>
                    <span className="font-medium">{data.total_orders.toLocaleString()}</span>
                </div>
                <div className="flex justify-between gap-4">
                    <span className="text-muted-foreground">Total Revenue:</span>
                    <span className="font-medium">
                        AED {typeof data.total_revenue === 'number' ? data.total_revenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : data.total_revenue}
                    </span>
                </div>
            </div>
        </div>
    );
};

type ClientScatterShapeProps = Omit<ScatterPointItem, 'payload'> & {
    payload: ClientData;
    fill?: string;
};

type CustomDotProps = ClientScatterShapeProps & {
    onClientClick?: (clientId: string) => void;
    isHighlighted?: boolean;
};

// Custom Dot Component for click handling
const CustomDot = (props: CustomDotProps) => {
    const { cx, cy, payload, fill, onClientClick, isHighlighted } = props;

    return (
        <circle
            cx={cx}
            cy={cy}
            r={isHighlighted ? 8 : 6}
            fill={fill}
            stroke={isHighlighted ? '#3b82f6' : '#fff'}
            strokeWidth={isHighlighted ? 3 : 1.5}
            className="cursor-pointer transition-all hover:r-8"
            onClick={() => onClientClick?.(payload.client_id)}
            style={{ transition: 'all 0.2s' }}
        />
    );
};

export function ClientScatter({
    data,
    onClientClick,
    title = 'Client Analysis: Orders vs Revenue',
    highlightedClient,
}: ClientScatterProps) {
    if (!data || data.length === 0) {
        return (
            <div className="w-full h-[400px] flex items-center justify-center bg-gray-50 dark:bg-gray-900 rounded-lg">
                <div className="text-center text-muted-foreground">
                    <Users className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No client data available</p>
                </div>
            </div>
        );
    }

    return (
        <div className="w-full">
            {title && (
                <div className="mb-4">
                    <h3 className="text-lg font-semibold">{title}</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                        {data.length} client{data.length === 1 ? '' : 's'} • Click on any point for details
                    </p>
                </div>
            )}

            <ResponsiveContainer width="100%" height={400}>
                <ScatterChart margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200 dark:stroke-gray-700" />

                    <XAxis
                        type="number"
                        dataKey="total_orders"
                        name="Total Orders"
                        tick={{ fontSize: 12 }}
                        className="text-muted-foreground"
                        label={{ value: 'Total Orders', position: 'insideBottom', offset: -10, style: { fontSize: 12 } }}
                    />

                    <YAxis
                        type="number"
                        dataKey="total_revenue"
                        name="Total Revenue"
                        tick={{ fontSize: 12 }}
                        className="text-muted-foreground"
                        label={{ value: 'Total Revenue (AED)', angle: -90, position: 'insideLeft', style: { fontSize: 12 } }}
                        tickFormatter={(value) => value.toLocaleString()}
                    />

                    <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />

                    <Scatter
                        name="Clients"
                        data={data}
                        fill="#3b82f6"
                        shape={(props: ScatterPointItem) => {
                            const point = props as ClientScatterShapeProps;
                            return (
                                <CustomDot
                                    {...point}
                                    onClientClick={onClientClick}
                                    isHighlighted={point.payload.client_id === highlightedClient}
                                />
                            );
                        }}
                    >
                        {data.map((entry, index) => (
                            <Cell
                                key={`cell-${index}`}
                                fill={entry.client_id === highlightedClient ? '#3b82f6' : '#60a5fa'}
                            />
                        ))}
                    </Scatter>
                </ScatterChart>
            </ResponsiveContainer>

            {/* Legend */}
            <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-blue-500" />
                    <span>Client Position</span>
                </div>
                {highlightedClient && (
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-blue-600 border-2 border-blue-400" />
                        <span>Selected Client</span>
                    </div>
                )}
            </div>
        </div>
    );
}
