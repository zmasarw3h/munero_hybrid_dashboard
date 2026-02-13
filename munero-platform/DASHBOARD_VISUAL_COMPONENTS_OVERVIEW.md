# Dashboard Visual Components Overview

Scope: This document describes the **visible UI/visual components** that make up the Munero Hybrid Dashboard shell and its **three dashboard pages**:
- Executive Overview (`/dashboard/overview`)
- Market Analysis (`/dashboard/market`)
- Catalog Performance (`/dashboard/catalog`)

Source of truth: `munero-platform/frontend/app/dashboard/*` and `munero-platform/frontend/components/**`.

Last updated: 2026-02-13

---

## 1) Global Dashboard Shell (Present on All 3 Pages)

These elements are rendered by the dashboard layout and remain consistent across page navigation.

### 1.1 Sticky Header (Top Bar)

- **Branding block (logo + title)**
  - Displays the Munero logo (`/public/munero-logo.jpeg`) and “Munero AI Platform” title/subtitle.
- **Navigation tabs (`NavTabs`)**
  - Tab-style navigation for the 3 dashboard pages: Executive Overview, Market Analysis, Catalog Performance.
  - Highlights the active page based on the current route.
- **Ask AI button**
  - Primary call-to-action that opens the AI chat sidebar.
  - Keyboard shortcut support: `Cmd/Ctrl + K` toggles the sidebar; `Esc` closes it.
- **Live status indicator**
  - Green “Live” pill with pulsing dot (visual-only indicator).
- **User menu placeholder**
  - Circular avatar placeholder (“ZM”).

### 1.2 Global Filter Bar (`FilterBar`)

A sticky, cross-page filter strip that controls the data scope for all pages (and is also passed into AI Chat requests).

- **Date range (start → end)**
  - Two date inputs defining the analysis period.
- **Currency selector**
  - Dropdown populated from backend filter options.
- **Country multi-select**
  - Searchable multi-select for one or more countries.
- **Product type multi-select**
  - Searchable multi-select (e.g., gift card vs merchandise).
- **More Filters popover**
  - **Clients multi-select**
  - **Brands multi-select**
  - **Suppliers multi-select**
  - **Anomaly Threshold input (Z-Score)**
    - Numeric input (bounded 1–5) that influences anomaly labeling in trend visuals.
  - Includes “Clear Advanced” and “Apply” actions.
- **Reset**
  - Resets all filters back to defaults.
- **Loading indicator**
  - Small “Loading filter options…” text shown while options are fetched.

### 1.3 AI Chat Sidebar (`ChatSidebar`)

A slide-over panel that allows users to ask questions in natural language and see:

- **Context indicator**
  - Shows the current filter context (date range + selected countries/product types when applicable).
- **Message list**
  - User and assistant message bubbles.
  - Assistant responses can include:
    - **Warnings** (yellow callout)
    - **Chart/table render** (based on `chart_config` + `data`)
    - **SQL viewer** (collapsible “View SQL” block with copy-to-clipboard)
    - **Export toolbar**
      - CSV download (enabled when backend returns an `export_token` in production)
      - PNG download (renders the chart container to an image)
    - **Error block**
      - Shows backend `error` messages when present (e.g., SQL generation failures).
- **Empty state with suggested questions**
  - Clickable prompt suggestions when the conversation is empty.
- **Health warning banner**
  - When chat health is not “healthy”, shows a yellow warning bar with a hint.

---

## 2) Executive Overview Page (`/dashboard/overview`)

### Shared (also present here)
- Sticky header (branding, tabs, status, Ask AI)
- Global filter bar
- AI chat sidebar

### Page-specific visuals

- **Page header**
  - Title: “Executive Overview”
  - Subtitle describing the page purpose.
  - Optional “Updated:” freshness badge when backend `meta.last_updated` is available.

- **Zone: KPI Cards (5× `EnhancedKPICard`)**
  - **Total Orders** (includes orders sparkline)
  - **Total Revenue** (includes revenue sparkline)
  - **Avg Order Value**
  - **Orders / Client**
  - **Stuck Orders** (alert styling when > 0; includes “View” action that scrolls to the stuck-orders panel)
  - Cards can include: value, trend %, trend direction color, optional sparkline, secondary text, and alert styling.

- **Zone: Sales & Volume Trend (`DualAxisChart`)**
  - Dual-axis time series combining **bar + line** metrics (orders + revenue).
  - **Granularity control** (Day / Month / Year).
  - **Swap Axis** control to invert which metric is bar vs line.
  - **Anomaly highlighting**
    - Bars can turn red when anomaly flags are present in the data.
    - Legend includes anomaly count when present.
  - Has explicit empty/loading states (“No data available”, skeleton card).

- **Zone: Operational Health (`StuckOrdersList`)**
  - List of stuck/failed/pending orders with:
    - Order number, status badge, age (days)
    - Retry icon button (non-pending)
    - View details icon button
    - Optional “View All” button when more items exist
  - Supports “Demo” badge when using mock data.

- **Zone: Revenue by Geography (`GeographyMap`)**
  - Interactive choropleth map shading countries by revenue intensity.
  - Hover tooltip shows revenue, orders, clients.
  - Zoom controls (in/out/reset) + gradient legend.
  - Note: the page currently wires clicks to a placeholder handler (logs to console / TODO to update filters).

- **Zone: Top Performers (`TopPerformersChart`)**
  - Stacked horizontal bar chart with a **Products / Brands** toggle:
    - **Products view:** completed vs failed/stuck revenue (stacked).
    - **Brands view:** gift card vs merchandise revenue (stacked).
  - Hover tooltip shows totals + split percentages.
  - Optional “Demo” badge for mock data.

- **Zone: Revenue by Type (`CompactDonut`)**
  - Donut chart with a compact legend table (percent + formatted value).
  - Note: segment click is currently wired to a placeholder handler (logs / TODO).

- **Zone: Anomalies strip (`AnomalyTicker`)**
  - Horizontal scrollable ticker of anomaly “chips” (date + metric + % change).
  - Empty state: “No anomalies detected in the selected period”.
  - Note: chip click is currently wired to a placeholder handler (logs / TODO).

---

## 3) Market Analysis Page (`/dashboard/market`)

### Shared (also present here)
- Sticky header (branding, tabs, status, Ask AI)
- Global filter bar
- AI chat sidebar

### Page-specific visuals

- **Page header**
  - Title: “Market Analysis”
  - Subtitle describing segmentation + concentration focus.

- **Zone: Market KPI Cards (3× `EnhancedKPICard`)**
  - **Active Clients** (can show “Top 500 shown” note when the scatter API limits output)
  - **Avg Revenue/Client**
  - **Top Client Share** (alert styling if concentration risk is detected)

- **Zone: Revenue Concentration (`RevenueConcentrationChart`)**
  - Pareto-style visualization:
    - Revenue bars by client rank (top N)
    - Cumulative % line with an 80% reference line
  - “Top X clients = Y% of revenue” insight line below the title.
  - Clickable bars to select/filter a client.

- **Zone: Client Segmentation (`ClientSegmentationMatrix`)**
  - Scatter plot splitting clients into 4 quadrants (e.g., Champion / Whale / Loyalist / Developing).
  - **Threshold controls** for Orders + Revenue (debounced inputs).
  - Quadrant shading + reference lines for thresholds.
  - Segment legend with counts; legend is clickable to filter by segment.
  - Supports log scales automatically when data ranges are large.

- **Zone: Segment Distribution (`CompactDonut`)**
  - Donut chart showing the number of clients per segment (count format).
  - Clicking a segment applies the segment filter (wired to page state).

- **Zone: Client Leaderboard (`ClientLeaderboard`)**
  - Sortable, selectable table of clients with:
    - Client name (truncated)
    - Segment badge
    - Revenue, Orders, Share %
  - Row click selects a client; “clear filter” resets the selection.
  - Shows count info (e.g., “N of M clients in Champion”).

- **Error state**
  - A centered error card with a “Retry” button when API calls fail.

---

## 4) Catalog Performance Page (`/dashboard/catalog`)

### Shared (also present here)
- Sticky header (branding, tabs, status, Ask AI)
- Global filter bar
- AI chat sidebar

### Page-specific visuals

- **Page header**
  - Title: “Catalog Analysis”
  - Subtitle describing product drivers focus.

- **Zone: Catalog KPI Cards (4× `EnhancedKPICard`)**
  - **Active SKUs**
  - **Global Reach** (currency count)
  - **Avg Margin**
  - **Supplier Health** (alert styling when at-risk suppliers exist; secondary text like “X at risk”)

- **Zone: Product Performance Matrix (`ProductPerformanceMatrix`)**
  - Scatter plot with **Quantity (x)** vs **Revenue (y)** and 4 quadrants:
    - Cash Cows, Premium Niche, Penny Stocks, Dead Stock
  - **Threshold controls** for Quantity + Revenue (debounced inputs).
  - Quadrant shading + reference lines for thresholds.
  - Point color indicates product type (gift_card vs merchandise) + tooltip shows revenue/quantity/margin/quadrant.
  - Shows a “Top 500 by Revenue” badge and a data-limit notice when applicable.

- **Zone: Segment Distribution (`CompactDonut`)**
  - Donut chart showing the count of products in each quadrant (count format).

- **Zone: Movers & Shakers (`TrendList`)**
  - Split list of **Top Risers** and **Top Fallers** based on revenue growth vs prior period.
  - Can show sample placeholder data when the backend doesn’t provide movers yet.

- **Zone: Supplier Concentration (`SupplierConcentrationChart`)**
  - Vertical bar chart of revenue share by supplier (top 5 + “Others”).
  - 30% risk threshold line.
  - Displays a warning alert when a supplier exceeds the risk threshold.
  - “None” (unassigned supplier) is handled specially (excluded from the chart but considered in risk checks).

- **Zone: Product Catalog Table (`CatalogTable`)**
  - Sortable table listing products with:
    - Name, type badge, revenue, growth %, failure rate (placeholder), margin %
  - Empty state guidance: “Adjust your filters or date range.”

- **Error state**
  - Inline error card with “Retry” button when catalog data fails to load.

