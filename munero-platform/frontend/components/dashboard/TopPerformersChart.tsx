'use client';

/**
 * TopPerformersChart - Stacked horizontal bar chart with Products/Brands toggle
 * 
 * Zone 4B component that shows:
 * - Products view: Revenue breakdown by order status (completed vs failed/stuck)
 * - Brands view: Revenue breakdown by product type (gift card vs merchandise)
 */

import { useState, useEffect } from 'react';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
    Cell,
    Legend,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api-client';
import { useFilters, transformFiltersForAPI } from '@/components/dashboard/FilterContext';
import { ProductByStatus, BrandByType } from '@/lib/types';
import { cn } from '@/lib/utils';

type ViewMode = 'products' | 'brands';

interface TopPerformersChartProps {
    /** Number of items to display */
    limit?: number;
    /** Chart height in pixels */
    height?: number;
    /** Optional className */
    className?: string;
}

// Colors for stacked bars
const COLORS = {
    // Products view (by status)
    completed: '#22c55e',      // Green
    failed: '#ef4444',         // Red
    stuck: '#f59e0b',          // Amber

    // Brands view (by type)
    gift_card: '#3b82f6',      // Blue
    merchandise: '#8b5cf6',    // Purple
};

function formatRevenue(value: number): string {
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(0)}K`;
    return value.toFixed(0);
}

function truncateLabel(label: string, maxLength: number = 15): string {
    if (label.length <= maxLength) return label;
    return label.substring(0, maxLength - 1) + '…';
}

export function TopPerformersChart({
    limit = 8,
    height = 320,
    className,
}: TopPerformersChartProps) {
    const { filters } = useFilters();
    const [viewMode, setViewMode] = useState<ViewMode>('products');
    const [productsData, setProductsData] = useState<ProductByStatus[]>([]);
    const [brandsData, setBrandsData] = useState<BrandByType[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isMock, setIsMock] = useState(false);

    // Fetch data based on view mode
    useEffect(() => {
        async function fetchData() {
            setIsLoading(true);
            try {
                const apiFilters = transformFiltersForAPI(filters);
                if (viewMode === 'products') {
                    const response = await apiClient.getTopProductsByStatus(apiFilters, limit);
                    setProductsData(response.data);
                    setIsMock(response.is_mock);
                } else {
                    const response = await apiClient.getTopBrandsByType(apiFilters, limit);
                    setBrandsData(response.data);
                    setIsMock(false);
                }
            } catch (error) {
                console.error(`Failed to fetch ${viewMode} data:`, error);
                if (viewMode === 'products') {
                    setProductsData([]);
                } else {
                    setBrandsData([]);
                }
            } finally {
                setIsLoading(false);
            }
        }
        fetchData();
    }, [viewMode, filters, limit]);

    // Transform data for chart
    const chartData = viewMode === 'products'
        ? productsData.map((item) => ({
            name: truncateLabel(item.product_name),
            fullName: item.product_name,
            completed: item.completed_revenue,
            failed: item.failed_revenue + item.stuck_revenue,
            total: item.total_revenue,
        }))
        : brandsData.map((item) => ({
            name: truncateLabel(item.brand_name),
            fullName: item.brand_name,
            gift_card: item.gift_card_revenue,
            merchandise: item.merchandise_revenue,
            total: item.total_revenue,
        }));

    // Custom tooltip
    const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload: Record<string, number | string> }> }) => {
        if (!active || !payload || !payload.length) return null;

        const data = payload[0].payload;
        const total = Number(data.total) || 0;

        if (viewMode === 'products') {
            const completed = Number(data.completed) || 0;
            const failed = Number(data.failed) || 0;
            return (
                <div className="bg-background border rounded-lg shadow-lg p-3 text-sm">
                    <p className="font-medium mb-2">{data.fullName}</p>
                    <div className="space-y-1">
                        <p>Total: <span className="font-medium">{formatRevenue(total)}</span></p>
                        <p className="text-green-600">
                            ✓ Completed: {formatRevenue(completed)} ({((completed / total) * 100).toFixed(0)}%)
                        </p>
                        <p className="text-red-600">
                            ⚠ Failed/Stuck: {formatRevenue(failed)} ({((failed / total) * 100).toFixed(0)}%)
                        </p>
                    </div>
                </div>
            );
        } else {
            const giftCard = Number(data.gift_card) || 0;
            const merchandise = Number(data.merchandise) || 0;
            return (
                <div className="bg-background border rounded-lg shadow-lg p-3 text-sm">
                    <p className="font-medium mb-2">{data.fullName}</p>
                    <div className="space-y-1">
                        <p>Total: <span className="font-medium">{formatRevenue(total)}</span></p>
                        <p className="text-blue-600">
                            Gift Card: {formatRevenue(giftCard)} ({((giftCard / total) * 100).toFixed(0)}%)
                        </p>
                        <p className="text-purple-600">
                            Merchandise: {formatRevenue(merchandise)} ({((merchandise / total) * 100).toFixed(0)}%)
                        </p>
                    </div>
                </div>
            );
        }
    };

    if (isLoading) {
        return (
            <Card className={className}>
                <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-base">Top Performers</CardTitle>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="animate-pulse space-y-3" style={{ height }}>
                        {[...Array(6)].map((_, i) => (
                            <div key={i} className="h-8 bg-muted rounded" />
                        ))}
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className={className} style={{ height: height + 90 }}>
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <CardTitle className="text-base">Top Performers</CardTitle>
                        {isMock && (
                            <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                                Demo
                            </Badge>
                        )}
                    </div>

                    {/* Toggle Buttons */}
                    <div className="flex items-center gap-1 bg-muted rounded-md p-0.5">
                        <Button
                            variant={viewMode === 'products' ? 'secondary' : 'ghost'}
                            size="sm"
                            className="h-7 text-xs px-3"
                            onClick={() => setViewMode('products')}
                        >
                            Products
                        </Button>
                        <Button
                            variant={viewMode === 'brands' ? 'secondary' : 'ghost'}
                            size="sm"
                            className="h-7 text-xs px-3"
                            onClick={() => setViewMode('brands')}
                        >
                            Brands
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="pt-0">
                {chartData.length === 0 ? (
                    <div className="flex items-center justify-center text-muted-foreground" style={{ height }}>
                        No data available
                    </div>
                ) : (
                    <>
                        <ResponsiveContainer width="100%" height={height - 50}>
                            <BarChart
                                data={chartData}
                                layout="vertical"
                                margin={{ top: 0, right: 10, left: 0, bottom: 0 }}
                            >
                                <XAxis
                                    type="number"
                                    tickFormatter={formatRevenue}
                                    fontSize={11}
                                    axisLine={false}
                                    tickLine={false}
                                />
                                <YAxis
                                    type="category"
                                    dataKey="name"
                                    width={100}
                                    fontSize={11}
                                    axisLine={false}
                                    tickLine={false}
                                />
                                <Tooltip content={<CustomTooltip />} />

                                {viewMode === 'products' ? (
                                    <>
                                        <Bar dataKey="completed" stackId="a" fill={COLORS.completed} radius={[0, 0, 0, 0]} />
                                        <Bar dataKey="failed" stackId="a" fill={COLORS.failed} radius={[0, 4, 4, 0]} />
                                    </>
                                ) : (
                                    <>
                                        <Bar dataKey="gift_card" stackId="a" fill={COLORS.gift_card} radius={[0, 0, 0, 0]} />
                                        <Bar dataKey="merchandise" stackId="a" fill={COLORS.merchandise} radius={[0, 4, 4, 0]} />
                                    </>
                                )}
                            </BarChart>
                        </ResponsiveContainer>

                        {/* Legend */}
                        <div className="flex items-center justify-center gap-6 mt-3 text-sm">
                            {viewMode === 'products' ? (
                                <>
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS.completed }} />
                                        <span className="text-foreground font-medium">Completed</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS.failed }} />
                                        <span className="text-foreground font-medium">Failed/Stuck</span>
                                    </div>
                                </>
                            ) : (
                                <>
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS.gift_card }} />
                                        <span className="text-foreground font-medium">Gift Card</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS.merchandise }} />
                                        <span className="text-foreground font-medium">Merchandise</span>
                                    </div>
                                </>
                            )}
                        </div>
                    </>
                )}
            </CardContent>
        </Card>
    );
}

export default TopPerformersChart;
