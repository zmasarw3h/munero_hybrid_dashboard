'use client';

import { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import {
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell,
    ReferenceArea,
    ReferenceLine,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Users, Settings2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
    ScatterPoint,
    SegmentedClient,
    SegmentThresholds,
    ClientSegment,
} from '@/lib/types';
import {
    calculateDefaultThresholds,
    segmentClients,
    shouldUseLogScale,
    calculateSmartAxisMin,
    SEGMENT_CONFIG,
} from '@/lib/market-utils';

export interface ClientSegmentationMatrixProps {
    data: ScatterPoint[];
    /** Median orders from ALL clients (backend-provided for market-wide thresholds) */
    medianOrders?: number;
    /** Median revenue from ALL clients (backend-provided for market-wide thresholds) */
    medianRevenue?: number;
    onClientClick?: (clientName: string) => void;
    onSegmentClick?: (segment: ClientSegment | null) => void;
    /** Called when segmented clients change (due to threshold adjustments) */
    onSegmentedClientsChange?: (clients: SegmentedClient[]) => void;
    selectedClient?: string | null;
    selectedSegment?: ClientSegment | null;
    height?: number;
    className?: string;
}

type TooltipPayloadItem<TPayload> = {
    payload?: TPayload;
};

type BasicTooltipProps<TPayload> = {
    active?: boolean;
    payload?: ReadonlyArray<TooltipPayloadItem<TPayload>>;
};

// Custom Tooltip with segment badge
const SegmentTooltip = ({ active, payload }: BasicTooltipProps<SegmentedClient>) => {
    if (!active || !payload || !payload.length) return null;

    const client = payload[0]?.payload;
    if (!client) return null;
    const config = SEGMENT_CONFIG[client.segment];

    return (
        <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50">
            <div className="flex items-center gap-2 mb-2">
                <Users className="h-4 w-4 text-blue-500" />
                <span className="font-semibold text-sm">{client.client_name}</span>
            </div>
            <Badge
                className="mb-2 text-white"
                style={{ backgroundColor: config.color }}
            >
                {config.label}
            </Badge>
            <div className="space-y-1 text-xs">
                <div className="flex justify-between gap-4">
                    <span className="text-muted-foreground">Country:</span>
                    <span className="font-medium">{client.country}</span>
                </div>
                <div className="flex justify-between gap-4">
                    <span className="text-muted-foreground">Orders:</span>
                    <span className="font-medium">{client.total_orders.toLocaleString()}</span>
                </div>
                <div className="flex justify-between gap-4">
                    <span className="text-muted-foreground">Revenue:</span>
                    <span className="font-medium">
                        AED {client.total_revenue.toLocaleString(undefined, {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0,
                        })}
                    </span>
                </div>
                <div className="flex justify-between gap-4">
                    <span className="text-muted-foreground">AOV:</span>
                    <span className="font-medium">
                        AED {client.aov.toLocaleString(undefined, {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0,
                        })}
                    </span>
                </div>
            </div>
        </div>
    );
};

// Debounce delay in milliseconds
const DEBOUNCE_DELAY = 300;

export function ClientSegmentationMatrix({
    data,
    medianOrders,
    medianRevenue,
    onClientClick,
    onSegmentClick,
    onSegmentedClientsChange,
    selectedClient,
    selectedSegment,
    height = 350,
    className,
}: ClientSegmentationMatrixProps) {
    // Calculate default thresholds from data (use backend-provided medians for market-wide accuracy)
    const defaultThresholds = useMemo(
        () => calculateDefaultThresholds(data, medianOrders, medianRevenue),
        [data, medianOrders, medianRevenue]
    );

    // Actual thresholds used for calculations (debounced)
    const [thresholds, setThresholds] = useState<SegmentThresholds>(defaultThresholds);

    // Input values for immediate UI feedback (not debounced)
    const [inputValues, setInputValues] = useState<SegmentThresholds>(defaultThresholds);

    // Track data identity to reset thresholds only when data actually changes
    const dataRef = useRef(data);

    // Debounce timer ref
    const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

    // Reset thresholds when data changes (new data array)
    useEffect(() => {
        if (dataRef.current !== data) {
            dataRef.current = data;
            const newDefaults = calculateDefaultThresholds(data, medianOrders, medianRevenue);
            setThresholds(newDefaults);
            setInputValues(newDefaults);
        }
    }, [data, medianOrders, medianRevenue]);

    // Segment clients based on current thresholds
    const segmentedClients = useMemo(
        () => segmentClients(data, thresholds),
        [data, thresholds]
    );

    // Notify parent of segmented clients when they change
    useEffect(() => {
        onSegmentedClientsChange?.(segmentedClients);
    }, [segmentedClients, onSegmentedClientsChange]);

    // Filter by selected segment if any
    const visibleClients = useMemo(
        () =>
            selectedSegment
                ? segmentedClients.filter((c) => c.segment === selectedSegment)
                : segmentedClients,
        [segmentedClients, selectedSegment]
    );

    // Calculate axis domains and determine log scale
    const { xMin, xMax, yMin, yMax, useLogX, useLogY } = useMemo(() => {
        if (data.length === 0) return { xMin: 0, xMax: 100, yMin: 0, yMax: 100000, useLogX: false, useLogY: false };
        const orders = data.map((d) => d.total_orders);
        const revenues = data.map((d) => d.total_revenue);

        const maxOrders = Math.max(...orders);
        const maxRevenue = Math.max(...revenues);

        // Step 1: Calculate smart axis minimums (before log scale)
        const smartXMin = calculateSmartAxisMin(orders, thresholds.minOrdersForHighFrequency);
        const smartYMin = calculateSmartAxisMin(revenues, thresholds.minRevenueForHighValue);

        // Step 2: Determine if log scale is needed for each axis independently
        const useLogX = shouldUseLogScale(orders);
        const useLogY = shouldUseLogScale(revenues);

        // Step 3: Adjust for log scale (min must be > 0)
        const xMin = useLogX ? Math.max(1, smartXMin) : smartXMin;
        const yMin = useLogY ? Math.max(1, smartYMin) : smartYMin;

        return {
            xMin,
            xMax: Math.ceil(maxOrders * 1.1),
            yMin,
            yMax: Math.ceil(maxRevenue * 1.1),
            useLogX,
            useLogY,
        };
    }, [data, thresholds]);

    // Calculate clamped threshold values for rendering (constrained to visible axis range)
    const visibleThresholdX = Math.max(xMin, Math.min(xMax, thresholds.minOrdersForHighFrequency));
    const visibleThresholdY = Math.max(yMin, Math.min(yMax, thresholds.minRevenueForHighValue));

    // Check if thresholds are within visible range (for showing/hiding reference lines)
    const showXThresholdLine = thresholds.minOrdersForHighFrequency >= xMin && thresholds.minOrdersForHighFrequency <= xMax;
    const showYThresholdLine = thresholds.minRevenueForHighValue >= yMin && thresholds.minRevenueForHighValue <= yMax;

    // Count clients per segment
    const segmentCounts = useMemo(() => {
        const counts: Record<ClientSegment, number> = {
            champion: 0,
            whale: 0,
            loyalist: 0,
            developing: 0,
        };
        segmentedClients.forEach((c) => {
            counts[c.segment]++;
        });
        return counts;
    }, [segmentedClients]);

    // Debounced threshold update
    const updateThresholdsDebounced = useCallback((newValues: SegmentThresholds) => {
        // Clear existing timer
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
        }
        // Set new debounce timer
        debounceTimerRef.current = setTimeout(() => {
            setThresholds(newValues);
        }, DEBOUNCE_DELAY);
    }, []);

    // Cleanup debounce timer on unmount
    useEffect(() => {
        return () => {
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current);
            }
        };
    }, []);

    // Handle threshold input changes with debouncing
    // Uses functional update to avoid dependency on inputValues (prevents infinite loop)
    const handleThresholdChange = useCallback((field: keyof SegmentThresholds, value: string) => {
        const numValue = parseInt(value, 10);
        if (!isNaN(numValue) && numValue >= 0) {
            // Update input immediately for responsive UI using functional update
            setInputValues((prev) => {
                const newValues = { ...prev, [field]: numValue };
                // Debounce the actual threshold update
                updateThresholdsDebounced(newValues);
                return newValues;
            });
        }
    }, [updateThresholdsDebounced]);

    if (!data || data.length === 0) {
        return (
            <Card className={cn('overflow-hidden', className)} style={{ height }}>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base">Client Segmentation Matrix</CardTitle>
                </CardHeader>
                <CardContent>
                    <div
                        className="flex items-center justify-center bg-gray-50 dark:bg-gray-900 rounded-lg"
                        style={{ height: height - 80 }}
                    >
                        <div className="text-center text-muted-foreground">
                            <Users className="h-12 w-12 mx-auto mb-2 opacity-50" />
                            <p className="text-sm">No client data available</p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className={cn('overflow-hidden', className)} style={{ height }}>
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between flex-wrap gap-2">
                    <CardTitle className="text-base flex items-center gap-2">
                        Client Segmentation
                        {data.length >= 500 && (
                            <Badge variant="secondary" className="text-xs font-normal">
                                Top 500 by Revenue
                            </Badge>
                        )}
                    </CardTitle>

                    {/* Threshold Controls */}
                    <div className="flex items-center gap-3 text-sm">
                        <Settings2 className="h-4 w-4 text-muted-foreground" />
                        <div className="flex items-center gap-1.5">
                            <Label className="text-xs text-muted-foreground whitespace-nowrap">
                                Orders:
                            </Label>
                            <Input
                                type="number"
                                value={inputValues.minOrdersForHighFrequency}
                                onChange={(e) =>
                                    handleThresholdChange('minOrdersForHighFrequency', e.target.value)
                                }
                                className="w-16 h-7 text-xs px-2"
                                min={0}
                            />
                        </div>
                        <div className="flex items-center gap-1.5">
                            <Label className="text-xs text-muted-foreground whitespace-nowrap">
                                Revenue:
                            </Label>
                            <Input
                                type="number"
                                value={inputValues.minRevenueForHighValue}
                                onChange={(e) =>
                                    handleThresholdChange('minRevenueForHighValue', e.target.value)
                                }
                                className="w-20 h-7 text-xs px-2"
                                min={0}
                                step={1000}
                            />
                        </div>
                    </div>
                </div>
            </CardHeader>

            <CardContent className="pt-0">
                <ResponsiveContainer width="100%" height={height - 140}>
                    <ScatterChart margin={{ top: 10, right: 10, bottom: 45, left: 50 }}>
                        {/* Quadrant backgrounds using ReferenceArea - clamped to visible axis range */}
                        {/* Champions: Top-Right (Green) - only show if threshold is within range */}
                        {visibleThresholdY < yMax && visibleThresholdX < xMax && (
                            <ReferenceArea
                                x1={visibleThresholdX}
                                x2={xMax}
                                y1={visibleThresholdY}
                                y2={yMax}
                                fill={SEGMENT_CONFIG.champion.color}
                                fillOpacity={0.08}
                            />
                        )}
                        {/* Whales: Top-Left (Blue) */}
                        {visibleThresholdY < yMax && visibleThresholdX > xMin && (
                            <ReferenceArea
                                x1={xMin}
                                x2={visibleThresholdX}
                                y1={visibleThresholdY}
                                y2={yMax}
                                fill={SEGMENT_CONFIG.whale.color}
                                fillOpacity={0.08}
                            />
                        )}
                        {/* Loyalists: Bottom-Right (Yellow) */}
                        {visibleThresholdY > yMin && visibleThresholdX < xMax && (
                            <ReferenceArea
                                x1={visibleThresholdX}
                                x2={xMax}
                                y1={yMin}
                                y2={visibleThresholdY}
                                fill={SEGMENT_CONFIG.loyalist.color}
                                fillOpacity={0.08}
                            />
                        )}
                        {/* Developing: Bottom-Left (Gray) */}
                        {visibleThresholdY > yMin && visibleThresholdX > xMin && (
                            <ReferenceArea
                                x1={xMin}
                                x2={visibleThresholdX}
                                y1={yMin}
                                y2={visibleThresholdY}
                                fill={SEGMENT_CONFIG.developing.color}
                                fillOpacity={0.08}
                            />
                        )}

                        {/* Threshold reference lines - only show if within visible range */}
                        {showXThresholdLine && (
                            <ReferenceLine
                                x={thresholds.minOrdersForHighFrequency}
                                stroke="#94a3b8"
                                strokeDasharray="5 5"
                                strokeWidth={1}
                            />
                        )}
                        {showYThresholdLine && (
                            <ReferenceLine
                                y={thresholds.minRevenueForHighValue}
                                stroke="#94a3b8"
                                strokeDasharray="5 5"
                                strokeWidth={1}
                            />
                        )}

                        <CartesianGrid
                            strokeDasharray="3 3"
                            className="stroke-gray-200 dark:stroke-gray-700"
                        />

                        <XAxis
                            type="number"
                            dataKey="total_orders"
                            name="Orders"
                            scale={useLogX ? 'log' : 'auto'}
                            domain={[xMin, xMax]}
                            tick={{ fontSize: 11 }}
                            tickCount={6}
                            tickFormatter={(v) => v.toLocaleString()}
                            label={{
                                value: `Total Orders (Frequency)${useLogX ? ' - Log Scale' : ''}`,
                                position: 'insideBottom',
                                offset: -20,
                                style: { fontSize: 11, fill: '#6b7280' },
                            }}
                            allowDataOverflow
                        />

                        <YAxis
                            type="number"
                            dataKey="total_revenue"
                            name="Revenue"
                            scale={useLogY ? 'log' : 'auto'}
                            domain={[yMin, yMax]}
                            tick={{ fontSize: 11 }}
                            tickCount={6}
                            tickFormatter={(v) =>
                                v >= 1000000
                                    ? `${(v / 1000000).toFixed(1)}M`
                                    : v >= 1000
                                        ? `${(v / 1000).toFixed(0)}K`
                                        : v.toString()
                            }
                            label={{
                                value: `Revenue (AED)${useLogY ? ' - Log' : ''}`,
                                angle: -90,
                                position: 'insideLeft',
                                offset: 10,
                                style: { fontSize: 11, fill: '#6b7280' },
                            }}
                            allowDataOverflow
                        />

                        <Tooltip
                            content={<SegmentTooltip />}
                            cursor={{ strokeDasharray: '3 3' }}
                        />

                        <Scatter name="Clients" data={visibleClients} isAnimationActive={false}>
                            {visibleClients.map((client, index) => (
                                <Cell
                                    key={`cell-${index}`}
                                    fill={SEGMENT_CONFIG[client.segment].color}
                                    fillOpacity={0.75}
                                    stroke={
                                        client.client_name === selectedClient ? '#000' : '#fff'
                                    }
                                    strokeWidth={
                                        client.client_name === selectedClient ? 2 : 0.5
                                    }
                                    r={client.client_name === selectedClient ? 6 : 4}
                                    cursor="pointer"
                                    onClick={() => onClientClick?.(client.client_name)}
                                />
                            ))}
                        </Scatter>
                    </ScatterChart>
                </ResponsiveContainer>

                {/* Segment Legend - Clickable */}
                <div className="flex justify-center gap-3 mt-3 flex-wrap">
                    {(['champion', 'whale', 'loyalist', 'developing'] as ClientSegment[]).map(
                        (seg) => (
                            <button
                                key={seg}
                                onClick={() =>
                                    onSegmentClick?.(selectedSegment === seg ? null : seg)
                                }
                                className={cn(
                                    'flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-all bg-gray-50 dark:bg-gray-800',
                                    selectedSegment === seg
                                        ? 'ring-2 ring-offset-1 ring-blue-500'
                                        : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                                )}
                            >
                                <div
                                    className="w-2.5 h-2.5 rounded"
                                    style={{
                                        backgroundColor: SEGMENT_CONFIG[seg].color + '20',
                                        border: `1px solid ${SEGMENT_CONFIG[seg].color}`,
                                    }}
                                />
                                <span className="font-medium">{SEGMENT_CONFIG[seg].label}</span>
                                <span className="text-muted-foreground">
                                    ({segmentCounts[seg]})
                                </span>
                            </button>
                        )
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
