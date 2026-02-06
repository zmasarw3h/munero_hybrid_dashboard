# Catalog Analysis Page Design Specification
## "The Product Engine"

**Version:** 1.0  
**Created:** January 6, 2026  
**Status:** Approved for Implementation

---

## Overview

The Catalog Analysis page answers the question: **"What products drive our business?"**

This page provides deep insights into product performance, brand analysis, and supplier concentration. It helps identify top-performing products, margin opportunities, and supply chain risks.

---

## Page Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ZONE 1: Supply Chain KPIs (4 cards)                                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ Active SKUs  │ │ Global Reach │ │ Avg Margin   │ │ Supplier     │        │
│  │ 1,247        │ │ 12 currencies│ │ 22.5%        │ │ Health: 85%  │        │
│  │ ↑12% vs LY   │ │ ↑2 new       │ │ ↓1.2pts      │ │ ⚠️ 1 at risk │        │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘        │
├─────────────────────────────────────────────────────────────────────────────┤
│  ZONE 2: Product Performance Matrix (full width)                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    ProductPerformanceMatrix                             ││
│  │                    (Scatter Plot with Quadrants)                        ││
│  │                                                                         ││
│  │    Revenue ($)                                                          ││
│  │        ▲                                                                ││
│  │        │   ┌─────────────────┬─────────────────┐                        ││
│  │        │   │  PREMIUM NICHE  │   CASH COWS     │                        ││
│  │        │   │  (High $, Low Q)│   (High $, Hi Q)│                        ││
│  │        │   │     ● ●         │     ● ● ● ●     │                        ││
│  │        │   ├─────────────────┼─────────────────┤                        ││
│  │        │   │   DEAD STOCK    │  PENNY STOCKS   │                        ││
│  │        │   │  (Low $, Low Q) │  (Low $, High Q)│                        ││
│  │        │   │     ●           │     ● ● ●       │                        ││
│  │        │   └─────────────────┴─────────────────┘                        ││
│  │        └──────────────────────────────────────────► Quantity Sold       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│  ZONE 3: Split View (8 cols + 4 cols)                                       │
│  ┌────────────────────────────────┐ ┌──────────────────────────────────────┐│
│  │  TrendList: Movers & Shakers   │ │  SupplierConcentrationChart          ││
│  │  ┌───────────────────────────┐ │ │  ┌──────────────────────────────────┐││
│  │  │  📈 TOP RISERS            │ │ │  │ Supplier A  ████████████ 35%     │││
│  │  │  1. iTunes $100   +45%   │ │ │  │ Supplier B  ██████████ 28%       │││
│  │  │  2. Google Play   +32%   │ │ │  │ Supplier C  ████████ 20%         │││
│  │  │  3. Netflix Card  +28%   │ │ │  │ Supplier D  ████ 10%             │││
│  │  ├───────────────────────────┤ │ │  │ Others      ██ 7%                │││
│  │  │  📉 TOP FALLERS           │ │ │  │             ┊                    │││
│  │  │  1. Steam Card    -38%   │ │ │  │             ┊ 30% threshold      │││
│  │  │  2. Xbox Gift     -25%   │ │ │  └──────────────────────────────────┘││
│  │  │  3. PSN Voucher   -18%   │ │ │                                      ││
│  │  └───────────────────────────┘ │ │  ⚠️ Supplier A exceeds 30% threshold││
│  └────────────────────────────────┘ └──────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│  ZONE 4: CatalogTable (full width, scrollable)                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Product Name      │ Type       │ Revenue  │ Growth │ Failure │ Stock   ││
│  │ ──────────────────┼────────────┼──────────┼────────┼─────────┼──────── ││
│  │ iTunes $100       │ Gift Card  │ $125,340 │ +45%   │ 0.3%    │ 🟢 OK   ││
│  │ Google Play $50   │ Gift Card  │ $98,200  │ +32%   │ 0.5%    │ 🟢 OK   ││
│  │ Netflix Premium   │ Voucher    │ $87,100  │ +28%   │ 0.2%    │ 🟢 OK   ││
│  │ Steam Wallet $20  │ Gift Card  │ $45,600  │ -38%   │ 2.1%    │ 🟡 Low  ││
│  │ Xbox Game Pass    │ Subscription│ $32,400 │ -25%   │ 1.8%    │ 🔴 Out  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Zone 1: Supply Chain KPIs

### Layout
4 KPI cards in a responsive grid (4 → 2 → 1 columns based on screen size)

### KPI Definitions

| KPI | Calculation | Format | Icon |
|-----|-------------|--------|------|
| **Active SKUs** | `COUNT(DISTINCT product_sku) WHERE quantity > 0` | Number with commas | 📦 |
| **Global Reach** | `COUNT(DISTINCT order_currency)` | "X currencies" | 🌍 |
| **Avg Margin** | `AVG((Revenue - COGS) / Revenue * 100)` | Percentage | 💰 |
| **Supplier Health** | `% of suppliers with <30% concentration` | Percentage + badge | 🏭 |

### Comparison Badges
Each card shows comparison vs prior period:
- **Green badge**: Positive change (↑12%)
- **Red badge**: Negative change (↓5%)
- **Gray badge**: No change (—)

### Margin Fallback Logic (Critical)

When COGS data is unavailable:

```
IF cogs IS NULL OR cogs = 0:
    Display: "X% Contribution" (gray/blue badge)
    Tooltip: "Cost data unavailable. Shows revenue contribution to total."
    Calculation: (Item Revenue / Total Revenue) * 100
ELSE:
    Display: "X% Margin" (green badge)
    Calculation: (Revenue - COGS) / Revenue * 100
```

**Visual Example:**
```
┌─────────────────────────┐     ┌─────────────────────────┐
│ Avg Margin %            │     │ Avg Contribution        │
│ ████████████ 22.5%      │     │ ████████████ 15.2%      │
│ 🟢 Healthy margin       │     │ ℹ️ Cost data missing    │
└─────────────────────────┘     └─────────────────────────┘
```

---

## Zone 2: Product Performance Matrix

### Component
`ProductPerformanceMatrix.tsx` - Scatter plot with strategic quadrants

### Chart Configuration

| Property | Value |
|----------|-------|
| **X-Axis** | Quantity Sold (volume) |
| **Y-Axis** | Revenue (value) |
| **Dot Size** | Fixed or by margin % |
| **Dot Color** | By product type |

### Quadrant Definitions

| Quadrant | Position | Meaning | Strategy |
|----------|----------|---------|----------|
| **Cash Cows** | Top-Right | High Revenue, High Volume | Protect & optimize |
| **Premium Niche** | Top-Left | High Revenue, Low Volume | Expand distribution |
| **Penny Stocks** | Bottom-Right | Low Revenue, High Volume | Increase pricing |
| **Dead Stock** | Bottom-Left | Low Revenue, Low Volume | Consider discontinuing |

### Quadrant Calculation
- **Median Revenue** = dividing line for Y-axis
- **Median Quantity** = dividing line for X-axis
- Products are plotted and categorized based on position

### Interactions

| Action | Behavior |
|--------|----------|
| Hover | Tooltip: Product name, Revenue, Quantity, Margin %, Type |
| Click | Updates FilterContext with selected product, navigates to detail |
| Quadrant Click | Filters table below to products in that quadrant |

### Visual Style
```tsx
const QUADRANT_COLORS = {
  'Cash Cows': 'rgba(34, 197, 94, 0.1)',      // Green tint
  'Premium Niche': 'rgba(99, 102, 241, 0.1)', // Purple tint
  'Penny Stocks': 'rgba(251, 191, 36, 0.1)',  // Amber tint
  'Dead Stock': 'rgba(239, 68, 68, 0.1)'      // Red tint
};
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
│  ─────────────────────────  │
│  1. iTunes $100      +45%   │
│  2. Google Play $50  +32%   │
│  3. Netflix Card     +28%   │
├─────────────────────────────┤
│  📉 TOP FALLERS             │
│  ─────────────────────────  │
│  1. Steam Card       -38%   │
│  2. Xbox Gift        -25%   │
│  3. PSN Voucher      -18%   │
└─────────────────────────────┘
```

### Data Source
```sql
-- Top Risers
SELECT 
    product_name,
    current_period_revenue,
    prior_period_revenue,
    ((current - prior) / prior * 100) as growth_pct
FROM product_comparison
WHERE growth_pct > 0
ORDER BY growth_pct DESC
LIMIT 3;

-- Top Fallers (same but WHERE growth_pct < 0 ORDER BY growth_pct ASC)
```

### Styling

| Element | Style |
|---------|-------|
| Riser badge | Green text, ↑ arrow |
| Faller badge | Red text, ↓ arrow |
| Product name | Clickable link (EntityLink) |
| Percentage | Bold, right-aligned |

---

## Zone 3B: Supplier Concentration Chart

### Component
`SupplierConcentrationChart.tsx` - Horizontal bar chart with risk threshold

### Chart Configuration

| Property | Value |
|----------|-------|
| **Type** | Horizontal Bar Chart |
| **Sort** | Descending by revenue share |
| **Bars Shown** | Top 5 suppliers + "Others" |
| **Reference Line** | Vertical dashed line at 30% |

### Risk Thresholds

| Concentration | Risk Level | Visual |
|---------------|------------|--------|
| <20% | Healthy | Green bar |
| 20-30% | Moderate | Amber bar |
| >30% | High Risk | Red bar + warning badge |

### Warning Display
If any supplier exceeds 30%:
```
⚠️ Supplier A exceeds 30% threshold - Consider diversifying
```

### Interactions

| Action | Behavior |
|--------|----------|
| Hover | Tooltip: Supplier name, Revenue, % of total, Order count |
| Click | Filters dashboard to that supplier |

---

## Zone 4: CatalogTable

### Component
`CatalogTable.tsx` using `DataTable` base component

### Column Definitions

| Column | Format | Sortable | Width | Priority |
|--------|--------|----------|-------|----------|
| **Product Name** | Text (EntityLink) | Yes | 25% | MVP |
| **Type** | Badge | Yes | 12% | MVP |
| **Revenue** | Currency | Yes (default) | 15% | MVP |
| **Growth %** | Percentage with ↑/↓ | Yes | 12% | MVP |
| **Failure Rate** | Percentage | Yes | 12% | MVP |
| **Stock Status** | Status badge | Yes | 12% | MVP |
| **Margin/Contrib** | Percentage | Yes | 12% | MVP |

### Column Details

#### Product Name
- Clickable `<EntityLink>` component
- Click navigates to product detail/filters

#### Type Badge
```tsx
const TYPE_BADGES = {
  'gift_card': { label: 'Gift Card', color: 'bg-blue-100 text-blue-800' },
  'voucher': { label: 'Voucher', color: 'bg-purple-100 text-purple-800' },
  'subscription': { label: 'Subscription', color: 'bg-green-100 text-green-800' },
  'top_up': { label: 'Top-up', color: 'bg-amber-100 text-amber-800' }
};
```

#### Growth %
- Green with ↑ for positive
- Red with ↓ for negative
- Gray for 0%

#### Failure Rate
- Definition: `(Failed Orders / Total Orders) * 100`
- Color coding:
  - 🟢 <1%: Green
  - 🟡 1-3%: Amber
  - 🔴 >3%: Red

#### Stock Status
```tsx
const STOCK_STATUS = {
  'ok': { label: 'OK', icon: '🟢', color: 'text-green-600' },
  'low': { label: 'Low', icon: '🟡', color: 'text-amber-600' },
  'out': { label: 'Out', icon: '🔴', color: 'text-red-600' }
};
```

### Table Features

| Feature | Description | Priority |
|---------|-------------|----------|
| **Sorting** | Click column header to sort | MVP |
| **Pagination** | 20 rows per page | MVP |
| **Search** | Filter by product name | MVP |
| **Quick Filters** | Type dropdown, Stock status | MVP |
| **Export** | CSV download button | v2 |
| **Row Selection** | Multi-select for bulk actions | v2 |

### Empty State
If no products match filters:
```
┌─────────────────────────────────────────────┐
│           📦 No Products Found              │
│                                             │
│  No products match your current filters.    │
│                                             │
│  Try:                                       │
│  • Expanding the date range                 │
│  • Removing product type filter             │
│  • Clearing the search                      │
│                                             │
│  [Reset Filters]                            │
└─────────────────────────────────────────────┘
```

---

## Data Requirements

### API Endpoints Needed

| Endpoint | Purpose | Parameters |
|----------|---------|------------|
| `GET /api/dashboard/kpis` | Zone 1 KPIs | filters, comparison_period |
| `GET /api/dashboard/scatter` | Zone 2 Matrix | filters, x_metric, y_metric |
| `GET /api/dashboard/trends` | Zone 3A Movers | filters, top_n, direction |
| `GET /api/dashboard/breakdown` | Zone 3B Suppliers | filters, dimension='supplier' |
| `GET /api/dashboard/products` | Zone 4 Table | filters, sort, pagination |

### Data Models

```typescript
// Zone 1 KPI Response
interface CatalogKPIs {
  active_skus: number;
  active_skus_change: number;
  global_reach: number; // currency count
  global_reach_change: number;
  avg_margin: number | null; // null if no COGS
  avg_contribution: number; // fallback
  supplier_health: number; // percentage healthy
  at_risk_suppliers: number;
}

// Zone 2 Scatter Point
interface ProductPoint {
  product_name: string;
  product_type: string;
  quantity: number;
  revenue: number;
  margin?: number;
  quadrant: 'cash_cow' | 'premium_niche' | 'penny_stock' | 'dead_stock';
}

// Zone 3A Trend Item
interface TrendItem {
  product_name: string;
  growth_pct: number;
  current_revenue: number;
  prior_revenue: number;
}

// Zone 3B Supplier Item
interface SupplierConcentration {
  supplier_name: string;
  revenue: number;
  share_pct: number;
  order_count: number;
  risk_level: 'healthy' | 'moderate' | 'high';
}

// Zone 4 Table Row
interface CatalogRow {
  product_id: string;
  product_name: string;
  product_type: string;
  revenue: number;
  growth_pct: number;
  failure_rate: number;
  stock_status: 'ok' | 'low' | 'out';
  margin?: number;
  contribution?: number;
}
```

---

## Component File Structure

```
frontend/components/dashboard/
├── catalog/
│   ├── ProductPerformanceMatrix.tsx   # Zone 2 scatter
│   ├── TrendList.tsx                  # Zone 3A movers
│   ├── SupplierConcentrationChart.tsx # Zone 3B chart
│   └── CatalogTable.tsx               # Zone 4 table
```

---

## Responsive Behavior

| Breakpoint | Layout Changes |
|------------|----------------|
| **Desktop (≥1280px)** | Full 4-column KPIs, 8+4 Zone 3 split |
| **Tablet (768-1279px)** | 2-column KPIs, Zone 3 stacks vertically |
| **Mobile (<768px)** | 1-column KPIs, all zones stack, table scrolls horizontally |

### Zone 3 Responsive
```tsx
// Desktop: side by side
<div className="grid grid-cols-12 gap-4">
  <div className="col-span-8"><TrendList /></div>
  <div className="col-span-4"><SupplierConcentrationChart /></div>
</div>

// Mobile: stacked
<div className="flex flex-col gap-4">
  <TrendList />
  <SupplierConcentrationChart />
</div>
```

---

## Interactions & Cross-Page Navigation

### EntityLink Behavior

| Entity Clicked | Action |
|----------------|--------|
| Product Name | Filter to product, stay on page |
| Brand Name | Navigate to Catalog, filter to brand |
| Supplier Name | Filter to supplier, stay on page |

### Filter Sync
All filters in Zone 4 table sync with global FilterContext:
- Date range from FilterBar
- Currency from FilterBar
- Product type from FilterBar or table quick filter

---

## Future Enhancements (v2+)

| Feature | Description | Version |
|---------|-------------|---------|
| Product Lifecycle Badges | 🆕 New, 📈 Growing, ✓ Mature, 📉 Declining | v2 |
| Anomaly Flags | ⚠️ icon for irregular patterns | v2 |
| Bulk Export | Select multiple rows → export CSV | v2 |
| Product Comparison | Select 2-3 products to compare side-by-side | v3 |
| Predictive Stock Alerts | ML-based stock-out predictions | v3 |

---

## Implementation Checklist

### Backend
- [ ] Add product scatter endpoint with quadrant calculation
- [ ] Add movers/shakers trend endpoint
- [ ] Add supplier concentration endpoint
- [ ] Add product list endpoint with failure rate
- [ ] Implement margin fallback logic

### Frontend
- [ ] Create `ProductPerformanceMatrix.tsx`
- [ ] Create `TrendList.tsx`
- [ ] Create `SupplierConcentrationChart.tsx`
- [ ] Create `CatalogTable.tsx`
- [ ] Wire up `catalog/page.tsx`
- [ ] Add responsive breakpoints
- [ ] Implement empty states
- [ ] Add loading skeletons

### Testing
- [ ] Verify KPI calculations match raw data
- [ ] Test quadrant assignment logic
- [ ] Validate concentration thresholds
- [ ] Test cross-page navigation
- [ ] Responsive testing on all breakpoints
