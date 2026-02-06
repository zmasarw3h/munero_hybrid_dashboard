# AI Chat Enhancements - Implementation Prompts

This document contains detailed prompts for implementing three enhancements to the AI Chat sidebar. Each prompt can be passed directly to a VS Code agent for implementation.

---

## Enhancement 1: Wider AI Answer Area

### Prompt

```
Fix the AI chat message width in the Munero Dashboard. Currently, assistant messages feel too squished because they have a max-width constraint.

**File to modify:** `frontend/components/chat/ChatMessage.tsx`

**Current issue:**
- The assistant message container has `max-w-[95%]` which constrains the content
- Charts and text feel cramped, especially pie charts where labels get cut off

**Changes needed:**
1. In the assistant message section, change `max-w-[95%]` to `w-full` on the outer wrapper div
2. Keep the user message styling unchanged (it should still have max-w-[85%] and align right)

**Expected result:**
- Assistant messages (text, charts, SQL blocks) should use the full available width of the chat panel
- User messages should remain right-aligned with their current max-width
- Charts should have more room to display labels properly

**Code location:**
Look for this section in ChatMessage.tsx:
```tsx
// Assistant message
return (
    <div className="flex flex-col items-start">
        <div className="max-w-[95%] bg-muted rounded-2xl rounded-bl-md px-4 py-3 space-y-3">
```

Change `max-w-[95%]` to `w-full`.
```

---

## Enhancement 2: CSV Export Feature

### Prompt

```
Add a CSV export feature to the AI chat in the Munero Dashboard. Users should be able to download the full query results (not limited to Top N) as a CSV file.

**Overview:**
- Add a backend endpoint that re-runs the SQL query without LIMIT and streams CSV
- Add a download button in the chat UI
- Include a safety cap of 10,000 rows to prevent performance issues

---

**PART A: Backend Changes**

**File to modify:** `backend/app/routers/chat.py`

**Add a new endpoint `/api/chat/export-csv`:**

1. Create a Pydantic model for the request:
```python
class ExportCSVRequest(BaseModel):
    sql_query: str
    filename: Optional[str] = "export.csv"
```

2. Add the endpoint that:
   - Accepts the SQL query from the chat response
   - Removes any existing LIMIT clause using regex: `re.sub(r'\bLIMIT\s+\d+\b', '', sql_query, flags=re.IGNORECASE)`
   - Adds a safety LIMIT of 10000
   - Executes the query against the SQLite database
   - Returns a StreamingResponse with CSV content

3. Use Python's `csv` module and `io.StringIO` to generate the CSV
4. Set proper headers:
   - `Content-Disposition: attachment; filename="{filename}"`
   - `Content-Type: text/csv`

**Example endpoint structure:**
```python
@router.post("/export-csv")
async def export_csv(request: ExportCSVRequest):
    # 1. Remove existing LIMIT
    # 2. Add safety LIMIT 10000
    # 3. Execute query
    # 4. Stream as CSV response
```

---

**PART B: Frontend API Client**

**File to modify:** `frontend/lib/api-client.ts`

Add a new method to the apiClient object:

```typescript
async exportChatCSV(sqlQuery: string, filename?: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/chat/export-csv`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            sql_query: sqlQuery, 
            filename: filename || 'chat-export.csv' 
        }),
    });
    
    if (!response.ok) {
        throw new Error('Failed to export CSV');
    }
    
    // Trigger browser download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || 'chat-export.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}
```

---

**PART C: Frontend UI**

**File to modify:** `frontend/components/chat/ChatMessage.tsx`

1. Import the Download icon from lucide-react
2. Import apiClient from '@/lib/api-client'
3. Add state for download loading: `const [isExporting, setIsExporting] = useState(false);`

4. Add a download handler:
```typescript
const handleExportCSV = async () => {
    if (!response?.sql_query) return;
    setIsExporting(true);
    try {
        await apiClient.exportChatCSV(response.sql_query, `chat-export-${Date.now()}.csv`);
    } catch (err) {
        console.error('Failed to export CSV:', err);
    } finally {
        setIsExporting(false);
    }
};
```

5. Add a download button next to the chart (inside the chart container div, positioned top-right):
```tsx
{response?.chart_config && response?.data && response.data.length > 0 && (
    <div className="bg-background rounded-md border p-2 relative">
        {/* Export buttons toolbar */}
        <div className="absolute top-2 right-2 flex gap-1">
            <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={handleExportCSV}
                disabled={isExporting}
                title="Download CSV"
            >
                <Download className="h-4 w-4" />
            </Button>
        </div>
        <ChatChart config={response.chart_config} data={response.data} />
    </div>
)}
```

**Expected result:**
- A download icon appears in the top-right of the chart container
- Clicking it downloads a CSV with up to 10,000 rows of the full query results
- Button shows loading state while downloading
```

---

## Enhancement 3: PNG Export Feature

### Prompt

```
Add a PNG export feature to the AI chat visualizations in the Munero Dashboard. Users should be able to download the chart as an image, including the title and context.

**Overview:**
- Install html-to-image package for capturing DOM elements as images
- Create an exportable chart container with title and context
- Add a camera/image download button next to the CSV button

---

**PART A: Install Dependency**

Run in the frontend directory:
```bash
cd frontend && npm install html-to-image
```

---

**PART B: Create Exportable Chart Wrapper**

**File to create:** `frontend/components/chat/ExportableChart.tsx`

Create a new component that wraps the chart with title and context for export:

```tsx
'use client';

import { forwardRef } from 'react';
import { ChatChart } from './ChatChart';
import { ChatChartConfig } from '@/lib/types';

interface ExportableChartProps {
    config: ChatChartConfig;
    data: Record<string, any>[];
    title?: string;
    dateRange?: string;
}

export const ExportableChart = forwardRef<HTMLDivElement, ExportableChartProps>(
    ({ config, data, title, dateRange }, ref) => {
        return (
            <div 
                ref={ref} 
                className="bg-white p-4 rounded-md"
                style={{ minWidth: '500px' }}
            >
                {/* Title section for export */}
                {(title || dateRange) && (
                    <div className="mb-3 pb-2 border-b">
                        {title && (
                            <h3 className="font-semibold text-gray-900">{title}</h3>
                        )}
                        {dateRange && (
                            <p className="text-sm text-gray-500">{dateRange}</p>
                        )}
                    </div>
                )}
                
                {/* Chart */}
                <ChatChart config={config} data={data} />
            </div>
        );
    }
);

ExportableChart.displayName = 'ExportableChart';
```

---

**PART C: Update ChatMessage Component**

**File to modify:** `frontend/components/chat/ChatMessage.tsx`

1. Add imports:
```typescript
import { useRef } from 'react';
import { toPng } from 'html-to-image';
import { Download, Image } from 'lucide-react';
import { ExportableChart } from './ExportableChart';
```

2. Add a ref for the chart container:
```typescript
const chartRef = useRef<HTMLDivElement>(null);
```

3. Add state for PNG export:
```typescript
const [isExportingPng, setIsExportingPng] = useState(false);
```

4. Add the PNG export handler:
```typescript
const handleExportPNG = async () => {
    if (!chartRef.current) return;
    setIsExportingPng(true);
    try {
        const dataUrl = await toPng(chartRef.current, {
            cacheBust: true,
            backgroundColor: '#ffffff',
            pixelRatio: 2, // Higher quality
        });
        
        const link = document.createElement('a');
        link.download = `chart-${Date.now()}.png`;
        link.href = dataUrl;
        link.click();
    } catch (err) {
        console.error('Failed to export PNG:', err);
    } finally {
        setIsExportingPng(false);
    }
};
```

5. Update the chart section to include both buttons and use ExportableChart:
```tsx
{response?.chart_config && response?.data && response.data.length > 0 && (
    <div className="bg-background rounded-md border p-2 relative">
        {/* Export buttons toolbar */}
        <div className="absolute top-2 right-2 z-10 flex gap-1">
            <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 bg-background/80 hover:bg-background"
                onClick={handleExportCSV}
                disabled={isExporting}
                title="Download CSV"
            >
                <Download className="h-4 w-4" />
            </Button>
            <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 bg-background/80 hover:bg-background"
                onClick={handleExportPNG}
                disabled={isExportingPng}
                title="Download PNG"
            >
                <Image className="h-4 w-4" />
            </Button>
        </div>
        
        {/* Exportable chart with title */}
        <ExportableChart
            ref={chartRef}
            config={response.chart_config}
            data={response.data}
            title={response.chart_config.title}
            dateRange={formatDateRange()} // You may need to pass this from parent
        />
    </div>
)}
```

---

**PART D: Update exports**

**File to modify:** `frontend/components/chat/index.ts`

Add the new component to exports:
```typescript
export { ExportableChart } from './ExportableChart';
```

---

**Expected result:**
- Two icons appear in the top-right of chart containers: Download (CSV) and Image (PNG)
- PNG export captures the chart with its title and date context
- Image is high quality (2x pixel ratio) with white background
- Both buttons show loading state while processing
```

---

## Implementation Order

1. **Enhancement 1** (Wider area) - 5 minutes, simple CSS change
2. **Enhancement 3** (PNG export) - 20 minutes, frontend only
3. **Enhancement 2** (CSV export) - 30 minutes, requires backend + frontend

---

## Testing

After implementation, test with these queries in the AI chat:

1. "Show me revenue breakdown by product type" - Should show pie chart with export buttons
2. "What are my top 10 products by revenue?" - Download CSV should include up to 10,000 products
3. "Show me monthly revenue trend" - PNG should include title and date range

---

## Files Summary

| Enhancement | Files to Modify/Create |
|-------------|----------------------|
| Wider Area | `frontend/components/chat/ChatMessage.tsx` |
| CSV Export | `backend/app/routers/chat.py`, `frontend/lib/api-client.ts`, `frontend/components/chat/ChatMessage.tsx` |
| PNG Export | `frontend/components/chat/ExportableChart.tsx` (new), `frontend/components/chat/ChatMessage.tsx`, `frontend/components/chat/index.ts` |
