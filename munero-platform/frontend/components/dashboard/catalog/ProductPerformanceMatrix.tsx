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
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Package, Loader2, Info, Settings2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { shouldUseLogScale, calculateSmartAxisMin } from '@/lib/market-utils';

// Types
export interface ProductScatterPoint {
    product_name: string;
    product_type: 'gift_card' | 'merchandise';
    quantity: number;
    revenue: number;
    margin: number | null;
    quadrant: 'cash_cow' | 'premium_niche' | 'penny_stock' | 'dead_stock';
}

export interface ProductPerformanceMatrixProps {
    data: ProductScatterPoint[];
    loading?: boolean;
    totalProducts?: number;
    medianRevenue?: number;
    medianQuantity?: number;
    onProductClick?: (product: ProductScatterPoint) => void;
    onQuadrantCountsChange?: (counts: Record<Quadrant, number>) => void;
    height?: number;
    className?: string;
}

// Quadrant configuration
export const QUADRANT_CONFIG = {
    cash_cow: {
        name: 'Cash Cows',
        color: 'rgba(34, 197, 94, 0.1)',
        borderColor: '#22c55e',
        label: 'High Revenue, High Volume',
    },
    premium_niche: {
        name: 'Premium Niche',
        color: 'rgba(99, 102, 241, 0.1)',
        borderColor: '#6366f1',
        label: 'High Revenue, Low Volume',
    },
    penny_stock: {
        name: 'Penny Stocks',
        color: 'rgba(251, 191, 36, 0.1)',
        borderColor: '#fbbf24',
        label: 'Low Revenue, High Volume',
    },
    dead_stock: {
        name: 'Dead Stock',
        color: 'rgba(239, 68, 68, 0.1)',
        borderColor: '#ef4444',
        label: 'Low Revenue, Low Volume',
    },
};

// Product type colors
const PRODUCT_TYPE_COLORS = {
    gift_card: '#3b82f6', // Blue
    merchandise: '#8b5cf6', // Purple
};

// Threshold type for quadrant division
interface ProductThresholds {
    minQuantity: number;
    minRevenue: number;
}

type TooltipPayloadItem<TPayload> = {
    payload?: TPayload;
};

type BasicTooltipProps<TPayload> = {
    active?: boolean;
    payload?: ReadonlyArray<TooltipPayloadItem<TPayload>>;
};

// Debounce delay in milliseconds
const DEBOUNCE_DELAY = 300;

// Format currency
const formatCurrency = (value: number): string => {
    if (value >= 1000000) {
        return `AED ${(value / 1000000).toFixed(1)}M`;
    }
    if (value >= 1000) {
        return `AED ${(value / 1000).toFixed(0)}K`;
    }
    return `AED ${value.toLocaleString()}`;
};

// Classify product into quadrant based on thresholds
export type Quadrant = 'cash_cow' | 'premium_niche' | 'penny_stock' | 'dead_stock';

const classifyProduct = (
    quantity: number,
    revenue: number,
    thresholds: ProductThresholds
): Quadrant => {
    const isHighRevenue = revenue >= thresholds.minRevenue;
    const isHighQuantity = quantity >= thresholds.minQuantity;

    if (isHighRevenue && isHighQuantity) return 'cash_cow';
    if (isHighRevenue && !isHighQuantity) return 'premium_niche';
    if (!isHighRevenue && isHighQuantity) return 'penny_stock';
    return 'dead_stock';
};

// Custom Tooltip - accepts thresholds for dynamic quadrant calculation
type ProductTooltipProps = BasicTooltipProps<ProductScatterPoint> & {
    thresholds?: ProductThresholds;
};

const ProductTooltip = ({ active, payload, thresholds }: ProductTooltipProps) => {
    if (!active || !payload || !payload.length) return null;

    const product = payload[0]?.payload;
    if (!product) return null;

    // Calculate quadrant dynamically based on current thresholds
    const dynamicQuadrant = thresholds
        ? classifyProduct(product.quantity, product.revenue, thresholds)
        : product.quadrant;

    return (
        <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50 max-w-xs">
            <div className="flex items-center gap-2 mb-2">
                <Package className="h-4 w-4 text-blue-500" />
                <span className="font-semibold text-sm truncate">{product.product_name}</span>
            </div>
            <div className="space-y-1 text-xs">
                <div className="flex justify-between gap-4">
                    <span className="text-muted-foreground">Revenue:</span>
                    <span className="font-medium">{formatCurrency(product.revenue)}</span>
                </div>
                <div className="flex justify-between gap-4">
                    <span className="text-muted-foreground">Quantity:</span>
                    <span className="font-medium">{product.quantity.toLocaleString()}</span>
                </div>
                {product.margin !== null && (
                    <div className="flex justify-between gap-4">
                        <span className="text-muted-foreground">Margin:</span>
                        <span className="font-medium">{product.margin.toFixed(1)}%</span>
                    </div>
                )}
                <div className="flex justify-between gap-4">
                    <span className="text-muted-foreground">Quadrant:</span>
                    <span className="font-medium">{QUADRANT_CONFIG[dynamicQuadrant].name}</span>
                </div>
            </div>
            <Badge
                className="mt-2 text-white text-xs"
                style={{
                    backgroundColor: PRODUCT_TYPE_COLORS[product.product_type],
                }}
            >
                {product.product_type === 'gift_card' ? 'Gift Card' : 'Merchandise'}
            </Badge>
        </div>
    );
};

export function ProductPerformanceMatrix({
    data,
    loading = false,
    totalProducts,
    medianRevenue: propMedianRevenue,
    medianQuantity: propMedianQuantity,
    onProductClick,
    onQuadrantCountsChange,
    height = 500,
    className,
}: ProductPerformanceMatrixProps) {
    // Calculate default thresholds from data
    const defaultThresholds = useMemo((): ProductThresholds => {
        if (!data || data.length === 0) {
            return { minQuantity: 50, minRevenue: 50000 };
        }
        const quantities = [...data.map((d) => d.quantity)].sort((a, b) => a - b);
        const revenues = [...data.map((d) => d.revenue)].sort((a, b) => a - b);

        const calcMedianRevenue =
            propMedianRevenue ?? revenues[Math.floor(revenues.length / 2)];
        const calcMedianQuantity =
            propMedianQuantity ?? quantities[Math.floor(quantities.length / 2)];

        return {
            minQuantity: Math.round(calcMedianQuantity),
            minRevenue: Math.round(calcMedianRevenue),
        };
    }, [data, propMedianRevenue, propMedianQuantity]);

    // Actual thresholds used for calculations (debounced)
    const [thresholds, setThresholds] = useState<ProductThresholds>(defaultThresholds);

    // Input values for immediate UI feedback (not debounced)
    const [inputValues, setInputValues] = useState<ProductThresholds>(defaultThresholds);

    // Track data identity to reset thresholds only when data actually changes
    const dataRef = useRef(data);

    // Debounce timer ref
    const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

    // Reset thresholds when data changes (new data array)
    useEffect(() => {
        if (dataRef.current !== data) {
            dataRef.current = data;
            setThresholds(defaultThresholds);
            setInputValues(defaultThresholds);
        }
    }, [data, defaultThresholds]);

    // Debounced threshold update
    const updateThresholdsDebounced = useCallback((newValues: ProductThresholds) => {
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
        }
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
    const handleThresholdChange = useCallback(
        (field: keyof ProductThresholds, value: string) => {
            const numValue = parseInt(value, 10);
            if (!isNaN(numValue) && numValue >= 0) {
                setInputValues((prev) => {
                    const newValues = { ...prev, [field]: numValue };
                    updateThresholdsDebounced(newValues);
                    return newValues;
                });
            }
        },
        [updateThresholdsDebounced]
    );

    // Calculate domains, log scale detection, and dynamic quadrant counts
    const { xMin, xMax, yMin, yMax, useLogX, useLogY, quadrantCounts } = useMemo(() => {
        if (!data || data.length === 0) {
            return {
                xMin: 0,
                xMax: 100,
                yMin: 0,
                yMax: 100000,
                useLogX: false,
                useLogY: false,
                quadrantCounts: { cash_cow: 0, premium_niche: 0, penny_stock: 0, dead_stock: 0 },
            };
        }

        const quantities = data.map((d) => d.quantity);
        const revenues = data.map((d) => d.revenue);

        const maxQuantity = Math.max(...quantities);
        const maxRevenue = Math.max(...revenues);

        // Step 1: Calculate smart axis minimums (before log scale)
        const smartXMin = calculateSmartAxisMin(quantities, thresholds.minQuantity);
        const smartYMin = calculateSmartAxisMin(revenues, thresholds.minRevenue);

        // Step 2: Determine if log scale is needed for each axis independently
        const useLogX = shouldUseLogScale(quantities);
        const useLogY = shouldUseLogScale(revenues);

        // Step 3: Adjust for log scale (min must be > 0)
        const xMin = useLogX ? Math.max(1, smartXMin) : smartXMin;
        const yMin = useLogY ? Math.max(1, smartYMin) : smartYMin;

        // Count products per quadrant based on current thresholds
        const counts = {
            cash_cow: 0,
            premium_niche: 0,
            penny_stock: 0,
            dead_stock: 0,
        };
        data.forEach((d) => {
            const quadrant = classifyProduct(d.quantity, d.revenue, thresholds);
            counts[quadrant]++;
        });

        return {
            xMin,
            xMax: Math.ceil(maxQuantity * 1.1),
            yMin,
            yMax: Math.ceil(maxRevenue * 1.1),
            useLogX,
            useLogY,
            quadrantCounts: counts,
        };
    }, [data, thresholds]);

    // Notify parent component of quadrant counts change
    useEffect(() => {
        if (onQuadrantCountsChange) {
            onQuadrantCountsChange(quadrantCounts);
        }
    }, [quadrantCounts, onQuadrantCountsChange]);

    // Calculate clamped threshold values for rendering (constrained to visible axis range)
    const visibleThresholdX = Math.max(xMin, Math.min(xMax, thresholds.minQuantity));
    const visibleThresholdY = Math.max(yMin, Math.min(yMax, thresholds.minRevenue));

    // Check if thresholds are within visible range (for showing/hiding reference lines)
    const showXThresholdLine = thresholds.minQuantity >= xMin && thresholds.minQuantity <= xMax;
    const showYThresholdLine = thresholds.minRevenue >= yMin && thresholds.minRevenue <= yMax;

    // Loading state
    if (loading) {
        return (
            <Card className={cn('overflow-hidden', className)}>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base">Product Performance Matrix</CardTitle>
                </CardHeader>
                <CardContent>
                    <div
                        className="flex items-center justify-center bg-gray-50 dark:bg-gray-900 rounded-lg"
                        style={{ height: height - 80 }}
                    >
                        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                        <span className="ml-2 text-gray-500">Loading products...</span>
                    </div>
                </CardContent>
            </Card>
        );
    }

    // Empty state
    if (!data || data.length === 0) {
        return (
            <Card className={cn('overflow-hidden', className)}>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base">Product Performance Matrix</CardTitle>
                </CardHeader>
                <CardContent>
                    <div
                        className="flex items-center justify-center bg-gray-50 dark:bg-gray-900 rounded-lg"
                        style={{ height: height - 80 }}
                    >
                        <div className="text-center text-muted-foreground">
                            <Package className="h-12 w-12 mx-auto mb-2 opacity-50" />
                            <p className="text-sm">No product data available</p>
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
                        Product Performance Matrix
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
                                Quantity:
                            </Label>
                            <Input
                                type="number"
                                value={inputValues.minQuantity}
                                onChange={(e) =>
                                    handleThresholdChange('minQuantity', e.target.value)
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
                                value={inputValues.minRevenue}
                                onChange={(e) =>
                                    handleThresholdChange('minRevenue', e.target.value)
                                }
                                className="w-20 h-7 text-xs px-2"
                                min={0}
                                step={1000}
                            />
                        </div>
                    </div>
                </div>
            </CardHeader>

            <CardContent className="pt-0 flex flex-col" style={{ height: height - 70 }}>
                <div className="flex-1 min-h-0">
                    <ResponsiveContainer width="100%" height="100%">
                        <ScatterChart margin={{ top: 10, right: 10, bottom: 45, left: 60 }}>
                            {/* Quadrant backgrounds using ReferenceArea - clamped to visible axis range */}
                            {/* Cash Cows: Top-Right (Green) - High Revenue, High Quantity */}
                            {visibleThresholdY < yMax && visibleThresholdX < xMax && (
                                <ReferenceArea
                                    x1={visibleThresholdX}
                                    x2={xMax}
                                    y1={visibleThresholdY}
                                    y2={yMax}
                                    fill={QUADRANT_CONFIG.cash_cow.color}
                                    fillOpacity={1}
                                />
                            )}
                            {/* Premium Niche: Top-Left (Indigo) - High Revenue, Low Quantity */}
                            {visibleThresholdY < yMax && visibleThresholdX > xMin && (
                                <ReferenceArea
                                    x1={xMin}
                                    x2={visibleThresholdX}
                                    y1={visibleThresholdY}
                                    y2={yMax}
                                    fill={QUADRANT_CONFIG.premium_niche.color}
                                    fillOpacity={1}
                                />
                            )}
                            {/* Penny Stocks: Bottom-Right (Yellow) - Low Revenue, High Quantity */}
                            {visibleThresholdY > yMin && visibleThresholdX < xMax && (
                                <ReferenceArea
                                    x1={visibleThresholdX}
                                    x2={xMax}
                                    y1={yMin}
                                    y2={visibleThresholdY}
                                    fill={QUADRANT_CONFIG.penny_stock.color}
                                    fillOpacity={1}
                                />
                            )}
                            {/* Dead Stock: Bottom-Left (Red) - Low Revenue, Low Quantity */}
                            {visibleThresholdY > yMin && visibleThresholdX > xMin && (
                                <ReferenceArea
                                    x1={xMin}
                                    x2={visibleThresholdX}
                                    y1={yMin}
                                    y2={visibleThresholdY}
                                    fill={QUADRANT_CONFIG.dead_stock.color}
                                    fillOpacity={1}
                                />
                            )}

                            {/* Threshold reference lines - only show if within visible range */}
                            {showXThresholdLine && (
                                <ReferenceLine
                                    x={thresholds.minQuantity}
                                    stroke="#94a3b8"
                                    strokeDasharray="5 5"
                                    strokeWidth={1}
                                />
                            )}
                            {showYThresholdLine && (
                                <ReferenceLine
                                    y={thresholds.minRevenue}
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
                                dataKey="quantity"
                                name="Quantity"
                                scale={useLogX ? 'log' : 'auto'}
                                domain={[xMin, xMax]}
                                tick={{ fontSize: 11 }}
                                tickCount={6}
                                tickFormatter={(v) => v.toLocaleString()}
                                label={{
                                    value: `Quantity Sold${useLogX ? ' - Log Scale' : ''}`,
                                    position: 'insideBottom',
                                    offset: -20,
                                    style: { fontSize: 11, fill: '#6b7280' },
                                }}
                                allowDataOverflow
                            />

                            <YAxis
                                type="number"
                                dataKey="revenue"
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
                                content={<ProductTooltip thresholds={thresholds} />}
                                cursor={{ strokeDasharray: '3 3' }}
                            />

                            <Scatter
                                name="Products"
                                data={data}
                                isAnimationActive={false}
                            >
                                {data.map((product, index) => (
                                    <Cell
                                        key={`cell-${index}`}
                                        fill={PRODUCT_TYPE_COLORS[product.product_type]}
                                        fillOpacity={0.75}
                                        stroke="#fff"
                                        strokeWidth={0.5}
                                        r={4}
                                        cursor={onProductClick ? 'pointer' : 'default'}
                                        onClick={() => onProductClick?.(product)}
                                    />
                                ))}
                            </Scatter>
                        </ScatterChart>
                    </ResponsiveContainer>
                </div>

                {/* Legend - Product Types */}
                <div className="flex items-center justify-center gap-6 mt-2 text-sm">
                    <div className="flex items-center gap-2">
                        <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: PRODUCT_TYPE_COLORS.gift_card }}
                        />
                        <span>Gift Card</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: PRODUCT_TYPE_COLORS.merchandise }}
                        />
                        <span>Merchandise</span>
                    </div>
                </div>

                {/* Quadrant Legend with Counts */}
                <div className="flex justify-center gap-3 mt-3 flex-wrap">
                    {(
                        ['cash_cow', 'premium_niche', 'penny_stock', 'dead_stock'] as const
                    ).map((quadrant) => (
                        <div
                            key={quadrant}
                            className="flex items-center gap-1.5 px-2 py-1 rounded text-xs bg-gray-50 dark:bg-gray-800"
                        >
                            <div
                                className="w-2.5 h-2.5 rounded"
                                style={{
                                    backgroundColor: QUADRANT_CONFIG[quadrant].color,
                                    border: `1px solid ${QUADRANT_CONFIG[quadrant].borderColor}`,
                                }}
                            />
                            <span className="font-medium">
                                {QUADRANT_CONFIG[quadrant].name}
                            </span>
                            <span className="text-muted-foreground">
                                ({quadrantCounts[quadrant]})
                            </span>
                        </div>
                    ))}
                </div>

                {/* Data Limit Notice */}
                {data.length >= 500 && totalProducts && totalProducts > 500 && (
                    <Alert className="mt-3">
                        <Info className="h-4 w-4" />
                        <AlertDescription>
                            Showing top 500 of {totalProducts.toLocaleString()} products by
                            revenue (performance optimized)
                        </AlertDescription>
                    </Alert>
                )}
            </CardContent>
        </Card>
    );
}

export default ProductPerformanceMatrix;
