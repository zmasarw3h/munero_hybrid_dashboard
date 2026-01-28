'use client';

/**
 * OperationalHealthPanel - Right sidebar with donut chart + stuck orders alerts
 * 
 * Composite component for Zone 3B containing:
 * - CompactDonut for revenue by type breakdown
 * - StuckOrdersList for critical alerts
 */

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api-client';
import { useFilters, transformFiltersForAPI } from '@/components/dashboard/FilterContext';
import { StuckOrder, LeaderboardRow } from '@/lib/types';
import { CompactDonut } from './CompactDonut';
import { StuckOrdersList } from './StuckOrdersList';

interface OperationalHealthPanelProps {
    /** Optional className for styling */
    className?: string;
}

// Colors for donut segments - keys match API labels (lowercase with underscores)
const TYPE_COLORS: Record<string, string> = {
    'gift_card': '#3b82f6',      // Blue
    'Gift Card': '#3b82f6',      // Blue (fallback)
    'merchandise': '#8b5cf6',    // Purple
    'Merchandise': '#8b5cf6',    // Purple (fallback)
};

export function OperationalHealthPanel({ className }: OperationalHealthPanelProps) {
    const { filters } = useFilters();

    // State for stuck orders
    const [stuckOrders, setStuckOrders] = useState<StuckOrder[]>([]);
    const [stuckOrdersLoading, setStuckOrdersLoading] = useState(true);
    const [isMockData, setIsMockData] = useState(false);

    // State for product type breakdown (from leaderboard endpoint)
    const [typeData, setTypeData] = useState<{ name: string; value: number; color: string }[]>([]);
    const [typeLoading, setTypeLoading] = useState(true);

    // Fetch stuck orders
    useEffect(() => {
        async function fetchStuckOrders() {
            setStuckOrdersLoading(true);
            try {
                const response = await apiClient.getStuckOrders(5);
                setStuckOrders(response.orders);
                setIsMockData(response.is_mock);
            } catch (error) {
                console.error('Failed to fetch stuck orders:', error);
                setStuckOrders([]);
            } finally {
                setStuckOrdersLoading(false);
            }
        }
        fetchStuckOrders();
    }, []);

    // Fetch product type breakdown
    useEffect(() => {
        async function fetchTypeBreakdown() {
            setTypeLoading(true);
            try {
                const apiFilters = transformFiltersForAPI(filters);
                const response = await apiClient.getLeaderboard(apiFilters, 'order_type');
                const donutData = response.data.map((row: LeaderboardRow) => {
                    // Format label for display (e.g., "gift_card" -> "Gift Card")
                    const displayName = row.label
                        .split('_')
                        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                        .join(' ');
                    return {
                        name: displayName,
                        value: row.revenue,
                        color: TYPE_COLORS[row.label] || TYPE_COLORS[displayName] || '#6b7280',
                    };
                });
                setTypeData(donutData);
            } catch (error) {
                console.error('Failed to fetch type breakdown:', error);
                setTypeData([]);
            } finally {
                setTypeLoading(false);
            }
        }
        fetchTypeBreakdown();
    }, [filters]);

    // Handlers for stuck orders actions
    const handleRetry = (order: StuckOrder) => {
        console.log('Retry order:', order.order_number);
        // TODO: Implement retry logic
    };

    const handleViewDetails = (order: StuckOrder) => {
        console.log('View details:', order.order_number);
        // TODO: Open order details modal/page
    };

    const handleViewAll = () => {
        console.log('View all stuck orders');
        // TODO: Navigate to full stuck orders list
    };

    return (
        <div className={`h-full ${className || ''}`}>
            <div className="space-y-2 h-full flex flex-col">
                {/* Revenue by Type Donut */}
                <CompactDonut
                    title="Revenue by Type"
                    data={typeData}
                    size={90}
                    currency={filters.currency}
                    onSegmentClick={(segment) => {
                        console.log('Filter by type:', segment.name);
                        // TODO: Update filter context
                    }}
                />

                {/* Stuck Orders List */}
                <div className="flex-1 min-h-0">
                    <StuckOrdersList
                        orders={stuckOrders}
                        isMock={isMockData}
                        maxDisplay={3}
                        totalCount={stuckOrders.length}
                        isLoading={stuckOrdersLoading}
                        onRetry={handleRetry}
                        onViewDetails={handleViewDetails}
                        onViewAll={stuckOrders.length > 3 ? handleViewAll : undefined}
                        className="h-full"
                    />
                </div>
            </div>
        </div>
    );
}

export default OperationalHealthPanel;
