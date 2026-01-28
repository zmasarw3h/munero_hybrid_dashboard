'use client';

import { useMemo } from 'react';
import { Users } from 'lucide-react';
import {
    BaseLeaderboard,
    SegmentBadge,
    formatCurrency,
    formatNumber,
    formatPercentage,
    truncateText,
    ColumnDef,
} from '@/components/dashboard/shared';
import { ClientSegment, LeaderboardRow } from '@/lib/types';
import { SEGMENT_CONFIG } from '@/lib/market-utils';

// ============================================================================
// TYPES
// ============================================================================

export interface ClientLeaderboardRow extends LeaderboardRow {
    segment?: ClientSegment;
}

export interface ClientLeaderboardProps {
    /** Client data rows */
    data: LeaderboardRow[];
    /** Map of client name to segment */
    clientSegmentMap: Map<string, ClientSegment>;
    /** Loading state */
    loading?: boolean;
    /** Currency for formatting */
    currency?: string;
    /** Currently selected client name */
    selectedClient?: string | null;
    /** Currently selected segment filter */
    selectedSegment?: ClientSegment | null;
    /** Callback when a client row is clicked */
    onClientClick?: (clientName: string) => void;
    /** Callback to clear the current filter */
    onClearFilter?: () => void;
    /** Total count before filtering */
    totalCount?: number;
}

// ============================================================================
// COMPONENT
// ============================================================================

export function ClientLeaderboard({
    data,
    clientSegmentMap,
    loading = false,
    currency = 'AED',
    selectedClient,
    selectedSegment,
    onClientClick,
    onClearFilter,
    totalCount,
}: ClientLeaderboardProps) {
    // Define columns
    const columns: ColumnDef<LeaderboardRow>[] = useMemo(() => [
        {
            key: 'label',
            header: 'Client',
            accessor: (row) => row.label,
            sortable: true,
            align: 'left',
            width: '35%',
            render: (value) => (
                <span className="font-medium truncate block" title={String(value)}>
                    {truncateText(String(value), 35)}
                </span>
            ),
        },
        {
            key: 'segment',
            header: 'Segment',
            accessor: (row) => clientSegmentMap.get(row.label) || 'developing',
            sortable: true,
            align: 'left',
            width: '20%',
            render: (value) => {
                const segment = value as ClientSegment;
                const config = SEGMENT_CONFIG[segment] || SEGMENT_CONFIG.developing;
                return <SegmentBadge label={config.label} color={config.color} />;
            },
        },
        {
            key: 'revenue',
            header: 'Revenue',
            accessor: (row) => row.revenue,
            sortable: true,
            align: 'right',
            width: '20%',
            render: (value) => formatCurrency(value as number, currency),
        },
        {
            key: 'orders',
            header: 'Orders',
            accessor: (row) => row.orders,
            sortable: true,
            align: 'right',
            width: '12%',
            render: (value) => formatNumber(value as number),
        },
        {
            key: 'share_pct',
            header: 'Share',
            accessor: (row) => row.share_pct,
            sortable: true,
            align: 'right',
            width: '13%',
            render: (value) => formatPercentage(value as number),
        },
    ], [clientSegmentMap, currency]);

    // Active filter info
    const activeFilter = useMemo(() => {
        if (selectedSegment) {
            const config = SEGMENT_CONFIG[selectedSegment];
            return {
                label: config.label,
                badge: <SegmentBadge label={config.label} color={config.color} />,
            };
        }
        if (selectedClient) {
            return {
                label: selectedClient,
            };
        }
        return undefined;
    }, [selectedSegment, selectedClient]);

    // Count info
    const countInfo = useMemo(() => {
        const total = totalCount ?? data.length;
        const filtered = data.length;
        const suffix = selectedSegment ? ` in ${SEGMENT_CONFIG[selectedSegment].label}` : '';
        return `${filtered} of ${total} clients${suffix}`;
    }, [data.length, totalCount, selectedSegment]);

    return (
        <BaseLeaderboard<LeaderboardRow>
            title="Client Leaderboard"
            columns={columns}
            data={data}
            loading={loading}
            loadingRows={5}
            getRowId={(row) => row.label}
            onRowClick={(row) => onClientClick?.(row.label)}
            selectedRowId={selectedClient}
            activeFilter={activeFilter}
            onClearFilter={activeFilter ? onClearFilter : undefined}
            countInfo={countInfo}
            emptyMessage="No clients match the current filter"
            emptyIcon={<Users className="h-10 w-10" />}
            defaultSort={{ key: 'revenue', direction: 'desc' }}
        />
    );
}

export default ClientLeaderboard;
