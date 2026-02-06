# MetricCard - Quick Reference

## Import
```tsx
import { MetricCard } from '@/components/dashboard/MetricCard';
```

## Basic Usage
```tsx
<MetricCard
  label="Total Revenue"
  value="AED 125,000"
  trend={12.5}
  trendDirection="up"
  comparisonLabel="vs Last Year"
  onToggleComparison={(mode) => setComparisonMode(mode)}
/>
```

## Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `label` | `string` | ✅ | - | Card title (e.g., "Total Revenue") |
| `value` | `string` | ✅ | - | Formatted value (e.g., "AED 125,000") |
| `trend` | `number` | ❌ | - | Percentage change (e.g., 12.5) |
| `trendDirection` | `'up' \| 'down' \| 'flat' \| 'neutral'` | ❌ | `'neutral'` | Arrow direction |
| `comparisonLabel` | `string` | ❌ | - | Context text (e.g., "vs Last Year") |
| `onToggleComparison` | `(mode) => void` | ❌ | - | Callback for settings menu |
| `isLoading` | `boolean` | ❌ | `false` | Show loading skeleton |

## Trend Directions

```tsx
'up'      → Green badge with ↑ ArrowUp
'down'    → Red badge with ↓ ArrowDown
'flat'    → Gray badge with − Minus
'neutral' → Gray badge with − Minus
```

## Comparison Modes

```tsx
onToggleComparison={(mode) => {
  // mode: 'yoy' | 'prev_period' | 'none'
}}
```

## Examples

### Positive Trend
```tsx
<MetricCard
  label="Orders"
  value="1,234"
  trend={8.3}
  trendDirection="up"
  comparisonLabel="vs Last Year"
/>
```

### Negative Trend
```tsx
<MetricCard
  label="Churn Rate"
  value="2.5%"
  trend={-1.2}
  trendDirection="down"
  comparisonLabel="vs Last Month"
/>
```

### No Trend
```tsx
<MetricCard
  label="Active Users"
  value="10,432"
/>
```

### Loading
```tsx
<MetricCard
  label="Revenue"
  value="Loading..."
  isLoading={true}
/>
```

### With Callback
```tsx
const [mode, setMode] = useState('yoy');

<MetricCard
  label="Revenue"
  value="AED 125K"
  trend={12.5}
  trendDirection="up"
  comparisonLabel={mode === 'yoy' ? 'vs Last Year' : 'vs Last Period'}
  onToggleComparison={setMode}
/>
```

## Grid Layout

```tsx
<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
  <MetricCard label="Metric 1" value="1,234" trend={8} trendDirection="up" />
  <MetricCard label="Metric 2" value="5,678" trend={-2} trendDirection="down" />
  <MetricCard label="Metric 3" value="9,012" trend={0} trendDirection="flat" />
  <MetricCard label="Metric 4" value="3,456" trend={5} trendDirection="up" />
</div>
```

## Styling

### Colors
- **Green (up)**: `bg-green-50 text-green-700 border-green-200`
- **Red (down)**: `bg-red-50 text-red-700 border-red-200`
- **Gray (flat/neutral)**: `bg-gray-50 text-gray-700 border-gray-200`

### Typography
- **Label**: `text-sm text-muted-foreground`
- **Value**: `text-2xl font-bold`
- **Trend**: `text-xs`

## Keyboard Navigation

- `Tab` - Focus settings button
- `Enter/Space` - Open dropdown
- `Arrow Up/Down` - Navigate menu
- `Enter` - Select option
- `Esc` - Close menu

## Accessibility

- Settings button has `aria-label`
- Screen reader text for icons
- Keyboard navigable
- Focus indicators visible

---

**Component**: `MetricCard`  
**Version**: 2.0.0  
**Status**: ✅ Production Ready
