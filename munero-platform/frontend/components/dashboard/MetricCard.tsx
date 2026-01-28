'use client';

import React from 'react';
import { ArrowUp, ArrowDown, Minus, Settings, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

/**
 * MetricCard Props Interface
 */
export interface MetricCardProps {
    label: string;
    value: string;
    trend?: number;
    trendDirection?: 'up' | 'down' | 'flat' | 'neutral';
    comparisonLabel?: string;
    onToggleComparison?: (mode: 'yoy' | 'prev_period' | 'none') => void;
    isLoading?: boolean;
}

/**
 * MetricCard Component
 * 
 * A clean card displaying a primary metric with trend indicator and comparison options.
 * 
 * Features:
 * - Large prominent value display
 * - Color-coded trend badge with icons
 * - Settings dropdown for comparison mode selection
 * - Loading state with skeleton
 * - Fully typed with TypeScript
 * 
 * @example
 * ```tsx
 * <MetricCard
 *   label="Total Revenue"
 *   value="AED 125,000"
 *   trend={12.5}
 *   trendDirection="up"
 *   comparisonLabel="vs Last Year"
 *   onToggleComparison={(mode) => setComparisonMode(mode)}
 * />
 * ```
 */
export function MetricCard({
    label,
    value,
    trend,
    trendDirection = 'neutral',
    comparisonLabel,
    onToggleComparison,
    isLoading = false,
}: MetricCardProps) {
    /**
     * Get trend badge styling based on direction
     */
    const getTrendStyles = () => {
        switch (trendDirection) {
            case 'up':
                return {
                    className: 'bg-green-50 text-green-700 border-green-200',
                    icon: ArrowUp,
                    iconClassName: 'text-green-600',
                };
            case 'down':
                return {
                    className: 'bg-red-50 text-red-700 border-red-200',
                    icon: ArrowDown,
                    iconClassName: 'text-red-600',
                };
            case 'flat':
                return {
                    className: 'bg-gray-50 text-gray-700 border-gray-200',
                    icon: Minus,
                    iconClassName: 'text-gray-600',
                };
            default:
                return {
                    className: 'bg-gray-50 text-gray-600 border-gray-200',
                    icon: Minus,
                    iconClassName: 'text-gray-500',
                };
        }
    };

    const trendStyles = getTrendStyles();
    const TrendIcon = trendStyles.icon;

    /**
     * Format trend percentage for display
     */
    const formatTrend = (trendValue: number) => {
        const sign = trendValue > 0 ? '+' : '';
        return `${sign}${trendValue.toFixed(1)}%`;
    };

    // Loading State
    if (isLoading) {
        return (
            <Card className="hover:shadow-lg transition-shadow">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <div className="h-4 w-24 bg-gray-200 rounded animate-pulse" />
                </CardHeader>
                <CardContent>
                    <div className="h-8 w-32 bg-gray-200 rounded animate-pulse mb-2" />
                    <div className="h-4 w-20 bg-gray-200 rounded animate-pulse" />
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="hover:shadow-lg transition-shadow relative">
            <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                    {label}
                </CardTitle>

                {/* Comparison Settings Dropdown */}
                {onToggleComparison && (
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0 hover:bg-muted"
                            >
                                <Settings className="h-4 w-4 text-muted-foreground" />
                                <span className="sr-only">Comparison settings</span>
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                            <DropdownMenuLabel>Comparison Mode</DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={() => onToggleComparison('yoy')}>
                                Year over Year
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => onToggleComparison('prev_period')}>
                                Prior Period
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => onToggleComparison('none')}>
                                No Comparison
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                )}
            </CardHeader>

            <CardContent>
                <div className="space-y-2">
                    {/* Primary Value */}
                    <div className="text-2xl font-bold tracking-tight">
                        {value}
                    </div>

                    {/* Trend Badge */}
                    {trend !== undefined && trend !== null && (
                        <div className="flex items-center gap-2">
                            <Badge
                                variant="outline"
                                className={cn(
                                    'px-2 py-0.5 text-xs font-medium',
                                    trendStyles.className
                                )}
                            >
                                <TrendIcon className={cn('mr-1 h-3 w-3', trendStyles.iconClassName)} />
                                {formatTrend(trend)}
                            </Badge>

                            {/* Comparison Label */}
                            {comparisonLabel && (
                                <span className="text-xs text-muted-foreground">
                                    {comparisonLabel}
                                </span>
                            )}
                        </div>
                    )}

                    {/* No Data Available */}
                    {trend === undefined && (
                        <div className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
                            <Info className="h-3 w-3" />
                            <span>Data Unavailable</span>
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
