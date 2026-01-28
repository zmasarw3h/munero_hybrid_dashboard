'use client';

import { forwardRef } from 'react';
import { ChatChart } from './ChatChart';
import { ChatChartConfig } from '@/lib/types';

interface ExportableChartProps {
    config: ChatChartConfig;
    data: Record<string, unknown>[];
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
