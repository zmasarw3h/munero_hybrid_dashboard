'use client';

/**
 * StuckOrdersList - List of problematic orders requiring attention
 * 
 * Shows stuck/failed/pending orders with status badges, age, and action buttons.
 * Part of the Operational Health Panel in Zone 3.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { StuckOrder, StuckOrderStatus } from '@/lib/types';
import { cn } from '@/lib/utils';
import { AlertTriangle, RefreshCw, ChevronRight, Clock } from 'lucide-react';

interface StuckOrdersListProps {
    /** List of stuck orders */
    orders: StuckOrder[];
    /** Whether data is mock */
    isMock?: boolean;
    /** Maximum orders to display */
    maxDisplay?: number;
    /** Total count (for "View All" button) */
    totalCount?: number;
    /** Click handler for retry button */
    onRetry?: (order: StuckOrder) => void;
    /** Click handler for view details */
    onViewDetails?: (order: StuckOrder) => void;
    /** Click handler for "View All" button */
    onViewAll?: () => void;
    /** Loading state */
    isLoading?: boolean;
    /** Optional className */
    className?: string;
}

const STATUS_CONFIG: Record<StuckOrderStatus, { label: string; variant: 'destructive' | 'warning' | 'secondary' }> = {
    stuck: { label: 'Stuck', variant: 'destructive' },
    failed: { label: 'Failed', variant: 'destructive' },
    pending: { label: 'Pending', variant: 'warning' },
};

function getStatusBadgeVariant(status: StuckOrderStatus): 'destructive' | 'secondary' | 'default' | 'outline' {
    switch (status) {
        case 'stuck':
        case 'failed':
            return 'destructive';
        case 'pending':
            return 'secondary';
        default:
            return 'default';
    }
}

export function StuckOrdersList({
    orders,
    isMock = false,
    maxDisplay = 5,
    totalCount,
    onRetry,
    onViewDetails,
    onViewAll,
    isLoading = false,
    className,
}: StuckOrdersListProps) {
    const displayOrders = orders.slice(0, maxDisplay);
    const remainingCount = (totalCount ?? orders.length) - displayOrders.length;

    if (isLoading) {
        return (
            <Card className={className}>
                <CardHeader className="py-3 px-4">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-amber-500" />
                        Attention Required
                    </CardTitle>
                </CardHeader>
                <CardContent className="pb-4 px-4">
                    <div className="space-y-2">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="h-10 bg-muted animate-pulse rounded" />
                        ))}
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (!orders || orders.length === 0) {
        return (
            <Card className={className}>
                <CardHeader className="py-3 px-4">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-green-500" />
                        All Clear
                    </CardTitle>
                </CardHeader>
                <CardContent className="pb-4 px-4">
                    <div className="text-sm text-muted-foreground text-center py-4">
                        No stuck or failed orders
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className={cn('border-amber-200 dark:border-amber-900/50 h-full flex flex-col', className)}>
            <CardHeader className="py-3 px-4">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-amber-500" />
                        Attention Required
                    </CardTitle>
                    {isMock && (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                            Demo
                        </Badge>
                    )}
                </div>
            </CardHeader>
            <CardContent className="pb-3 px-4 flex-1 flex flex-col">
                <div className="space-y-2 flex-1">
                    {displayOrders.map((order) => (
                        <div
                            key={order.order_number}
                            className="flex items-center justify-between py-1.5 border-b border-border/50 last:border-0"
                        >
                            <div className="flex items-center gap-2 min-w-0">
                                {/* Order Number */}
                                <span className="text-sm font-mono font-medium truncate">
                                    #{order.order_number.replace('ORD-', '')}
                                </span>

                                {/* Status Badge */}
                                <Badge
                                    variant={getStatusBadgeVariant(order.status)}
                                    className="text-[10px] px-1.5 py-0"
                                >
                                    {STATUS_CONFIG[order.status]?.label || order.status}
                                </Badge>

                                {/* Age */}
                                <span className="text-xs text-muted-foreground flex items-center gap-0.5">
                                    <Clock className="h-3 w-3" />
                                    {order.age_days}d
                                </span>
                            </div>

                            {/* Actions */}
                            <div className="flex items-center gap-1">
                                {onRetry && order.status !== 'pending' && (
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-6 w-6"
                                        onClick={() => onRetry(order)}
                                        title="Retry order"
                                    >
                                        <RefreshCw className="h-3 w-3" />
                                    </Button>
                                )}
                                {onViewDetails && (
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-6 w-6"
                                        onClick={() => onViewDetails(order)}
                                        title="View details"
                                    >
                                        <ChevronRight className="h-3 w-3" />
                                    </Button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>

                {/* View All Button */}
                {remainingCount > 0 && onViewAll && (
                    <Button
                        variant="ghost"
                        size="sm"
                        className="w-full mt-2 text-xs"
                        onClick={onViewAll}
                    >
                        View All ({totalCount ?? orders.length})
                    </Button>
                )}
            </CardContent>
        </Card>
    );
}

export default StuckOrdersList;
