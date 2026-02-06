# Catalog Analysis Page Design Specification
## "The Product Engine"

**Version:** 1.1 (Revised)
**Created:** January 6, 2026
**Updated:** January 7, 2026
**Status:** Ready for Implementation

---

## Overview

The Catalog Analysis page answers the question: **"What products drive our business?"**

This page provides deep insights into product performance, brand analysis, and supplier concentration. It helps identify top-performing products, margin opportunities, and supply chain risks.

---

## Page Layout

### Desktop View (≥1280px)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  Header: Catalog Analysis                                                       │
│  "What products drive our business?"                                            │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ZONE 1: Supply Chain KPIs (4 cards in grid)                                    │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐    │
│  │ Active SKUs    │ │ Global Reach   │ │ Avg Margin     │ │ Supplier       │    │
│  │ 1,247          │ │ 12 currencies  │ │ 22.5%          │ │ Health: 85%    │    │
│  │ ↑12% vs prior  │ │ ↑2 new         │ │ ↓1.2pts        │ │ ⚠️ 1 at risk   │    │
│  └────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘    │
│                                                                                  │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ZONE 2: Product Performance Matrix (full width, 500px height)                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                          │   │
│  │                    Product Performance Matrix                            │   │
│  │                    (Scatter Plot with Quadrants)                         │   │
│  │                                                                          │   │
│  │    Revenue (AED)                                                         │   │
│  │        ▲                                                                 │   │
│  │        │   ┌────────────────────┬────────────────────┐                   │   │
│  │        │   │  PREMIUM NICHE     │   CASH COWS        │                   │   │
│  │        │   │  High $, Low Qty   │   High $, High Qty │                   │   │
│  │   1M   │   │     ● ●            │     ● ● ● ●        │                   │   │
│  │        │   │                    │                    │                   │   │
│  │   500K │   ├────────────────────┼────────────────────┤ Median Revenue    │   │
│  │        │   │   DEAD STOCK       │  PENNY STOCKS      │                   │   │
│  │        │   │   Low $, Low Qty   │   Low $, High Qty  │                   │   │
│  │   100K │   │     ●              │     ● ● ●          │                   │   │
│  │        │   └────────────────────┴────────────────────┘                   │   │
│  │        └────────────┬──────────────────────────┬──────────────► Quantity │   │
│  │                   100         Median         500                         │   │
│  │                              Quantity                                    │   │
│  │                                                                          │   │
│  │  Legend: ● Gift Card (Blue)  ● Merchandise (Purple)                     │   │
│  │  Note: Showing top 500 products by revenue (870 total)                  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ZONE 3: Split View (8 columns + 4 columns)                                     │
│  ┌────────────────────────────────────┐ ┌────────────────────────────────────┐  │
│  │  Movers & Shakers                  │ │  Supplier Concentration            │  │
│  │  ┌──────────────────────────────┐  │ │  ┌──────────────────────────────┐  │  │
│  │  │  📈 TOP RISERS               │  │ │  │ Supplier A  ████████████ 35% │  │  │
│  │  │  ───────────────────────────│  │ │  │ Supplier B  ██████████ 28%   │  │  │
│  │  │  1. iTunes $100      +45%   │  │ │  │ Supplier C  ████████ 20%     │  │  │
│  │  │  2. Google Play $50  +32%   │  │ │  │ Supplier D  ████ 10%         │  │  │
│  │  │  3. Netflix Card     +28%   │  │ │  │ Others      ██ 7%            │  │  │
│  │  │  4. Amazon Gift      +25%   │  │ │  │             ┊                │  │  │
│  │  │  5. Spotify Premium  +22%   │  │ │  │             ┊ 30% threshold  │  │  │
│  │  ├──────────────────────────────┤  │ │  └──────────────────────────────┘  │  │
��  │  │  📉 TOP FALLERS              │  │ │                                    │  │
│  │  │  ───────────────────────────│  │ │  ⚠️ Supplier A exceeds 30%        │  │
│  │  │  1. Steam Card       -38%   │  │ │  Consider diversifying supply     │  │
│  │  │  2. Xbox Gift        -25%   │  │ │  chain to reduce risk.            │  │
│  │  │  3. PSN Voucher      -18%   │  │ │                                    │  │
│  │  │  4. Roblox Card      -15%   │  │ │                                    │  │
│  │  │  5. Twitch Sub       -12%   │  │ │                                    │  │
│  │  └──────────────────────────────┘  │ │                                    │  │
│  └────────────────────────────────────┘ └────────────────────────────────────┘  │
│                                                                                  │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ZONE 4: Catalog Table (full width, scrollable, sortable)                       │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │ 🔍 [Search products...]                            [⬇️ Export CSV]       │   │
│  ├──────────────┬──────────┬───────────┬─────────┬────────────┬───────────┤   │
│  │ Product Name │   Type   │  Revenue  │ Growth  │ Failure    │  Margin   │   │
│  │              │          │   (AED)   │   %     │  Rate      │    %      │   │
│  ├──────────────┼──────────┼───────────┼─────────┼────────────┼───────────┤   │
│  │ iTunes $100  │ Gift Card│ 125,340   │ ↑ 45%   │ 🟢 0.3%    │ 22.5%     │   │
│  │ Google Play  │ Gift Card│  98,200   │ ↑ 32%   │ 🟢 0.5%    │ 18.2%     │   │
│  │ Netflix Card │ Gift Card│  87,100   │ ↑ 28%   │ 🟢 0.2%    │ 25.1%     │   │
│  │ Steam Wallet │ Gift Card│  45,600   │ ↓ 38%   │ 🟡 2.1%    │ 15.8%     │   │
│  │ Xbox Game    │ Merchandise│ 32,400  │ ↓ 25%   │ 🟡 1.8%    │ 12.3%     │   │
│  │ ...          │          │           │         │            │           │   │
│  ├──────────────┴──────────┴───────────┴─────────┴────────────┴───────────┤   │
│  │                         Showing 1-20 of 870 products                    │   │
│  │                    [◀ Previous]  [1] 2 3 ... 44  [Next ▶]              │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Tablet View (768-1279px)

```
┌────────────────────────────────────────┐
│  Header: Catalog Analysis              │
├────────────────────────────────────────┤
│  ZONE 1: KPIs (2x2 grid)               │
│  ┌──────────────┐ ┌──────────────┐     │
│  │ Active SKUs  │ │ Global Reach │     │
│  └──────────────┘ └──────────────┘     │
│  ┌──────────────┐ ┌──────────────┐     │
│  │ Avg Margin   │ │ Supplier     │     │
│  └──────────────┘ └──────────────┘     │
├────────────────────────────────────────┤
│  ZONE 2: Scatter (full width, 400px)  │
│  ┌──────────────────────────────────┐  │
│  │  Product Performance Matrix      │  │
│  └──────────────────────────────────┘  │
├────────────────────────────────────────┤
│  ZONE 3: Stacked (full width)         │
│  ┌──────────────────────────────────┐  │
│  │  Movers & Shakers                │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │  Supplier Concentration          │  │
│  └──────────────────────────────────┘  │
├────────────────────────────────────────┤
│  ZONE 4: Table (horizontal scroll)    │
│  ┌──────────────────────────────────┐  │
│  │  [Scrollable table]              │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

### Mobile View (<768px)

```
┌──────────────────────┐
│  Catalog Analysis    │
├──────────────────────┤
│  ZONE 1: Stacked KPIs│
│  ┌──────────────────┐│
│  │ Active SKUs      ││
│  └──────────────────┘│
│  ┌──────────────────┐│
│  │ Global Reach     ││
│  └──────────────────┘│
│  ┌──────────────────┐│
│  │ Avg Margin       ││
│  └──────────────────┘│
│  ┌──────────────────┐│
│  │ Supplier Health  ││
│  └──────────────────┘│
├──────────────────────┤
│  ZONE 2: Simplified  │
│  (Show top 20 bar    │
│  chart instead of    │
│  scatter plot)       │
├──────────────────────┤
│  ZONE 3: Stacked     │
│  ┌──────────────────┐│
│  │ Movers & Shakers ││
│  └──────────────────┘│
│  ┌──────────────────┐│
│  │ Suppliers        ││
│  └──────────────────┘│
├──────────────────────┤
│  ZONE 4: Compact     │
│  (Card-based layout, │
│  not table)          │
└──────────────────────┘
```

---

## Zone 1: Supply Chain KPIs

### Layout
4 KPI cards in a responsive grid:
- Desktop (≥1280px): 4 columns
- Tablet (768-1279px): 2×2 grid
- Mobile (<768px): Stacked (1 column)

### KPI Definitions

| KPI | Calculation | Format | Icon | Data Source |
|-----|-------------|--------|------|-------------|
| **Active SKUs** | `COUNT(DISTINCT product_sku) WHERE quantity > 0` | Number with commas | 📦 Package | fact_orders |
| **Global Reach** | `COUNT(DISTINCT currency)` | "X currencies" | 🌍 Globe | fact_orders |
| **Avg Margin** | `AVG((Revenue - COGS) / Revenue * 100)` | Percentage | 💰 DollarSign | fact_orders |
| **Supplier Health** | `% of suppliers with <30% concentration` | Percentage + badge | 🏭 Factory | fact_orders + calc |

### Comparison Badges
Each card shows comparison vs **prior period** (defined as same number of days immediately before current filter range):
- **Green badge with ↑**: Positive change (e.g., ↑12%)
- **Red badge with ↓**: Negative change (e.g., ↓5%)
- **Gray badge**: No change (—)

### Margin Fallback Logic

When COGS data is unavailable or zero:

```
IF cogs IS NULL OR cogs = 0:
    Display: "X% Contribution" (blue/gray badge)
    Tooltip: "Cost data unavailable. Shows revenue contribution to total."
    Calculation: (Item Revenue / Total Revenue) * 100
ELSE:
    Display: "X% Margin" (green badge)
    Calculation: (Revenue - COGS) / Revenue * 100
```

**Visual Example:**
```
┌─────────────────────────┐     ┌─────────────────────────┐
│ Avg Margin              │     │ Avg Contribution        │
│ 22.5%                   │     │ 15.2%                   │
│ 🟢 Healthy margin       │     │ ℹ️ Cost data missing    │
└─────────────────────────┘     └─────────────────────────┘
```

### Implementation Notes
- Use **Lucide React icons** (not emojis) for consistency with existing dashboard
- KPI cards use `EnhancedKPICard` component
- Loading state: Show skeleton placeholders with pulse animation
- Error state: Show "—" with retry button in card footer

---

## Zone 2: Product Performance Matrix

### Component
`ProductPerformanceMatrix.tsx` - Scatter plot with strategic quadrants

### Chart Configuration

| Property | Value | Notes |
|----------|-------|-------|
| **X-Axis** | Quantity Sold (volume) | Total units sold across all orders |
| **Y-Axis** | Revenue (AED) | Total revenue in AED |
| **Dot Size** | Fixed (40px radius) | Consistent size for readability |
| **Dot Color** | By product type | Blue (gift_card), Purple (merchandise) |
| **Data Limit** | Top 500 products | **Performance optimization** - prevents lag |
| **Chart Height** | 500px desktop, 400px tablet | Responsive |
| **Animation** | Disabled (`isAnimationActive={false}`) | Performance optimization |

### Quadrant Definitions

| Quadrant | Position | Criteria | Meaning | Strategy |
|----------|----------|----------|---------|----------|
| **Cash Cows** | Top-Right | Revenue > median AND Quantity > median | High Revenue, High Volume | Protect & optimize |
| **Premium Niche** | Top-Left | Revenue > median AND Quantity < median | High Revenue, Low Volume | Expand distribution |
| **Penny Stocks** | Bottom-Right | Revenue < median AND Quantity > median | Low Revenue, High Volume | Increase pricing |
| **Dead Stock** | Bottom-Left | Revenue < median AND Quantity < median | Low Revenue, Low Volume | Consider discontinuing |

### Quadrant Calculation
```python
median_revenue = df['revenue'].median()
median_quantity = df['quantity'].median()

def assign_quadrant(revenue, quantity):
    if revenue > median_revenue:
        return 'cash_cow' if quantity > median_quantity else 'premium_niche'
    else:
        return 'penny_stock' if quantity > median_quantity else 'dead_stock'
```

### Interactions

| Action | Behavior |
|--------|----------|
| **Hover** | Tooltip shows: Product name, Revenue (formatted), Quantity, Margin %, Type |
| **Click** | Updates FilterContext with selected product *(v2 feature)* |
| **Quadrant Label Hover** | Highlights all dots in that quadrant |

### Visual Style
```tsx
const QUADRANT_COLORS = {
  'cash_cow': 'rgba(34, 197, 94, 0.1)',       // Green tint
  'premium_niche': 'rgba(99, 102, 241, 0.1)', // Indigo tint
  'penny_stock': 'rgba(251, 191, 36, 0.1)',   // Amber tint
  'dead_stock': 'rgba(239, 68, 68, 0.1)'      // Red tint
};

const PRODUCT_TYPE_COLORS = {
  'gift_card': '#3b82f6',    // Blue
  'merchandise': '#8b5cf6'   // Purple
};
```

### Performance Optimizations
1. **Limit to 500 products**: Backend enforces `.nlargest(500, 'total_revenue')`
2. **No animation**: `isAnimationActive={false}` on Scatter component
3. **Integer domains**: `Math.ceil()` applied to domain values to avoid duplicate keys
4. **Limited tick count**: `tickCount={6}` on both axes
5. **Log scale opt-out**: Use linear scales by default (log scale causes duplicate key errors)

### Data Limit Indicator
Display below chart:
```
ℹ️ Showing top 500 of 870 products by revenue (performance optimized)
```

---

## Zone 3A: TrendList (Movers & Shakers)

### Component
`TrendList.tsx` - Compact list showing top risers and fallers

### Layout
Two stacked sections within a single card:

```
┌─────────────────────────────┐
│  📈 TOP RISERS              │
│  ───────────────────────── │
│  1. iTunes $100      +45%   │
│  2. Google Play $50  +32%   │
│  3. Netflix Card     +28%   │
│  4. Amazon Gift      +25%   │
│  5. Spotify Premium  +22%   │
├─────────────────────────────┤
│  📉 TOP FALLERS             │
│  ───────────────────────── │
│  1. Steam Card       -38%   │
│  2. Xbox Gift        -25%   │
│  3. PSN Voucher      -18%   │
│  4. Roblox Card      -15%   │
│  5. Twitch Sub       -12%   │
└─────────────────────────────┘
```

### Data Source

**Period Comparison Logic**:
```python
# Prior period = same number of days immediately before current filter range
date_range_days = (filters.end_date - filters.start_date).days
prior_start = filters.start_date - timedelta(days=date_range_days)
prior_end = filters.start_date - timedelta(days=1)
```

**SQL Query**:
```sql
WITH current_period AS (
    SELECT product_name, SUM(order_price_in_aed) as revenue
    FROM fact_orders
    WHERE order_date BETWEEN :current_start AND :current_end
      AND {filters}
    GROUP BY product_name
),
prior_period AS (
    SELECT product_name, SUM(order_price_in_aed) as revenue
    FROM fact_orders
    WHERE order_date BETWEEN :prior_start AND :prior_end
      AND {filters}
    GROUP BY product_name
)
SELECT
    c.product_name,
    c.revenue as current_revenue,
    COALESCE(p.revenue, 0) as prior_revenue,
    ((c.revenue - COALESCE(p.revenue, 0)) / NULLIF(p.revenue, 0) * 100) as growth_pct
FROM current_period c
LEFT JOIN prior_period p ON c.product_name = p.product_name
WHERE p.revenue > 0  -- Only products that existed in prior period
ORDER BY growth_pct DESC  -- For risers
LIMIT 5;

-- Same query with ORDER BY growth_pct ASC for fallers
```

### Styling

| Element | Style |
|---------|-------|
| **Section header** | Text-xs, font-semibold, green (risers) / red (fallers) |
| **Riser badge** | Text-green-600, ↑ arrow, font-semibold |
| **Faller badge** | Text-red-600, ↓ arrow, font-semibold |
| **Product name** | Text-gray-700, truncate to 30 chars |
| **Percentage** | Bold, right-aligned |
| **Rank number** | Text-gray-500, small |

### Edge Cases
- **New products** (no prior period data): Excluded from movers list
- **Zero prior revenue**: Excluded (avoid infinity % growth)
- **Less than 5 products**: Show whatever is available, don't error

---

## Zone 3B: Supplier Concentration Chart

### Component
`SupplierConcentrationChart.tsx` - Horizontal bar chart with risk threshold

### Chart Configuration

| Property | Value |
|----------|-------|
| **Type** | Horizontal Bar Chart (Recharts BarChart with layout="vertical") |
| **Sort** | Descending by revenue share (%) |
| **Bars Shown** | Top 5 suppliers + "Others" (if revenue > 0) |
| **Reference Line** | Vertical dashed line at 30% (x={30}) |
| **Height** | 280px |
| **X-Axis** | 0-100% range |
| **Y-Axis** | Supplier names (truncate to 20 chars) |

### Risk Thresholds

| Concentration | Risk Level | Bar Color | Visual |
|---------------|------------|-----------|--------|
| <20% | Healthy | Green (#22c55e) | 🟢 |
| 20-30% | Moderate | Amber (#f59e0b) | 🟡 |
| >30% | High Risk | Red (#ef4444) | 🔴 |

### Warning Display
If any supplier exceeds 30%:
```tsx
<Alert variant="warning">
  <AlertCircle className="h-4 w-4" />
  <AlertTitle>⚠️ High Concentration Risk</AlertTitle>
  <AlertDescription>
    {supplier_name} exceeds 30% threshold ({share_pct}%).
    Consider diversifying supply chain to reduce risk.
  </AlertDescription>
</Alert>
```

### Interactions

| Action | Behavior |
|--------|----------|
| **Hover** | Tooltip: Supplier name (full), Revenue (AED), % of total, Order count |
| **Click** | *(v2 feature)* Filters dashboard to that supplier |

### Data Source
**Existing Endpoint**: `POST /api/dashboard/breakdown?dimension=supplier`

**Client-side Risk Calculation**:
```tsx
function getRiskLevel(sharePct: number): 'healthy' | 'moderate' | 'high' {
  if (sharePct > 30) return 'high';
  if (sharePct > 20) return 'moderate';
  return 'healthy';
}

function getRiskColor(sharePct: number): string {
  if (sharePct > 30) return '#ef4444'; // Red
  if (sharePct > 20) return '#f59e0b'; // Amber
  return '#22c55e'; // Green
}
```

---

## Zone 4: CatalogTable

### Component
`CatalogTable.tsx` using `DataTable` base component

### Column Definitions

| Column | Data Key | Format | Sortable | Width | Default Sort | Priority |
|--------|----------|--------|----------|-------|--------------|----------|
| **Product Name** | `label` | Text (truncate 40 chars) | Yes | 30% | — | MVP |
| **Type** | `product_type` | Badge | Yes | 12% | — | MVP |
| **Revenue** | `revenue` | Currency (AED) | Yes | 15% | ✓ DESC | MVP |
| **Growth %** | `growth_pct` | Percentage with ↑/↓ | Yes | 12% | — | MVP |
| **Failure Rate** | `failure_rate` | Percentage with color | Yes | 12% | — | MVP |
| **Margin %** | `margin_pct` | Percentage | Yes | 12% | — | MVP |

### Column Details

#### Product Name
- Display full name (truncate with `...` if >40 chars)
- Tooltip shows full name on hover
- *(v2)* Clickable `<EntityLink>` that filters to product

#### Type Badge
```tsx
const TYPE_BADGES = {
  'gift_card': {
    label: 'Gift Card',
    className: 'bg-blue-100 text-blue-800 border-blue-200'
  },
  'merchandise': {
    label: 'Merchandise',
    className: 'bg-purple-100 text-purple-800 border-purple-200'
  }
};
```

**Note**: Only 2 types exist in database (not 4 as in original spec)

#### Growth %
```tsx
function renderGrowth(growthPct: number | null) {
  if (growthPct === null) return <span className="text-gray-400">N/A</span>;

  const isPositive = growthPct >= 0;
  return (
    <span className={isPositive ? 'text-green-600' : 'text-red-600'}>
      {isPositive ? '↑' : '↓'} {Math.abs(growthPct).toFixed(1)}%
    </span>
  );
}
```

#### Failure Rate ⚠️ PLACEHOLDER DATA

**Note**: Order status field does not exist in database. Using **deterministic mock data** until real data is available.

```python
# Backend: Generate deterministic mock data based on product name hash
import hashlib

def mock_failure_rate(product_name: str) -> float:
    """Returns a consistent failure rate (0.1-3.0%) for the same product name."""
    hash_val = int(hashlib.md5(product_name.encode()).hexdigest(), 16)
    return 0.1 + (hash_val % 30) / 10.0  # Range: 0.1% to 3.0%
```

**Frontend Rendering**:
```tsx
function renderFailureRate(rate: number) {
  let color = 'text-green-600';  // <1%
  let icon = '🟢';

  if (rate >= 3) {
    color = 'text-red-600';    // >3%
    icon = '🔴';
  } else if (rate >= 1) {
    color = 'text-amber-600';  // 1-3%
    icon = '🟡';
  }

  return (
    <span className={color} title="Placeholder data - order status not yet available">
      {icon} {rate.toFixed(1)}%
    </span>
  );
}
```

**User Communication**:
- Add tooltip: "Placeholder data - order status tracking coming soon"
- Display notice above table: "ℹ️ Failure rates are simulated for demonstration purposes"

#### Margin/Contrib %
```tsx
function renderMargin(marginPct: number | null, contribution: number | null) {
  if (marginPct !== null && marginPct !== 0) {
    return <span className="font-medium">{marginPct.toFixed(1)}%</span>;
  } else if (contribution !== null) {
    return (
      <span className="text-gray-500" title="Margin unavailable - showing contribution">
        {contribution.toFixed(1)}%*
      </span>
    );
  }
  return <span className="text-gray-400">N/A</span>;
}
```

### Table Features

| Feature | Description | Priority | Implementation |
|---------|-------------|----------|----------------|
| **Sorting** | Click column header to sort | MVP | DataTable built-in |
| **Pagination** | 20 rows per page | MVP | DataTable built-in |
| **Search** | Filter by product name | MVP | Local filter in DataTable |
| **Quick Filters** | Type dropdown (gift_card/merchandise) | MVP | Dropdown above table |
| **Export CSV** | Download visible data | v2 | Button in header |
| **Row Selection** | Multi-select for bulk actions | v2 | Checkbox column |

### Empty State
If no products match filters:
```
┌─────────────────────────────────────┐
│          📦 No Products Found       │
│                                     │
│  Adjust your filters or date range  │
│                                     │
│         [Reset Filters]             │
└─────────────────────────────────────┘
```

**Note**: Simplified from original 8-line empty state for better UX

---

## Data Requirements

### API Endpoints

| Endpoint | Purpose | Status | Parameters |
|----------|---------|--------|------------|
| `POST /api/dashboard/catalog/kpis` | Zone 1 KPIs | **NEW** | filters, comparison_period |
| `POST /api/dashboard/catalog/scatter` | Zone 2 Matrix | **NEW** | filters, limit=500 |
| `POST /api/dashboard/catalog/movers` | Zone 3A Movers | **NEW** | filters, top_n=5 |
| `POST /api/dashboard/breakdown?dimension=supplier` | Zone 3B Suppliers | **EXISTS** | filters, limit=5 |
| `POST /api/dashboard/breakdown?dimension=product&include_growth=true` | Zone 4 Table | **ENHANCE** | filters, include_growth |

### Data Models

```typescript
// Zone 1 KPI Response
interface CatalogKPIs {
  active_skus: number;
  active_skus_change: number | null;
  currency_count: number;
  currency_count_change: number | null;
  avg_margin: number | null;
  avg_contribution: number | null;  // Fallback
  supplier_health: number;           // Percentage healthy
  at_risk_suppliers: number;
}

// Zone 2 Scatter Point
interface ProductScatterPoint {
  product_name: string;
  product_type: 'gift_card' | 'merchandise';  // Only 2 types
  quantity: number;
  revenue: number;
  margin: number | null;
  quadrant: 'cash_cow' | 'premium_niche' | 'penny_stock' | 'dead_stock';
}

interface ProductScatterResponse {
  data: ProductScatterPoint[];
  median_revenue: number;
  median_quantity: number;
  total_products: number;  // Total before limiting to 500
}

// Zone 3A Trend Item
interface TrendItem {
  product_name: string;
  growth_pct: number;
  current_revenue: number;
  prior_revenue: number;
}

interface ProductMoversResponse {
  risers: TrendItem[];   // Top 5
  fallers: TrendItem[];  // Top 5
}

// Zone 3B Supplier Item (existing)
interface SupplierConcentration {
  label: string;          // Supplier name
  revenue: number;
  share_pct: number;
  orders: number;
}

// Zone 4 Table Row (enhanced)
interface CatalogRow {
  label: string;               // Product name
  product_type: 'gift_card' | 'merchandise';
  revenue: number;
  growth_pct: number | null;
  failure_rate: number;        // ⚠️ MOCK DATA
  margin_pct: number | null;
  contribution: number | null; // Fallback
  share_pct: number;
}
```

---

## Component File Structure

```
frontend/
├── app/dashboard/catalog/
│   └── page.tsx                               # Main page (NEW)
├── components/dashboard/catalog/
│   ├── ProductPerformanceMatrix.tsx           # Zone 2 scatter (NEW)
│   ├── TrendList.tsx                          # Zone 3A movers (NEW)
│   ├── SupplierConcentrationChart.tsx         # Zone 3B chart (NEW)
│   └── CatalogTable.tsx                       # Zone 4 table (NEW)
├── lib/
│   ├── api-client.ts                          # Add 3 new methods
│   └── formatters.ts                          # Reuse existing
└── types/
    └── dashboard.ts                           # Add new interfaces

backend/
└── app/api/
    └── dashboard.py                           # Add 3 new endpoints
```

---

## Responsive Behavior

| Breakpoint | Layout Changes |
|------------|----------------|
| **Desktop (≥1280px)** | Full 4-column KPIs, 8+4 Zone 3 split, 500px scatter height |
| **Tablet (768-1279px)** | 2×2 KPI grid, Zone 3 stacks vertically, 400px scatter height |
| **Mobile (<768px)** | 1-column KPIs, all zones stack, table horizontal scroll, **scatter replaced with bar chart** |

### Zone 3 Responsive Implementation
```tsx
// Desktop: side by side
<div className="hidden lg:grid lg:grid-cols-12 gap-2">
  <div className="col-span-8"><TrendList /></div>
  <div className="col-span-4"><SupplierConcentrationChart /></div>
</div>

// Mobile: stacked
<div className="flex flex-col gap-2 lg:hidden">
  <TrendList />
  <SupplierConcentrationChart />
</div>
```

### Mobile Optimization for Zone 2
**Problem**: Scatter plot is unusable on mobile with 500 tiny dots

**Solution**: Replace with Top 20 Products bar chart
```tsx
{isMobile ? (
  <TopProductsBarChart products={scatterData.slice(0, 20)} />
) : (
  <ProductPerformanceMatrix data={scatterData} />
)}
```

---

## Interactions & Cross-Page Navigation

### EntityLink Behavior (v2 Feature)

| Entity Clicked | Action |
|----------------|--------|
| Product Name | Update FilterContext with product filter, stay on page |
| Brand Name | Navigate to Catalog, filter to brand |
| Supplier Name | Update FilterContext with supplier filter, stay on page |

### Filter Sync
All filters sync with global FilterContext:
- Date range from FilterBar → All API calls
- Currency from FilterBar → Revenue display
- Product type from local dropdown → Table filter only

---

## Loading & Error States

### Loading States
```tsx
// KPI Cards
<EnhancedKPICard
  label="Active SKUs"
  value="—"
  isLoading={true}  // Shows skeleton pulse
/>

// Scatter Plot
<div className="h-[500px] flex items-center justify-center">
  <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
  <span className="ml-2 text-gray-500">Loading products...</span>
</div>

// Table
<div className="animate-pulse space-y-2">
  {[...Array(5)].map((_, i) => (
    <div key={i} className="h-12 bg-gray-100 rounded" />
  ))}
</div>
```

### Error States
```tsx
<Card className="border-red-200 bg-red-50">
  <CardHeader>
    <CardTitle className="flex items-center gap-2 text-red-600">
      <AlertCircle className="h-5 w-5" />
      Failed to Load Data
    </CardTitle>
  </CardHeader>
  <CardContent>
    <p className="text-sm text-gray-600 mb-3">{error.message}</p>
    <Button onClick={retry} variant="outline" size="sm">
      <RefreshCw className="h-4 w-4 mr-2" />
      Retry
    </Button>
  </CardContent>
</Card>
```

---

## Performance Optimizations

### Applied Optimizations

1. **Scatter Plot Limit**: Top 500 products by revenue (prevents 870 SVG elements)
2. **Animation Disabled**: `isAnimationActive={false}` on Scatter component
3. **Integer Domains**: `Math.ceil()` applied to avoid duplicate key errors
4. **Limited Ticks**: `tickCount={6}` on both XAxis and YAxis
5. **Parallel API Calls**: All Zone data fetched in `Promise.all()`
6. **Endpoint Reuse**: Supplier concentration uses existing `/breakdown` endpoint
7. **Deterministic Mocks**: Failure rate hash-based (no random() causing re-renders)

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Initial Load** | <5 seconds | Time to interactive (TTI) |
| **Scatter Render** | <1 second | Paint time for 500 dots |
| **Table Sort** | <200ms | Click to re-render |
| **Tooltip Hover** | <50ms | Hover to tooltip display |
| **API Response** | <2 seconds | All 5 endpoints in parallel |

---

## Implementation Checklist

### Backend
- [ ] Add `POST /api/dashboard/catalog/kpis` endpoint
- [ ] Add `POST /api/dashboard/catalog/scatter` endpoint with 500 limit
- [ ] Add `POST /api/dashboard/catalog/movers` endpoint
- [ ] Enhance `POST /api/dashboard/breakdown` with `include_growth` parameter
- [ ] Implement deterministic mock failure rate function
- [ ] Add period comparison logic (prior period calculation)
- [ ] Implement margin fallback logic (COGS check)
- [ ] Test all endpoints with Postman/curl

### Frontend Components
- [ ] Create `ProductPerformanceMatrix.tsx` (adapt from ClientSegmentationMatrix)
- [ ] Create `TrendList.tsx` (new compact list component)
- [ ] Create `SupplierConcentrationChart.tsx` (horizontal bar chart)
- [ ] Create `CatalogTable.tsx` (use DataTable wrapper)
- [ ] Wire up `catalog/page.tsx` with all zones
- [ ] Add loading skeletons for all components
- [ ] Add error states with retry buttons
- [ ] Implement mobile responsive layout (zone stacking)
- [ ] Add mobile bar chart alternative for scatter plot

### API Client
- [ ] Add `getCatalogKPIs()` method
- [ ] Add `getProductScatter()` method
- [ ] Add `getProductMovers()` method
- [ ] Update `getLeaderboard()` to support `include_growth` param

### Testing
- [ ] Verify KPI calculations match raw SQL
- [ ] Test quadrant assignment logic with sample data
- [ ] Validate concentration threshold (>30% = red)
- [ ] Test period comparison with various date ranges
- [ ] Verify 500 product limit is enforced
- [ ] Test responsive layout on mobile/tablet/desktop
- [ ] Performance test: measure TTI with real data
- [ ] Test sorting on all table columns
- [ ] Verify placeholder failure rate is deterministic

### Documentation
- [ ] Add API endpoint documentation
- [ ] Document mock failure rate logic
- [ ] Add comments explaining period comparison
- [ ] Update README with new page details

---

## Known Limitations & Future Enhancements

### Current Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| **No order status** | Cannot calculate real failure rate | Using deterministic mock data (0.1-3%) |
| **No inventory data** | Cannot show stock status (OK/Low/Out) | ~~Removed from table~~ |
| **Only 2 product types** | Less color variety in scatter plot | Blue (gift_card), Purple (merchandise) |
| **500 product limit** | Not showing all 870 products | Display notice: "Top 500 by revenue" |
| **Mock failure rates** | Not actionable for users | Add tooltip: "Placeholder data" |

### Future Enhancements (v2+)

| Feature | Description | Version | Priority |
|---------|-------------|---------|----------|
| **Product Lifecycle Badges** | 🆕 New, 📈 Growing, ✓ Mature, 📉 Declining | v2 | Medium |
| **Anomaly Flags** | ⚠️ icon for irregular patterns (sudden spikes/drops) | v2 | Medium |
| **Bulk Export** | Select multiple rows → export CSV | v2 | Low |
| **Product Comparison** | Select 2-3 products to compare side-by-side | v3 | Low |
| **Predictive Stock Alerts** | ML-based stock-out predictions | v3 | Low |
| **Real Failure Rates** | When order status is available in DB | v2 | High |
| **Stock Status** | When inventory data is available | v2 | High |
| **Quadrant Click Filter** | Click quadrant to filter table | v2 | Medium |
| **Product Detail Drill-down** | Click product → detail modal | v2 | Medium |

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Jan 6, 2026 | Initial design specification |
| 1.1 | Jan 7, 2026 | **Revised:** Removed stock status, updated product types to 2 (gift_card/merchandise), added placeholder failure rate logic, limited scatter to 500 products, clarified period comparison, documented performance optimizations, added detailed layout diagrams, switched to Lucide icons |

---

## Approval & Sign-off

**Status**: ✅ Ready for Implementation

**Design Reviewed By**: [Your Name]
**Date**: January 7, 2026

**Implementation Estimates**:
- Backend: 2-3 hours
- Frontend: 4-5 hours
- Testing & Polish: 1-2 hours
- **Total**: 7-10 hours

---

**Next Steps**: Proceed with implementation following the plan in `/Users/zmasarweh/.claude/plans/snug-questing-zephyr.md`
