'use client';

import { useState, useEffect } from 'react';
import { FilterProvider } from '@/components/dashboard/FilterContext';
import { FilterBar } from '@/components/dashboard/FilterBar';
import { NavTabs } from '@/components/dashboard/NavTabs';
import { ChatSidebar } from '@/components/chat';
import { Button } from '@/components/ui/button';
import { Circle, MessageSquare, Sparkles } from 'lucide-react';
import { ReactNode } from 'react';

interface DashboardLayoutProps {
    children: ReactNode;
}

/**
 * Dashboard Layout
 * Global shell with persistent state, navigation, and filters
 */
export default function DashboardLayout({ children }: DashboardLayoutProps) {
    const [isChatOpen, setIsChatOpen] = useState(false);

    // Keyboard shortcuts: Cmd+K / Ctrl+K to toggle, Escape to close
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Cmd+K or Ctrl+K to toggle chat
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                setIsChatOpen(prev => !prev);
            }
            // Escape to close
            if (e.key === 'Escape' && isChatOpen) {
                setIsChatOpen(false);
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [isChatOpen]);

    return (
        <FilterProvider>
            <div className="min-h-screen bg-gray-50">
                {/* Sticky Header */}
                <header className="sticky top-0 z-40 bg-white border-b shadow-sm">
                    {/* Top Bar: Logo + Navigation + Status */}
                    <div className="px-6 py-3 flex items-center justify-between">
                        {/* Logo */}
                        <div className="flex items-center gap-3">
                            <img
                                src="/munero-logo.jpeg"
                                alt="Munero"
                                className="h-10 w-auto object-contain"
                            />
                            <div>
                                <h1 className="text-xl font-bold text-gray-900">
                                    Munero AI Platform
                                </h1>
                                <p className="text-xs text-gray-500">
                                    Data Analytics & Intelligence
                                </p>
                            </div>
                        </div>

                        {/* Navigation Tabs */}
                        <NavTabs />

                        {/* Status & Actions */}
                        <div className="flex items-center gap-3">
                            {/* AI Chat Toggle Button */}
                            <Button
                                variant="default"
                                size="sm"
                                onClick={() => setIsChatOpen(true)}
                                className="gap-2 bg-blue-600 hover:bg-blue-700 text-white"
                                title="Ask AI (⌘K)"
                            >
                                <Sparkles className="h-4 w-4" />
                                <span className="hidden sm:inline">Ask AI</span>
                            </Button>

                            {/* Live Status Indicator */}
                            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-50 border border-green-200">
                                <Circle className="h-2 w-2 fill-green-500 text-green-500 animate-pulse" />
                                <span className="text-xs font-medium text-green-700">Live</span>
                            </div>

                            {/* User Menu Placeholder */}
                            <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                                <span className="text-xs font-medium text-gray-600">ZM</span>
                            </div>
                        </div>
                    </div>

                    {/* Filter Bar - Secondary Control Layer */}
                    <FilterBar />
                </header>

                {/* Main Content Area */}
                <main className="p-4">
                    {children}
                </main>

                {/* Chat Sidebar (Slide-over) */}
                <ChatSidebar
                    isOpen={isChatOpen}
                    onClose={() => setIsChatOpen(false)}
                />
            </div>
        </FilterProvider>
    );
}
