# DualAxisChart Visual Structure

## Component Layout

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                        Card Container (Shadcn)                        ┃
┃ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ┃
┃ ┃                         CardHeader                               ┃ ┃
┃ ┃                                                                   ┃ ┃
┃ ┃  Revenue & Order Volume Trends          [⇄ Swap Axis]           ┃ ┃
┃ ┃  ─────────────────────────────           ────────────            ┃ ┃
┃ ┃  Title (h3, left)                        Button (ghost, sm)      ┃ ┃
┃ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ┃
┃ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ ┃
┃ ┃                         CardContent                              ┃ ┃
┃ ┃ ┌─────────────────────────────────────────────────────────────┐ ┃ ┃
┃ ┃ │          ResponsiveContainer (width=100%, height=400)       │ ┃ ┃
┃ ┃ │ ┌─────────────────────────────────────────────────────────┐ │ ┃ ┃
┃ ┃ │ │                    ComposedChart                        │ │ ┃ ┃
┃ ┃ │ │                                                         │ │ ┃ ┃
┃ ┃ │ │  Y-Axis                                      Y-Axis     │ │ ┃ ┃
┃ ┃ │ │  (Left)                                      (Right)    │ │ ┃ ┃
┃ ┃ │ │    │                                            │        │ │ ┃ ┃
┃ ┃ │ │ 200K│                                           │600     │ │ ┃ ┃
┃ ┃ │ │     │      ▂▂                                   │        │ │ ┃ ┃
┃ ┃ │ │ 150K│     █  █                                  │450     │ │ ┃ ┃
┃ ┃ │ │     │    █    █──────●                          │        │ │ ┃ ┃
┃ ┃ │ │ 100K│   █      │  ●───●───────●                 │300     │ │ ┃ ┃
┃ ┃ │ │     │  █       │      │       │                 │        │ │ ┃ ┃
┃ ┃ │ │  50K│ █        │  ●   │       │                 │150     │ │ ┃ ┃
┃ ┃ │ │     │          │      │       │                 │        │ │ ┃ ┃
┃ ┃ │ │   0 ┼──────────────────────────────────────────┼   0    │ │ ┃ ┃
┃ ┃ │ │     Jan  Feb  Mar  Apr  May  Jun  Jul  Aug          │ │ ┃ ┃
┃ ┃ │ │                                                         │ │ ┃ ┃
┃ ┃ │ │     █ Blue Bar (#3b82f6) - Revenue                     │ │ ┃ ┃
┃ ┃ │ │     ─ Orange Line (#f97316, 2px) - Order Count         │ │ ┃ ┃
┃ ┃ │ │     ● Red Dots (#ef4444) - Anomalies                   │ │ ┃ ┃
┃ ┃ │ │                                                         │ │ ┃ ┃
┃ ┃ │ │  Legend: [█] Revenue  [─] Order Count  [●] Anomalies (2) │ │ ┃ ┃
┃ ┃ │ └─────────────────────────────────────────────────────────┘ │ ┃ ┃
┃ ┃ └─────────────────────────────────────────────────────────────┘ ┃ ┃
┃ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## Chart Layers (Z-Index Order)

```
Layer 5 (Top):    Scatter (Red Anomaly Dots) 🔴
Layer 4:          Line (Orange, 2px stroke) 🟠
Layer 3:          Bar (Blue) 🔵
Layer 2:          CartesianGrid (Dashed)
Layer 1 (Bottom): Axes & Labels
```

## Tooltip on Hover

```
┌──────────────────────────┐
│ Feb 2025                 │  ← Period label (xKey)
│ ● Revenue: 180,000       │  ← Bar value (barKey)
│ ● Order Count: 520       │  ← Line value (lineKey)
│ ──────────────────────   │
│ ⚠ Revenue Anomaly Detected │  ← If is_revenue_anomaly === true
│ ⚠ Order Anomaly Detected   │  ← If is_order_anomaly === true
└──────────────────────────┘
```

## Swap Axis Button States

```
BEFORE SWAP:
┌─────────────────────────────────┐
│ Revenue (Bar - Blue)            │
│ Order Count (Line - Orange)     │
└─────────────────────────────────┘

           ↓ [Click Swap Axis]

AFTER SWAP:
┌─────────────────────────────────┐
│ Order Count (Bar - Blue)        │
│ Revenue (Line - Orange)         │
└─────────────────────────────────┘
```

## Color Palette

```
Component         Color Code    Swatch
───────────────────────────────────────
Bar Chart         #3b82f6       ████ Blue 500
Line Chart        #f97316       ████ Orange 500
Anomaly Dot       #ef4444       ████ Red 500
Anomaly Stroke    #dc2626       ████ Red 600
Grid Lines        #e5e7eb       ──── Gray 200
Axis Lines        #d1d5db       ──── Gray 300
Axis Labels       #6b7280       ──── Gray 500
Title             #111827       ──── Gray 900
Background        #ffffff       ████ White

Dark Mode:
Grid Lines        #374151       ──── Gray 700
Background        #1f2937       ████ Gray 800
Title             #f9fafb       ──── Gray 100
```

## Measurements

```
Chart Container:
  Height: 400px
  Width: 100% (responsive)
  Margin: top=20, right=30, left=20, bottom=20

Bar:
  Max Width: 60px
  Border Radius: 4px (top corners only)
  Fill: #3b82f6

Line:
  Stroke Width: 2px
  Stroke: #f97316
  Dot Radius: 4px (normal), 6px (active)

Anomaly Dots:
  Radius: 6px
  Fill: #ef4444
  Stroke: #dc2626
  Stroke Width: 2px
  Opacity: 0.9

Legend:
  Icon Size: 4x4 (16px)
  Gap: 16px
  Font Size: 14px
```

## Empty State

```
┌────────────────────────────────────┐
│                                    │
│                                    │
│        No data available           │
│                                    │
│   Adjust filters to view chart     │
│            data                    │
│                                    │
│                                    │
└────────────────────────────────────┘
```

## Responsive Behavior

```
Desktop (>1024px):
┌─────────────────────────────────────────────────┐
│ Full width chart with all details visible      │
└─────────────────────────────────────────────────┘

Tablet (768-1024px):
┌────────────────────────────────────┐
│ Slightly compressed, readable      │
└────────────────────────────────────┘

Mobile (<768px):
┌──────────────────────┐
│ Compact layout,      │
│ smaller fonts        │
└──────────────────────┘
```

## Data Flow

```
Parent Component
       ↓
   [data prop]
       ↓
DualAxisChart Component
       ↓
   Filter Anomalies
       ↓
┌──────┴──────┐
│             │
Bar Chart   Line Chart   Scatter (Anomalies)
│             │               │
xKey        xKey            Filtered data
barKey      lineKey         (only anomalies)
│             │               │
Left Y      Right Y         Left Y
```

## Interaction Flow

```
User hovers over chart
       ↓
Tooltip appears
       ↓
Shows: Period, Values, Anomaly warnings

User clicks "Swap Axis"
       ↓
onMetricToggle() called
       ↓
Parent updates barKey/lineKey
       ↓
Chart re-renders with swapped metrics
```

## Component Architecture

```
DualAxisChart.tsx
├── DualAxisChartProps (interface)
│   ├── data: Array
│   ├── barKey: string
│   ├── lineKey: string
│   ├── xKey: string
│   ├── title: string
│   └── onMetricToggle?: function
│
├── CustomTooltip (internal component)
│   ├── Shows period label
│   ├── Shows metric values
│   └── Shows anomaly warnings
│
├── formatYAxis (helper function)
│   └── Formats numbers to K/M notation
│
├── renderLegend (helper function)
│   └── Adds anomaly count to legend
│
└── DualAxisChart (main component)
    ├── Filter anomalies
    ├── Format metric names
    ├── Render Card header
    ├── Render chart or empty state
    └── Export component
```

## Usage Pattern

```typescript
// 1. Import component
import { DualAxisChart } from '@/components/dashboard';

// 2. Prepare data
const data = [
  { month: 'Jan', revenue: 125000, orders: 450, is_revenue_anomaly: false },
  { month: 'Feb', revenue: 180000, orders: 520, is_revenue_anomaly: true },
];

// 3. Render component
<DualAxisChart
  data={data}
  barKey="revenue"
  lineKey="orders"
  xKey="month"
  title="Revenue & Order Volume"
  onMetricToggle={() => handleSwap()}
/>
```

## Anomaly Detection Logic

```typescript
// Filter data to find anomalies
const anomalyData = data.filter(
  (point) => 
    point.is_revenue_anomaly === true ||  // Revenue anomaly
    point.is_order_anomaly === true       // Order anomaly
);

// Only render scatter layer if anomalies exist
{anomalyData.length > 0 && (
  <Scatter
    yAxisId="left"
    data={anomalyData}
    fill="#ef4444"
    // Red dots appear!
  />
)}
```

---

**Visual Reference Created**: December 31, 2025  
**Component**: DualAxisChart  
**Status**: ✅ Complete & Production Ready
