'use client';

import { useMemo } from 'react';
import { Package } from 'lucide-react';
import {
  BaseLeaderboard,
  ProductTypeBadge,
  formatCurrency,
  formatGrowth,
  truncateText,
  ColumnDef,
} from '@/components/dashboard/shared';

// Types
export interface ProductRow {
  label: string;
  product_type: 'gift_card' | 'merchandise';
  revenue: number;
  growth_pct: number | null;
  failure_rate: number;
  margin_pct: number | null;
  share_pct: number;
  orders: number;
}

export interface CatalogTableProps {
  products: ProductRow[];
  loading?: boolean;
  onProductClick?: (product: ProductRow) => void;
  selectedProductId?: string | null;
}

// Failure rate indicator component
function FailureRateCell({ rate }: { rate: number }) {
  let color = 'text-green-600';
  if (rate >= 3) {
    color = 'text-red-600';
  } else if (rate >= 1) {
    color = 'text-amber-600';
  }

  return (
    <span
      className={color}
      title="Placeholder data - order status not yet available"
    >
      ● {rate.toFixed(1)}%
    </span>
  );
}

export function CatalogTable({
  products,
  loading = false,
  onProductClick,
  selectedProductId,
}: CatalogTableProps) {
  // Define columns using the shared ColumnDef type
  const columns: ColumnDef<ProductRow>[] = useMemo(() => [
    {
      key: 'label',
      header: 'Product Name',
      accessor: (row) => row.label,
      sortable: true,
      align: 'left',
      width: '30%',
      render: (value) => (
        <span className="truncate block" title={String(value)}>
          {truncateText(String(value), 40)}
        </span>
      ),
    },
    {
      key: 'product_type',
      header: 'Type',
      accessor: (row) => row.product_type,
      sortable: true,
      align: 'left',
      width: '12%',
      render: (value) => <ProductTypeBadge type={value as string} />,
    },
    {
      key: 'revenue',
      header: 'Revenue',
      accessor: (row) => row.revenue,
      sortable: true,
      align: 'right',
      width: '15%',
      render: (value) => formatCurrency(value as number),
    },
    {
      key: 'growth_pct',
      header: 'Growth %',
      accessor: (row) => row.growth_pct,
      sortable: true,
      align: 'right',
      width: '12%',
      render: (value) => {
        const growth = formatGrowth(value as number | null);
        return <span className={growth.color}>{growth.text}</span>;
      },
    },
    {
      key: 'failure_rate',
      header: 'Failure Rate',
      accessor: (row) => row.failure_rate,
      sortable: true,
      align: 'right',
      width: '12%',
      render: (value) => <FailureRateCell rate={value as number} />,
    },
    {
      key: 'margin_pct',
      header: 'Margin %',
      accessor: (row) => row.margin_pct,
      sortable: true,
      align: 'right',
      width: '12%',
      render: (value) => {
        const margin = value as number | null;
        if (margin === null || margin === 0) {
          return <span className="text-gray-400">N/A</span>;
        }
        return <span className="font-medium">{margin.toFixed(1)}%</span>;
      },
    },
  ], []);

  return (
    <BaseLeaderboard<ProductRow>
      title="Product Catalog"
      description="Failure rates are placeholder data for demonstration"
      columns={columns}
      data={products}
      loading={loading}
      loadingRows={5}
      getRowId={(row) => row.label}
      onRowClick={onProductClick}
      selectedRowId={selectedProductId}
      emptyMessage="No products found. Adjust your filters or date range."
      emptyIcon={<Package className="h-10 w-10" />}
      defaultSort={{ key: 'revenue', direction: 'desc' }}
    />
  );
}

export default CatalogTable;
