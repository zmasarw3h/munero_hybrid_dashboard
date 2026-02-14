# Munero Dashboard — User Guide

> This guide walks you through everything you can see and do in the Munero Dashboard. It covers the three main pages, the filtering system, and the built-in AI assistant.

---

## Getting Around the Dashboard

The dashboard has a **fixed header bar** at the top of every page. It includes:

- **Munero AI Platform** logo and title (top left)
- **Page tabs** to switch between the three dashboard pages:
  - Executive Overview
  - Market Analysis
  - Catalog Performance
- **"Ask AI" button** (top right) — opens the AI chat assistant
- **Live indicator** — a green "Live" label confirming the dashboard is connected to current data
- **User avatar** — your profile icon (top right corner)

The active page tab is highlighted so you always know which page you're on.

---

## Filtering Your Data

A **filter bar** sits just below the header and stays visible as you scroll. It controls what data is shown across all three pages.

### Available Filters

| Filter | What It Does |
|--------|-------------|
| **Date Range** | Pick a start and end date to define the time period you want to analyze |
| **Currency** | Choose which currency to display monetary values in |
| **Country** | Select one or more countries to focus on specific markets |
| **Product Type** | Filter by product type (e.g., gift card vs. merchandise) |

### More Filters

Click the **"More Filters"** button to access additional filters:

| Filter | What It Does |
|--------|-------------|
| **Clients** | Narrow results to specific client accounts |
| **Brands** | Narrow results to specific brands |
| **Suppliers** | Narrow results to specific suppliers |
| **Anomaly Threshold** | Adjust the sensitivity for anomaly detection in trend charts (higher = only flag large deviations; lower = flag smaller deviations) |

After choosing your advanced filters, click **"Apply"** to update the dashboard, or **"Clear Advanced"** to remove them.

### Resetting Filters

Click the **"Reset"** button to return all filters to their default values (last 30 days, all countries, all product types, etc.).

---

## Page 1: Executive Overview

> **What this page is for:** A high-level snapshot of your business — total orders, revenue, trends, and anything that needs attention.

When you open this page, you'll see a subtitle describing its purpose and an **"Updated"** timestamp showing when the data was last refreshed.

---

### Key Metrics (Top Row)

Five large metric cards appear across the top of the page. Each card shows the current value, a percentage change versus the prior period (with an up or down arrow), and a small trend sparkline.

| Card | What It Shows |
|------|--------------|
| **Total Orders** | The total number of orders in your selected date range, with a mini trend chart |
| **Total Revenue** | Total revenue earned, with a mini trend chart |
| **Avg Order Value** | The average value per order |
| **Orders / Client** | The average number of orders per client account |
| **Stuck Orders** | The number of orders that are stuck, failed, or stalled. If any exist, this card turns red and includes a "View" link that jumps you down to the details |

---

### Sales & Volume Trend (Chart)

A combined chart showing **two metrics over time**:
- **Bars** represent one metric (e.g., number of orders)
- **A line** represents another metric (e.g., revenue)

**What you can do:**
- **Switch time granularity** — toggle between Day, Month, and Year views
- **Swap axes** — flip which metric is shown as bars vs. the line
- **Spot anomalies** — bars turn red when an unusual spike or dip is detected, and the legend shows how many anomalies were found
- **Hover** over any bar or point to see the exact values for that date

---

### Operational Health (Stuck Orders List)

A list of orders that are stuck, failed, or pending action. Each row shows:

| Column | What It Shows |
|--------|--------------|
| Order Number | The order identifier |
| Status | A color-coded label (e.g., Failed, Pending) |
| Age | How many days the order has been in this state |

Each row has action buttons to **retry** a failed order or **view its details**. If there are more items than fit on screen, a **"View All"** button appears at the bottom.

---

### Revenue by Geography (Map)

An interactive world map where countries are shaded based on how much revenue they generate — darker shading means higher revenue.

**What you can do:**
- **Hover** over any country to see its revenue, order count, and number of clients
- **Zoom in/out** using the controls, or reset the zoom to see the full map
- A **color legend** shows what the shading levels represent

---

### Top Performers (Bar Chart)

A horizontal bar chart showing your top-performing products or brands by revenue.

**What you can do:**
- **Toggle between Products and Brands** using the switch at the top of the chart
  - **Products view:** Shows completed vs. failed/stuck revenue per product (stacked bars)
  - **Brands view:** Shows gift card vs. merchandise revenue per brand (stacked bars)
- **Hover** over any bar to see the exact totals and percentage breakdown

---

### Revenue by Type (Pie Chart)

A donut chart showing how revenue is split across product types (e.g., gift card vs. merchandise). A legend table beside the chart shows the exact percentage and dollar amount for each segment.

---

### Anomaly Alerts (Scrollable Strip)

A horizontal strip of small alert chips at the bottom of the page. Each chip represents a detected anomaly — an unusual data point in your trends.

Each chip shows:
- The **date** the anomaly occurred
- Which **metric** was affected
- The **percentage change** that triggered the flag

If no anomalies are found, the strip shows: *"No anomalies detected in the selected period."*

---

## Page 2: Market Analysis

> **What this page is for:** Understand your client base — who your biggest clients are, how revenue is concentrated, and how clients segment into different categories.

---

### Key Metrics (Top Row)

Three metric cards appear at the top:

| Card | What It Shows |
|------|--------------|
| **Active Clients** | The number of clients with orders in the selected period. May show a note like "Top 500 shown" if the dataset is large |
| **Avg Revenue/Client** | The average revenue generated per client |
| **Top Client Share** | The revenue share held by your largest client. Highlights in red if concentration risk is detected (too much revenue from one client) |

---

### Revenue Concentration (Bar + Line Chart)

A chart that answers the question: *"How dependent are we on our top clients?"*

- **Bars** show revenue by client, ranked from highest to lowest
- **A line** shows the cumulative percentage of total revenue
- A horizontal reference line marks the **80% threshold** — you can see how many clients make up 80% of your revenue
- Below the chart title, a summary line reads something like: *"Top 12 clients = 80% of revenue"*

**What you can do:**
- **Click on a bar** to select and filter to that specific client

---

### Client Segmentation (Scatter Plot)

A scatter plot that places each client on a grid based on their **order volume** (horizontal axis) and **revenue** (vertical axis). The grid is divided into **four quadrants** with labels like:

- **Champions** — high orders + high revenue (top right)
- **Whales** — low orders + high revenue (top left)
- **Loyalists** — high orders + low revenue (bottom right)
- **Developing** — low orders + low revenue (bottom left)

**What you can do:**
- **Adjust the threshold lines** that define the quadrant boundaries (using the input controls)
- **Click on a segment name** in the legend to filter the view to just that segment
- **Hover** over any dot to see the client name, revenue, order count, and segment

---

### Segment Distribution (Pie Chart)

A donut chart showing how many clients fall into each segment (Champions, Whales, Loyalists, Developing). Click on a segment to filter the page to clients in that category.

---

### Client Leaderboard (Table)

A sortable table listing your clients with:

| Column | What It Shows |
|--------|--------------|
| Client Name | The account name |
| Segment | Which quadrant they belong to (shown as a color-coded label) |
| Revenue | Total revenue from this client |
| Orders | Total order count |
| Share % | This client's share of your total revenue |

**What you can do:**
- **Click a column header** to sort by that column
- **Click a row** to select a client and filter the page to their data
- A **"Clear filter"** option appears when a client is selected, to return to the full view
- The table shows a count like *"5 of 42 clients in Champion"* to indicate how the filter is applied

---

## Page 3: Catalog Performance

> **What this page is for:** Understand which products are driving your business, spot rising and falling performers, and monitor supplier concentration risk.

---

### Key Metrics (Top Row)

Four metric cards appear at the top:

| Card | What It Shows |
|------|--------------|
| **Active SKUs** | The number of unique products with activity in the selected period |
| **Global Reach** | How many currencies your products are sold in |
| **Avg Margin** | The average profit margin across your product catalog |
| **Supplier Health** | Overall supplier risk status. Turns red if any suppliers are flagged as "at risk," with text like "2 at risk" |

---

### Product Performance (Scatter Plot)

A scatter plot placing each product on a grid based on **quantity sold** (horizontal axis) and **revenue** (vertical axis). Products are divided into four quadrants:

- **Cash Cows** — high quantity + high revenue
- **Premium Niche** — low quantity + high revenue
- **Penny Stocks** — high quantity + low revenue
- **Dead Stock** — low quantity + low revenue

Products are color-coded by type (e.g., gift card vs. merchandise).

**What you can do:**
- **Adjust the threshold lines** to change where the quadrant boundaries sit
- **Hover** over any dot to see the product name, revenue, quantity, margin, and which quadrant it falls in
- If the dataset is large, a **"Top 500 by Revenue"** label appears, indicating only the top 500 products are plotted

---

### Segment Distribution (Pie Chart)

A donut chart showing how many products fall into each quadrant (Cash Cows, Premium Niche, Penny Stocks, Dead Stock).

---

### Movers & Shakers (Two Lists)

A split-panel showing two ranked lists side by side:

- **Top Risers** — products with the biggest revenue growth compared to the prior period
- **Top Fallers** — products with the biggest revenue decline

This helps you quickly spot which products are gaining or losing momentum.

---

### Supplier Concentration (Bar Chart)

A vertical bar chart showing what share of your revenue comes from each supplier (top 5 suppliers shown, with an "Others" bucket for the rest).

A **30% threshold line** is drawn across the chart. If any single supplier accounts for more than 30% of your revenue, a **warning alert** appears — this signals concentration risk (too much dependence on one supplier).

---

### Product Catalog Table

A sortable table listing your products with:

| Column | What It Shows |
|--------|--------------|
| Product Name | The product title |
| Type | Gift card or merchandise (shown as a label) |
| Revenue | Total revenue from this product |
| Growth % | Revenue growth compared to the prior period |
| Failure Rate | Percentage of orders for this product that failed |
| Margin % | Profit margin for this product |

**What you can do:**
- **Click a column header** to sort by that column (e.g., sort by growth % to find your fastest-growing products)
- If no products match your current filters, the table shows: *"Adjust your filters or date range."*

---

## The AI Assistant ("Ask AI")

Click the **"Ask AI"** button in the top-right corner (or press **Cmd+K** / **Ctrl+K**) to open a chat panel on the right side of the screen. Press **Esc** to close it.

### What You Can Do

Ask questions about your data in plain English. For example:
- *"Which clients had the highest revenue last month?"*
- *"Show me order trends for the last 90 days."*
- *"What's the average fulfillment time by country?"*

### What You'll See in Responses

The AI can respond with:
- **Text answers** explaining the data
- **Charts and tables** generated on the fly based on your question
- **Warnings** (shown in yellow) if there are data limitations or caveats
- **Export options** — download the response as a **CSV** (spreadsheet) or **PNG** (image)

If you haven't asked anything yet, the panel shows **suggested questions** you can click to get started.

### Context Awareness

The AI assistant is aware of your current filters. A label at the top of the chat panel shows which date range and filters are active, so answers are always scoped to the data you're looking at.

### Health Status

If the AI assistant is experiencing issues, a **yellow warning bar** appears at the top of the chat panel with guidance on what to do.

---

## Tips for Getting the Most Out of the Dashboard

1. **Start with the Executive Overview** for a quick health check, then drill into Market Analysis or Catalog Performance for deeper insight.
2. **Use the date range filter** to compare different periods — the trend arrows on metric cards automatically adjust.
3. **Click on chart elements** (bars, pie segments, scatter dots, table rows) to filter the page — most visuals are interactive.
4. **Use the AI assistant** for ad-hoc questions that aren't answered by the pre-built charts.
5. **Watch for red highlights and warnings** — these indicate areas that may need your attention (stuck orders, concentration risk, at-risk suppliers).
6. **Export data** from charts and AI responses using the CSV and PNG download options when you need to share findings.

---

*If you have questions about the dashboard or need help, click "Ask AI" or reach out to the Munero support team.*
