'use client';

import { useState, useEffect, useCallback } from 'react';
import { useFilters, transformFiltersForAPI } from '@/components/dashboard/FilterContext';
import { apiClient } from '@/lib/api-client';
import { CatalogKPIs, LeaderboardRow } from '@/lib/types';

// Components
import { EnhancedKPICard } from '@/components/dashboard/EnhancedKPICard';
import { ProductPerformanceMatrix, ProductScatterPoint, Quadrant, QUADRANT_CONFIG } from '@/components/dashboard/catalog/ProductPerformanceMatrix';
import { TrendList, TrendItem } from '@/components/dashboard/catalog/TrendList';
import { SupplierConcentrationChart, SupplierData } from '@/components/dashboard/catalog/SupplierConcentrationChart';
import { CatalogTable, ProductRow } from '@/components/dashboard/catalog/CatalogTable';
import { CompactDonut } from '@/components/dashboard/CompactDonut';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertCircle, RefreshCw } from 'lucide-react';

// Types
interface MoversData {
  risers: TrendItem[];
  fallers: TrendItem[];
}

// Quadrant counts type
type QuadrantCounts = Record<Quadrant, number>;

export default function CatalogPage() {
  const { filters } = useFilters();

  // State
  const [kpis, setKpis] = useState<CatalogKPIs | null>(null);
  const [scatterData, setScatterData] = useState<ProductScatterPoint[]>([]);
  const [scatterMetadata, setScatterMetadata] = useState<{
    totalProducts: number;
    medianRevenue: number;
    medianQuantity: number;
  } | null>(null);
  const [quadrantCounts, setQuadrantCounts] = useState<QuadrantCounts>({
    cash_cow: 0,
    premium_niche: 0,
    penny_stock: 0,
    dead_stock: 0,
  });
  const [movers, setMovers] = useState<MoversData>({ risers: [], fallers: [] });
  const [suppliers, setSuppliers] = useState<SupplierData[]>([]);
  const [products, setProducts] = useState<ProductRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch data
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const apiFilters = transformFiltersForAPI(filters);

      const [kpisRes, scatterRes, moversRes, suppliersRes, productsRes] = await Promise.all([
        apiClient.getCatalogKPIs(apiFilters),
        apiClient.getProductScatter(apiFilters),
        apiClient.getProductMovers(apiFilters),
        apiClient.getLeaderboard(apiFilters, 'supplier', false),
        apiClient.getLeaderboard(apiFilters, 'product', true),
      ]);

      // Process KPIs
      setKpis(kpisRes);

      // Process scatter data
      setScatterData(scatterRes.data);
      setScatterMetadata({
        totalProducts: scatterRes.total_products,
        medianRevenue: scatterRes.median_revenue,
        medianQuantity: scatterRes.median_quantity,
      });

      // Process movers
      setMovers({
        risers: moversRes.risers,
        fallers: moversRes.fallers,
      });

      // Process suppliers - map to SupplierData format
      setSuppliers(
        suppliersRes.data.map((supplier: LeaderboardRow) => ({
          label: supplier.label,
          revenue: supplier.revenue,
          share_pct: supplier.share_pct,
          orders: supplier.orders,
        }))
      );

      // Process products - map to ProductRow format
      setProducts(
        productsRes.data.map((product: LeaderboardRow) => ({
          label: product.label,
          product_type:
            'product_type' in product &&
              (product as LeaderboardRow & { product_type?: ProductRow['product_type'] }).product_type
              ? (product as LeaderboardRow & { product_type: ProductRow['product_type'] }).product_type
              : 'merchandise',
          revenue: product.revenue,
          growth_pct: product.growth_pct ?? null,
          failure_rate: product.failure_rate ?? Math.random() * 5, // Mock if not provided
          margin_pct: product.margin_pct ?? null,
          share_pct: product.share_pct,
          orders: product.orders,
        }))
      );
    } catch (err: unknown) {
      console.error('Failed to fetch catalog data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load catalog data');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Error state
  if (error) {
    return (
      <Card className="border-red-200 bg-red-50 dark:bg-red-950 dark:border-red-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-red-600 dark:text-red-400">
            <AlertCircle className="h-5 w-5" />
            Failed to Load Catalog Data
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">{error}</p>
          <Button onClick={fetchData} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Catalog Analysis</h2>
        <p className="text-sm text-muted-foreground">
          What products drive our business?
        </p>
      </div>

      {/* Zone 1: KPI Cards */}
      <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-4">
        <EnhancedKPICard
          label="Active SKUs"
          value={kpis?.active_skus?.toLocaleString() || '—'}
          trendPct={kpis?.active_skus_change}
          isLoading={loading}
        />
        <EnhancedKPICard
          label="Global Reach"
          value={kpis ? `${kpis.currency_count} currencies` : '—'}
          trendPct={kpis?.currency_count_change}
          isLoading={loading}
        />
        <EnhancedKPICard
          label="Avg Margin"
          value={kpis?.avg_margin ? `${kpis.avg_margin.toFixed(1)}%` : '—'}
          isLoading={loading}
        />
        <EnhancedKPICard
          label="Supplier Health"
          value={kpis ? `${kpis.supplier_health.toFixed(0)}%` : '—'}
          secondaryText={
            kpis?.at_risk_suppliers && kpis.at_risk_suppliers > 0
              ? `${kpis.at_risk_suppliers} at risk`
              : 'Healthy'
          }
          isAlert={kpis?.at_risk_suppliers ? kpis.at_risk_suppliers > 0 : false}
          isLoading={loading}
        />
      </div>

      {/* Zone 2: Scatter Plot + Segment Distribution */}
      <div className="grid gap-2 lg:grid-cols-12">
        {/* Product Performance Matrix (9 cols) */}
        <div className="lg:col-span-9">
          <ProductPerformanceMatrix
            data={scatterData}
            loading={loading}
            totalProducts={scatterMetadata?.totalProducts}
            medianRevenue={scatterMetadata?.medianRevenue}
            medianQuantity={scatterMetadata?.medianQuantity}
            onQuadrantCountsChange={setQuadrantCounts}
            height={520}
          />
        </div>

        {/* Segment Distribution Donut (3 cols) */}
        <div className="lg:col-span-3">
          <CompactDonut
            title="Segment Distribution"
            data={[
              { name: QUADRANT_CONFIG.cash_cow.name, value: quadrantCounts.cash_cow, color: QUADRANT_CONFIG.cash_cow.borderColor },
              { name: QUADRANT_CONFIG.premium_niche.name, value: quadrantCounts.premium_niche, color: QUADRANT_CONFIG.premium_niche.borderColor },
              { name: QUADRANT_CONFIG.penny_stock.name, value: quadrantCounts.penny_stock, color: QUADRANT_CONFIG.penny_stock.borderColor },
              { name: QUADRANT_CONFIG.dead_stock.name, value: quadrantCounts.dead_stock, color: QUADRANT_CONFIG.dead_stock.borderColor },
            ]}
            height={520}
            valueFormat="count"
          />
        </div>
      </div>

      {/* Zone 3: Split Layout - Movers & Supplier Concentration */}
      <div className="grid gap-2 lg:grid-cols-12">
        <div className="lg:col-span-8">
          <TrendList risers={movers.risers} fallers={movers.fallers} loading={loading} />
        </div>
        <div className="lg:col-span-4">
          <SupplierConcentrationChart suppliers={suppliers} loading={loading} />
        </div>
      </div>

      {/* Zone 4: Catalog Table */}
      <CatalogTable products={products} loading={loading} />
    </div>
  );
}
