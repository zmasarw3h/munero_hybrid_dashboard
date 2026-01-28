'use client';

/**
 * EnhancedKPICard - KPI card with optional sparkline, secondary info, and actions
 * 
 * An enhanced version of MetricCard that supports:
 * - Sparkline visualization
 * - Secondary text (e.g., "Top: Acme Corp")
 * - Action button (e.g., "[View →]")
 * - Trend percentage with color coding
 */

import { Card, CardContent } from '@/components/ui/card';
import { TrendDirection } from '@/lib/types';
import { cn } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus, AlertTriangle, ChevronRight } from 'lucide-react';
import { MiniSparkline } from './MiniSparkline';

interface EnhancedKPICardProps {
    /** Card label/title */
    label: string;
    /** Primary value to display */
    value: string;
    /** Trend percentage (e.g., 12.5 for +12.5%) */
    trendPct?: number;
    /** Direction of trend for color coding */
    trendDirection?: TrendDirection;
    /** Sparkline data (array of values) */
    sparklineData?: number[];
    /** Type of sparkline chart */
    sparklineType?: 'area' | 'line';
    /** Sparkline color */
    sparklineColor?: string;
    /** Secondary text below the value */
    secondaryText?: string;
    /** Action button text */
    actionText?: string;
    /** Action button click handler */
    onAction?: () => void;
    /** Whether this is an alert/warning card (red styling) */
    isAlert?: boolean;
    /** Custom icon to display */
    icon?: React.ReactNode;
    /** Optional className for styling */
    className?: string;
    /** Loading state */
    isLoading?: boolean;
}

export function EnhancedKPICard({
    label,
    value,
    trendPct,
    trendDirection = 'neutral',
    sparklineData,
    sparklineType = 'area',
    sparklineColor,
    secondaryText,
    actionText,
    onAction,
    isAlert = false,
    icon,
    className,
    isLoading = false,
}: EnhancedKPICardProps) {
    // Determine trend icon and color
    const getTrendDisplay = () => {
        if (trendPct === undefined || trendPct === null) return null;

        const absValue = Math.abs(trendPct);
        const formattedPct = `${trendPct >= 0 ? '+' : ''}${absValue.toFixed(1)}%`;

        let IconComponent = Minus;
        let colorClass = 'text-muted-foreground';

        if (trendDirection === 'up') {
            IconComponent = TrendingUp;
            colorClass = 'text-green-600';
        } else if (trendDirection === 'down') {
            IconComponent = TrendingDown;
            colorClass = 'text-red-600';
        }

        return (
            <div className={cn('flex items-center gap-1 text-xs font-medium', colorClass)}>
                <IconComponent className="h-3 w-3" />
                <span>{formattedPct}</span>
            </div>
        );
    };

    // Determine sparkline color based on card type
    const getSparklineColor = () => {
        if (sparklineColor) return sparklineColor;
        if (isAlert) return '#ef4444'; // Red for alerts
        if (trendDirection === 'up') return '#22c55e'; // Green
        if (trendDirection === 'down') return '#ef4444'; // Red
        return '#3b82f6'; // Default blue
    };

    if (isLoading) {
        return (
            <Card className={cn('animate-pulse', className)}>
                <CardContent className="p-3">
                    <div className="h-4 bg-muted rounded w-24 mb-2" />
                    <div className="h-7 bg-muted rounded w-32 mb-2" />
                    <div className="h-6 bg-muted rounded w-full" />
                </CardContent>
            </Card>
        );
    }

    return (
        <Card
            className={cn(
                'relative overflow-hidden transition-shadow hover:shadow-md',
                isAlert && 'border-amber-500/50 bg-amber-50/30 dark:bg-amber-950/20',
                className
            )}
        >
            <CardContent className="p-3">
                {/* Header: Label + Icon */}
                <div className="flex items-center justify-between mb-1">
                    <span className={cn(
                        'text-sm font-medium text-muted-foreground',
                        isAlert && 'text-amber-700 dark:text-amber-400'
                    )}>
                        {isAlert && <AlertTriangle className="inline h-3.5 w-3.5 mr-1 -mt-0.5" />}
                        {label}
                    </span>
                    {icon && <span className="text-muted-foreground">{icon}</span>}
                </div>

                {/* Primary Value */}
                <div className={cn(
                    'text-xl font-bold tracking-tight',
                    isAlert && 'text-amber-700 dark:text-amber-400'
                )}>
                    {value}
                </div>

                {/* Sparkline (if provided) */}
                {sparklineData && sparklineData.length > 0 && (
                    <div className="mt-1.5">
                        <MiniSparkline
                            data={sparklineData}
                            type={sparklineType}
                            color={getSparklineColor()}
                            height={24}
                        />
                    </div>
                )}

                {/* Bottom row: Trend + Secondary Text + Action */}
                <div className="flex items-center justify-between mt-1.5 min-h-[18px]">
                    <div className="flex items-center gap-2">
                        {getTrendDisplay()}
                        {secondaryText && (
                            <span className="text-xs text-muted-foreground truncate max-w-[120px]">
                                {secondaryText}
                            </span>
                        )}
                    </div>

                    {actionText && onAction && (
                        <button
                            onClick={onAction}
                            className={cn(
                                'flex items-center gap-0.5 text-xs font-medium transition-colors',
                                isAlert
                                    ? 'text-amber-700 hover:text-amber-800 dark:text-amber-400 dark:hover:text-amber-300'
                                    : 'text-primary hover:text-primary/80'
                            )}
                        >
                            {actionText}
                            <ChevronRight className="h-3 w-3" />
                        </button>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}

export default EnhancedKPICard;
