'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useFilters, transformFiltersForAPI } from './FilterContext';
import { apiClient } from '@/lib/api-client';
import { LeaderboardResponse } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart3 } from 'lucide-react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

// Color palette for product types
const COLORS = ['#3b82f6', '#6366f1', '#8b5cf6', '#a855f7', '#d946ef', '#ec4899', '#f43f5e', '#ef4444'];

type ProductTypeDataPoint = {
  label: string;
  revenue: number;
  share_pct: number;
};

type TooltipPayloadItem<TPayload> = {
  payload?: TPayload;
  value?: string | number;
};

type BasicTooltipProps<TPayload> = {
  active?: boolean;
  payload?: TooltipPayloadItem<TPayload>[];
  label?: string | number;
};

// Format currency values for display
const formatCurrency = (value: number) => {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }
  return value.toFixed(0);
};

// Custom tooltip for pie chart
const PieTooltip = ({ active, payload }: BasicTooltipProps<ProductTypeDataPoint>) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0]?.payload;
  if (!data) return null;

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
      <p className="font-semibold text-sm text-gray-900 mb-1">{data.label}</p>
      <p className="text-sm text-gray-600">
        Revenue: <span className="font-medium">AED {data.revenue.toLocaleString()}</span>
      </p>
      <p className="text-sm text-gray-600">
        Share: <span className="font-medium">{data.share_pct.toFixed(1)}%</span>
      </p>
    </div>
  );
};

// Custom tooltip for bar chart
const BarTooltip = ({ active, payload, label }: BasicTooltipProps<ProductTypeDataPoint>) => {
  if (!active || !payload || !payload.length) return null;
  const value = payload[0]?.value;

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
      <p className="font-semibold text-sm text-gray-900 mb-1">{label}</p>
      <p className="text-sm text-gray-600">
        Revenue:{' '}
        <span className="font-medium">
          AED {typeof value === 'number' ? value.toLocaleString() : String(value ?? '')}
        </span>
      </p>
    </div>
  );
};

interface ProductTypeChartProps {
  height?: number;
}

/**
 * ProductTypeChart Component
 *
 * Displays revenue breakdown by product type (order_type).
 * - If ≤5 types: Renders as Donut chart
 * - If >5 types: Renders as Horizontal Bar chart
 * - Auto-groups smallest into "Other" if >8 categories
 */
export function ProductTypeChart({ height = 280 }: ProductTypeChartProps) {
  const { filters } = useFilters();
  const [data, setData] = useState<LeaderboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const apiFilters = transformFiltersForAPI(filters);
      const result = await apiClient.getLeaderboard(apiFilters, 'order_type');
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
      console.error('Error fetching product type data:', err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Process data: group small categories into "Other" if >8
  const processedData = React.useMemo(() => {
    if (!data || !data.data.length) return [];

    let chartData = data.data.map((item) => ({
      label: item.label,
      revenue: item.revenue,
      share_pct: item.share_pct,
    }));

    // If more than 8 categories, group smallest into "Other"
    if (chartData.length > 8) {
      const top7 = chartData.slice(0, 7);
      const others = chartData.slice(7);
      const otherRevenue = others.reduce((sum, item) => sum + item.revenue, 0);
      const otherShare = others.reduce((sum, item) => sum + item.share_pct, 0);

      chartData = [
        ...top7,
        { label: 'Other', revenue: otherRevenue, share_pct: otherShare },
      ];
    }

    return chartData;
  }, [data]);

  // Determine chart type based on data count
  const useDonutChart = processedData.length <= 5;

  if (loading) {
    return (
      <Card className="h-full">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Revenue by Product Type</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className="bg-gray-100 animate-pulse rounded-lg"
            style={{ height: height - 60 }}
          />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="h-full">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Revenue by Product Type</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className="flex items-center justify-center text-gray-400"
            style={{ height: height - 60 }}
          >
            <div className="text-center">
              <BarChart3 className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p className="text-sm text-red-500">{error}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!processedData.length) {
    return (
      <Card className="h-full">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Revenue by Product Type</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            className="flex items-center justify-center text-gray-400"
            style={{ height: height - 60 }}
          >
            <div className="text-center">
              <BarChart3 className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No product type data available</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg">Revenue by Product Type</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={height - 60}>
          {useDonutChart ? (
            // Donut Chart for ≤5 categories
            <PieChart>
              <Pie
                data={processedData}
                dataKey="revenue"
                nameKey="label"
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={2}
                label={(props) => {
                  const payload = props.payload as ProductTypeDataPoint;
                  return `${payload.label} (${payload.share_pct.toFixed(0)}%)`;
                }}
                labelLine={{ stroke: '#6b7280', strokeWidth: 1 }}
              >
                {processedData.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip content={<PieTooltip />} />
              <Legend />
            </PieChart>
          ) : (
            // Horizontal Bar Chart for >5 categories
            <BarChart
              data={processedData}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                type="number"
                tickFormatter={formatCurrency}
                tick={{ fill: '#6b7280', fontSize: 12 }}
              />
              <YAxis
                type="category"
                dataKey="label"
                width={100}
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickLine={false}
              />
              <Tooltip content={<BarTooltip />} />
              <Bar dataKey="revenue" radius={[0, 4, 4, 0]}>
                {processedData.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                  />
                ))}
              </Bar>
            </BarChart>
          )}
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
