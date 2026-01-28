'use client';

import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertCircle, Loader2 } from 'lucide-react';

// Types
export interface SupplierData {
  label: string;
  revenue: number;
  share_pct: number;
  orders: number;
}

export interface SupplierConcentrationChartProps {
  suppliers: SupplierData[];
  loading?: boolean;
}

type TooltipPayloadItem<TPayload> = {
  payload?: TPayload;
};

type BasicTooltipProps<TPayload> = {
  active?: boolean;
  payload?: ReadonlyArray<TooltipPayloadItem<TPayload>>;
};

// Risk color based on concentration percentage (only for individual suppliers, not aggregates)
function getRiskColor(sharePct: number, isAggregate: boolean = false): string {
  // "Others" aggregate uses neutral gray - high "Others" is actually good (diversification)
  if (isAggregate) return '#9ca3af'; // Gray - neutral/aggregated

  if (sharePct > 30) return '#ef4444'; // Red - High risk
  if (sharePct > 20) return '#f59e0b'; // Amber - Moderate risk
  return '#22c55e'; // Green - Healthy
}

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

// Custom Tooltip
const SupplierTooltip = ({ active, payload }: BasicTooltipProps<SupplierData>) => {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0]?.payload;
  if (!data) return null;
  const displayName = data.label === 'None' ? 'Unassigned' : data.label;

  return (
    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
      <p className="font-semibold text-sm">{displayName}</p>
      <p className="text-xs text-gray-600 dark:text-gray-400">
        Revenue: {formatCurrency(data.revenue)}
      </p>
      <p className="text-xs text-gray-600 dark:text-gray-400">
        Share: {data.share_pct.toFixed(1)}%
      </p>
      <p className="text-xs text-gray-600 dark:text-gray-400">
        Orders: {data.orders.toLocaleString()}
      </p>
    </div>
  );
};

export function SupplierConcentrationChart({
  suppliers,
  loading = false,
}: SupplierConcentrationChartProps) {
  // Prepare chart data: top 5 + Others (excluding "None" from visualization)
  const { chartData, atRiskSuppliers, hasUnassigned } = useMemo(() => {
    if (!suppliers || suppliers.length === 0) {
      return { chartData: [], atRiskSuppliers: [], hasUnassigned: false };
    }

    // Check if there's an unassigned supplier and track it separately
    const unassignedSupplier = suppliers.find((s) => s.label === 'None');
    const hasUnassigned = !!unassignedSupplier;

    // Filter out "None" for visualization, but include in risk calculation
    const namedSuppliers = suppliers.filter((s) => s.label !== 'None');

    const topSuppliers = namedSuppliers.slice(0, 5);
    const others = namedSuppliers.slice(5);

    const data: SupplierData[] = [...topSuppliers];

    // Combine "Others" with any remaining named suppliers
    if (others.length > 0) {
      const othersTotal: SupplierData = {
        label: 'Others',
        share_pct: others.reduce((sum, s) => sum + s.share_pct, 0),
        revenue: others.reduce((sum, s) => sum + s.revenue, 0),
        orders: others.reduce((sum, s) => sum + s.orders, 0),
      };
      data.push(othersTotal);
    }

    // Identify at-risk suppliers (>30%) - include unassigned in risk check
    const allForRiskCheck = unassignedSupplier ? [...topSuppliers, unassignedSupplier] : topSuppliers;
    const atRisk = allForRiskCheck.filter((s) => s.share_pct > 30);

    return { chartData: data, atRiskSuppliers: atRisk, hasUnassigned };
  }, [suppliers]);

  // Loading state
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Supplier Concentration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[280px] flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Empty state
  if (!suppliers || suppliers.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Supplier Concentration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[280px] flex items-center justify-center text-gray-400">
            <p className="text-sm">No supplier data available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Supplier Concentration</CardTitle>
        <CardDescription className="text-xs">
          Revenue share by supplier (risk threshold: 30%)
          {hasUnassigned && (
            <span className="text-amber-600 ml-1">• Excludes unassigned products</span>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ left: 20, right: 20, top: 10, bottom: 10 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />

            <XAxis
              type="number"
              domain={[0, 100]}
              tickFormatter={(val) => `${val}%`}
              tick={{ fontSize: 11 }}
            />

            <YAxis
              type="category"
              dataKey="label"
              width={120}
              tick={{ fontSize: 11 }}
              tickFormatter={(val: string) => {
                const displayVal = val === 'None' ? 'Unassigned' : val;
                return displayVal.length > 20 ? displayVal.substring(0, 18) + '...' : displayVal;
              }}
            />

            <Tooltip content={<SupplierTooltip />} cursor={{ fill: 'rgba(0, 0, 0, 0.05)' }} />

            {/* 30% Risk Threshold Line */}
            <ReferenceLine
              x={30}
              stroke="#f59e0b"
              strokeDasharray="3 3"
              label={{
                value: '30% threshold',
                position: 'top',
                fontSize: 10,
                fill: '#f59e0b',
              }}
            />

            {/* Bar with dynamic colors - "Others" uses neutral gray */}
            <Bar dataKey="share_pct" radius={[0, 4, 4, 0]} isAnimationActive={false}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={getRiskColor(entry.share_pct, entry.label === 'Others')}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        {/* Warning Alert for high-risk suppliers */}
        {atRiskSuppliers.length > 0 && (
          <Alert variant="destructive" className="mt-3">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle className="text-sm font-semibold">High Concentration Risk</AlertTitle>
            <AlertDescription className="text-xs">
              {atRiskSuppliers[0].label === 'None' ? 'Unassigned supplier' : atRiskSuppliers[0].label} exceeds 30% threshold (
              {atRiskSuppliers[0].share_pct.toFixed(1)}%). Consider diversifying supply chain to
              reduce risk.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

export default SupplierConcentrationChart;
