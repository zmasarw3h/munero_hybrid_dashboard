# Munero Operational Metrics Dashboard — Design Preview

> **Date:** February 13, 2026
> **Status:** Preliminary Design — Awaiting Your Feedback
> **Prepared by:** Munero Product Team

---

## About This Document

We're designing a new **Operational Metrics Dashboard** for the Munero platform. This document is a preview of the proposed design for your review.

**What we're asking from you:**
- Does the proposed layout make sense for your team's daily workflow?
- Are there any metrics missing, or any that aren't needed?
- Do the sample numbers and alerts look like the kind of information you'd act on?
- Are there any terms, labels, or groupings that don't match how your team thinks about the data?

Please review each section and share any feedback. A list of specific questions is included at the end.

---

## 1. Dashboard Overview

### Structure: 2 Pages

The dashboard is split into **two pages**, each accessible via a tab at the top:

| Page | Tab Name | What It Covers |
|------|----------|----------------|
| 1 | **Order Fulfillment** | Order status, fulfillment speed, SLA compliance, and supplier delivery times |
| 2 | **Support & Ticketing** | Ticket volume, response times, resolution performance, and backlog |

### Why Two Pages?

- **Order Fulfillment** and **Support & Ticketing** are two distinct workflows. Teams working on logistics don't typically need to see ticketing data at the same time, and vice versa.
- **Supplier delivery performance** is included on the Fulfillment page because it's part of the same pipeline (purchase order → delivery → invoice).
- Putting everything on one page would create too much scrolling. A third page for suppliers alone would feel too sparse.

### Who Is This For?

| Role | How They'll Use It |
|------|-------------------|
| **Operations Manager** | Daily check on order pipeline health, SLA risks, and stuck orders |
| **Support Team Lead** | Monitor ticket volume, response times, and the backlog of unresolved tickets |
| **Supply Chain Analyst** | Review supplier delivery times to flag slow suppliers |
| **VP of Operations** | Weekly/monthly summary of operational health across fulfillment and support |

### Key Scenarios

1. **Morning check-in:** "Which orders are about to miss their SLA? I need to follow up before they become customer complaints."
2. **Failure spike:** "Fulfillment failures are up — which clients, brands, or suppliers are responsible?"
3. **Support surge:** "Tickets are piling up on live chat — I need to move agents over from email."
4. **Slow resolution:** "Resolution time is creeping up — which unresolved tickets have been sitting the longest?"
5. **Supplier review:** "Which suppliers are consistently slow? I need data for our next negotiation."

---

## 2. What You Can Filter By

The dashboard includes a **filter bar** at the top of every page. Filters let you narrow the data to the exact slice you care about.

### Filters Available on Both Pages

| Filter | What It Does | Default |
|--------|-------------|---------|
| **Date Range** | Pick a start and end date for the data | Last 30 days |
| **Currency** | Choose which currency to display values in | USD |
| **Country** | Select one or more countries | All countries |
| **Product Type** | Filter by product type (e.g., gift card, merchandise) | All types |
| **Order Status** | Show only fulfilled, pending, or failed orders | All statuses |
| **SLA Days** | Set your SLA target (e.g., 7 days) — the dashboard measures compliance against this number | 7 days |
| **Clients** | Filter to specific client accounts (under "More Filters") | All |
| **Brands** | Filter to specific brands (under "More Filters") | All |
| **Suppliers** | Filter to specific suppliers (under "More Filters") | All |
| **Breach Warning Window** | How many days before SLA deadline to flag an order as "approaching breach" (under "More Filters") | 2 days |
| **Failure Category** | Filter by type of failure (under "More Filters") | All |

### Additional Filters on the Support & Ticketing Page

| Filter | What It Does | Default |
|--------|-------------|---------|
| **Channel** | Filter by support channel (Email, Phone, Live Chat, Web Form, Social, Other) | All channels |
| **Ticket Status** | Show only Open, In Progress, Resolved, or Closed tickets | All statuses |
| **Issue Type** | Filter by type of issue (e.g., Order Inquiry, Return/Refund, Product Defect) | All types |
| **Program** | Filter by program (e.g., Standard, Premium, Loyalty) | All programs |

A **Reset** button clears all filters back to the defaults shown above.

---

## 3. Page 1: Order Fulfillment — What You'll See

### Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Header: Munero AI Platform   [Order Fulfillment] [Support]  │
├─────────────────────────────────────────────────────────────┤
│ Filter Bar: Date Range | Currency | Country | Status | SLA  │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ Total Orders │ Avg          │ SLA          │ Approaching    │
│              │ Fulfillment  │ Compliance   │ Breach         │
│              │ Time         │              │                │
├──────────────┴──────────────┼──────────────┴────────────────┤
│ Order Status                │ Fulfillment Volume & Speed    │
│ Pie Chart                   │ Bar + Line Chart              │
├─────────────────────────────┴───────────────────────────────┤
│ SLA Breach Watch — Attention Required                       │
│ (Table of orders closest to missing their SLA)              │
├─────────────────────────────┬───────────────────────────────┤
│ SLA Performance             │ Supplier Delivery             │
│ by Client / Brand           │ Performance                   │
│ (Comparison table)          │ (Horizontal bar chart)        │
└─────────────────────────────┴───────────────────────────────┘
```

---

### What Each Section Shows

#### Top Row: Four Key Numbers at a Glance

These are large, prominent metric cards across the top of the page. Each shows the current value, how it compares to the prior period (up/down arrow with percentage), and a small trend sparkline.

**Card 1 — "Total Orders"**
The total number of orders in the selected date range.

**Card 2 — "Avg Fulfillment Time"**
The average time from when an order is created to when the last item is fulfilled. Shown as days and hours (e.g., "2d 14h"). If this exceeds your SLA target, the card highlights in red.

**Card 3 — "SLA Compliance"**
The percentage of fulfilled orders that were completed within your SLA target (e.g., "91.4% within 7-day SLA"). If compliance drops below 90%, the card shows a warning.

**Card 4 — "Approaching Breach"**
The number of pending orders that will miss the SLA if not fulfilled within the warning window (e.g., "23 orders within 2-day warning window"). This card turns amber when any orders are approaching breach, and red if orders have already breached.

---

#### Order Status Pie Chart

A donut chart showing how orders break down by status: **Fulfilled**, **Pending**, and **Failed**. You can click on a segment to filter the entire page to just that status.

---

#### Fulfillment Volume & Speed Chart

A time-series chart with two layers:
- **Bars** show the number of orders per day/week/month
- **A line** shows the average fulfillment time over the same period

This helps you spot patterns like "when volume spikes, does fulfillment slow down?" You can toggle between daily, weekly, and monthly views.

---

#### SLA Breach Watch — Attention Required

A table listing the specific orders that are closest to (or have already missed) their SLA deadline. Each row shows:

| Column | What It Shows |
|--------|--------------|
| Order ID | The order number |
| Client | Which client account placed the order |
| Brand | The brand associated with the order |
| Status | Pending or Failed (shown as a color-coded label) |
| Age | How many days since the order was created |
| SLA Remaining | Days until the SLA deadline; negative means it's already breached |
| Failure Category | If the order failed, what type of failure |

Orders that have already breached the SLA are highlighted in **red** with a "SLA Breached" label. Orders approaching the deadline are highlighted in **amber**. The most urgent orders appear first.

---

#### SLA Performance by Client / Brand

A sortable table comparing SLA compliance across your different client accounts (or brands — you can toggle between the two views). Each row shows:

- Client/Brand name
- Total orders
- SLA compliance percentage
- Average fulfillment time
- Number of breached orders

Worst performers are shown first by default, so you can immediately spot which clients or brands need attention. Poor compliance rates are highlighted in red.

---

#### Supplier Delivery Performance

A horizontal bar chart comparing delivery times across your top 10 suppliers. Each bar is split into two segments:

- **Time from purchase order to item receipt** (how long the supplier takes to deliver)
- **Time from receipt to invoice** (how long after delivery the invoice is issued)

You can toggle this view to see the same data grouped **by brand** or **by product** instead of by supplier. Suppliers with unusually slow delivery times (more than double the average) are flagged with a warning.

---

### Sample Data — What the Numbers Might Look Like

> *Note: All values below are illustrative examples, not real data.*

#### Key Metric Cards

| Metric | Sample Value | Trend | Context |
|--------|-------------|-------|---------|
| Total Orders | 12,847 | +8.3% vs prior period | — |
| Avg Fulfillment Time | 2 days, 14 hours | Improved by 12.1% | From order creation to last item fulfilled |
| SLA Compliance | 91.4% | Up 2.3% | Within 7-day SLA |
| Approaching Breach | 23 orders | Up 15% | Within 2-day warning window |

#### Order Status Breakdown

| Status | Count | Share |
|--------|-------|-------|
| Fulfilled | 11,203 | 87.2% |
| Pending | 1,389 | 10.8% |
| Failed | 255 | 2.0% |

#### SLA Breach Watch (Sample Rows)

| Order ID | Client | Brand | Status | Age | SLA Remaining | Failure Reason |
|----------|--------|-------|--------|-----|---------------|----------------|
| ORD-78421 | Acme Corp | BrandX | Pending | 6 days | **1 day left** | — |
| ORD-78390 | GlobalTech | BrandY | Failed | 8 days | **1 day overdue — SLA Breached** | Payment Failure |
| ORD-78455 | RetailCo | BrandZ | Pending | 5 days | 2 days left | — |

#### SLA Performance by Client (Sample Rows)

| Client | Total Orders | SLA Compliance | Avg Fulfillment Time | Breached Orders |
|--------|-------------|----------------|----------------------|-----------------|
| Acme Corp | 3,241 | **78.2%** (below target) | 3 days, 2 hours | 42 |
| GlobalTech | 2,890 | 94.1% | 1 day, 18 hours | 8 |
| RetailCo | 1,756 | 96.8% | 1 day, 6 hours | 3 |

#### Supplier Delivery Times (Sample Rows)

| Supplier | Order to Delivery | Delivery to Invoice | Total Time |
|----------|-------------------|---------------------|------------|
| Supplier Alpha | 12 days | 5 days | **17 days** (flagged — unusually slow) |
| Supplier Beta | 7 days | 3 days | 10 days |
| Supplier Gamma | 6 days | 2 days | 8 days |

---

## 4. Page 2: Support & Ticketing — What You'll See

### Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Header: Munero AI Platform   [Order Fulfillment] [Support]  │
├─────────────────────────────────────────────────────────────┤
│ Filter Bar: Date Range | Currency | Country | ...           │
├─────────────────────────────────────────────────────────────┤
│ Page Filters: Channel | Ticket Status | Issue Type | Program │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ Total        │ Avg          │ Avg          │ Unresolved     │
│ Tickets      │ Acknowledge- │ Resolution   │ Tickets        │
│              │ ment Time    │ Time         │                │
├──────────────┴──────────────┼──────────────┴────────────────┤
│ Tickets by                  │ Tickets by                    │
│ Channel                     │ Issue Type                    │
│ (Pie Chart)                 │ (Horizontal Bar Chart)        │
├─────────────────────────────┴───────────────────────────────┤
│ Ticket Volume & Resolution Trend                            │
│ (Bar + Line Chart over time)                                │
├─────────────────────────────────────────────────────────────┤
│ Unresolved Tickets — Attention Required                     │
│ (Table of open/in-progress tickets, oldest first)           │
└─────────────────────────────────────────────────────────────┘
```

---

### What Each Section Shows

#### Top Row: Four Key Numbers at a Glance

**Card 1 — "Total Tickets"**
The total number of support tickets created in the selected date range, with trend vs. prior period.

**Card 2 — "Avg Acknowledgement Time"**
How quickly your team sends the first response to a new ticket. Shown as hours and minutes (e.g., "4h 23m"). If this exceeds 24 hours, the card highlights in amber.

**Card 3 — "Avg Resolution Time"**
The average time from ticket creation to full resolution. Shown as days and hours (e.g., "1d 8h"). If this exceeds 3 days, the card highlights in red.

**Card 4 — "Unresolved Tickets"**
The current count of tickets that are still Open or In Progress (not the period total — this is a real-time backlog number). Shows a breakdown like "89 open, 38 in progress." Highlights amber at 50+ unresolved, red at 100+ with a "Backlog Alert" label.

---

#### Tickets by Channel

A donut chart showing how tickets are distributed across support channels (Email, Phone, Live Chat, Web Form, Social, Other). Click on a segment to filter the page to just that channel.

---

#### Tickets by Issue Type

A horizontal bar chart showing ticket volume by issue type (e.g., Order Inquiry, Return/Refund, Product Defect). Each bar is color-coded to show the status breakdown: Open, In Progress, Resolved, and Closed.

You can toggle this view to see the data grouped **by Program** instead of by issue type.

---

#### Ticket Volume & Resolution Trend

A time-series chart with two layers:
- **Bars** show the number of tickets per day/week/month
- **A line** shows the average resolution time over the same period

This helps you see whether resolution speed keeps pace with incoming volume. You can toggle between daily, weekly, and monthly views.

---

#### Unresolved Tickets — Attention Required

A table listing specific tickets that are still open or in progress. Each row shows:

| Column | What It Shows |
|--------|--------------|
| Ticket ID | The ticket number |
| Channel | How the ticket came in (Email, Phone, etc.) |
| Issue Type | What kind of issue it is |
| Program | Which program it belongs to |
| Status | Open or In Progress |
| Age | How many days the ticket has been open |
| Last Updated | When the ticket was last touched |

Tickets open for more than 7 days are highlighted in **red**. The oldest tickets appear first so your team can prioritize the most stale cases.

---

### Sample Data — What the Numbers Might Look Like

> *Note: All values below are illustrative examples, not real data.*

#### Key Metric Cards

| Metric | Sample Value | Trend | Context |
|--------|-------------|-------|---------|
| Total Tickets | 1,842 | +5.7% vs prior period | — |
| Avg Acknowledgement Time | 4 hours, 23 minutes | Improved by 18.5% | Time to first response |
| Avg Resolution Time | 1 day, 8 hours | Up 3.2% (getting slower) | Ticket creation to resolution |
| Unresolved Tickets | 127 | Up 22.1% | 89 open + 38 in progress — **Backlog Alert** |

#### Tickets by Channel

| Channel | Count | Share |
|---------|-------|-------|
| Email | 743 | 40.3% |
| Live Chat | 512 | 27.8% |
| Phone | 298 | 16.2% |
| Web Form | 187 | 10.2% |
| Social | 68 | 3.7% |
| Other | 34 | 1.8% |

#### Tickets by Issue Type (Sample Rows)

| Issue Type | Open | In Progress | Resolved | Closed | Total |
|------------|------|-------------|----------|--------|-------|
| Order Inquiry | 34 | 12 | 289 | 410 | 745 |
| Return/Refund | 28 | 15 | 178 | 245 | 466 |
| Product Defect | 19 | 8 | 102 | 134 | 263 |

#### Unresolved Tickets (Sample Rows)

| Ticket ID | Channel | Issue Type | Program | Status | Age | Last Updated |
|-----------|---------|------------|---------|--------|-----|-------------|
| TKT-9021 | Email | Return/Refund | Loyalty | Open | **12 days** (flagged) | 3 days ago |
| TKT-9187 | Live Chat | Order Inquiry | Standard | In Progress | 4 days | 2 hours ago |
| TKT-9203 | Phone | Product Defect | Premium | Open | 2 days | 1 day ago |

---

## 5. Built-In AI Assistant

Both pages include an **"Ask AI"** button in the top-right corner. Clicking it opens a chat panel where you can ask questions about your data in plain English. The AI will generate answers, charts, and tables on the fly.

**Example questions you could ask:**

*On the Order Fulfillment page:*
- "Which clients have the worst SLA compliance this month?"
- "What are the top failure reasons for failed orders?"
- "Show me the trend in fulfillment time over the last 90 days."
- "Which suppliers have the longest delivery times?"

*On the Support & Ticketing page:*
- "What's the average resolution time by channel this week?"
- "Which issue types have the most unresolved tickets?"
- "Show me ticket volume trends for the last quarter."
- "Which programs generate the most support tickets?"

---

## 6. Assumptions — We'd Like Your Input

During the design process, we made the following assumptions. Please let us know if any of these should be changed:

| # | What We Assumed | Why It Matters |
|---|-----------------|----------------|
| 1 | **The default SLA target is 7 days.** Users can change this at any time using the SLA filter. | This determines which orders are flagged as "approaching breach" or "breached." |
| 2 | **"Client" means the contracting account that placed the order** (e.g., Acme Corp, GlobalTech). | This is the dimension used for "SLA performance by client." |
| 3 | **Support channels are generic labels:** Email, Phone, Live Chat, Web Form, Social, Other. | The dashboard is designed to work with any ticketing system — not tied to a specific platform. |
| 4 | **Fulfillment time is measured from order creation to the last item being fulfilled.** If an order has multiple shipments, the clock stops when the final item ships. | This affects the "Avg Fulfillment Time" metric. |
| 5 | **Supplier delivery time is shown as two separate measurements:** (a) time from purchase order to item receipt, and (b) time from receipt to invoice. | The original request mentioned "PO creation to item receipt and invoice issued" — we split it into two segments so you can see where delays happen. |

---

## 7. We'd Love Your Feedback On...

Please review the design above and share your thoughts on these specific questions. Feel free to respond with brief notes — even a "looks good" or "change this" is helpful.

1. **Page structure:** Does splitting the dashboard into "Order Fulfillment" and "Support & Ticketing" match how your team works? Or would you prefer a different grouping?

2. **Key metrics (top cards):** Are the four metrics on each page the most important numbers your team needs to see first? Would you add, remove, or replace any?

3. **SLA defaults:** Is 7 days a reasonable default SLA target? Is a 2-day warning window before breach the right alert threshold?

4. **Supplier delivery:** Is it useful to see supplier performance on the same page as order fulfillment, or would you prefer it on a separate page?

5. **Ticket channels and categories:** Do the channel names (Email, Phone, Live Chat, Web Form, Social, Other) match how your support operation is structured? Are there channels we're missing?

6. **Issue types:** What issue type categories does your team use? (We've shown examples like "Order Inquiry," "Return/Refund," and "Product Defect" — but we'll use your actual categories.)

7. **Alerts and thresholds:** We've proposed these automatic warning thresholds. Do they make sense for your operation?
   - SLA compliance drops below 90% → red alert on the card
   - Acknowledgement time exceeds 24 hours → amber alert
   - Resolution time exceeds 3 days → red alert
   - Unresolved tickets exceed 50 → amber alert; exceed 100 → red alert

8. **Filters:** Are there any filters you'd want that aren't listed? Any that seem unnecessary?

9. **AI assistant:** Are the example AI questions relevant to what your team would actually ask? What other questions would be useful?

10. **Anything else:** Is there anything missing from this dashboard that your team needs to see day-to-day?

---

*We look forward to your feedback. Once we align on the design, we'll move into development.*
