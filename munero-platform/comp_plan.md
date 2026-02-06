Munero Dashboard - Frontend Implementation Plan
Overview
Complete the frontend implementation with: Market page, Catalog page, AI Chat (slide-over + dedicated page), and polish.
COMPREHENSIVE DASHBOARD DESIGN SPECIFICATION
Document Info
Version: 2.0
Last Updated: January 2026
Status: Final Design for Implementation
Feature Priority Legend
Tag	Meaning
MVP	Must have for initial release
v2	Second iteration enhancement
v3	Future roadmap item
Global Design Patterns
Cross-Page Navigation (MVP)
All entity names (clients, brands, products, suppliers) are clickable links across ALL pages with consistent behavior:
Click action: Updates FilterContext with selected entity + navigates to relevant page
Visual cue: Underline on hover, cursor pointer
Examples:
Click "Acme Corp" on Overview → Navigate to Market page filtered to Acme Corp
Click "Apple" brand on Market → Navigate to Catalog page filtered to Apple brand
Click product name anywhere → Navigate to Catalog page filtered to that product
Empty State Design (MVP)
When filters return zero results, display:

┌─────────────────────────────────────────────┐
│           📊 No Data Available              │
│                                             │
│  No results match your current filters.     │
│                                             │
│  Suggestions:                               │
│  • Expand the date range                    │
│  • Remove some filters                      │
│  • Try a different currency                 │
│                                             │
│  [Reset Filters]                            │
└─────────────────────────────────────────────┘
Per-component empty states:
Charts: Gray placeholder with "No data" message
Tables: Single row spanning all columns with message
KPI Cards: Show "—" with muted styling
Data Freshness Indicator (MVP)
Display in header: "Last updated: Jan 4, 2026 at 09:15 AM"
Fetch from backend /health endpoint or new /api/meta endpoint
Tooltip on hover: "Data refreshes daily at 2:00 AM UTC"
Page 1: Executive Overview ("The Pulse")
Purpose
High-level business health at a glance. Answer: "How are we doing?"
Zone 1: Global Filters (Sticky Header)
Element	Type	Behavior	Priority
Date Range	Date Picker	Start/End date selection	MVP
Currency	Dropdown	AED/USD/EUR	MVP
Country	Multi-select	Filter by client country	MVP
Product Type	Multi-select	gift_cards, vouchers, etc.	MVP
Client	Multi-select	Expandable in "Advanced"	MVP
Brand	Multi-select	Expandable in "Advanced"	MVP
Supplier	Multi-select	Expandable in "Advanced"	MVP
Anomaly Threshold	Slider	Z-score threshold (1.5-3.0)	MVP
Last Updated	Text	Timestamp of data freshness	MVP
Zone 2: KPI Cards
Layout: 5 cards in responsive grid (5 → 3 → 2 → 1 columns)
Metric	Calculation	Format	Priority
Total Orders	COUNT(DISTINCT order_number)	Number with commas	MVP
Total Revenue	SUM(order_price_in_aed)	Currency formatted	MVP
Avg Order Value	Revenue / Orders	Currency formatted	MVP
Orders per Client	Orders / Distinct Clients	Decimal (1 place)	MVP
Brands Sold	COUNT(DISTINCT product_brand)	Number	MVP
Features:
Feature	Description	Priority
Comparison Badge	Pill showing % change with ↑/↓ arrow, color-coded (green=good, red=bad)	MVP
Comparison Toggle	Dropdown: "vs Last Year" / "vs Prior Period" / "None"	MVP
Trend Sparkline	Mini 6-month trend line inside card	v2
Zone 3: Main Trend Visualizations
3A: Dual-Axis Trend Chart
Chart Type: ComposedChart (Recharts)
Primary Y-Axis (Left): Revenue (Bar chart, blue)
Secondary Y-Axis (Right): Orders (Line chart, orange)
X-Axis: Time periods (auto-granularity: daily/weekly/monthly based on date range)
Feature	Description	Priority
Metric Role Toggle	Button to swap which metric is Bar vs Line	v2
Anomaly Overlay	Red scatter dots on anomalous data points	MVP
Target/Goal Line	Horizontal dashed line showing budget/target	v2
Tooltip	Date, Revenue, Orders, % change from prior period	MVP
3B: Revenue by Product Type
Chart Type: Horizontal Bar Chart (if >5 types) OR Donut Chart (if ≤5 types)
Feature	Description	Priority
Enhanced Tooltip	Shows: Amount, % of total, YoY growth %	MVP
Auto "Other" Grouping	If >8 categories, group smallest into "Other"	MVP
Click to Filter	Click segment → filter dashboard to that product type	v2
Zone 4: Anomaly Detection
4A: Anomaly Timeline
Chart Type: Area chart with red scatter overlay Anomaly Definition:
Z-score > threshold (default 2.0, configurable via filter)
Calculated per metric (Revenue OR Orders, user toggleable)
Lookback period: Trailing 12 months
Feature	Description	Priority
Metric Toggle	Switch between "Revenue Anomalies" and "Order Anomalies"	MVP
Threshold Display	Show current Z-score threshold in chart legend	MVP
Drill Action	Click anomaly dot → Filter entire dashboard to that date + open AI chat with pre-filled question: "What caused the anomaly on [date]?"	v2
Anomaly Table	Below chart: Table listing top 5 anomalies with Date, Metric, Value, Z-score	MVP
4B: Top 3 Anomalies Summary Card (NEW)
Location: Right side of Zone 4

┌─────────────────────────────────┐
│ ⚠️ Recent Anomalies            │
├─────────────────────────────────┤
│ Dec 15: Revenue +340% (Z=3.2)  │
│ Dec 3:  Orders -45% (Z=2.8)    │
│ Nov 28: Revenue +180% (Z=2.1)  │
├─────────────────────────────────┤
│ [View All Anomalies]           │
└─────────────────────────────────┘
Feature	Description	Priority
Quick Summary	Shows top 3 most significant anomalies	MVP
Click to Investigate	Click row → same drill action as dots	MVP
Zone 5: Quick Actions (NEW)
Location: Bottom of page or floating action button
Action	Behavior	Priority
"Ask AI"	Opens chat sidebar with current context	MVP
"Export Report"	Generates PDF/Excel of current view	v2
"Share View"	Copies URL with encoded filter state	v2
"Save View"	Saves current filter combination	v3
Page 2: Market Analysis ("The Who")
Purpose
Understand client performance and geographic distribution. Answer: "Who are our best customers?"
Zone 1: Client KPIs
Layout: 3 cards in row
Metric	Calculation	Format	Priority
Active Clients	COUNT(DISTINCT client_name) WHERE orders > 0	Number	MVP
Avg Revenue/Client	Total Revenue / Active Clients	Currency	MVP
Top Client Share %	Top Client Revenue / Total Revenue * 100	Percentage	MVP
Features:
Feature	Description	Priority
Concentration Risk Tooltip	On "Top Client Share %": "⚠️ High concentration risk if >25%. Diversify client base to reduce dependency."	MVP
Threshold Warning	If Top Client Share >25%, show amber badge	MVP
Zone 2: Geography & Segments
2A: Revenue by Country (Left Half)
Chart Type: Horizontal Bar Chart
Feature	Description	Priority
Sorted by Revenue	Descending order	MVP
Country Flag Icons	Small flag emoji/icon next to country name	v2
Click to Filter	Click bar → filter to that country	MVP
Top N + Other	Show top 10 countries, rest grouped as "Other"	MVP
2B: Client Scatter Plot (Right Half)
Chart Type: Scatter Plot (Recharts)
X-Axis: Total Orders (volume)
Y-Axis: Total Revenue (value)
Each dot: One client
Feature	Description	Priority
Basic Scatter	X=Orders, Y=Revenue	MVP
Tooltip	Client name, Country, Orders, Revenue, AOV	MVP
Click to Filter	Click dot → update global FilterContext with client	MVP
Dot Size = AOV	Larger dots = higher average order value	v2
Dot Color = Product Type	Color-coded by primary product type purchased	v2
Quadrant Labels	"High Value/High Volume", "High Value/Low Volume", etc.	v2
Zone 3: Client Leaderboard
Component: DataTable Columns:
Column	Format	Sortable	Priority
Client Name	Text (clickable link)	Yes	MVP
Country	Text with flag	Yes	MVP
Revenue	Currency	Yes (default)	MVP
Orders	Number	Yes	MVP
AOV	Currency	Yes	MVP
% Share	Percentage	Yes	MVP
Trend Sparkline	Mini 6-month chart	No	MVP
Churn Risk	Badge (🟢/🟡/🔴)	Yes	v2
Features:
Feature	Description	Priority
Row Click → Global Filter	Click row → updates FilterContext.selectedClients + updates AI context	MVP
Row Highlighting	Selected client row highlighted	MVP
Trend Sparklines	Mini line chart showing 6-month revenue trend per client	MVP
Churn Risk Flag	🔴 if no orders in 90 days, 🟡 if declining 3 consecutive months, 🟢 otherwise	v2
Export Table	Button to download as CSV	v2
Zone 4: New vs Returning Analysis (NEW - v2)
Metric	Description	Priority
New Clients	First order in selected period	v2
Returning Clients	Had orders before selected period	v2
Retention Rate	Returning / Total from prior period	v2
Page 3: Catalog Analysis ("The What")
Purpose
Understand product and supplier performance. Answer: "What products drive our business?"
Zone 1: Supply Chain KPIs
Layout: 3 cards in row
Metric	Calculation	Format	Priority
Active Suppliers	COUNT(DISTINCT supplier_name)	Number	MVP
SKUs Sold	COUNT(DISTINCT product_sku)	Number	MVP
Avg Margin %	(Revenue - COGS) / Revenue * 100	Percentage	MVP
Margin Fallback Logic (MVP): When COGS is NULL or 0:

IF cogs IS NULL OR cogs = 0:
    Display: "X% Contribution" (gray/blue badge)
    Tooltip: "Cost data unavailable. Shows revenue contribution to total."
    Calculation: (Item Revenue / Total Revenue) * 100
ELSE:
    Display: "X% Margin" (green badge)
    Calculation: (Revenue - COGS) / Revenue * 100
Visual Implementation:

┌─────────────────────────┐     ┌─────────────────────────┐
│ Avg Margin %            │     │ Avg Contribution        │
│ ████████████ 22.5%      │     │ ████████████ 15.2%      │
│ 🟢 Healthy margin       │     │ ℹ️ Cost data missing    │
└─────────────────────────┘     └─────────────────────────┘
Zone 2: Brand & Supplier Analysis
2A: Brand Leaderboard (Left Half)
Component: DataTable Columns:
Column	Format	Sortable	Priority
Brand	Text (clickable)	Yes	MVP
Revenue	Currency	Yes (default)	MVP
Orders	Number	Yes	MVP
Products	Number	Yes	MVP
Growth %	Percentage with ↑/↓	Yes	MVP
Margin/Contribution	Percentage	Yes	MVP
Features:
Feature	Description	Priority
Growth % Tooltip	"Growth calculated as: (Current Period - Prior Period) / Prior Period × 100"	MVP
Click to Filter	Click brand → filter dashboard to that brand	MVP
2B: Supplier Concentration (Right Half)
Chart Type: Horizontal Bar Chart
Feature	Description	Priority
Sorted by Revenue	Descending	MVP
Concentration Reference Line	Vertical line at 25% showing "healthy diversification threshold"	v2
Click to Filter	Click bar → filter to supplier	MVP
Warning Badge	If any supplier >40%, show ⚠️	v2
Zone 3: Product Deep Dive
Component: DataTable Columns:
Column	Format	Sortable	Priority
Product Name	Text (clickable)	Yes	MVP
SKU	Text	Yes	MVP
Brand	Text (clickable)	Yes	MVP
Type	Badge	Yes	MVP
Quantity Sold	Number	Yes	MVP
Revenue	Currency	Yes	MVP
Margin/Contribution	Percentage	Yes (default)	MVP
Anomaly Flag	⚠️ icon	No	v2
Features:
Feature	Description	Priority
Sort Toggle	Default sort by Profit Margin (or Contribution if no COGS)	MVP
Unprofitable Filter	Toggle: "Show unprofitable only" (margin < 0)	MVP
Product Anomaly Flag	⚠️ icon for products with irregular patterns (sudden drop, spike)	v2
Bulk Export	Select multiple → export to CSV	v2
Zone 4: Product Lifecycle (NEW - v2)
Stage	Definition	Visual	Priority
New	First sold in last 30 days	🆕 badge	v2
Growing	Revenue up >20% MoM for 2+ months	📈 badge	v2
Mature	Stable revenue (±10%) for 3+ months	✓ badge	v2
Declining	Revenue down >20% MoM for 2+ months	📉 badge	v2
AI Chat Feature
AI Capabilities Overview
The AI Copilot has two distinct modes of operation:
Mode	Trigger	Behavior	Example
Data Query Mode	"Show me...", "What are...", "List..."	Generates SQL, executes, returns data + chart	"Show me top 10 products by revenue"
Driver Analysis Mode	"Why did...", "Explain...", "What caused..."	Calls variance analysis endpoint, narrates results	"Why did sales drop this month?"
Driver Analysis System (MVP)
Purpose
Answer diagnostic questions like "Why did sales drop?" with mathematically guaranteed answers, not LLM guessing.
Architecture

┌─────────────────────────────────────────────────────────────────┐
│ User Question: "Why did revenue drop compared to last month?"   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ LLM Intent Detection                                            │
│ Detects: diagnostic question → triggers Driver Analysis         │
│ Extracts: metric="revenue", period="month", comparison="prior"  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Backend: POST /api/analyze/drivers                              │
│                                                                 │
│ Input: { metric: "revenue", current_period, prior_period }      │
│                                                                 │
│ Process:                                                        │
│ 1. Calculate total delta: Current - Prior = -$10,000            │
│ 2. Run variance scan across dimensions:                         │
│    - By Client: GROUP BY client_name                            │
│    - By Brand: GROUP BY product_brand                           │
│    - By Country: GROUP BY client_country                        │
│    - By Product Type: GROUP BY order_type                       │
│ 3. Calculate delta per entity: (current - prior)                │
│ 4. Sort by absolute impact (largest contributors first)         │
│ 5. Return top N drivers per dimension                           │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Response Structure                                              │
│                                                                 │
│ {                                                               │
│   "metric": "revenue",                                          │
│   "total_change": -10000,                                       │
│   "total_change_pct": -15.2,                                    │
│   "current_total": 55000,                                       │
│   "prior_total": 65000,                                         │
│   "drivers": {                                                  │
│     "by_client": [                                              │
│       { "name": "TechCorp", "delta": -8000, "pct_of_total": 80 },│
│       { "name": "RetailCo", "delta": -1500, "pct_of_total": 15 },│
│       { "name": "StartupX", "delta": +500, "pct_of_total": -5 } │
│     ],                                                          │
│     "by_brand": [...],                                          │
│     "by_country": [...],                                        │
│     "by_product_type": [...]                                    │
│   }                                                             │
│ }                                                               │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ LLM Narration                                                   │
│                                                                 │
│ "Revenue dropped $10,000 (-15.2%) compared to last month.       │
│                                                                 │
│ **Primary Drivers:**                                            │
│ 1. **TechCorp** accounts for 80% of the decline (-$8,000).      │
│    This was your largest client last month.                     │
│ 2. **RetailCo** contributed 15% (-$1,500).                      │
│                                                                 │
│ **By Brand:** Apple products saw the biggest drop (-$6,000).    │
│                                                                 │
│ **Positive Note:** StartupX actually increased (+$500)."        │
└─────────────────────────────────────────────────────────────────┘
Supported Diagnostic Questions
Question Pattern	Parsed As	Dimensions Analyzed
"Why did revenue drop?"	metric=revenue, direction=decrease	Client, Brand, Country, Product Type
"Why are orders down this quarter?"	metric=orders, period=quarter	Client, Brand, Country, Product Type
"What caused the spike in December?"	metric=revenue, direction=increase, period=Dec	Client, Brand, Country, Product Type
"Explain the margin decline"	metric=margin, direction=decrease	Client, Brand, Supplier, Product
"Why is AOV lower?"	metric=aov, direction=decrease	Client, Product Type, Brand
Backend Endpoint Specification
Endpoint: POST /api/analyze/drivers Request:

{
  "metric": "revenue" | "orders" | "margin" | "aov",
  "current_period": { "start": "2025-12-01", "end": "2025-12-31" },
  "prior_period": { "start": "2025-11-01", "end": "2025-11-30" },
  "filters": { /* current dashboard filters */ },
  "dimensions": ["client_name", "product_brand", "client_country", "order_type"],
  "top_n": 5
}
Response:

{
  "metric": "revenue",
  "current_total": 55000,
  "prior_total": 65000,
  "total_change": -10000,
  "total_change_pct": -15.38,
  "direction": "decrease",
  "drivers": {
    "by_client_name": [
      {
        "name": "TechCorp",
        "current_value": 5000,
        "prior_value": 13000,
        "delta": -8000,
        "delta_pct": -61.5,
        "contribution_to_total_change": 80.0
      }
    ],
    "by_product_brand": [...],
    "by_client_country": [...],
    "by_order_type": [...]
  },
  "summary": {
    "primary_driver": {
      "dimension": "client_name",
      "entity": "TechCorp",
      "contribution": 80.0
    },
    "secondary_driver": {
      "dimension": "client_name",
      "entity": "RetailCo",
      "contribution": 15.0
    }
  }
}
LLM Prompt Template for Narration

You are a business analyst. Convert this variance analysis into a clear,
actionable explanation. Be concise but insightful.

DATA:
{driver_analysis_json}

GUIDELINES:
1. Start with the headline: what changed and by how much
2. Identify the #1 driver (highest contribution %)
3. Mention 2-3 secondary drivers if significant (>10% contribution)
4. Note any positive offsetting factors
5. If one dimension dominates (e.g., single client = 80%), emphasize this
6. Keep it under 150 words
7. Use bullet points for clarity
8. Do NOT speculate on business reasons - stick to the data
Frontend Integration
Chat Message Component:

┌──────────────────────────────────────────────────────────────┐
│ You: Why did revenue drop compared to last month?            │
├──────────────────────────────────────────────────────────────┤
│ AI: Revenue dropped $10,000 (-15.2%) compared to November.   │
│                                                              │
│ **Primary Drivers:**                                         │
│ • **TechCorp** accounts for 80% of the decline (-$8,000)     │
│ • **RetailCo** contributed 15% (-$1,500)                     │
│                                                              │
│ **By Brand:** Apple products saw the biggest drop (-$6,000)  │
│                                                              │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ [Waterfall Chart: Revenue Change by Client]            │  │
│ │                                                        │  │
│ │ Prior    TechCorp  RetailCo  Others   Current          │  │
│ │ $65k     -$8k      -$1.5k    -$0.5k   $55k             │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ▼ View Analysis Details                                      │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Dimension      │ Top Driver  │ Impact    │ % of Total  │  │
│ │ ───────────────┼─────────────┼───────────┼──────────── │  │
│ │ Client         │ TechCorp    │ -$8,000   │ 80%         │  │
│ │ Brand          │ Apple       │ -$6,000   │ 60%         │  │
│ │ Country        │ UAE         │ -$7,000   │ 70%         │  │
│ │ Product Type   │ Gift Cards  │ -$5,000   │ 50%         │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ [Drill into TechCorp →]                                      │
└──────────────────────────────────────────────────────────────┘
Visualization Options for Driver Analysis
Chart Type	Use Case	Priority
Waterfall Chart	Show how each driver contributed to total change	MVP
Horizontal Bar	Compare drivers within a dimension	MVP
Table	Detailed breakdown with all metrics	MVP
Treemap	Visual representation of contribution %	v2
Chat Slide-Over Panel (MVP)
Trigger: Button in sticky header or floating action button Position: Slides in from right, 400px width Behavior: Overlay, doesn't push content Components:

┌──────────────────────────────────────┐
│ 🤖 AI Assistant              [✕]    │
├──────────────────────────────────────┤
│ Context: Filtered to UAE, Dec 2025  │
├──────────────────────────────────────┤
│                                      │
│ User: What are my top products?      │
│                                      │
│ AI: Based on your current filters,   │
│ here are the top 5 products:         │
│                                      │
│ ┌────────────────────────────────┐  │
│ │ [Bar Chart Visualization]      │  │
│ └────────────────────────────────┘  │
│                                      │
│ 1. iTunes Gift Card - $45,230       │
│ 2. Google Play $50 - $38,100        │
│ ...                                  │
│                                      │
│ ▼ View SQL                          │
│ ```sql                              │
│ SELECT product_name, SUM(...)       │
│ ```                                 │
│                                      │
├──────────────────────────────────────┤
│ [Ask a question...]          [Send] │
└──────────────────────────────────────┘
Features:
Feature	Description	Priority
Context Awareness	Reads current filters from FilterContext	MVP
Message History	Scrollable conversation	MVP
Chart Rendering	Renders related_chart from AI response	MVP
SQL Display	Collapsible code block showing generated SQL	MVP
Copy SQL	Button to copy SQL to clipboard	MVP
Auto-scroll	Scrolls to latest message	MVP
Typing Indicator	"AI is thinking..." animation	MVP
Suggested Questions	3-4 starter questions based on current page	v2
Chat Dedicated Page (MVP)
Route: /dashboard/chat Layout: Full-width chat interface with larger visualization area Additional Features:
Feature	Description	Priority
Wider Charts	Full-width visualizations	MVP
Conversation Sidebar	List of past conversations	v2
Export Conversation	Download as PDF/Markdown	v2
Export & Share (v2)
Export Options
Export Type	Format	Scope	Priority
Current View PDF	PDF	Single page snapshot	v2
Data Export	CSV/Excel	Table data with current filters	v2
Chart Export	PNG/SVG	Individual chart	v2
Full Report	PDF	All 3 pages combined	v3
Share Features
Feature	Description	Priority
Copy Link	URL with encoded filter state (e.g., /dashboard/overview?filters=base64...)	v2
Email Share	Opens email client with link + summary	v3
Saved Views & Bookmarks (v3)
User Saved Views

┌─────────────────────────────────────┐
│ 📑 Saved Views                [+]   │
├─────────────────────────────────────┤
│ ⭐ Q4 UAE Analysis                  │
│    Filters: UAE, Oct-Dec 2025       │
│                                     │
│ ⭐ Problem Clients                  │
│    Filters: Margin < 10%            │
│                                     │
│ ⭐ Apple Products Only              │
│    Filters: Brand = Apple           │
└─────────────────────────────────────┘
Features:
Feature	Description	Priority
Save Current	Save current filter combination with name	v3
Load View	One-click apply saved filters	v3
Default View	Set a saved view as default on login	v3
Share View	Share saved view with team members	v3
Alerts & Thresholds (v3)
Alert Configuration

┌─────────────────────────────────────┐
│ 🔔 Alerts                    [+]    │
├─────────────────────────────────────┤
│ ⚡ AOV Below $50                    │
│    Status: 🟢 OK (Current: $67)     │
│                                     │
│ ⚡ Top Client >30% Revenue          │
│    Status: 🟡 Warning (28%)         │
│                                     │
│ ⚡ Daily Revenue Drop >20%          │
│    Status: 🟢 OK                    │
└─────────────────────────────────────┘
Alert Types:
Type	Example	Priority
Threshold Alert	"Alert if AOV < $50"	v3
Trend Alert	"Alert if revenue drops >20% week-over-week"	v3
Anomaly Alert	"Alert on any Z-score > 3.0"	v3
Concentration Alert	"Alert if any client >30% of revenue"	v3
Delivery:
Channel	Priority
In-app notification	v3
Email digest	v3
Slack integration	v3
Comparison Benchmarks (v2-v3)
Benchmark Types
Benchmark	Description	Implementation	Priority
Target/Goal Line	User-defined targets	Horizontal dashed line on charts	v2
Budget vs Actual	Compare to budget data	Requires budget data source	v3
Industry Benchmark	Compare to industry averages	Requires external data	v3
Target/Goal Implementation (v2)
UI: Settings modal to define targets

┌─────────────────────────────────────┐
│ 🎯 Performance Targets              │
├─────────────────────────────────────┤
│ Monthly Revenue Target: $________   │
│ AOV Target: $________               │
│ Margin Target: ________%            │
│ Orders/Client Target: ________      │
├─────────────────────────────────────┤
│ [Cancel]              [Save]        │
└─────────────────────────────────────┘
Display:
Dashed horizontal line on trend charts
KPI cards show "vs Target" comparison option
Color coding: Green if above target, Red if below
Budget vs Actual (v3)
Requirements:
Budget data table in database
Budget by: Month, Product Type, Country
UI to input/import budget
Display:
Side-by-side bars: Actual (solid) vs Budget (striped)
Variance column in tables: "Actual - Budget"
Implementation Phases Summary
Phase MVP (Current Sprint)
Component	Page	Description
Overview Enhancements	P1	Wire up DualAxisChart, add anomaly table
Market Page	P2	ClientScatter, Leaderboard with sparklines
Catalog Page	P3	Product table with margin fallback
Chat Slide-Over	Global	Basic chat with visualization
Chat Page	Global	Full-page chat
Cross-Page Navigation	Global	Clickable entity links
Empty States	Global	No-data handling
Data Freshness	Global	Last updated timestamp
Phase v2
Component	Description
Metric Role Toggle	Swap bar/line on dual-axis
Dot Sizing/Coloring	Enhanced scatter plot
Churn Risk Flags	Client health indicators
Export Features	PDF, CSV, PNG exports
Share Link	Encoded filter URLs
Target Lines	Goal visualization
Concentration Warnings	Supplier/client risk
Phase v3
Component	Description
Saved Views	Bookmark filter combinations
Alert System	Threshold-based notifications
Budget Comparison	Budget vs actual
Industry Benchmarks	External comparison data
Advanced Exports	Full report generation
Technical Notes
Backend Requirements for New Features
Feature	Backend Change Needed	Priority
Data Freshness	Add /api/meta endpoint or include in /health	MVP
Sparklines	Modify leaderboard endpoint to include trend data	MVP
Driver Analysis	New POST /api/analyze/drivers endpoint (see AI Chat section)	MVP
Churn Risk	Add last_order_date to client data	v2
Targets	New targets table + CRUD endpoints	v2
Saved Views	New saved_views table + CRUD endpoints	v3
Alerts	New alerts table + background job processor	v3
Driver Analysis Endpoint Implementation Notes
File: backend/app/api/analyze.py (new) SQL Logic:

-- For each dimension (e.g., client_name):
WITH current_period AS (
  SELECT client_name, SUM(order_price_in_aed) as revenue
  FROM fact_orders
  WHERE order_date BETWEEN :current_start AND :current_end
  GROUP BY client_name
),
prior_period AS (
  SELECT client_name, SUM(order_price_in_aed) as revenue
  FROM fact_orders
  WHERE order_date BETWEEN :prior_start AND :prior_end
  GROUP BY client_name
)
SELECT
  COALESCE(c.client_name, p.client_name) as name,
  COALESCE(c.revenue, 0) as current_value,
  COALESCE(p.revenue, 0) as prior_value,
  COALESCE(c.revenue, 0) - COALESCE(p.revenue, 0) as delta
FROM current_period c
FULL OUTER JOIN prior_period p ON c.client_name = p.client_name
ORDER BY ABS(delta) DESC
LIMIT 5;
LLM Integration:
Detect "why/explain/what caused" intent in llm_engine.py
Call driver analysis endpoint instead of SQL generation
Pass structured results to narration prompt
State Management Additions

// FilterContext additions
interface FilterContextType {
  // Existing...

  // New MVP
  selectedClient: string | null;  // For cross-page navigation

  // New v2
  targets: {
    monthlyRevenue?: number;
    aov?: number;
    margin?: number;
  };

  // New v3
  savedViews: SavedView[];
  alerts: Alert[];
}
File Structure for Implementation

frontend/
├── app/dashboard/
│   ├── overview/page.tsx      # Enhance with trends, anomalies
│   ├── market/page.tsx        # Build from scratch
│   ├── catalog/page.tsx       # Build from scratch
│   └── chat/page.tsx          # New page
├── components/
│   ├── dashboard/
│   │   ├── ... (existing)
│   │   ├── AnomalyCard.tsx    # New - Top 3 anomalies
│   │   ├── SparklineCell.tsx  # New - For table sparklines
│   │   └── EmptyState.tsx     # New - Empty state component
│   ├── chat/
│   │   ├── ChatSidebar.tsx    # New - Slide-over panel
│   │   ├── ChatMessage.tsx    # New - Message bubble
│   │   ├── ChatInput.tsx      # New - Input field
│   │   └── ChatViz.tsx        # New - Embedded visualization
│   └── shared/
│       ├── EntityLink.tsx     # New - Clickable entity names
│       └── ExportMenu.tsx     # New v2 - Export dropdown
└── lib/
    ├── api-client.ts          # Add meta endpoint
    └── types.ts               # Add new types
IMPLEMENTATION PLAN
Phase 0: Backend Enhancements (Required Before Frontend)
0A: Driver Analysis Endpoint (MVP)
File: backend/app/api/analyze.py (new) Purpose: Enable AI to answer "why did X change?" questions with mathematical precision. Tasks:
Create new router file analyze.py
Implement POST /api/analyze/drivers endpoint
Create Pydantic models for request/response
Implement variance scan logic across dimensions (client, brand, country, product_type)
Add contribution percentage calculation
Register router in main.py
Request Model:

class DriverAnalysisRequest(BaseModel):
    metric: Literal["revenue", "orders", "margin", "aov"]
    current_period: DateRange
    prior_period: DateRange
    filters: Optional[DashboardFilters]
    dimensions: List[str] = ["client_name", "product_brand", "client_country", "order_type"]
    top_n: int = 5
Core SQL Logic:

WITH current_period AS (
    SELECT {dimension}, SUM(order_price_in_aed) as value
    FROM fact_orders
    WHERE order_date BETWEEN :current_start AND :current_end
    GROUP BY {dimension}
),
prior_period AS (
    SELECT {dimension}, SUM(order_price_in_aed) as value
    FROM fact_orders
    WHERE order_date BETWEEN :prior_start AND :prior_end
    GROUP BY {dimension}
)
SELECT
    COALESCE(c.{dimension}, p.{dimension}) as name,
    COALESCE(c.value, 0) as current_value,
    COALESCE(p.value, 0) as prior_value,
    COALESCE(c.value, 0) - COALESCE(p.value, 0) as delta
FROM current_period c
FULL OUTER JOIN prior_period p ON c.{dimension} = p.{dimension}
ORDER BY ABS(delta) DESC
LIMIT :top_n;
Files to create/modify:
backend/app/api/analyze.py (new)
backend/app/models.py (add DriverAnalysisRequest, DriverAnalysisResponse)
backend/main.py (register analyze router)
0B: LLM Engine Enhancement for Driver Analysis (MVP)
File: backend/app/services/llm_engine.py Tasks:
Add intent detection to classify questions:
Data Query: "show me", "list", "what are" → SQL generation
Driver Analysis: "why did", "explain", "what caused" → call /api/analyze/drivers
Add narration prompt template for driver analysis results
Integrate driver endpoint call when diagnostic intent detected
Intent Detection Logic:

DIAGNOSTIC_PATTERNS = [
    r"why did",
    r"why is",
    r"why are",
    r"what caused",
    r"explain the",
    r"reason for",
    r"what happened to"
]

def detect_intent(question: str) -> Literal["data_query", "driver_analysis"]:
    question_lower = question.lower()
    for pattern in DIAGNOSTIC_PATTERNS:
        if re.search(pattern, question_lower):
            return "driver_analysis"
    return "data_query"
Files to modify:
backend/app/services/llm_engine.py
0C: Data Freshness Endpoint (MVP)
File: backend/app/api/dashboard.py or backend/main.py Tasks:
Add last_updated field to /health response OR create new /api/meta endpoint
Query database for MAX(load_ts) from fact_orders table
Return formatted timestamp
Implementation:

@app.get("/api/meta")
async def get_meta():
    query = "SELECT MAX(load_ts) as last_updated FROM fact_orders"
    result = execute_query(query)
    return {
        "last_updated": result[0]["last_updated"],
        "data_source": "munero.sqlite",
        "refresh_schedule": "Daily at 2:00 AM UTC"
    }
Files to modify:
backend/main.py or backend/app/api/dashboard.py
0D: Sparkline Data Enhancement (MVP)
File: backend/app/api/dashboard.py Tasks:
Modify /api/dashboard/breakdown endpoint to include optional trend data
Add include_trend: bool = False parameter
When true, include 6-month revenue trend per entity
Enhanced Response:

class LeaderboardRow(BaseModel):
    name: str
    revenue: float
    orders: int
    # ... existing fields
    trend: Optional[List[float]] = None  # 6 monthly values for sparkline
SQL for Trend:

SELECT
    client_name,
    strftime('%Y-%m', order_date) as month,
    SUM(order_price_in_aed) as revenue
FROM fact_orders
WHERE order_date >= date('now', '-6 months')
GROUP BY client_name, month
ORDER BY month
Files to modify:
backend/app/api/dashboard.py
backend/app/models.py (add trend field to LeaderboardRow)
0E: Backend Testing
Tasks:
Test driver analysis endpoint with various metrics and periods
Verify intent detection in LLM engine
Test sparkline data generation
Validate meta endpoint response
Test Script: scripts/test_analyze.sh

# Test driver analysis
curl -X POST http://localhost:8000/api/analyze/drivers \
  -H "Content-Type: application/json" \
  -d '{
    "metric": "revenue",
    "current_period": {"start": "2025-12-01", "end": "2025-12-31"},
    "prior_period": {"start": "2025-11-01", "end": "2025-11-30"},
    "top_n": 5
  }'

# Test meta endpoint
curl http://localhost:8000/api/meta
Phase 1: Overview Page Enhancements (Frontend)
File: frontend/app/dashboard/overview/page.tsx
Note: Starting with Overview because it's the landing page and already 60% complete.
Tasks:
Revenue Trend Chart (Zone 3A)
Replace placeholder with actual <DualAxisChart />
Fetch via apiClient.getTrend(filters, 'month')
Wire up Metric Role Toggle (swap bar/line data keys)
Revenue by Product Type (Zone 3B)
Create <ProductTypeChart /> component
Fetch via apiClient.getLeaderboard(filters, 'order_type')
If ≤5 types: Render as Donut chart (PieChart with inner radius)
If >5 types: Render as Horizontal Bar chart
Auto-group smallest into "Other" if >8 categories
Enhanced tooltip showing: Amount, % of total, YoY growth
Top 3 Anomalies Card (Zone 4B)
Create <AnomalyCard /> component
Extract top 3 anomalies from trend data (highest Z-scores)
Display: Date, Metric, % change, Z-score
Click row → (v2) drill to that date
Top Products Widget
Fetch via apiClient.getTopProducts(filters, 5)
Display in card format or mini-table
Data Freshness Indicator
Add apiClient.getMeta() call
Display "Last updated: X" in header
Files to create/modify:
frontend/app/dashboard/overview/page.tsx
frontend/components/dashboard/ProductTypeChart.tsx (new)
frontend/components/dashboard/AnomalyCard.tsx (new)
frontend/lib/api-client.ts (add getMeta method)
frontend/app/dashboard/layout.tsx (add freshness indicator to header)
Phase 2: Market Analysis Page (Frontend)
File: frontend/app/dashboard/market/page.tsx
Tasks:
Client Scatter Plot (Zone 2)
Fetch data via apiClient.getScatter(filters)
Render <ClientScatter /> component
Implement onClientClick → update FilterContext.selectedClients (global filter)
Client Leaderboard (Zone 3)
Fetch via apiClient.getLeaderboard(filters, 'client_name')
Render <DataTable /> with columns: Client, Revenue, Orders, AOV, Margin
Row click → same global filter behavior as scatter
Country Bar Chart (Zone 2A)
Create <CountryBarChart /> component (or reuse generic HorizontalBarChart)
Fetch via apiClient.getLeaderboard(filters, 'client_country')
Render as horizontal bar chart sorted by revenue (descending)
Show top 10 countries, group rest as "Other"
Click bar → filter to that country (update FilterContext)
Tooltip: Country name, Revenue, Orders, % of total
Client KPI Cards (Zone 1)
Display 3 cards: Active Clients, Avg Revenue/Client, Top Client Share %
Add concentration risk tooltip on Top Client Share %
If Top Client Share >25%, show amber warning badge
Files to create/modify:
frontend/app/dashboard/market/page.tsx
frontend/components/dashboard/CountryBarChart.tsx (new - or reuse existing bar chart)
frontend/components/dashboard/FilterContext.tsx (add setSelectedClient helper if needed)
Phase 3: Catalog Analysis Page (Frontend)
File: frontend/app/dashboard/catalog/page.tsx
Tasks:
Supply KPIs with Margin Fallback Logic
Reuse <MetricCard /> for product/brand metrics
Implement Contribution Index fallback:
If COGS exists: Show "X% Margin" (green badge)
If COGS null/0: Show "X% Contribution" (gray/blue badge) with tooltip
Formula: Contribution = (Item Revenue / Total Revenue) * 100
Product Grid (Zone 3)
Fetch via apiClient.getTopProducts(filters, 20) or getLeaderboard(filters, 'product_name')
Render <DataTable /> with sortable columns
Default sort: Profit Margin (or Contribution if no COGS)
Brand Leaderboard (Zone 2A)
Fetch via apiClient.getLeaderboard(filters, 'product_brand')
Render <DataTable /> with columns: Brand, Revenue, Orders, Products, Growth %, Margin/Contribution
Click brand → filter dashboard to that brand
Growth % tooltip explaining calculation
Supplier Concentration Chart (Zone 2B)
Create <SupplierBarChart /> component
Fetch via apiClient.getLeaderboard(filters, 'supplier_name')
Render as horizontal bar chart sorted by revenue (descending)
Click bar → filter to that supplier
(v2) Add vertical reference line at 25% for "healthy diversification threshold"
(v2) Show warning badge if any supplier >40%
Files to create/modify:
frontend/app/dashboard/catalog/page.tsx
frontend/components/dashboard/SupplierBarChart.tsx (new)
frontend/components/dashboard/MetricCard.tsx (add contribution fallback display)
Phase 4: AI Chat Feature (Frontend + Backend Integration)
4A: Chat Slide-Over Panel
File: frontend/components/chat/ChatSidebar.tsx (new)
Slide-over panel triggered by button in sticky header
On open: read selectedClients, dateRange from FilterContext
Message input + send button
Message history display
Parse AI response:
Display answer_text as formatted text
If related_chart present, render appropriate chart component
Show sql_generated in collapsible code block
4B: Dedicated Chat Page
File: frontend/app/dashboard/chat/page.tsx (new)
Full-page chat experience
Same functionality as slide-over but with more space
Larger visualization area for charts
Longer conversation history visible
4C: Navigation Update
File: frontend/components/dashboard/NavTabs.tsx
Add "AI Assistant" or "Chat" tab linking to /dashboard/chat
4D: Driver Analysis Visualization
Files: frontend/components/chat/DriverAnalysisViz.tsx (new) Tasks:
Create Waterfall chart component for driver analysis results
Create breakdown table showing drivers by dimension
Add "Drill into [Entity]" button that updates FilterContext
Waterfall Chart Implementation (using Recharts):

// Waterfall chart showing: Prior → Driver1 → Driver2 → ... → Current
const WaterfallChart = ({ data }: { data: DriverAnalysisResponse }) => {
  const chartData = [
    { name: 'Prior', value: data.prior_total, fill: '#6366f1' },
    ...data.drivers.by_client_name.slice(0, 3).map(d => ({
      name: d.name,
      value: d.delta,
      fill: d.delta > 0 ? '#22c55e' : '#ef4444'
    })),
    { name: 'Current', value: data.current_total, fill: '#6366f1' }
  ];
  // Render as ComposedChart with Bar + ReferenceLine
};
4E: API Client Updates
File: frontend/lib/api-client.ts Add methods:

// Driver analysis for "why" questions
async analyzeDrivers(request: DriverAnalysisRequest): Promise<DriverAnalysisResponse>

// Enhanced chat that handles both query modes
async chat(message: string, filters: DashboardFilters): Promise<ChatResponse>
Files to create/modify:
frontend/components/chat/ChatSidebar.tsx (new)
frontend/components/chat/ChatMessage.tsx (new)
frontend/components/chat/ChatInput.tsx (new)
frontend/components/chat/DriverAnalysisViz.tsx (new - waterfall + table)
frontend/app/dashboard/chat/page.tsx (new)
frontend/app/dashboard/layout.tsx (add chat toggle button)
frontend/components/dashboard/NavTabs.tsx (add chat tab)
frontend/lib/api-client.ts (add analyzeDrivers method)
frontend/lib/types.ts (add DriverAnalysisRequest/Response types)
Phase 5: Shared Components (MVP)
5A: EntityLink Component
File: frontend/components/shared/EntityLink.tsx (new) Purpose: Reusable clickable link for entity names (clients, brands, products, suppliers) across all pages. Props:

interface EntityLinkProps {
  type: 'client' | 'brand' | 'product' | 'supplier' | 'country';
  value: string;
  navigateTo?: string;  // Optional override for target page
  children?: React.ReactNode;
}
Implementation:

const EntityLink = ({ type, value, navigateTo, children }: EntityLinkProps) => {
  const { setFilters } = useFilter();
  const router = useRouter();

  const defaultRoutes = {
    client: '/dashboard/market',
    brand: '/dashboard/catalog',
    product: '/dashboard/catalog',
    supplier: '/dashboard/catalog',
    country: '/dashboard/market'
  };

  const handleClick = () => {
    // Update FilterContext with selected entity
    setFilters(prev => ({
      ...prev,
      [`selected${type.charAt(0).toUpperCase() + type.slice(1)}`]: value
    }));
    // Navigate to appropriate page
    router.push(navigateTo || defaultRoutes[type]);
  };

  return (
    <button
      onClick={handleClick}
      className="text-blue-600 hover:underline cursor-pointer font-medium"
    >
      {children || value}
    </button>
  );
};
Usage:

// In DataTable cells
<EntityLink type="client" value={row.client_name} />
<EntityLink type="brand" value={row.product_brand} />
5B: EmptyState Component
File: frontend/components/shared/EmptyState.tsx (new) Purpose: Consistent empty state display when filters return no data. Props:

interface EmptyStateProps {
  title?: string;
  message?: string;
  suggestions?: string[];
  showResetButton?: boolean;
  onReset?: () => void;
  variant?: 'full' | 'inline' | 'card';  // Different sizes
}
Implementation:

const EmptyState = ({
  title = "No Data Available",
  message = "No results match your current filters.",
  suggestions = [
    "Expand the date range",
    "Remove some filters",
    "Try a different currency"
  ],
  showResetButton = true,
  onReset,
  variant = 'full'
}: EmptyStateProps) => {
  const { resetFilters } = useFilter();

  return (
    <div className={cn(
      "flex flex-col items-center justify-center text-center",
      variant === 'full' && "py-16",
      variant === 'inline' && "py-8",
      variant === 'card' && "py-4"
    )}>
      <BarChart3 className="h-12 w-12 text-muted-foreground mb-4" />
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="text-muted-foreground mt-1">{message}</p>

      {suggestions.length > 0 && variant !== 'card' && (
        <ul className="mt-4 text-sm text-muted-foreground">
          {suggestions.map((s, i) => (
            <li key={i}>• {s}</li>
          ))}
        </ul>
      )}

      {showResetButton && (
        <Button
          variant="outline"
          className="mt-4"
          onClick={onReset || resetFilters}
        >
          Reset Filters
        </Button>
      )}
    </div>
  );
};
Usage:

// In charts
{data.length === 0 ? <EmptyState variant="inline" /> : <Chart data={data} />}

// In tables
{rows.length === 0 && <EmptyState variant="card" title="No matching records" />}
5C: SparklineCell Component
File: frontend/components/dashboard/SparklineCell.tsx (new) Purpose: Mini trend chart for use in DataTable cells showing 6-month trend. Props:

interface SparklineCellProps {
  data: number[];  // 6 monthly values
  width?: number;
  height?: number;
  color?: string;
  showTrend?: boolean;  // Show ↑/↓ indicator
}
Implementation:

const SparklineCell = ({
  data,
  width = 80,
  height = 24,
  color = '#6366f1',
  showTrend = true
}: SparklineCellProps) => {
  if (!data || data.length === 0) {
    return <span className="text-muted-foreground">—</span>;
  }

  const trend = data[data.length - 1] - data[0];
  const trendColor = trend >= 0 ? 'text-green-600' : 'text-red-600';

  return (
    <div className="flex items-center gap-2">
      <LineChart width={width} height={height}>
        <Line
          data={data.map((value, index) => ({ value, index }))}
          dataKey="value"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
        />
      </LineChart>
      {showTrend && (
        <span className={cn("text-xs", trendColor)}>
          {trend >= 0 ? '↑' : '↓'}
        </span>
      )}
    </div>
  );
};
Usage in DataTable:

// Column definition
{
  id: 'trend',
  header: 'Trend',
  cell: ({ row }) => <SparklineCell data={row.original.trend} />
}
Files to create:
frontend/components/shared/EntityLink.tsx (new)
frontend/components/shared/EmptyState.tsx (new)
frontend/components/dashboard/SparklineCell.tsx (new)
Phase 6: Polish & Validation
Tasks:
Data Consistency Audit
Verify Overview "Total Revenue" matches sum of Market page client revenues
Cross-check with backend directly if discrepancies found
Responsive Design
Ensure 4-column KPI grid → 2-column on tablet → 1-column on mobile
Test scatter plot and charts on smaller screens
Contribution Index Tooltip
When margin unavailable, show tooltip: "Cost data missing. This item contributes X% to total revenue."
Loading States
Ensure all data fetches show skeleton loaders
Handle error states gracefully
Chat UX Polish
Auto-scroll to latest message
Show typing indicator while AI responds
Copy button for SQL queries
Implementation Order (Recommended)
Phase 0: Backend (Required First)
Driver Analysis Endpoint - POST /api/analyze/drivers for "why" questions
LLM Intent Detection - Route diagnostic questions to driver analysis
Meta Endpoint - Data freshness timestamp
Sparkline Enhancement - Add trend data to leaderboard response
Phase 1-3: Frontend Dashboard Pages
Overview Enhancements - Landing page, trend chart, top products, data freshness
Market Page - ClientScatter, Country Bar Chart, Leaderboard with sparklines, global filtering
Catalog Page - Product table, Brand leaderboard, Supplier chart, margin fallback logic
Phase 4: AI Chat
Chat Slide-Over - Core chat with SQL display + chart rendering
Chat Dedicated Page - Full-page experience
Driver Analysis Viz - Waterfall chart + breakdown table for "why" answers
Phase 5: Shared Components
EntityLink - Cross-page navigation for clickable entity names
EmptyState - No-data handling component
SparklineCell - Mini trend charts for DataTable cells
Phase 6: Polish
Data Consistency - Validate totals across pages
Responsive Design - Mobile/tablet breakpoints
Loading States - Skeleton loaders
Chat UX - Auto-scroll, typing indicators, copy SQL button
Rationale: Backend must be done first since Driver Analysis endpoint is required for the AI "why did X drop?" capability. Then Overview page first (landing page, 60% done), followed by other dashboard pages, then chat feature which depends on all the above.
Key Files Reference
Existing Components (Done)
Component	Path	Status
FilterContext	frontend/components/dashboard/FilterContext.tsx	✅ Done
FilterBar	frontend/components/dashboard/FilterBar.tsx	✅ Done
MetricCard	frontend/components/dashboard/MetricCard.tsx	✅ Done (needs fallback)
DualAxisChart	frontend/components/dashboard/DualAxisChart.tsx	✅ Done
ClientScatter	frontend/components/dashboard/ClientScatter.tsx	✅ Done
DataTable	frontend/components/dashboard/DataTable.tsx	✅ Done
API Client	frontend/lib/api-client.ts	✅ Done
Types	frontend/lib/types.ts	✅ Done
Pages (To Build)
Page	Path	Status
Overview Page	frontend/app/dashboard/overview/page.tsx	🔶 Partial
Market Page	frontend/app/dashboard/market/page.tsx	❌ Placeholder
Catalog Page	frontend/app/dashboard/catalog/page.tsx	❌ Placeholder
Chat Page	frontend/app/dashboard/chat/page.tsx	❌ Not started
New Components to Create (MVP)
Component	Path	Phase
ProductTypeChart	frontend/components/dashboard/ProductTypeChart.tsx	Phase 1
AnomalyCard	frontend/components/dashboard/AnomalyCard.tsx	Phase 1
CountryBarChart	frontend/components/dashboard/CountryBarChart.tsx	Phase 2
SupplierBarChart	frontend/components/dashboard/SupplierBarChart.tsx	Phase 3
ChatSidebar	frontend/components/chat/ChatSidebar.tsx	Phase 4
ChatMessage	frontend/components/chat/ChatMessage.tsx	Phase 4
ChatInput	frontend/components/chat/ChatInput.tsx	Phase 4
DriverAnalysisViz	frontend/components/chat/DriverAnalysisViz.tsx	Phase 4
EntityLink	frontend/components/shared/EntityLink.tsx	Phase 5
EmptyState	frontend/components/shared/EmptyState.tsx	Phase 5
SparklineCell	frontend/components/dashboard/SparklineCell.tsx	Phase 5
Backend Files to Create/Modify
File	Change	Phase
backend/app/api/analyze.py	New - Driver Analysis endpoint	Phase 0
backend/app/services/llm_engine.py	Add intent detection	Phase 0
backend/app/models.py	Add new Pydantic models	Phase 0
backend/main.py	Register analyze router, add /api/meta	Phase 0
backend/app/api/dashboard.py	Add sparkline trend data	Phase 0