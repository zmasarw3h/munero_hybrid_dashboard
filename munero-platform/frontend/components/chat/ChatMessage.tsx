'use client';

import { useState, useRef } from 'react';
import { toPng } from 'html-to-image';
import { ChevronDown, ChevronUp, Copy, Check, AlertTriangle, Download, Image as ImageIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ChatMessage as ChatMessageType } from '@/lib/types';
import { ExportableChart } from './ExportableChart';
import { apiClient } from '@/lib/api-client';

interface ChatMessageProps {
    message: ChatMessageType;
    onFollowUp?: (question: string) => void;
}

export function ChatMessage({ message, onFollowUp }: ChatMessageProps) {
    const [sqlExpanded, setSqlExpanded] = useState(false);
    const [copied, setCopied] = useState(false);
    const [isExporting, setIsExporting] = useState(false);
    const [isExportingPng, setIsExportingPng] = useState(false);
    const [exportError, setExportError] = useState<string | null>(null);
    const chartRef = useRef<HTMLDivElement>(null);

    const isUser = message.role === 'user';
    const response = message.response;
    const requiresExportToken = process.env.NODE_ENV === 'production';
    const exportTokenMissing = requiresExportToken && !response?.export_token;
    const canExportCSV = Boolean(response?.sql_query) && !exportTokenMissing;

    const handleCopySql = async () => {
        if (!response?.sql_query) return;

        try {
            await navigator.clipboard.writeText(response.sql_query);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy SQL:', err);
        }
    };

    const handleExportCSV = async () => {
        if (!response?.sql_query) return;
        if (exportTokenMissing) return;

        setIsExporting(true);
        setExportError(null);
        try {
            await apiClient.exportChatCSV(
                response.sql_query,
                message.requestFilters,
                `chat-export-${Date.now()}.csv`,
                response.export_token
            );
        } catch (err) {
            setExportError(err instanceof Error ? err.message : 'Failed to export CSV.');
            console.error('Failed to export CSV:', err);
        } finally {
            setIsExporting(false);
        }
    };

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

    // Format timestamp
    const formattedTime = message.timestamp.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
    });

    // User message
    if (isUser) {
        return (
            <div className="flex flex-col items-end">
                <div className="max-w-[85%] bg-blue-600 text-white rounded-2xl rounded-br-md px-4 py-2">
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                </div>
                <span className="text-xs text-muted-foreground mt-1">{formattedTime}</span>
            </div>
        );
    }

    // Assistant message
    return (
        <div className="flex flex-col items-start">
            <div className="w-full bg-muted rounded-2xl rounded-bl-md px-4 py-3 space-y-3">
                {/* Answer text */}
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>

                {/* Warnings */}
                {response?.warnings && response.warnings.length > 0 && (
                    <div className="flex items-start gap-2 bg-yellow-50 dark:bg-yellow-950/30 border border-yellow-200 dark:border-yellow-800 rounded-md px-3 py-2">
                        <AlertTriangle className="h-4 w-4 text-yellow-600 shrink-0 mt-0.5" />
                        <div className="text-xs text-yellow-800 dark:text-yellow-200">
                            {response.warnings.map((warning, idx) => (
                                <p key={idx}>{warning}</p>
                            ))}
                        </div>
                    </div>
                )}

                {/* Chart visualization */}
                {response?.chart_config && response?.data && response.data.length > 0 && (
                    <div className="bg-background rounded-md border p-2 relative">
                        {/* Export buttons toolbar */}
                        <div className="absolute top-2 right-2 z-10 flex gap-1">
                            <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 bg-background/80 hover:bg-background"
                                onClick={handleExportCSV}
                                disabled={isExporting || !canExportCSV}
                                title={exportTokenMissing ? 'CSV export is disabled (backend not configured)' : 'Download CSV'}
                            >
                                <Download className="h-4 w-4" />
                            </Button>
                            <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 bg-background/80 hover:bg-background"
                                onClick={handleExportPNG}
                                disabled={isExportingPng}
                                title="Download PNG"
                            >
                                <ImageIcon className="h-4 w-4" />
                            </Button>
                        </div>

                        {/* Exportable chart with title */}
                        <ExportableChart
                            ref={chartRef}
                            config={response.chart_config}
                            data={response.data}
                            title={response.chart_config.title}
                        />

                        {exportTokenMissing && (
                            <p className="mt-2 text-xs text-muted-foreground">
                                CSV export is disabled (backend not configured).
                            </p>
                        )}

                        {exportError && (
                            <div className="mt-2 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-md px-3 py-2">
                                <p className="text-xs text-red-800 dark:text-red-200">
                                    {exportError}
                                </p>
                            </div>
                        )}
                    </div>
                )}

                {/* SQL Query (collapsible) */}
                {response?.sql_query && (
                    <div className="border rounded-md overflow-hidden">
                        <button
                            type="button"
                            onClick={() => setSqlExpanded(!sqlExpanded)}
                            className="w-full flex items-center justify-between px-3 py-2 text-xs text-muted-foreground hover:bg-accent/50 transition-colors"
                        >
                            <span>View SQL</span>
                            {sqlExpanded ? (
                                <ChevronUp className="h-3 w-3" />
                            ) : (
                                <ChevronDown className="h-3 w-3" />
                            )}
                        </button>

                        {sqlExpanded && (
                            <div className="relative">
                                <pre className="bg-slate-900 text-slate-100 text-xs p-3 overflow-x-auto max-h-[200px]">
                                    <code>{response.sql_query}</code>
                                </pre>
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon"
                                    className="absolute top-2 right-2 h-6 w-6 bg-slate-800 hover:bg-slate-700"
                                    onClick={handleCopySql}
                                >
                                    {copied ? (
                                        <Check className="h-3 w-3 text-green-400" />
                                    ) : (
                                        <Copy className="h-3 w-3 text-slate-300" />
                                    )}
                                </Button>
                            </div>
                        )}
                    </div>
                )}

                {/* Error display */}
                {response?.error && (
                    <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-md px-3 py-2">
                        <p className="text-xs text-red-800 dark:text-red-200">
                            {response.error}
                        </p>
                    </div>
                )}

                {/* Row count info */}
                {response && response.row_count > 0 && (
                    <p className="text-xs text-muted-foreground">
                        {response.row_count} {response.row_count === 1 ? 'result' : 'results'}
                    </p>
                )}

                {/* Follow-up suggestions */}
                {onFollowUp && response && !response.error && response.row_count > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                        <button
                            onClick={() => onFollowUp("Show me the trend over time")}
                            className="text-xs px-2 py-1 rounded-full bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-950/50 transition-colors"
                        >
                            Show trend
                        </button>
                        <button
                            onClick={() => onFollowUp("Break this down by category")}
                            className="text-xs px-2 py-1 rounded-full bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-950/50 transition-colors"
                        >
                            By category
                        </button>
                        <button
                            onClick={() => onFollowUp("Compare to last period")}
                            className="text-xs px-2 py-1 rounded-full bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-950/50 transition-colors"
                        >
                            Compare
                        </button>
                    </div>
                )}
            </div>
            <span className="text-xs text-muted-foreground mt-1">{formattedTime}</span>
        </div>
    );
}
