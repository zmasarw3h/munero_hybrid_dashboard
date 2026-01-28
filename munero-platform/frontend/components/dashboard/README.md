# Dashboard Components Library

A collection of 5 enhanced, reusable dashboard components for the Munero AI Dashboard.

## Quick Start

```tsx
import {
  MetricCard,
  DualAxisChart,
  ClientScatter,
  DataTable,
  formatters,
  type ColumnDef
} from '@/components/dashboard';
import { useFilters } from '@/lib/filter-context';
```

---

## 1. MetricCard - Enhanced KPI Display

### Basic Usage
```tsx
<MetricCard
  label="Total Revenue"
  value="AED 1,234,567.89"
  trend={{ value: 12.5, direction: 'up' }}
/>
```

### With Comparison Toggle
```tsx
const { setComparisonMode } = useFilters();

<MetricCard
  label="Total Orders"
  value="15,432"
  trend={{ value: -3.2, direction: 'down' }}
  comparisonLabel="vs last year"
  onComparisonToggle={(mode) => setComparisonMode(mode)}
/>
```

### Handling Missing Data
```tsx
<MetricCard
  label="Cost of Goods"
  value="Not Available"
  trend={null}  // Shows "Data Unavailable" badge
/>
```

### Loading State
```tsx
<MetricCard
  label="Avg Order Value"
  value=""
  isLoading={true}  // Shows skeleton
/>
```

---

## 2. DualAxisChart - Trend Widget with Anomalies

### Basic Usage
```tsx
const trendData = [
  { label: 'Jan', revenue: 45000, orders: 120, is_anomaly: false, percent_change: 5.2 },
  { label: 'Feb', revenue: 52000, orders: 135, is_anomaly: true, percent_change: 15.6 },
  { label: 'Mar', revenue: 48000, orders: 128, is_anomaly: false, percent_change: -7.7 },
];

<DualAxisChart
  data={trendData}
  barMetric="revenue"
  lineMetric="orders"
  barLabel="Revenue (AED)"
  lineLabel="Order Count"
  title="Monthly Performance"
/>
```

### Custom Colors and Threshold
```tsx
<DualAxisChart
  data={trendData}
  barMetric="revenue"
  lineMetric="orders"
  anomalyThreshold={2.5}  // More sensitive detection
  barColor="#8b5cf6"      // Purple
  lineColor="#f59e0b"     // Amber
  anomalyColor="#dc2626"  // Red
/>
```

---

## 3. ClientScatter - Interactive Market Analysis

### Basic Usage
```tsx
const clientData = [
  {
    client_id: 'c1',
    client_name: 'ABC Corp',
    client_country: 'UAE',
    total_orders: 250,
    total_revenue: 125000
  },
  // ...more clients
];

<ClientScatter data={clientData} />
```

### With Click Interaction
```tsx
const { setSelectedClient, selectedClient } = useFilters();

<ClientScatter
  data={clientData}
  onClientClick={(clientId) => setSelectedClient(clientId)}
  highlightedClient={selectedClient}
  title="Top Clients: Performance Matrix"
/>
```

---

## 4. DataTable - Generic Sortable Table

### Basic Product Leaderboard
```tsx
interface Product {
  product_id: string;
  product_name: string;
  total_revenue: number;
  total_orders: number;
  avg_price: number;
}

const columns: ColumnDef<Product>[] = [
  {
    key: 'rank',
    header: '#',
    accessor: (_, idx) => idx + 1,
    align: 'center',
  },
  {
    key: 'name',
    header: 'Product Name',
    accessor: (row) => row.product_name,
    sortable: true,
  },
  {
    key: 'revenue',
    header: 'Total Revenue',
    accessor: (row) => row.total_revenue,
    sortable: true,
    align: 'right',
    format: (value) => formatters.currency(value, 'AED'),
  },
  {
    key: 'orders',
    header: 'Orders',
    accessor: (row) => row.total_orders,
    sortable: true,
    align: 'right',
    format: formatters.number,
  },
];

<DataTable
  columns={columns}
  data={products}
  getRowId={(row) => row.product_id}
/>
```

### With Row Selection
```tsx
const [selectedProduct, setSelectedProduct] = useState<string | null>(null);

<DataTable
  columns={columns}
  data={products}
  onRowClick={(row) => setSelectedProduct(row.product_id)}
  highlightedRowId={selectedProduct}
  getRowId={(row) => row.product_id}
/>
```

### Custom Formatters
```tsx
const columns: ColumnDef<Order>[] = [
  {
    key: 'date',
    header: 'Order Date',
    accessor: (row) => row.order_date,
    format: formatters.date,
  },
  {
    key: 'growth',
    header: 'Growth',
    accessor: (row) => row.growth_pct,
    format: formatters.percentage,
  },
  {
    key: 'status',
    header: 'Status',
    accessor: (row) => row.status,
    format: (value) => formatters.badge(value, {
      'completed': 'green',
      'pending': 'yellow',
      'cancelled': 'red'
    }),
  },
];
```

---

## 5. FilterContext - Global State Management

### Setup (Already Done in layout.tsx)
```tsx
// app/layout.tsx
import { FilterProvider } from '@/lib/filter-context';

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <FilterProvider>
          {children}
        </FilterProvider>
      </body>
    </html>
  );
}
```

### Using in Components
```tsx
import { useFilters } from '@/lib/filter-context';

function MyDashboard() {
  const {
    filters,
    dateRange,
    currency,
    selectedClient,
    comparisonMode,
    setDateRange,
    setCurrency,
    setSelectedClient,
    setComparisonMode,
    resetFilters,
  } = useFilters();

  // Update date range
  const handleDateChange = () => {
    setDateRange('2024-01-01', '2024-12-31');
  };

  // Change currency
  const handleCurrencyChange = () => {
    setCurrency('USD');
  };

  // Select a client (drill-down)
  const handleClientClick = (clientId: string) => {
    setSelectedClient(clientId);
  };

  // Change comparison mode
  const handleComparisonToggle = (mode: 'yoy' | 'prev_period' | 'none') => {
    setComparisonMode(mode);
  };

  // Reset everything
  const handleReset = () => {
    resetFilters();
  };

  return (
    <div>
      {/* Components automatically react to filter changes */}
      <MetricCard onComparisonToggle={handleComparisonToggle} />
      <ClientScatter onClientClick={handleClientClick} highlightedClient={selectedClient} />
    </div>
  );
}
```

---

## Complete Page Example

Here's a complete example of a dashboard page using all components:

```tsx
'use client';

import { useEffect, useState } from 'react';
import { useFilters } from '@/lib/filter-context';
import {
  MetricCard,
  DualAxisChart,
  ClientScatter,
  DataTable,
  KPIGrid,
  formatters,
  type ColumnDef
} from '@/components/dashboard';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function OverviewPage() {
  const {
    filters,
    selectedClient,
    setSelectedClient,
    setComparisonMode,
  } = useFilters();

  const [stats, setStats] = useState<any>(null);
  const [trendData, setTrendData] = useState<any[]>([]);
  const [clientData, setClientData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch data
  useEffect(() => {
    fetchDashboardData();
  }, [filters]);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // Fetch headline stats
      const statsRes = await fetch('/api/dashboard/headline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(filters),
      });
      const statsData = await statsRes.json();
      setStats(statsData);

      // Fetch trend data
      const trendRes = await fetch('/api/dashboard/trend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...filters, group_by: 'month' }),
      });
      const trendData = await trendRes.json();
      setTrendData(trendData);

      // Fetch client breakdown
      const clientRes = await fetch('/api/dashboard/breakdown', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...filters, dimension: 'client' }),
      });
      const clientData = await clientRes.json();
      setClientData(clientData);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Table columns
  const clientColumns: ColumnDef[] = [
    {
      key: 'rank',
      header: '#',
      accessor: (_, idx) => idx + 1,
      align: 'center',
    },
    {
      key: 'name',
      header: 'Client Name',
      accessor: (row) => row.client_name,
      sortable: true,
    },
    {
      key: 'revenue',
      header: 'Revenue',
      accessor: (row) => row.total_revenue,
      sortable: true,
      align: 'right',
      format: (v) => formatters.currency(v, filters.currency),
    },
    {
      key: 'orders',
      header: 'Orders',
      accessor: (row) => row.total_orders,
      sortable: true,
      align: 'right',
      format: formatters.number,
    },
  ];

  return (
    <div className="space-y-6 p-6">
      {/* KPI Cards */}
      <KPIGrid>
        <MetricCard
          label="Total Revenue"
          value={stats?.total_revenue.formatted || '-'}
          trend={{
            value: stats?.total_revenue.trend_pct || 0,
            direction: stats?.total_revenue.trend_direction || 'neutral'
          }}
          onComparisonToggle={setComparisonMode}
          isLoading={loading}
        />
        <MetricCard
          label="Total Orders"
          value={stats?.total_orders.formatted || '-'}
          trend={{
            value: stats?.total_orders.trend_pct || 0,
            direction: stats?.total_orders.trend_direction || 'neutral'
          }}
          isLoading={loading}
        />
        {/* ...more metric cards */}
      </KPIGrid>

      {/* Trend Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Performance Trend</CardTitle>
        </CardHeader>
        <CardContent>
          <DualAxisChart
            data={trendData}
            barMetric="total_revenue"
            lineMetric="total_orders"
            barLabel="Revenue (AED)"
            lineLabel="Orders"
            anomalyThreshold={filters.anomaly_threshold}
          />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Client Scatter */}
        <Card>
          <CardHeader>
            <CardTitle>Client Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <ClientScatter
              data={clientData}
              onClientClick={setSelectedClient}
              highlightedClient={selectedClient}
            />
          </CardContent>
        </Card>

        {/* Client Table */}
        <Card>
          <CardHeader>
            <CardTitle>Top Clients</CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable
              columns={clientColumns}
              data={clientData}
              onRowClick={(row) => setSelectedClient(row.client_id)}
              highlightedRowId={selectedClient}
              getRowId={(row) => row.client_id}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

---

## Component Props Reference

### MetricCard
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| label | string | ✅ | - | KPI label |
| value | string | ✅ | - | Formatted value |
| trend | TrendData \| null | ❌ | undefined | Trend information |
| comparisonLabel | string | ❌ | 'vs previous period' | Comparison text |
| onComparisonToggle | function | ❌ | undefined | Mode change handler |
| isLoading | boolean | ❌ | false | Show skeleton |

### DualAxisChart
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| data | DataPoint[] | ✅ | - | Chart data |
| barMetric | string | ✅ | - | Bar data key |
| lineMetric | string | ✅ | - | Line data key |
| anomalyThreshold | number | ❌ | 3.0 | Z-score threshold |
| title | string | ❌ | undefined | Chart title |
| barLabel | string | ❌ | 'Bar Metric' | Bar label |
| lineLabel | string | ❌ | 'Line Metric' | Line label |
| barColor | string | ❌ | '#3b82f6' | Bar color |
| lineColor | string | ❌ | '#10b981' | Line color |
| anomalyColor | string | ❌ | '#ef4444' | Anomaly color |

### ClientScatter
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| data | ClientData[] | ✅ | - | Client data |
| onClientClick | function | ❌ | undefined | Click handler |
| title | string | ❌ | 'Client Analysis...' | Chart title |
| highlightedClient | string | ❌ | undefined | Client ID to highlight |

### DataTable
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| columns | ColumnDef[] | ✅ | - | Column definitions |
| data | T[] | ✅ | - | Table data |
| onRowClick | function | ❌ | undefined | Row click handler |
| emptyMessage | string | ❌ | 'No data available' | Empty state text |
| highlightedRowId | string | ❌ | undefined | Row ID to highlight |
| getRowId | function | ❌ | undefined | Extract row ID |

---

## Best Practices

### 1. Error Handling
```tsx
const [error, setError] = useState<string | null>(null);

useEffect(() => {
  fetchData().catch(err => {
    setError(err.message);
    console.error('Dashboard error:', err);
  });
}, [filters]);

if (error) {
  return <div className="text-red-600">Error: {error}</div>;
}
```

### 2. Loading States
```tsx
{loading ? (
  <MetricCard label="Revenue" value="" isLoading={true} />
) : (
  <MetricCard label="Revenue" value={stats.revenue.formatted} />
)}
```

### 3. Empty States
```tsx
{data.length === 0 ? (
  <div className="text-center py-12">
    <p>No data available for selected filters</p>
  </div>
) : (
  <DataTable columns={columns} data={data} />
)}
```

### 4. Performance Optimization
```tsx
// Debounce filter updates
const debouncedFilters = useDebounce(filters, 300);

useEffect(() => {
  fetchData(debouncedFilters);
}, [debouncedFilters]);

// Memoize expensive calculations
const sortedData = useMemo(() => {
  return data.sort((a, b) => b.revenue - a.revenue);
}, [data]);
```

---

## Troubleshooting

### Issue: Components not updating on filter change
**Solution:** Ensure FilterProvider wraps your app and you're using `useFilters()` hook.

### Issue: Anomalies not showing in chart
**Solution:** Check that your data includes `is_anomaly: true` flag.

### Issue: Table sorting not working
**Solution:** Ensure columns have `sortable: true` property.

### Issue: TypeScript errors
**Solution:** Import types: `import type { ColumnDef } from '@/components/dashboard'`

---

## Migration from v1 Components

If upgrading from basic components:

```tsx
// Old (basic MetricCard)
<MetricCard label="Revenue" value="$1M" />

// New (enhanced MetricCard)
<MetricCard
  label="Revenue"
  value="$1M"
  trend={{ value: 10, direction: 'up' }}
  onComparisonToggle={(mode) => handleToggle(mode)}
/>
```

---

**Documentation Version:** 1.0.0  
**Last Updated:** December 31, 2025  
**Components Version:** Phase 4 Complete
