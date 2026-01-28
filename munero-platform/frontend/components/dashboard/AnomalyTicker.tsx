'use client';

/**
 * AnomalyTicker - Horizontal scrollable strip showing anomalies
 * 
 * Zone 5 component that displays detected anomalies in a horizontally
 * scrollable strip. User can scroll left/right to see all anomalies.
 */

import { useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendPoint, AnomalyItem } from '@/lib/types';
import { cn } from '@/lib/utils';
import { AlertTriangle, TrendingUp, TrendingDown, ChevronLeft, ChevronRight } from 'lucide-react';

interface AnomalyTickerProps {
    /** Trend data containing anomaly flags */
    trendData: TrendPoint[];
    /** Click handler for anomaly items */
    onAnomalyClick?: (anomaly: AnomalyItem) => void;
    /** Optional className */
    className?: string;
}

function extractAnomalies(trendData: TrendPoint[]): AnomalyItem[] {
    const anomalies: AnomalyItem[] = [];

    for (const point of trendData) {
        if (point.is_revenue_anomaly) {
            anomalies.push({
                date: point.date_label,
                metric: 'revenue',
                change_pct: point.revenue_growth,
                z_score: 3.0, // Placeholder - would come from backend
                direction: point.revenue_growth >= 0 ? 'positive' : 'negative',
            });
        }
        if (point.is_order_anomaly) {
            anomalies.push({
                date: point.date_label,
                metric: 'orders',
                change_pct: point.orders_growth,
                z_score: 3.0, // Placeholder
                direction: point.orders_growth >= 0 ? 'positive' : 'negative',
            });
        }
    }

    // Sort by absolute change (most significant first)
    return anomalies.sort((a, b) => Math.abs(b.change_pct) - Math.abs(a.change_pct));
}

function formatDate(dateLabel: string): string {
    // Handle various date formats
    try {
        const date = new Date(dateLabel);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
        return dateLabel;
    }
}

export function AnomalyTicker({
    trendData,
    onAnomalyClick,
    className,
}: AnomalyTickerProps) {
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const anomalies = extractAnomalies(trendData);

    // Scroll handlers
    const scroll = (direction: 'left' | 'right') => {
        if (!scrollContainerRef.current) return;
        const scrollAmount = 200;
        scrollContainerRef.current.scrollBy({
            left: direction === 'left' ? -scrollAmount : scrollAmount,
            behavior: 'smooth',
        });
    };

    // Empty state
    if (!anomalies || anomalies.length === 0) {
        return (
            <Card className={cn('py-2 px-4', className)}>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <AlertTriangle className="h-4 w-4 text-green-500" />
                    <span>No anomalies detected in the selected period</span>
                </div>
            </Card>
        );
    }

    return (
        <Card className={cn('relative', className)}>
            {/* Left scroll button */}
            <button
                onClick={() => scroll('left')}
                className="absolute left-0 top-0 bottom-0 z-10 px-1 bg-gradient-to-r from-background to-transparent hover:from-muted flex items-center"
                aria-label="Scroll left"
            >
                <ChevronLeft className="h-4 w-4 text-muted-foreground" />
            </button>

            {/* Scrollable container */}
            <div
                ref={scrollContainerRef}
                className="flex items-center gap-2 overflow-x-auto scrollbar-thin scrollbar-thumb-muted py-2 px-8 scroll-smooth"
                style={{ scrollSnapType: 'x mandatory' }}
            >
                {/* Alert icon */}
                <div className="flex-shrink-0 flex items-center gap-2 pr-2 border-r border-border">
                    <AlertTriangle className="h-4 w-4 text-amber-500" />
                    <span className="text-xs font-medium text-muted-foreground">
                        {anomalies.length} Anomal{anomalies.length === 1 ? 'y' : 'ies'}
                    </span>
                </div>

                {/* Anomaly items */}
                {anomalies.map((anomaly, index) => (
                    <button
                        key={`${anomaly.date}-${anomaly.metric}-${index}`}
                        onClick={() => onAnomalyClick?.(anomaly)}
                        className={cn(
                            'flex-shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-md transition-colors',
                            'hover:bg-muted cursor-pointer',
                            'scroll-snap-align-start'
                        )}
                        style={{ scrollSnapAlign: 'start' }}
                    >
                        {/* Direction icon */}
                        {anomaly.direction === 'positive' ? (
                            <TrendingUp className="h-3.5 w-3.5 text-green-600" />
                        ) : (
                            <TrendingDown className="h-3.5 w-3.5 text-red-600" />
                        )}

                        {/* Date and metric */}
                        <span className="text-xs font-medium">
                            {formatDate(anomaly.date)}:
                        </span>

                        {/* Change badge */}
                        <Badge
                            variant={anomaly.direction === 'positive' ? 'default' : 'destructive'}
                            className={cn(
                                'text-[10px] px-1.5 py-0',
                                anomaly.direction === 'positive' && 'bg-green-600 hover:bg-green-700'
                            )}
                        >
                            {anomaly.metric === 'revenue' ? 'Rev' : 'Ord'}{' '}
                            {anomaly.change_pct >= 0 ? '+' : ''}
                            {anomaly.change_pct.toFixed(0)}%
                        </Badge>
                    </button>
                ))}
            </div>

            {/* Right scroll button */}
            <button
                onClick={() => scroll('right')}
                className="absolute right-0 top-0 bottom-0 z-10 px-1 bg-gradient-to-l from-background to-transparent hover:from-muted flex items-center"
                aria-label="Scroll right"
            >
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </button>
        </Card>
    );
}

export default AnomalyTicker;
