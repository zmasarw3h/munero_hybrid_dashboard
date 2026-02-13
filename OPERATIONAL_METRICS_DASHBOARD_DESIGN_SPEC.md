# Munero Operational Metrics Dashboard — Design Specification

> **Version:** 1.0
> **Date:** 2026-02-13
> **Status:** Draft — Pending Review
> **Visual language source of truth:** `munero-platform/DASHBOARD_VISUAL_COMPONENTS_OVERVIEW.md`

---

## STEP 1 — Clarifying Questions

Before producing this spec, the following assumptions were made. If any are incorrect, the relevant sections should be revised.

| # | Question | Assumption Used |
|---|----------|-----------------|
| Q1 | What is the default SLA threshold (in days)? | **7 days.** The SLA threshold is fully parameterized via a numeric input, so users can adjust it. 7 days is used as the factory default. |
| Q2 | What does "entity" mean in "entity-wise SLA performance"? | **Client entity** — the contracting client/account that placed the order (same dimension as "Clients" in the existing filter bar). |
| Q3 | What channels should appear in the ticket-channel filter? | Generic, system-agnostic labels: **Email, Phone, Live Chat, Web Form, Social, Other.** The list is API-driven, so platform-specific channels can be added without UI changes. |
| Q4 | How is "fulfillment time" calculated when an order has multiple shipments? | **Order-level:** `MAX(shipment_fulfilled_at) − order_created_at` — the clock stops when the last item is fulfilled. |
| Q5 | Should "Average supplier delivery time" include time to invoice, or is PO-to-receipt sufficient? | The wishlist says "PO creation to item receipt **and** invoice issued." We treat these as **two separate metrics**: (a) PO-to-Receipt and (b) PO-to-Invoice, shown side by side. |

---

## SECTION 1 — Information Architecture

### 1.1 Proposed Page Count: **2 Pages**

| # | Tab Name | URL Route | Focus |
|---|----------|-----------|-------|
| 1 | **Order Fulfillment** | `/ops/fulfillment` | Order status, fulfillment time, SLA compliance, supplier delivery (secondary) |
| 2 | **Support & Ticketing** | `/ops/support` | Ticket volume, acknowledgement & resolution times, unresolved tickets |

### 1.2 Justification

- **Why not 1 page?** The combined wishlist (fulfillment + SLA + ticketing + supplier) would produce 10+ zones on a single page, exceeding comfortable cognitive load and scroll depth. Fulfillment and ticketing are distinct operational workflows with different user triggers.
- **Why not 3 pages?** The Supplier Performance wishlist is compact (2 items: delivery time + breakdown). Supplier delivery is logically part of the fulfillment pipeline (PO → receipt → invoice), so it fits naturally as a secondary zone on the Fulfillment page — avoiding a sparse third page.
- **Why this split?** The two pages map to two distinct mental models: (1) "Is my order pipeline healthy?" and (2) "Is my support operation keeping up?" This mirrors how operations teams typically divide responsibilities (logistics vs. customer service).

### 1.3 Audience Summary

| Persona | Description |
|---------|-------------|
| **Operations Manager** | Monitors fulfillment pipeline daily; needs to spot SLA risks and escalate stuck orders. |
| **Support Team Lead** | Tracks ticket volume, response times, and backlog; needs to allocate agent capacity. |
| **Supply Chain Analyst** | Reviews supplier delivery performance to flag slow suppliers and negotiate SLAs. |
| **VP of Operations** | Weekly/monthly review of operational health across fulfillment and support. |

### 1.4 Primary Jobs-to-Be-Done

1. **When** I start my morning shift, **I need to** see which orders are approaching SLA breach **so I can** prioritize follow-ups before they become customer complaints.
2. **When** fulfillment failure rates spike, **I need to** identify the failing entities, brands, or suppliers **so I can** escalate to the right team.
3. **When** ticket volume surges on a specific channel, **I need to** see the breakdown by channel and issue type **so I can** reallocate support agents.
4. **When** average resolution time exceeds our target, **I need to** drill into unresolved tickets **so I can** unblock the oldest cases first.
5. **When** preparing a supplier performance review, **I need to** compare delivery times across suppliers **so I can** negotiate better terms or switch providers.

---

## SECTION 2 — Global Filters & Control Surface

### 2.1 Global Filters (Applied Across All Pages)

| Filter | Type | Default | Reset Restores To |
|--------|------|---------|-------------------|
| Date Range | Date range (start → end) | Last 30 days | Last 30 days |
| Currency | Dropdown (API-driven) | USD (or first option) | USD |
| Country | Searchable multi-select (API-driven) | All (none selected = all) | All |
| Product Type | Searchable multi-select (API-driven) | All | All |
| Clients | Multi-select (in "More Filters" popover) | All | All |
| Brands | Multi-select (in "More Filters" popover) | All | All |
| Suppliers | Multi-select (in "More Filters" popover) | All | All |

> **Note:** Commercial Entity filter is explicitly excluded per constraint C6.
> **Note:** Anomaly Threshold (Z-Score) from the existing dashboard is retained in "More Filters" but has no effect on Operational Metrics pages (carried forward for shell consistency and AI sidebar context).

### 2.2 New Operational Filters

| Filter Name | Label | Input Type | Location | Default | Options Source |
|-------------|-------|------------|----------|---------|---------------|
| Order Status | "Order Status" | Multi-select | Primary filter bar | All (Fulfilled, Pending, Failed) | Static list |
| SLA Threshold | "SLA Days" | Numeric input (1–90) | Primary filter bar | 7 | User input |
| SLA Breach Window | "Breach Warning (days)" | Numeric input (1–30) | "More Filters" popover | 2 | User input |
| Failure Category | "Failure Category" | Multi-select | "More Filters" popover | All | API-driven |
| Ticket Channel | "Channel" | Multi-select | Page-level (Support & Ticketing) | All | API-driven |
| Ticket Status | "Ticket Status" | Multi-select | Page-level (Support & Ticketing) | All (Open, In Progress, Resolved, Closed) | Static list |
| Issue Type | "Issue Type" | Multi-select | Page-level (Support & Ticketing) | All | API-driven |
| Program | "Program" | Multi-select | Page-level (Support & Ticketing) | All | API-driven |

### 2.3 Page-Specific Filters

| Page | Filters |
|------|---------|
| Order Fulfillment | (none beyond global + new operational — Order Status, SLA Threshold, SLA Breach Window, and Failure Category are global/popover) |
| Support & Ticketing | Ticket Channel, Ticket Status, Issue Type, Program (rendered as a secondary filter strip below the global bar) |

### 2.4 "Reset" Behavior

Clicking **Reset** restores ALL filters (global + new operational + page-specific) to the defaults listed above. Page-specific filters reset only when the user clicks Reset while on that page.

---

## SECTION 3 — Per-Page Layout (Zone-Based)

---

### PAGE 1: Order Fulfillment (`/ops/fulfillment`)

#### Page Header

- **Title:** "Order Fulfillment"
- **Subtitle:** "Monitor order pipeline health, SLA compliance, and supplier delivery performance."
- **Freshness badge:** Shows "Updated: [timestamp]" when backend `meta.last_updated` is available; otherwise hidden.

---

#### Zone: Fulfillment KPI Cards (4× `EnhancedKPICard`)

##### Component 1: Total Orders

| Field | Specification |
|-------|---------------|
| **Component name** | `EnhancedKPICard` (reuse as-is) |
| **Title text** | "Total Orders" |
| **Purpose** | Gives the user an at-a-glance count of order volume over the selected period to gauge workload. |
| **Metrics shown** | **Value:** Count of all orders in selected date range. **Trend %:** `(current_period_count − prior_period_count) / prior_period_count × 100`. Unit: count. Time basis: selected date range vs. prior equivalent period. **Sparkline:** Daily order count mini-chart. |
| **Dimensional breakdowns** | N/A (aggregate card). |
| **Sorting & Top-N rules** | N/A. |
| **Interactions** | Hover: tooltip shows exact count + prior period count. Click: no action. |
| **Empty state** | "No orders found for the selected filters." |
| **Loading state** | Skeleton card (matching existing `EnhancedKPICard` skeleton). |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | "Demo" badge when using mock data. |

##### Component 2: Avg Fulfillment Time

| Field | Specification |
|-------|---------------|
| **Component name** | `EnhancedKPICard` (reuse as-is) |
| **Title text** | "Avg Fulfillment Time" |
| **Purpose** | Helps the user assess whether fulfillment speed is improving or degrading. |
| **Metrics shown** | **Value:** `SUM(fulfillment_time_hours) / COUNT(fulfilled_orders)`, displayed as days + hours (e.g., "2d 14h"). **Trend %:** vs. prior period. **Secondary text:** "Order creation → last item fulfilled". **Sparkline:** Daily average fulfillment time. |
| **Dimensional breakdowns** | N/A (aggregate card). |
| **Sorting & Top-N rules** | N/A. |
| **Interactions** | Hover: tooltip shows exact hours + prior period value. |
| **Empty state** | "No fulfilled orders in selected period." |
| **Loading state** | Skeleton card. |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | Alert styling (red border) if avg fulfillment time > SLA Threshold. |

##### Component 3: SLA Compliance Rate

| Field | Specification |
|-------|---------------|
| **Component name** | `EnhancedKPICard` (reuse as-is) |
| **Title text** | "SLA Compliance" |
| **Purpose** | Tells the user what percentage of orders met the SLA target so they can assess overall pipeline health. |
| **Metrics shown** | **Value:** `COUNT(orders WHERE fulfillment_time ≤ SLA_threshold) / COUNT(all_fulfilled_orders) × 100`. Unit: %. **Trend %:** vs. prior period. **Secondary text:** "Within [N]-day SLA" (dynamically reflects the SLA Threshold filter). **Sparkline:** Daily compliance rate. |
| **Dimensional breakdowns** | N/A (aggregate card). |
| **Sorting & Top-N rules** | N/A. |
| **Interactions** | Hover: tooltip shows numerator/denominator. Click on card scrolls to SLA Breach Watch zone. |
| **Empty state** | "No fulfilled orders to calculate compliance." |
| **Loading state** | Skeleton card. |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | Alert styling (red border + "SLA At Risk" badge) when compliance < 90%. Threshold is visual-only, not configurable (hardcoded at 90% for the alert trigger). |

##### Component 4: Orders Approaching Breach

| Field | Specification |
|-------|---------------|
| **Component name** | `EnhancedKPICard` (reuse as-is, with alert styling) |
| **Title text** | "Approaching Breach" |
| **Purpose** | Alerts the user to orders that will breach SLA within the warning window so they can take preventive action. |
| **Metrics shown** | **Value:** Count of pending orders where `(SLA_threshold − days_since_creation) ≤ Breach_Warning_days AND (SLA_threshold − days_since_creation) > 0`. Unit: count. **Trend %:** vs. prior period snapshot. **Secondary text:** "Within [N]-day warning window" (reflects Breach Warning filter). |
| **Dimensional breakdowns** | N/A (aggregate card). |
| **Sorting & Top-N rules** | N/A. |
| **Interactions** | Hover: tooltip shows count. Click: scrolls to SLA Breach Watch zone. |
| **Empty state** | Value shows "0" with green styling — "All clear." |
| **Loading state** | Skeleton card. |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | Alert styling (amber border) when count > 0. Red border + "SLA Breached" badge when any orders have already exceeded SLA (i.e., `days_since_creation > SLA_threshold`). |

---

#### Zone: Order Status Breakdown (`CompactDonut`)

| Field | Specification |
|-------|---------------|
| **Component name** | `CompactDonut` (reuse as-is) |
| **Title text** | "Order Status Breakdown" |
| **Purpose** | Shows the distribution of orders across fulfillment statuses to identify bottlenecks. |
| **Metrics shown** | Three segments: **Fulfilled** (count + %), **Pending** (count + %), **Failed** (count + %). Unit: count. Time basis: selected date range. |
| **Dimensional breakdowns** | Segments: Fulfilled, Pending, Failed. No further breakdown toggle. |
| **Sorting & Top-N rules** | Segments ordered: Fulfilled → Pending → Failed (largest status first by convention, but fixed order for consistency). |
| **Interactions** | Segment click applies Order Status filter (e.g., clicking "Failed" filters the entire page to failed orders). Hover tooltip: status name + count + percentage. |
| **Empty state** | "No orders found for the selected filters." |
| **Loading state** | Skeleton card. |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | "Demo" badge when using mock data. |

---

#### Zone: Fulfillment Time Trend (`DualAxisChart`)

| Field | Specification |
|-------|---------------|
| **Component name** | `DualAxisChart` (reuse with minor adaptation — second axis is avg fulfillment time instead of revenue) |
| **Title text** | "Fulfillment Volume & Speed" |
| **Purpose** | Helps the user correlate order volume changes with fulfillment speed over time to spot capacity constraints. |
| **Metrics shown** | **Bar (left axis):** Order count per time bucket. **Line (right axis):** Avg fulfillment time (hours) per time bucket. **Granularity toggle:** Day / Week / Month. |
| **Dimensional breakdowns** | Time-based only. |
| **Sorting & Top-N rules** | Chronological (ascending). |
| **Interactions** | Granularity toggle (Day/Week/Month). Swap Axis control. Hover tooltip: date, order count, avg fulfillment time. Anomaly highlighting: bars turn red when fulfillment time anomaly flags are present. Export: CSV, PNG via toolbar. |
| **Empty state** | "No data available for the selected period." |
| **Loading state** | Skeleton card. |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | Anomaly count in legend when anomalies are present. "Demo" badge when using mock data. |

---

#### Zone: SLA Breach Watch (`StuckOrdersList`-style → `SLABreachList`)

| Field | Specification |
|-------|---------------|
| **Component name** | `SLABreachList` (new component, modeled on `StuckOrdersList`) — Operational list with SLA-specific columns. |
| **Title text** | "SLA Breach Watch — Attention Required" |
| **Purpose** | Lists the specific orders closest to or past SLA breach so the user can take immediate action. |
| **Metrics shown** | Per row: **Order ID**, **Entity** (client name), **Brand**, **Status** (badge: Pending / Failed), **Age** (days since creation), **SLA Remaining** (days until breach; negative = breached), **Failure Category** (if failed). |
| **Dimensional breakdowns** | Filterable by Entity, Brand, Status via global/operational filters. |
| **Sorting & Top-N rules** | Default sort: SLA Remaining ascending (most urgent first). Configurable: sort by Age, Entity, Brand. **Top 50 shown** with "View All" button to expand or navigate to a full list. |
| **Interactions** | Row click: opens order detail (drilldown, implementation-dependent). "View All" button expands the list. Hover tooltip on SLA Remaining: exact datetime of breach. Export: CSV. |
| **Empty state** | "No orders approaching SLA breach. All clear! ✓" |
| **Loading state** | Skeleton list (matching `StuckOrdersList` pattern). |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | **"SLA Breached"** red badge on rows where SLA Remaining < 0. **Amber highlight** on rows where SLA Remaining ≤ Breach Warning threshold. **"Top 50 shown"** badge when list is truncated. |

---

#### Zone: SLA Performance by Entity & Brand (`ClientLeaderboard`-style → `SLALeaderboard`)

| Field | Specification |
|-------|---------------|
| **Component name** | `SLALeaderboard` (new component, modeled on `ClientLeaderboard`) — Sortable table with SLA metrics per entity/brand. |
| **Title text** | "SLA Performance by Entity" |
| **Purpose** | Lets the user compare SLA compliance across entities and brands to identify underperformers. |
| **Metrics shown** | Per row: **Entity Name**, **Brand** (or "All" when grouped by entity only), **Total Orders** (count), **SLA Compliance %** (`fulfilled_within_SLA / total_fulfilled × 100`), **Avg Fulfillment Time** (days), **Breached Orders** (count). |
| **Dimensional breakdowns** | Toggle: **By Entity** / **By Brand** (similar to Products/Brands toggle in `TopPerformersChart`). |
| **Sorting & Top-N rules** | Default sort: SLA Compliance % ascending (worst performers first). Configurable: sort by any column. **Top 20** shown with "View All" button. |
| **Interactions** | Column header click to sort. Row click applies Entity/Brand filter to the page. Hover tooltip: full entity name (if truncated). Export: CSV. |
| **Empty state** | "No SLA data available. Adjust your filters or date range." |
| **Loading state** | Skeleton table. |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | Red text styling on SLA Compliance % when < 85%. "Top 20 shown" badge when truncated. |

---

#### Zone: Supplier Delivery Performance (`TopPerformersChart`-style → `SupplierDeliveryChart`)

| Field | Specification |
|-------|---------------|
| **Component name** | `SupplierDeliveryChart` (new component, modeled on `TopPerformersChart` — horizontal bar chart with dual metric) |
| **Title text** | "Supplier Delivery Performance" |
| **Purpose** | Compares supplier delivery times to identify slow suppliers and support procurement decisions. |
| **Metrics shown** | Per supplier: **Avg PO-to-Receipt Time** (days) — stacked bar segment 1, **Avg Receipt-to-Invoice Time** (days) — stacked bar segment 2. Formula: PO-to-Receipt = `AVG(item_received_at − po_created_at)`. Receipt-to-Invoice = `AVG(invoice_issued_at − item_received_at)`. |
| **Dimensional breakdowns** | Toggle: **By Supplier** / **By Brand** / **By Product**. |
| **Sorting & Top-N rules** | Default sort: Total delivery time (PO-to-Invoice) descending (slowest first). **Top 10** shown. |
| **Interactions** | Dimension toggle (Supplier/Brand/Product). Hover tooltip: supplier name, PO-to-Receipt days, Receipt-to-Invoice days, total days, PO count. Bar click: applies Supplier filter. Export: CSV, PNG. |
| **Empty state** | "No supplier delivery data available for the selected filters." |
| **Loading state** | Skeleton card. |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | "Demo" badge when using mock data. Warning icon next to suppliers where total delivery time > 2× the average across all suppliers. |

---

### PAGE 2: Support & Ticketing (`/ops/support`)

#### Page Header

- **Title:** "Support & Ticketing"
- **Subtitle:** "Track ticket volume, response times, and resolution performance across all support channels."
- **Freshness badge:** Shows "Updated: [timestamp]" when backend `meta.last_updated` is available; otherwise hidden.

#### Page-Level Filter Strip

Rendered below the global filter bar: **Ticket Channel**, **Ticket Status**, **Issue Type**, **Program** (see Section 2.2 for specs).

---

#### Zone: Support KPI Cards (4× `EnhancedKPICard`)

##### Component 1: Total Tickets

| Field | Specification |
|-------|---------------|
| **Component name** | `EnhancedKPICard` (reuse as-is) |
| **Title text** | "Total Tickets" |
| **Purpose** | Shows the overall support workload for the selected period. |
| **Metrics shown** | **Value:** Count of all tickets created in selected date range. **Trend %:** vs. prior period. **Sparkline:** Daily ticket creation count. |
| **Dimensional breakdowns** | N/A (aggregate card). |
| **Sorting & Top-N rules** | N/A. |
| **Interactions** | Hover: tooltip shows exact count + prior period count. |
| **Empty state** | "No tickets found for the selected filters." |
| **Loading state** | Skeleton card. |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | "Demo" badge when using mock data. |

##### Component 2: Avg Acknowledgement Time

| Field | Specification |
|-------|---------------|
| **Component name** | `EnhancedKPICard` (reuse as-is) |
| **Title text** | "Avg Acknowledgement Time" |
| **Purpose** | Tells the user how quickly the team is responding to new tickets. |
| **Metrics shown** | **Value:** `SUM(first_response_time) / COUNT(acknowledged_tickets)`. Displayed as hours + minutes (e.g., "4h 23m"). **Trend %:** vs. prior period. **Secondary text:** "Time to first response". **Sparkline:** Daily average acknowledgement time. |
| **Dimensional breakdowns** | N/A (aggregate card). |
| **Sorting & Top-N rules** | N/A. |
| **Interactions** | Hover: tooltip shows exact minutes + prior period value. |
| **Empty state** | "No acknowledged tickets in selected period." |
| **Loading state** | Skeleton card. |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | Alert styling (amber border) when avg acknowledgement time > 24h. |

##### Component 3: Avg Resolution Time

| Field | Specification |
|-------|---------------|
| **Component name** | `EnhancedKPICard` (reuse as-is) |
| **Title text** | "Avg Resolution Time" |
| **Purpose** | Measures how long it takes to fully resolve tickets, indicating support efficiency. |
| **Metrics shown** | **Value:** `SUM(resolution_time) / COUNT(resolved_tickets)`. Displayed as days + hours (e.g., "1d 8h"). **Trend %:** vs. prior period. **Secondary text:** "Ticket creation → resolution". **Sparkline:** Daily average resolution time. |
| **Dimensional breakdowns** | N/A (aggregate card). |
| **Sorting & Top-N rules** | N/A. |
| **Interactions** | Hover: tooltip shows exact hours + prior period value. |
| **Empty state** | "No resolved tickets in selected period." |
| **Loading state** | Skeleton card. |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | Alert styling (red border) when avg resolution time exceeds 3 days. |

##### Component 4: Unresolved Tickets

| Field | Specification |
|-------|---------------|
| **Component name** | `EnhancedKPICard` (reuse as-is, with alert styling) |
| **Title text** | "Unresolved Tickets" |
| **Purpose** | Shows the current backlog of open tickets so the team lead can assess capacity needs. |
| **Metrics shown** | **Value:** Count of tickets where status ∈ {Open, In Progress} as of now (point-in-time, not period-based). **Trend %:** vs. same metric at the start of the selected date range. **Secondary text:** "[X] open · [Y] in progress". |
| **Dimensional breakdowns** | N/A (aggregate card). |
| **Sorting & Top-N rules** | N/A. |
| **Interactions** | Hover: tooltip shows open vs. in-progress breakdown. Click: scrolls to Unresolved Tickets table. |
| **Empty state** | Value shows "0" with green styling — "All caught up!" |
| **Loading state** | Skeleton card. |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | Alert styling (amber border) when count > 50. Red border + "Backlog Alert" badge when count > 100. |

---

#### Zone: Tickets by Channel (`CompactDonut`)

| Field | Specification |
|-------|---------------|
| **Component name** | `CompactDonut` (reuse as-is) |
| **Title text** | "Tickets by Channel" |
| **Purpose** | Shows the distribution of support tickets across channels to guide staffing decisions. |
| **Metrics shown** | Segments: one per channel (Email, Phone, Live Chat, Web Form, Social, Other). Each shows count + percentage. |
| **Dimensional breakdowns** | Segments by channel. |
| **Sorting & Top-N rules** | Segments ordered by count descending. |
| **Interactions** | Segment click applies Ticket Channel filter. Hover tooltip: channel name, count, percentage. |
| **Empty state** | "No tickets found for the selected filters." |
| **Loading state** | Skeleton card. |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | "Demo" badge when using mock data. |

---

#### Zone: Tickets by Issue Type (`TopPerformersChart`-style → `IssueTypeChart`)

| Field | Specification |
|-------|---------------|
| **Component name** | `IssueTypeChart` (new component, modeled on `TopPerformersChart` — horizontal bar chart with status stacking) |
| **Title text** | "Tickets by Issue Type" |
| **Purpose** | Identifies which issue types generate the most support volume so teams can prioritize process improvements. |
| **Metrics shown** | Per issue type: stacked bar showing **Open** (count), **In Progress** (count), **Resolved** (count), **Closed** (count). |
| **Dimensional breakdowns** | Toggle: **By Issue Type** / **By Program**. |
| **Sorting & Top-N rules** | Default sort: Total ticket count descending. **Top 10** shown. |
| **Interactions** | Dimension toggle (Issue Type / Program). Hover tooltip: issue type, status breakdown counts. Bar click: applies Issue Type or Program filter. Export: CSV, PNG. |
| **Empty state** | "No tickets found for the selected filters." |
| **Loading state** | Skeleton card. |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | "Demo" badge when using mock data. |

---

#### Zone: Ticket Volume Trend (`DualAxisChart`)

| Field | Specification |
|-------|---------------|
| **Component name** | `DualAxisChart` (reuse with adaptation — axes are ticket volume + avg resolution time) |
| **Title text** | "Ticket Volume & Resolution Trend" |
| **Purpose** | Helps the user spot trends in ticket volume relative to resolution speed over time. |
| **Metrics shown** | **Bar (left axis):** Ticket count per time bucket. **Line (right axis):** Avg resolution time (hours) per time bucket. **Granularity toggle:** Day / Week / Month. |
| **Dimensional breakdowns** | Time-based only. |
| **Sorting & Top-N rules** | Chronological (ascending). |
| **Interactions** | Granularity toggle (Day/Week/Month). Swap Axis control. Hover tooltip: date, ticket count, avg resolution time. Export: CSV, PNG. |
| **Empty state** | "No data available for the selected period." |
| **Loading state** | Skeleton card. |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | Anomaly count in legend when anomalies are present. |

---

#### Zone: Unresolved Tickets List (`StuckOrdersList`-style → `UnresolvedTicketsList`)

| Field | Specification |
|-------|---------------|
| **Component name** | `UnresolvedTicketsList` (new component, modeled on `StuckOrdersList`) — Operational list for open/in-progress tickets. |
| **Title text** | "Unresolved Tickets — Attention Required" |
| **Purpose** | Lists specific unresolved tickets so the support lead can triage and assign the oldest or most critical cases. |
| **Metrics shown** | Per row: **Ticket ID**, **Channel** (badge), **Issue Type**, **Program**, **Status** (badge: Open / In Progress), **Age** (days since creation), **Last Updated** (relative time). |
| **Dimensional breakdowns** | Filterable via page-level filters (Channel, Status, Issue Type, Program). |
| **Sorting & Top-N rules** | Default sort: Age descending (oldest first). Configurable: sort by Channel, Issue Type, Last Updated. **Top 50 shown** with "View All" button. |
| **Interactions** | Row click: opens ticket detail (drilldown, implementation-dependent). "View All" expands or navigates. Hover tooltip on Age: exact creation datetime. Export: CSV. |
| **Empty state** | "No unresolved tickets. All caught up! ✓" |
| **Loading state** | Skeleton list. |
| **Error state** | Inline error card with "Retry" button. |
| **Warnings / badges** | Red highlight on rows where Age > 7 days. **"Top 50 shown"** badge when list is truncated. |

---

### AI Chat Sidebar (Both Pages)

The "Ask AI" sidebar is present on both pages, matching the existing shell pattern. Suggested questions are updated to reflect operational context:

**Suggested Questions — Order Fulfillment Page:**
- "Which entities have the worst SLA compliance this month?"
- "What are the top failure categories for failed orders?"
- "Show me the trend in fulfillment time over the last 90 days."
- "Which suppliers have the longest delivery times?"

**Suggested Questions — Support & Ticketing Page:**
- "What is the average resolution time by channel this week?"
- "Which issue types have the highest unresolved ticket count?"
- "Show me ticket volume trends for the last quarter."
- "Which programs generate the most support tickets?"

---

## SECTION 4 — Wireframe-Style Layout Diagrams

### Page 1: Order Fulfillment — Desktop (12-Column Grid)

```
┌─────────────────────────────────────────────────────────────┐
│ Sticky Header: Logo + "Munero AI Platform" | Nav Tabs:      │
│ [Order Fulfillment] [Support & Ticketing]  | Ask AI | 🟢 Live│
├─────────────────────────────────────────────────────────────┤
│ Global Filter Bar: Date Range | Currency | Country |         │
│ Product Type | Order Status | SLA Days | [More Filters] [⟲] │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ Total Orders │ Avg Fulfill  │ SLA          │ Approaching    │
│              │ Time         │ Compliance   │ Breach         │
│ (3 cols)     │ (3 cols)     │ (3 cols)     │ (3 cols)       │
├──────────────┴──────────────┼──────────────┴────────────────┤
│ Order Status Breakdown      │ Fulfillment Volume & Speed    │
│ (CompactDonut)              │ (DualAxisChart)               │
│ (4 cols)                    │ (8 cols)                      │
├─────────────────────────────┴───────────────────────────────┤
│ SLA Breach Watch — Attention Required                       │
│ (SLABreachList — 12 cols)                                   │
├─────────────────────────────────────────────────────────────┤
│ SLA Performance by Entity          │ Supplier Delivery      │
│ (SLALeaderboard)                   │ Performance            │
│ (7 cols)                           │ (5 cols)               │
└────────────────────────────────────┴────────────────────────┘
```

### Page 1: Order Fulfillment — Mobile (Single Column)

1. **KPI Cards** — 2×2 grid (each card 50% width)
2. **Order Status Breakdown** (CompactDonut) — full width
3. **Fulfillment Volume & Speed** (DualAxisChart) — full width, horizontal scroll enabled for time axis
4. **SLA Breach Watch** (SLABreachList) — full width, horizontally scrollable table
5. **SLA Performance by Entity** (SLALeaderboard) — full width, horizontally scrollable table
6. **Supplier Delivery Performance** (SupplierDeliveryChart) — full width

**Mobile-specific changes:**
- KPI cards stack as a 2×2 grid instead of 4-across
- Tables become horizontally scrollable
- Charts maintain full width with touch-friendly tooltips
- "View All" buttons become more prominent (full-width)

---

### Page 2: Support & Ticketing — Desktop (12-Column Grid)

```
┌─────────────────────────────────────────────────────────────┐
│ Sticky Header: Logo + "Munero AI Platform" | Nav Tabs:      │
│ [Order Fulfillment] [Support & Ticketing]  | Ask AI | 🟢 Live│
├─────────────────────────────────────────────────────────────┤
│ Global Filter Bar: Date Range | Currency | Country |         │
│ Product Type | Order Status | SLA Days | [More Filters] [⟲] │
├─────────────────────────────────────────────────────────────┤
│ Page Filters: Channel | Ticket Status | Issue Type | Program │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ Total        │ Avg Ack      │ Avg          │ Unresolved     │
│ Tickets      │ Time         │ Resolution   │ Tickets        │
│ (3 cols)     │ (3 cols)     │ (3 cols)     │ (3 cols)       │
├──────────────┴──────────────┼──────────────┴────────────────┤
│ Tickets by Channel          │ Tickets by Issue Type         │
│ (CompactDonut)              │ (IssueTypeChart)              │
│ (4 cols)                    │ (8 cols)                      │
├─────────────────────────────┴───────────────────────────────┤
│ Ticket Volume & Resolution Trend                            │
│ (DualAxisChart — 12 cols)                                   │
├─────────────────────────────────────────────────────────────┤
│ Unresolved Tickets — Attention Required                     │
│ (UnresolvedTicketsList — 12 cols)                           │
└─────────────────────────────────────────────────────────────┘
```

### Page 2: Support & Ticketing — Mobile (Single Column)

1. **KPI Cards** — 2×2 grid (each card 50% width)
2. **Tickets by Channel** (CompactDonut) — full width
3. **Tickets by Issue Type** (IssueTypeChart) — full width
4. **Ticket Volume & Resolution Trend** (DualAxisChart) — full width, horizontal scroll for time axis
5. **Unresolved Tickets** (UnresolvedTicketsList) — full width, horizontally scrollable table

**Mobile-specific changes:**
- Page-level filter strip collapses into a "Filters" dropdown button
- KPI cards stack as 2×2 grid
- Tables become horizontally scrollable
- Charts maintain full width with touch-friendly tooltips

---

## SECTION 5 — Mock Data Examples

> ⚠️ MOCK DATA — for illustration only

### Page 1: Order Fulfillment — KPI Cards

| Card | Value | Trend % | Direction | Secondary Text |
|------|-------|---------|-----------|----------------|
| Total Orders | 12,847 | +8.3% | ↑ (green) | "vs. prior 30 days" |
| Avg Fulfillment Time | 2d 14h | −12.1% | ↓ (green, lower is better) | "Order creation → last item fulfilled" |
| SLA Compliance | 91.4% | +2.3% | ↑ (green) | "Within 7-day SLA" |
| Approaching Breach | 23 | +15.0% | ↑ (red, higher is worse) | "Within 2-day warning window" |

### Page 1: Order Status Breakdown (Donut)

| Segment | Count | Percentage |
|---------|-------|------------|
| Fulfilled | 11,203 | 87.2% |
| Pending | 1,389 | 10.8% |
| Failed | 255 | 2.0% |

### Page 1: Fulfillment Volume & Speed (Time Series — 3 Data Points)

| Date | Order Count | Avg Fulfillment Time (hours) |
|------|-------------|------------------------------|
| 2026-01-15 | 428 | 58 |
| 2026-01-22 | 451 | 62 |
| 2026-01-29 | 410 | 54 |

### Page 1: SLA Breach Watch (3 Sample Rows)

| Order ID | Entity | Brand | Status | Age (days) | SLA Remaining | Failure Category |
|----------|--------|-------|--------|------------|---------------|------------------|
| ORD-78421 | Acme Corp | BrandX | Pending | 6 | **1 day** ⚠️ | — |
| ORD-78390 | GlobalTech | BrandY | Failed | 8 | **−1 day** 🔴 **SLA Breached** | Payment Failure |
| ORD-78455 | RetailCo | BrandZ | Pending | 5 | 2 days | — |

### Page 1: SLA Performance by Entity (3 Sample Rows)

| Entity | Total Orders | SLA Compliance % | Avg Fulfillment Time | Breached Orders |
|--------|-------------|-------------------|----------------------|-----------------|
| Acme Corp | 3,241 | **78.2%** 🔴 | 3d 2h | 42 |
| GlobalTech | 2,890 | 94.1% | 1d 18h | 8 |
| RetailCo | 1,756 | 96.8% | 1d 6h | 3 |

### Page 1: Supplier Delivery Performance (3 Sample Bars)

| Supplier | PO-to-Receipt (days) | Receipt-to-Invoice (days) | Total (days) |
|----------|----------------------|---------------------------|-------------|
| Supplier Alpha | 12 | 5 | 17 ⚠️ (>2× avg) |
| Supplier Beta | 7 | 3 | 10 |
| Supplier Gamma | 6 | 2 | 8 |

### Page 2: Support & Ticketing — KPI Cards

| Card | Value | Trend % | Direction | Secondary Text |
|------|-------|---------|-----------|----------------|
| Total Tickets | 1,842 | +5.7% | ↑ (neutral) | "vs. prior 30 days" |
| Avg Acknowledgement Time | 4h 23m | −18.5% | ↓ (green, lower is better) | "Time to first response" |
| Avg Resolution Time | 1d 8h | +3.2% | ↑ (red, higher is worse) | "Ticket creation → resolution" |
| Unresolved Tickets | 127 | +22.1% | ↑ (red) | "89 open · 38 in progress" — **Backlog Alert** |

### Page 2: Tickets by Channel (Donut)

| Channel | Count | Percentage |
|---------|-------|------------|
| Email | 743 | 40.3% |
| Live Chat | 512 | 27.8% |
| Phone | 298 | 16.2% |
| Web Form | 187 | 10.2% |
| Social | 68 | 3.7% |
| Other | 34 | 1.8% |

### Page 2: Tickets by Issue Type (3 Sample Bars)

| Issue Type | Open | In Progress | Resolved | Closed | Total |
|------------|------|-------------|----------|--------|-------|
| Order Inquiry | 34 | 12 | 289 | 410 | 745 |
| Return/Refund | 28 | 15 | 178 | 245 | 466 |
| Product Defect | 19 | 8 | 102 | 134 | 263 |

### Page 2: Ticket Volume & Resolution Trend (3 Data Points)

| Date | Ticket Count | Avg Resolution Time (hours) |
|------|-------------|------------------------------|
| 2026-01-15 | 62 | 30 |
| 2026-01-22 | 71 | 34 |
| 2026-01-29 | 58 | 28 |

### Page 2: Unresolved Tickets (3 Sample Rows)

| Ticket ID | Channel | Issue Type | Program | Status | Age (days) | Last Updated |
|-----------|---------|------------|---------|--------|------------|-------------|
| TKT-9021 | Email | Return/Refund | Loyalty | Open | **12 days** 🔴 | 3 days ago |
| TKT-9187 | Live Chat | Order Inquiry | Standard | In Progress | 4 days | 2 hours ago |
| TKT-9203 | Phone | Product Defect | Premium | Open | 2 days | 1 day ago |

### Alert/Warning State Example

> **SLA Breach Alert (Page 1):** Order ORD-78390 (GlobalTech / BrandY) has exceeded the 7-day SLA by 1 day. The "Approaching Breach" KPI card shows 23 orders in the warning window. The SLA Compliance card displays 91.4% with the secondary text "Within 7-day SLA." Entity "Acme Corp" shows SLA Compliance of 78.2% in the leaderboard table, highlighted in red.

> **Backlog Alert (Page 2):** Unresolved Tickets KPI card shows 127 with a red "Backlog Alert" badge (threshold: >100). Ticket TKT-9021 has been open for 12 days, highlighted in red in the Unresolved Tickets list.

---

## SECTION 6 — Implementation Notes (High Level)

### 6.1 Data Requirements per Component

#### Endpoint Group 1: `/api/ops/fulfillment`

| Component | Required Fields |
|-----------|----------------|
| **KPI Cards** (all 4) | `total_orders` (int), `total_orders_prior` (int), `avg_fulfillment_time_hours` (float), `avg_fulfillment_time_prior` (float), `sla_compliance_pct` (float), `sla_compliance_prior` (float), `sla_compliant_count` (int), `total_fulfilled_count` (int), `approaching_breach_count` (int), `approaching_breach_prior` (int), `sparklines` (object: daily arrays for each metric) |
| **Order Status Breakdown** | `status_counts` (object: `{fulfilled: int, pending: int, failed: int}`) |
| **Fulfillment Time Trend** | `time_series[]` (array: `{date, order_count, avg_fulfillment_hours, anomaly_flag}`) |
| **SLA Breach Watch** | `breach_orders[]` (array: `{order_id, entity, brand, status, created_at, sla_remaining_days, failure_category}`) |
| **SLA Leaderboard** | `entity_sla[]` (array: `{entity_name, brand, total_orders, sla_compliance_pct, avg_fulfillment_days, breached_count}`) |

#### Endpoint Group 2: `/api/ops/supplier-delivery`

| Component | Required Fields |
|-----------|----------------|
| **Supplier Delivery Chart** | `suppliers[]` (array: `{name, avg_po_to_receipt_days, avg_receipt_to_invoice_days, po_count}`) |

#### Endpoint Group 3: `/api/ops/support`

| Component | Required Fields |
|-----------|----------------|
| **KPI Cards** (all 4) | `total_tickets` (int), `total_tickets_prior` (int), `avg_ack_time_minutes` (float), `avg_ack_time_prior` (float), `avg_resolution_time_hours` (float), `avg_resolution_prior` (float), `unresolved_count` (int), `unresolved_open` (int), `unresolved_in_progress` (int), `unresolved_prior` (int), `sparklines` (object) |
| **Tickets by Channel** | `channel_counts[]` (array: `{channel, count}`) |
| **Tickets by Issue Type** | `issue_type_breakdown[]` (array: `{issue_type, open, in_progress, resolved, closed}`) |
| **Ticket Volume Trend** | `time_series[]` (array: `{date, ticket_count, avg_resolution_hours, anomaly_flag}`) |
| **Unresolved Tickets** | `unresolved_tickets[]` (array: `{ticket_id, channel, issue_type, program, status, created_at, updated_at}`) |

### 6.2 Suggested Endpoint Shapes

#### Example 1: Fulfillment KPIs + Status Breakdown

**Request:** `GET /api/ops/fulfillment/summary?start_date=2026-01-01&end_date=2026-01-31&currency=USD&sla_days=7&breach_warning_days=2`

**Response:**
```json
{
  "meta": { "last_updated": "2026-01-31T14:30:00Z" },
  "kpis": {
    "total_orders": 12847,
    "total_orders_prior": 11860,
    "avg_fulfillment_time_hours": 62.4,
    "avg_fulfillment_time_prior_hours": 71.0,
    "sla_compliance_pct": 91.4,
    "sla_compliance_prior_pct": 89.1,
    "sla_compliant_count": 10240,
    "total_fulfilled_count": 11203,
    "approaching_breach_count": 23,
    "approaching_breach_prior_count": 20
  },
  "sparklines": {
    "total_orders": [410, 428, 451, 410, 438],
    "avg_fulfillment_hours": [58, 62, 54, 60, 55]
  },
  "status_breakdown": {
    "fulfilled": 11203,
    "pending": 1389,
    "failed": 255
  }
}
```

#### Example 2: SLA Breach Watch List

**Request:** `GET /api/ops/fulfillment/breach-watch?sla_days=7&breach_warning_days=2&sort=sla_remaining&order=asc&limit=50`

**Response:**
```json
{
  "total_count": 23,
  "showing": 23,
  "orders": [
    {
      "order_id": "ORD-78390",
      "entity": "GlobalTech",
      "brand": "BrandY",
      "status": "failed",
      "created_at": "2026-01-23T09:15:00Z",
      "sla_remaining_days": -1,
      "failure_category": "Payment Failure"
    },
    {
      "order_id": "ORD-78421",
      "entity": "Acme Corp",
      "brand": "BrandX",
      "status": "pending",
      "created_at": "2026-01-25T11:30:00Z",
      "sla_remaining_days": 1,
      "failure_category": null
    }
  ]
}
```

#### Example 3: Support Ticket Breakdown

**Request:** `GET /api/ops/support/breakdown?start_date=2026-01-01&end_date=2026-01-31&group_by=issue_type`

**Response:**
```json
{
  "meta": { "last_updated": "2026-01-31T14:30:00Z" },
  "breakdown": [
    {
      "dimension": "Order Inquiry",
      "open": 34,
      "in_progress": 12,
      "resolved": 289,
      "closed": 410,
      "total": 745
    },
    {
      "dimension": "Return/Refund",
      "open": 28,
      "in_progress": 15,
      "resolved": 178,
      "closed": 245,
      "total": 466
    }
  ]
}
```

### 6.3 Reuse Opportunities

| Category | Component | Notes |
|----------|-----------|-------|
| **Reuse as-is** | `EnhancedKPICard` | Used for all 8 KPI cards (4 per page). No changes needed — metric definitions and alert thresholds are data-driven. |
| **Reuse as-is** | `CompactDonut` | Used for "Order Status Breakdown" and "Tickets by Channel." Same segment-click-to-filter behavior. |
| **Reuse as-is** | Sticky Header | Same shell pattern: logo, nav tabs (new tab names), Ask AI button, live indicator. |
| **Reuse as-is** | Global Filter Bar | Same component with new filter inputs injected into the primary bar and "More Filters" popover. |
| **Reuse as-is** | AI Chat Sidebar | Same interaction model; only suggested questions change. |
| **Minor adaptation** | `DualAxisChart` | Used for "Fulfillment Volume & Speed" and "Ticket Volume & Resolution Trend." Axis labels and metric names change; core component logic is identical. |
| **Minor adaptation** | `TopPerformersChart` | Adapted for "Supplier Delivery Performance" (stacked horizontal bars with delivery-time segments) and "Tickets by Issue Type" (stacked by status). Toggle labels change. |
| **Minor adaptation** | `ClientLeaderboard` | Adapted for "SLA Performance by Entity." Column definitions change; sort/select mechanics are identical. |
| **Minor adaptation** | `StuckOrdersList` | Adapted for "SLA Breach Watch" and "Unresolved Tickets." Column definitions and badge logic change; list chrome (actions, View All, skeleton) is identical. |
| **Net-new** | None | All components are adaptations of existing patterns. No fundamentally new visualization type is required. |

### 6.4 Performance Considerations

| Concern | Strategy |
|---------|----------|
| **SLA Breach Watch list** | Server-side sort + limit. Default Top 50. "View All" loads paginated (50 per page). |
| **SLA Leaderboard** | Default Top 20 entities. "View All" navigates to full paginated table view. |
| **Supplier Delivery Chart** | Top 10 suppliers by total delivery time. "Others" bucket aggregates the rest. |
| **Unresolved Tickets list** | Server-side sort + limit. Default Top 50. "View All" loads paginated. |
| **Ticket Issue Type Chart** | Top 10 issue types by total count. |
| **Time series charts** | Day granularity limited to 90-day windows. Week/Month granularity supports up to 2 years. Server returns pre-aggregated buckets. |
| **Caching** | KPI summary endpoints: cache for 5 minutes (operational data changes frequently). Trend/time-series: cache for 15 minutes. Breach watch/unresolved lists: cache for 2 minutes (urgent data). Filter options: cache for 1 hour. |
| **Client-side aggregation** | Minimal. All aggregations (SLA compliance %, averages, status counts) are computed server-side. Client only renders. |
| **"Top N shown" badge** | Applied to SLA Breach Watch (Top 50), SLA Leaderboard (Top 20), Supplier Delivery (Top 10), Unresolved Tickets (Top 50), Issue Type Chart (Top 10). Badge text dynamically reflects the limit. |

---

## SECTION 7 — Acceptance Criteria & QA Checklist

### Core Checklist

- [ ] Every wishlist item from §APPENDIX A is addressed by at least one component:
  - [ ] Order status breakdown → "Order Status Breakdown" (`CompactDonut`)
  - [ ] Average fulfillment time → "Avg Fulfillment Time" KPI card + "Fulfillment Volume & Speed" trend
  - [ ] SLA compliance tracking → "SLA Compliance" KPI card + "SLA Performance by Entity" table
  - [ ] Orders approaching SLA breach → "Approaching Breach" KPI card + "SLA Breach Watch" list
  - [ ] Entity-wise, brand-wise SLA performance → "SLA Performance by Entity" with Entity/Brand toggle
  - [ ] Tickets by channel → "Tickets by Channel" (`CompactDonut`)
  - [ ] Tickets by program, issue type → "Tickets by Issue Type" chart with Issue Type/Program toggle
  - [ ] Average acknowledgement time → "Avg Acknowledgement Time" KPI card
  - [ ] Average resolution time → "Avg Resolution Time" KPI card + trend line in "Ticket Volume & Resolution Trend"
  - [ ] Volume of unresolved tickets → "Unresolved Tickets" KPI card + "Unresolved Tickets" list
  - [ ] Average supplier delivery time → "Supplier Delivery Performance" chart (PO-to-Receipt + Receipt-to-Invoice)
  - [ ] Breakdown by supplier, brand, product → "Supplier Delivery Performance" with Supplier/Brand/Product toggle
- [ ] All KPI definitions include formulas and units.
- [ ] Visual language matches the existing Munero dashboard (zone naming, card style, badge patterns, color conventions).
- [ ] Filter bar includes all required operational filters with correct placement.
- [ ] AI sidebar is present with domain-relevant suggested questions (4 per page).
- [ ] Empty, loading, and error states are defined for every component.
- [ ] Wireframes are provided for desktop and mobile (both pages).
- [ ] Mock data is provided and clearly marked with "⚠️ MOCK DATA."
- [ ] Page structure justification is present (Section 1.2).
- [ ] Sorting, Top-N, and interaction behaviors are specified for every component.
- [ ] SLA-related components have parameterized thresholds (SLA Days + Breach Warning Days).
- [ ] No Commercial Entity filter is included.
- [ ] Ticketing metrics are system-agnostic (no vendor-specific terminology like "Zendesk" or "Freshdesk").
- [ ] Priority ordering is reflected: Fulfillment (Page 1, primary) + Support (Page 2, primary); Supplier is secondary zone on Page 1.

### Additional Checklist Items

- [ ] All new operational filters specify input type, default value, location, and options source.
- [ ] "Reset" behavior is documented with full defaults.
- [ ] SLA Compliance alert threshold (90%) is documented.
- [ ] Unresolved Tickets backlog alert thresholds (50 = amber, 100 = red) are documented.
- [ ] Supplier warning threshold (>2× average delivery time) is documented.
- [ ] All components specify hover tooltip content.
- [ ] Export affordances (CSV, PNG) are specified per component.
- [ ] Mobile layout specifies horizontal scroll behavior for tables.
- [ ] Page-level filter strip for Support & Ticketing is documented.
- [ ] API endpoint shapes include request parameters and response structure.
- [ ] Caching strategy is documented per endpoint group.
- [ ] "Top N shown" badge rules are specified for all truncated lists/charts.
- [ ] Acknowledgement time alert threshold (>24h = amber) is documented.
- [ ] Resolution time alert threshold (>3 days = red) is documented.
- [ ] All mock data examples include at least one alert/warning state.

---

*End of Design Specification*
