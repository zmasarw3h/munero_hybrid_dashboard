```markdown
# MASTER PROMPT — Munero Operational Metrics Dashboard Design Spec

You are a senior product-design AI. Your job is to produce a **detailed mock dashboard design specification in Markdown** for a new **Munero Operational Metrics Dashboard**.

---

## STEP 0 — Read the Reference Material

Before doing anything else, read these two documents carefully:

1. **`munero-platform/DASHBOARD_VISUAL_COMPONENTS_OVERVIEW.md`**
   This describes the existing Munero dashboard's visual language, component library, shell structure (header, filter bar, AI sidebar), and the three existing pages (Executive Overview, Market Analysis, Catalog Performance). You must match this visual language.

2. **The Operational Metrics Wishlist** (embedded below in §APPENDIX A).
   This is the feature wishlist for the new dashboard.

---

## STEP 1 — Ask Clarifying Questions (if needed)

If anything critical is ambiguous after reading the two inputs above, ask up to **5 targeted clarifying questions** before proceeding. Do not guess on business-critical definitions (e.g., SLA formulas, ticket-channel taxonomy).

---

## STEP 2 — Produce the Design Spec

Generate a single, comprehensive Markdown document with the sections described below. Use precise language and the exact formatting instructions given.

---

### DESIGN CONSTRAINTS (you must enforce all of these)

| # | Constraint |
|---|-----------|
| C1 | **Visual language match.** Reuse the Munero dashboard's zone-based layout style, crisp KPI card titles, "Attention Required"–style operational panels, color conventions, badge patterns ("Demo", "Top 500 shown", "SLA Breached"), and component naming tone. Refer to `DASHBOARD_VISUAL_COMPONENTS_OVERVIEW.md` as the source of truth. |
| C2 | **Standalone dashboard.** This is a separate dashboard application, not new tabs on the existing Munero Orders/Insights dashboard. However, it must reuse the same shell patterns: sticky header + nav tabs, global filter bar, and AI chat sidebar ("Ask AI") with the same interaction model. |
| C3 | **Priority ordering.** Order Fulfillment and Support & Ticketing are **primary** focus areas. Supplier Performance is **secondary/supporting**. Page structure, zone ordering, and KPI prominence must reflect this priority. |
| C4 | **Page count.** The dashboard may have **1, 2, or 3 pages**. Choose the best structure and explicitly justify the decision based on the wishlist scope, user mental model, and cognitive load. |
| C5 | **Filters.** Reuse the existing global filter bar pattern (date range, currency, country multi-select, product type multi-select, "More Filters" popover with clients/brands/suppliers/anomaly threshold). Add new operational filters as needed (e.g., order status, SLA threshold, failure category, ticket channel, ticket status, supplier, pipeline stage). Specify which filters are global vs page-specific and where new filters live (primary bar vs "More Filters" popover). |
| C6 | **Ignore Commercial Entity filter** — do not include it. |
| C7 | **Ticketing system-agnostic.** Do not assume a specific ticketing platform (Zendesk, Freshdesk, etc.). Keep metric definitions and filter labels generic. |
| C8 | **AI sidebar.** The "Ask AI" sidebar must be present, with suggested operational questions relevant to this dashboard's domain (fulfillment, support, supplier). |

---

### SECTION 1 — Information Architecture

Produce:

- **Proposed page count** (1, 2, or 3), with tab names and URL routes.
- **Justification** for the page structure (why this number of pages, how they map to user workflows).
- **Audience summary**: "Who is this for" — the primary personas.
- **Primary jobs-to-be-done** (3–5 bullet points, framed as "When [trigger], I need to [action] so I can [outcome]").

---

### SECTION 2 — Global Filters & Control Surface

Produce:

- **Global filters** (applied across all pages): list each filter with its type (dropdown, multi-select, date range, numeric input), default value, and reset behavior.
- **Page-specific filters** (if any): list each with the page it belongs to.
- **New operational filters** required by the wishlist that don't exist in the current dashboard. For each, specify:
  - Filter name and label
  - Input type (dropdown, multi-select, numeric slider, toggle, etc.)
  - Where it lives: primary filter bar, "More Filters" popover, or page-level control
  - Default state
  - Options source (static list or API-driven)
- **"Reset" behavior**: What state does "Reset" restore? (define defaults for all filters)

---

### SECTION 3 — Per-Page Layout (Zone-Based)

For **each page**, produce:

#### Page header
- Title text (exact UI copy)
- Subtitle text (exact UI copy)
- Optional freshness badge behavior

#### Zone-by-zone layout

For every zone, list each visual component with:

| Field | What to specify |
|-------|----------------|
| **Component name** | Name and, when possible, map to an existing Munero component pattern (e.g., `EnhancedKPICard`, `DualAxisChart`, `CompactDonut`, `TrendList`, `StuckOrdersList`, `ClientLeaderboard`-style table). If no existing pattern fits, name the new component and describe it. |
| **Title text** | Exact UI heading copy as it would appear on screen. |
| **Purpose** | What decision does this component help the user make? (1 sentence) |
| **Metrics shown** | Every metric displayed, with precise definitions: formula (numerator / denominator), unit, time basis (e.g., "over selected date range", "trailing 30 days"). |
| **Dimensional breakdowns** | What dimensions can the user group/slice by? (e.g., by entity, brand, supplier, product, channel, status) |
| **Sorting & Top-N rules** | Default sort order, configurable sort options, any "Top N" limit (e.g., "Top 10 by volume"). |
| **Interactions** | Click-to-filter, drilldown targets, toggle controls, hover tooltips (what data appears), export affordances (CSV, PNG). |
| **Empty state** | What text/visual is shown when there's no data? |
| **Loading state** | Skeleton card, spinner, or shimmer — specify which pattern. |
| **Error state** | What happens when the API call fails? (inline error card with retry, toast, etc.) |
| **Warnings / badges** | Any conditional badges or alerts (e.g., "SLA Breached", "Demo", "Top 500 shown", threshold warnings). Include trigger conditions. |

Use the zone naming convention from the existing dashboard: "Zone: [Name]".

---

### SECTION 4 — Wireframe-Style Layout Diagrams

Produce:

- **Desktop layout** (12-column grid): ASCII or Markdown-table wireframes for each page showing zone placement, approximate column spans, and row ordering.
- **Mobile layout**: A condensed single-column stacking order for each page, listing zones top-to-bottom with any mobile-specific changes (e.g., charts collapse to summary cards, tables become scrollable, etc.).

Use a format like this for desktop:

```
┌──────────────────────────────────────────────────┐
│ Sticky Header + Nav Tabs                         │
├──────────────────────────────────────────────────┤
│ Global Filter Bar                                │
├────────────┬────────────┬────────────┬───────────┤
│ KPI Card 1 │ KPI Card 2 │ KPI Card 3 │ KPI Card 4│
│ (3 cols)   │ (3 cols)   │ (3 cols)   │ (3 cols)  │
├────────────┴────────────┴────────────┴───────────┤
│ Chart Name (12 cols)                             │
├──────────────────────┬───────────────────────────┤
│ Component A (6 cols) │ Component B (6 cols)      │
└──────────────────────┴───────────────────────────┘
```

---

### SECTION 5 — Mock Data Examples

Provide plausible sample values for:

- **Every KPI card** (value, trend %, trend direction, secondary text).
- **At least 3 data points** for each chart or table (enough to show the shape of the visualization).
- **At least 1 example** of an alert/warning state being triggered (e.g., SLA breach, high-volume failure category).

Clearly mark all values with: `⚠️ MOCK DATA — for illustration only`.

---

### SECTION 6 — Implementation Notes (High Level)

Produce:

- **Data requirements per component**: For each chart/table/KPI, list the API fields required (field name, type, description). Group by endpoint.
- **Suggested endpoint shapes**: Provide 2–3 example JSON response shapes (request params → response body) for the most data-intensive components. No code — just JSON structure.
- **Reuse opportunities**: Explicitly list which existing Munero components (from `DASHBOARD_VISUAL_COMPONENTS_OVERVIEW.md`) can be reused as-is, which need minor adaptation, and which are net-new.
- **Performance considerations**: Top-N limits, pagination strategy, "Top 500 shown" patterns, any client-side aggregation concerns, caching recommendations.

---

### SECTION 7 — Acceptance Criteria & QA Checklist

Produce a checklist (Markdown checkboxes) that a reviewer can use to validate:

- [ ] Every wishlist item from §APPENDIX A is addressed by at least one component.
- [ ] All KPI definitions include formulas and units.
- [ ] Visual language matches the existing Munero dashboard (zone naming, card style, badge patterns, color conventions).
- [ ] Filter bar includes all required operational filters with correct placement.
- [ ] AI sidebar is present with domain-relevant suggested questions.
- [ ] Empty, loading, and error states are defined for every component.
- [ ] Wireframes are provided for desktop and mobile.
- [ ] Mock data is provided and clearly marked.
- [ ] Page structure justification is present.
- [ ] Sorting, Top-N, and interaction behaviors are specified for every component.
- [ ] SLA-related components have parameterized thresholds.
- [ ] No Commercial Entity filter is included.
- [ ] Ticketing metrics are system-agnostic (no vendor-specific terminology).
- [ ] Priority ordering is reflected: Fulfillment + Support are primary; Supplier is secondary.

Add any additional checklist items specific to the design you produce.

---

## §APPENDIX A — Operational Metrics Dashboard Wishlist

> This is the complete feature wishlist. Every item below must be addressed in the design spec.

### Main Filters
- All filters from Order Insights plus any new operational filters needed.

### Order Fulfilment Metrics
- Order status breakdown: fulfilled, pending, failed
- Average fulfillment time per order (order creation to fulfillment)
- SLA compliance tracking (parameterized SLA days)
- Orders approaching SLA breach (threshold parameterized)
- Entity-wise, brand-wise SLA performance

### Support & Ticketing
- Number of tickets by channel, program, issue type
- Average acknowledgement time
- Average resolution time
- Volume of unresolved tickets

### Supplier Performance
- Average supplier delivery time (PO creation to item receipt and invoice issued)
- Breakdown by supplier, brand, product

---

## §APPENDIX B — Existing Dashboard Component Patterns (Summary)

> These are the reusable component patterns from the existing Munero dashboard. Map new components to these wherever possible.

| Pattern | Description | Used In |
|---------|-------------|---------|
| `EnhancedKPICard` | Metric card with value, trend %, sparkline, secondary text, alert styling | All 3 existing pages |
| `DualAxisChart` | Dual-axis time series (bar + line), granularity toggle, anomaly highlighting | Executive Overview |
| `StuckOrdersList` | Operational list with status badges, age, retry/view actions, "View All" | Executive Overview |
| `GeographyMap` | Choropleth map with hover tooltips, zoom controls, gradient legend | Executive Overview |
| `TopPerformersChart` | Stacked horizontal bar chart with dimension toggle | Executive Overview |
| `CompactDonut` | Donut chart with compact legend table (percent + value) | Overview, Market, Catalog |
| `AnomalyTicker` | Horizontal scrollable ticker of anomaly chips | Executive Overview |
| `RevenueConcentrationChart` | Pareto-style bars + cumulative % line with 80% reference | Market Analysis |
| `ClientSegmentationMatrix` | Scatter plot with 4 quadrants, threshold controls, segment legend | Market Analysis |
| `ClientLeaderboard` | Sortable, selectable table with badges, share %, row selection | Market Analysis |
| `ProductPerformanceMatrix` | Scatter plot with quadrants, threshold controls, type color coding | Catalog Performance |
| `TrendList` | Split list of Top Risers / Top Fallers | Catalog Performance |
| `SupplierConcentrationChart` | Vertical bar chart with risk threshold line + warning alert | Catalog Performance |
| `CatalogTable` | Sortable product table with type badge, growth %, failure rate | Catalog Performance |

### Shell Patterns to Reuse
- **Sticky Header**: Logo + title, nav tabs, "Ask AI" button, live status indicator, user menu
- **Global Filter Bar**: Date range, currency, country multi-select, product type multi-select, "More Filters" popover, reset button
- **AI Chat Sidebar**: Context indicator, message list with charts/SQL/exports, suggested questions, health warning

---

## OUTPUT FORMAT

- Produce the entire design spec as a **single Markdown document**.
- Use `##` for major sections, `###` for subsections, and `####` for zones/components.
- Use tables for structured data (metrics definitions, field lists, etc.).
- Use the exact section numbering (1–7) from the instructions above.
- Do not omit any section.
```
