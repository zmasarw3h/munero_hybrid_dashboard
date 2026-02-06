# MultiSelect Component - Quick Reference

## Import
```tsx
import { MultiSelect } from '@/components/ui/multi-select';
```

## Basic Usage
```tsx
const [selected, setSelected] = useState<string[]>([]);

<MultiSelect
  options={['Option 1', 'Option 2', 'Option 3']}
  selected={selected}
  onChange={setSelected}
  placeholder="Select items..."
/>
```

## Props Reference

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `options` | `string[]` | ✅ | - | Array of available options |
| `selected` | `string[]` | ✅ | - | Array of selected values |
| `onChange` | `(selected: string[]) => void` | ✅ | - | Callback when selection changes |
| `placeholder` | `string` | ❌ | "Select items..." | Placeholder text when empty |
| `emptyText` | `string` | ❌ | "No results found." | Text when search has no results |
| `className` | `string` | ❌ | - | Additional CSS classes for trigger |

## Features

### ✅ Search & Filter
- Type to filter options
- Case-insensitive search
- Works with large datasets (12k+ items)

### ✅ Bulk Actions
- **Select All**: Click to select all options
- **Clear All**: Click to clear all selections
- Action bar between search and options

### ✅ Smart Badge Display
- **≤3 selections**: Individual badges (e.g., "USA", "UAE", "UK")
- **>3 selections**: Count badge (e.g., "12 selected")
- Prevents UI overflow

### ✅ Clear Button
- X icon in trigger button
- Clears all selections
- Doesn't reopen popover

## Integration Examples

### With FilterContext
```tsx
const { filters, setFilter } = useFilters();

<MultiSelect
  options={filterOptions.countries}
  selected={filters.countries}
  onChange={(selected) => setFilter('countries', selected)}
  placeholder="All Countries"
/>
```

### With Custom Width
```tsx
<MultiSelect
  options={options}
  selected={selected}
  onChange={setSelected}
  className="w-[200px] h-10"
/>
```

### Large Dataset (Searchable)
```tsx
<MultiSelect
  options={clients}  // 12,849 items
  selected={selectedClients}
  onChange={setSelectedClients}
  placeholder="Search clients..."
  emptyText="No clients found"
/>
```

## Keyboard Navigation
- `Tab` - Focus trigger button
- `Space/Enter` - Open/close popover
- `Arrow Up/Down` - Navigate options
- `Space` - Toggle selection
- `Esc` - Close popover

## Styling

### Default Styles
- Trigger: Outline variant, min-height 10 (2.5rem)
- Badges: Secondary variant, rounded-sm
- Popover: 300px width, aligned to start

### Custom Styling
```tsx
<MultiSelect
  options={options}
  selected={selected}
  onChange={setSelected}
  className="w-full h-12 text-lg"  // Custom size
/>
```

## Common Patterns

### Filter with Label
```tsx
<div className="flex items-center gap-2">
  <Label className="text-sm">Country:</Label>
  <MultiSelect
    options={countries}
    selected={selectedCountries}
    onChange={setSelectedCountries}
    placeholder="All Countries"
    className="w-[160px]"
  />
</div>
```

### In Popover (Advanced Filters)
```tsx
<Popover>
  <PopoverTrigger asChild>
    <Button>More Filters</Button>
  </PopoverTrigger>
  <PopoverContent className="w-80">
    <div className="space-y-3">
      <Label>Clients</Label>
      <MultiSelect
        options={clients}
        selected={selectedClients}
        onChange={setSelectedClients}
        placeholder="Search clients..."
      />
    </div>
  </PopoverContent>
</Popover>
```

## Performance Tips

### Large Datasets (1000+ items)
- ✅ Built-in search optimization
- ✅ Virtualized scrolling via Command component
- ✅ Efficient re-rendering

### State Management
```tsx
// ❌ Avoid inline functions
<MultiSelect onChange={(val) => setSelected(val)} />

// ✅ Use direct setters
<MultiSelect onChange={setSelected} />

// ✅ Or memoized callbacks
const handleChange = useCallback((val) => {
  setSelected(val);
  logAnalytics('filter_change', { values: val });
}, []);

<MultiSelect onChange={handleChange} />
```

## Accessibility

- ✅ ARIA attributes (role="combobox", aria-expanded)
- ✅ Keyboard navigation support
- ✅ Focus management
- ✅ Screen reader friendly

## Browser Support

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Troubleshooting

### Popover doesn't close after clearing
**Solution**: Ensure `e.stopPropagation()` in clear handler (already implemented)

### Search not working
**Check**: Options array is properly populated and not empty

### Badges overflowing
**Solution**: Component automatically switches to count badge for >3 selections

### Performance issues with large dataset
**Check**: Options array size. Component handles up to 50k items efficiently.

---

**Component Version**: 1.2.0  
**Last Updated**: 2024  
**File**: `frontend/components/ui/multi-select.tsx`
