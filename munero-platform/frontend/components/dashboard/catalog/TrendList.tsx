'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { TrendingUp, TrendingDown } from 'lucide-react';

// Types
export interface TrendItem {
  product_name: string;
  growth_pct: number;
  current_revenue: number;
  prior_revenue: number;
}

export interface TrendListProps {
  risers: TrendItem[];
  fallers: TrendItem[];
  loading?: boolean;
  usePlaceholder?: boolean; // Show placeholder data when no real data
}

// Placeholder data for demonstration
const PLACEHOLDER_RISERS: TrendItem[] = [
  { product_name: 'Amazon Gift Card $100', growth_pct: 156.2, current_revenue: 45000, prior_revenue: 17560 },
  { product_name: 'Netflix Premium Subscription', growth_pct: 89.5, current_revenue: 32000, prior_revenue: 16880 },
  { product_name: 'Apple iTunes $50 Card', growth_pct: 67.3, current_revenue: 28500, prior_revenue: 17030 },
  { product_name: 'Spotify Annual Membership', growth_pct: 45.8, current_revenue: 19200, prior_revenue: 13170 },
  { product_name: 'PlayStation Store $25', growth_pct: 34.2, current_revenue: 15600, prior_revenue: 11625 },
];

const PLACEHOLDER_FALLERS: TrendItem[] = [
  { product_name: 'Google Play $10 Card', growth_pct: -42.5, current_revenue: 8500, prior_revenue: 14780 },
  { product_name: 'Xbox Game Pass 1 Month', growth_pct: -28.7, current_revenue: 12300, prior_revenue: 17250 },
  { product_name: 'Steam Wallet $20', growth_pct: -19.3, current_revenue: 14200, prior_revenue: 17595 },
];

// Truncate product name to 30 characters
const truncateName = (name: string, maxLength: number = 30): string => {
  return name.length > maxLength ? name.substring(0, maxLength) + '...' : name;
};

export function TrendList({ risers, fallers, loading = false, usePlaceholder = true }: TrendListProps) {
  // Determine if we should show placeholder data
  const hasNoData = risers.length === 0 && fallers.length === 0;
  const showPlaceholder = usePlaceholder && hasNoData && !loading;

  // Use placeholder data if no real data available
  const displayRisers = showPlaceholder ? PLACEHOLDER_RISERS : risers;
  const displayFallers = showPlaceholder ? PLACEHOLDER_FALLERS : fallers;

  // Loading state
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Movers & Shakers</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-6 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Movers & Shakers</CardTitle>
        <CardDescription className="text-xs">
          Top products by revenue growth vs prior period
          {showPlaceholder && (
            <span className="text-amber-600 ml-1">• Sample data</span>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Risers Section */}
        <div>
          <h3 className="text-xs font-semibold text-green-600 mb-2 flex items-center gap-1">
            <TrendingUp className="h-3 w-3" />
            TOP RISERS
          </h3>
          <div className="space-y-2">
            {displayRisers.length === 0 ? (
              <p className="text-sm text-gray-400 italic">No products with positive growth</p>
            ) : (
              displayRisers.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between text-sm">
                  <span className="text-gray-700 truncate flex-1" title={item.product_name}>
                    <span className="text-gray-400 mr-1">{idx + 1}.</span>
                    {truncateName(item.product_name)}
                  </span>
                  <span className="text-green-600 font-semibold ml-2 whitespace-nowrap">
                    ↑ {item.growth_pct.toFixed(1)}%
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Divider */}
        <Separator />

        {/* Fallers Section */}
        <div>
          <h3 className="text-xs font-semibold text-red-600 mb-2 flex items-center gap-1">
            <TrendingDown className="h-3 w-3" />
            TOP FALLERS
          </h3>
          <div className="space-y-2">
            {displayFallers.length === 0 ? (
              <p className="text-sm text-gray-400 italic">No products with negative growth</p>
            ) : (
              displayFallers.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between text-sm">
                  <span className="text-gray-700 truncate flex-1" title={item.product_name}>
                    <span className="text-gray-400 mr-1">{idx + 1}.</span>
                    {truncateName(item.product_name)}
                  </span>
                  <span className="text-red-600 font-semibold ml-2 whitespace-nowrap">
                    ↓ {Math.abs(item.growth_pct).toFixed(1)}%
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default TrendList;
