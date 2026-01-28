'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useFilters, transformFiltersForAPI } from '@/components/dashboard/FilterContext';
import { apiClient } from '@/lib/api-client';
import {
    ScatterPoint,
    LeaderboardRow,
    ClientSegment,
    SegmentedClient,
} from '@/lib/types';
import {
    calculateMarketKPIs,
    calculateSegmentSummaries,
    SEGMENT_CONFIG,
    formatCurrencyCompact,
} from '@/lib/market-utils';

// Components
import { EnhancedKPICard } from '@/components/dashboard/EnhancedKPICard';
import { ClientSegmentationMatrix } from '@/components/dashboard/ClientSegmentationMatrix';
import { RevenueConcentrationChart } from '@/components/dashboard/RevenueConcentrationChart';
import { CompactDonut } from '@/components/dashboard/CompactDonut';
import { ClientLeaderboard } from '@/components/dashboard/ClientLeaderboard';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertTriangle } from 'lucide-react';

export default function MarketPage() {
    const { filters } = useFilters();

    // Data state
    const [scatterData, setScatterData] = useState<ScatterPoint[]>([]);
    const [leaderboardData, setLeaderboardData] = useState<LeaderboardRow[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Metadata from scatter API (for accurate KPIs when data is limited to top 500)
    const [scatterMetadata, setScatterMetadata] = useState<{
        totalClients: number;
        medianOrders: number;
        medianRevenue: number;
    } | null>(null);

    // Interaction state
    const [selectedClient, setSelectedClient] = useState<string | null>(null);
    const [selectedSegment, setSelectedSegment] = useState<ClientSegment | null>(null);
    // Segmented clients come from the ClientSegmentationMatrix component
    const [segmentedClients, setSegmentedClients] = useState<SegmentedClient[]>([]);

    // Fetch data
    const fetchData = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const apiFilters = transformFiltersForAPI(filters);

            const [scatterResponse, leaderboardResponse] = await Promise.all([
                apiClient.getScatter(apiFilters),
                apiClient.getLeaderboard(apiFilters, 'client', false), // include_trend=false for performance
            ]);

            setScatterData(scatterResponse.data);
            setLeaderboardData(leaderboardResponse.data);

            // Store metadata for accurate KPIs (total count and medians from ALL clients)
            setScatterMetadata({
                totalClients: scatterResponse.total_clients,
                medianOrders: scatterResponse.median_orders,
                medianRevenue: scatterResponse.median_revenue,
            });
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch data');
            console.error('Error fetching market data:', err);
        } finally {
            setLoading(false);
        }
    }, [filters]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const marketKPIs = useMemo(
        () => calculateMarketKPIs(scatterData, scatterMetadata?.totalClients),
        [scatterData, scatterMetadata]
    );

    const segmentSummaries = useMemo(
        () => calculateSegmentSummaries(segmentedClients),
        [segmentedClients]
    );

    // Create a map of client name to segment for leaderboard
    const clientSegmentMap = useMemo(() => {
        const map = new Map<string, ClientSegment>();
        segmentedClients.forEach((c) => {
            map.set(c.client_name, c.segment);
        });
        return map;
    }, [segmentedClients]);

    // Filter leaderboard by selected segment or client
    const filteredLeaderboard = useMemo(() => {
        let filtered = leaderboardData;

        if (selectedClient) {
            filtered = filtered.filter((row) => row.label === selectedClient);
        } else if (selectedSegment) {
            const segmentClientNames = segmentedClients
                .filter((c) => c.segment === selectedSegment)
                .map((c) => c.client_name);
            filtered = filtered.filter((row) => segmentClientNames.includes(row.label));
        }

        return filtered;
    }, [leaderboardData, selectedClient, selectedSegment, segmentedClients]);

    // Handlers - wrapped in useCallback to prevent unnecessary re-renders
    const handleClientClick = useCallback((clientName: string) => {
        setSelectedClient((prev) => (prev === clientName ? null : clientName));
        setSelectedSegment(null);
    }, []);

    const handleSegmentClick = useCallback((segment: ClientSegment | null) => {
        setSelectedSegment(segment);
        setSelectedClient(null);
    }, []);

    // Handler to receive segmented clients from the matrix component
    const handleSegmentedClientsChange = useCallback((clients: SegmentedClient[]) => {
        setSegmentedClients(clients);
    }, []);

    const clearFilters = useCallback(() => {
        setSelectedClient(null);
        setSelectedSegment(null);
    }, []);

    // Error state
    if (error) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Card className="w-full max-w-md">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-red-600">
                            <AlertTriangle className="h-5 w-5" />
                            Error Loading Data
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-sm text-gray-600">{error}</p>
                        <Button onClick={fetchData} className="mt-4" variant="outline">
                            Retry
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Page Header */}
            <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                    Market Analysis
                </h2>
                <p className="text-sm text-muted-foreground">
                    Client segmentation, concentration analysis, and performance insights
                </p>
            </div>

            {/* ZONE 1: Market KPIs (3 cards) */}
            <div className="grid gap-2 md:grid-cols-3">
                <EnhancedKPICard
                    label="Active Clients"
                    value={marketKPIs.activeClients.toLocaleString()}
                    secondaryText={
                        scatterMetadata && scatterMetadata.totalClients > 500
                            ? 'Top 500 shown'
                            : undefined
                    }
                    isLoading={loading}
                />
                <EnhancedKPICard
                    label="Avg Revenue/Client"
                    value={formatCurrencyCompact(marketKPIs.avgRevenuePerClient, filters.currency)}
                    isLoading={loading}
                />
                <EnhancedKPICard
                    label="Top Client Share"
                    value={`${marketKPIs.topClientSharePct.toFixed(1)}%`}
                    secondaryText={marketKPIs.topClientName}
                    isAlert={marketKPIs.isConcentrationRisk}
                    isLoading={loading}
                />
            </div>

            {/* ZONE 2: Main Visualizations (12-col grid) */}
            <div className="grid gap-2 lg:grid-cols-12">
                {/* Revenue Concentration Chart (4 cols) */}
                <div className="lg:col-span-4">
                    <RevenueConcentrationChart
                        data={scatterData}
                        topN={10}
                        height={500}
                        onClientClick={handleClientClick}
                    />
                </div>

                {/* Segmentation Matrix (5 cols) */}
                <div className="lg:col-span-5">
                    <ClientSegmentationMatrix
                        data={scatterData}
                        medianOrders={scatterMetadata?.medianOrders}
                        medianRevenue={scatterMetadata?.medianRevenue}
                        onClientClick={handleClientClick}
                        onSegmentClick={handleSegmentClick}
                        onSegmentedClientsChange={handleSegmentedClientsChange}
                        selectedClient={selectedClient}
                        selectedSegment={selectedSegment}
                        height={500}
                    />
                </div>

                {/* Segment Distribution Donut (3 cols) */}
                <div className="lg:col-span-3">
                    <CompactDonut
                        title="Segment Distribution"
                        data={segmentSummaries.map((s) => ({
                            name: s.label,
                            value: s.count,
                            color: s.color,
                        }))}
                        height={500}
                        onSegmentClick={(segment) => {
                            const seg = segmentSummaries.find((s) => s.label === segment.name);
                            if (seg) handleSegmentClick(seg.segment);
                        }}
                    />
                </div>
            </div>

            {/* ZONE 3: Client Leaderboard (full width) */}
            <ClientLeaderboard
                data={filteredLeaderboard}
                clientSegmentMap={clientSegmentMap}
                loading={loading}
                currency={filters.currency}
                selectedClient={selectedClient}
                selectedSegment={selectedSegment}
                onClientClick={handleClientClick}
                onClearFilter={clearFilters}
                totalCount={leaderboardData.length}
            />
        </div>
    );
}
