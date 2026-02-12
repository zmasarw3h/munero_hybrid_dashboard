'use client';

import { useState, useRef, useEffect } from 'react';
import { X, AlertCircle, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useFilters, transformFiltersForAPI } from '@/components/dashboard/FilterContext';
import { apiClient } from '@/lib/api-client';
import { ChatMessage as ChatMessageType, ChatRequest } from '@/lib/types';
import { ChatInput } from './ChatInput';
import { ChatMessage } from './ChatMessage';
import { cn } from '@/lib/utils';

interface ChatSidebarProps {
    isOpen: boolean;
    onClose: () => void;
}

export function ChatSidebar({ isOpen, onClose }: ChatSidebarProps) {
    const { filters } = useFilters();
    const [messages, setMessages] = useState<ChatMessageType[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [aiWarning, setAiWarning] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // Check AI chat health on mount
    useEffect(() => {
        const checkHealth = async () => {
            try {
                const health = await apiClient.checkChatHealth();
                if (health.status !== 'healthy') {
                    const hintText = health.hint ? ` ${health.hint}` : '';
                    setAiWarning(`${health.message}${hintText}`.trim());
                } else {
                    setAiWarning(null);
                }
            } catch (error) {
                setAiWarning('Unable to connect to AI service. Make sure the backend is running.');
            }
        };

        if (isOpen) {
            checkHealth();
        }
    }, [isOpen]);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Focus input when sidebar opens
    useEffect(() => {
        if (isOpen) {
            setTimeout(() => {
                inputRef.current?.focus();
            }, 300); // Wait for animation
        }
    }, [isOpen]);

    // Convert frontend filters to API format
    const getApiFilters = (): ChatRequest['filters'] => {
        return transformFiltersForAPI(filters);
    };

    const handleSend = async (message: string) => {
        // Add user message
        const userMessage: ChatMessageType = {
            id: crypto.randomUUID(),
            role: 'user',
            content: message,
            timestamp: new Date(),
        };
        setMessages((prev) => [...prev, userMessage]);
        setIsLoading(true);

        try {
            const requestFilters = getApiFilters();
            // Call API with current filters
            const response = await apiClient.sendChatMessage({
                message,
                filters: requestFilters,
            });

            // Add assistant message
            const assistantMessage: ChatMessageType = {
                id: crypto.randomUUID(),
                role: 'assistant',
                content: response.answer_text,
                timestamp: new Date(),
                response,
                requestFilters,
            };
            setMessages((prev) => [...prev, assistantMessage]);
        } catch (error) {
            // Handle error
            const errorMessage: ChatMessageType = {
                id: crypto.randomUUID(),
                role: 'assistant',
                content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}`,
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    // Format filter context for display
    const formatFilterContext = (): string => {
        const parts: string[] = [];

        // Date range
        const startDate = filters.dateRange.start.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        const endDate = filters.dateRange.end.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        parts.push(`${startDate} - ${endDate}`);

        // Countries
        if (filters.countries.length > 0) {
            parts.push(filters.countries.length <= 2
                ? filters.countries.join(', ')
                : `${filters.countries.length} countries`);
        }

        // Product types
        if (filters.productTypes.length > 0) {
            parts.push(filters.productTypes.join(', '));
        }

        return parts.length > 0 ? parts.join(' | ') : 'All data';
    };

    // Suggested questions
    const suggestedQuestions = [
        "What are my top 5 products by revenue?",
        "Show me monthly revenue trend",
        "Which clients have the highest order volume?",
    ];

    return (
        <>
            {/* Backdrop */}
            {isOpen && (
                <div
                    className="fixed inset-0 bg-black/20 z-40 transition-opacity"
                    onClick={onClose}
                    aria-hidden="true"
                />
            )}

            {/* Sidebar */}
            <div
                className={cn(
                    "fixed inset-y-0 right-0 w-full sm:w-[650px] bg-background border-l shadow-lg",
                    "transform transition-transform duration-300 ease-in-out z-50",
                    "flex flex-col",
                    isOpen ? "translate-x-0" : "translate-x-full"
                )}
                role="dialog"
                aria-modal="true"
                aria-label="AI Assistant"
            >
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b shrink-0">
                    <div className="flex items-center gap-2">
                        <span className="font-semibold">AI Assistant</span>
                    </div>
                    <div className="flex items-center gap-1">
                        {messages.length > 0 && (
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => setMessages([])}
                                title="Clear conversation"
                            >
                                <Trash2 className="h-4 w-4" />
                                <span className="sr-only">Clear conversation</span>
                            </Button>
                        )}
                        <Button variant="ghost" size="icon" onClick={onClose}>
                            <X className="h-4 w-4" />
                            <span className="sr-only">Close</span>
                        </Button>
                    </div>
                </div>

                {/* AI Warning */}
                {aiWarning && (
                    <div className="bg-yellow-50 dark:bg-yellow-950/30 border-b border-yellow-200 dark:border-yellow-800 px-4 py-2 text-sm text-yellow-800 dark:text-yellow-200 flex items-start gap-2 shrink-0">
                        <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                        <span>{aiWarning}</span>
                    </div>
                )}

                {/* Context indicator */}
                <div className="px-4 py-2 bg-muted/50 text-xs text-muted-foreground border-b shrink-0">
                    Context: {formatFilterContext()}
                </div>

                {/* Messages */}
                <div
                    className="flex-1 overflow-y-auto p-4 space-y-4"
                    role="log"
                    aria-label="Chat messages"
                    aria-live="polite"
                >
                    {/* Empty state with suggestions */}
                    {messages.length === 0 && (
                        <div className="text-center text-muted-foreground py-8">
                            <h3 className="font-semibold mb-2">AI Data Assistant</h3>
                            <p className="text-sm mb-6">
                                Ask questions about your sales data in plain English.
                            </p>
                            <div className="space-y-2 text-sm">
                                {suggestedQuestions.map((question, idx) => (
                                    <p
                                        key={idx}
                                        className="text-blue-600 cursor-pointer hover:underline"
                                        onClick={() => handleSend(question)}
                                    >
                                        &ldquo;{question}&rdquo;
                                    </p>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Message list */}
                    {messages.map((msg) => (
                        <ChatMessage
                            key={msg.id}
                            message={msg}
                        />
                    ))}

                    {/* Loading indicator with skeleton */}
                    {isLoading && (
                        <div className="flex flex-col items-start">
                            <div className="max-w-[95%] bg-muted rounded-2xl rounded-bl-md px-4 py-3 space-y-3">
                                <div className="flex items-center gap-2 text-muted-foreground">
                                    <span className="text-sm">Thinking...</span>
                                </div>
                                <div className="space-y-2 animate-pulse">
                                    <div className="h-3 bg-muted-foreground/20 rounded w-3/4" />
                                    <div className="h-3 bg-muted-foreground/20 rounded w-1/2" />
                                    <div className="h-24 bg-muted-foreground/10 rounded mt-2" />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Scroll anchor */}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <div className="p-4 border-t shrink-0 bg-background">
                    <ChatInput onSend={handleSend} disabled={isLoading} />
                </div>
            </div>
        </>
    );
}
