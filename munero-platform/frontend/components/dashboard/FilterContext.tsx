'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';

/**
 * Global Filter State for Dashboard
 * Matches backend DashboardFilters model exactly
 */
export interface DashboardFilters {
    // Date Range
    dateRange: {
        start: Date;
        end: Date;
    };

    // Core Filters
    currency: string;                 // Changed to string for dynamic currencies
    countries: string[];              // Multi-select for countries
    productTypes: string[];           // Multi-select for product types

    // Advanced Filters (Multi-Select)
    selectedClients: string[];
    selectedBrands: string[];
    selectedSuppliers: string[];

    // Analysis Options
    comparisonMode: 'yoy' | 'prev_period' | 'none';
    anomalyThreshold: number;
}

/**
 * Filter Context Value
 */
interface FilterContextValue {
    filters: DashboardFilters;
    setFilter: <K extends keyof DashboardFilters>(
        key: K,
        value: DashboardFilters[K]
    ) => void;
    resetFilters: () => void;
}

// Default filter values
const DEFAULT_FILTERS: DashboardFilters = {
    dateRange: {
        start: new Date('2025-01-01'),
        end: new Date('2025-12-31'),
    },
    currency: 'AED',
    countries: [],
    productTypes: [],
    selectedClients: [],
    selectedBrands: [],
    selectedSuppliers: [],
    comparisonMode: 'none',
    anomalyThreshold: 3.0,
};

// Create Context
const FilterContext = createContext<FilterContextValue | undefined>(undefined);

/**
 * Filter Provider Component
 * Wraps the dashboard to provide global state
 */
export function FilterProvider({ children }: { children: ReactNode }) {
    const [filters, setFilters] = useState<DashboardFilters>(DEFAULT_FILTERS);

    const setFilter = <K extends keyof DashboardFilters>(
        key: K,
        value: DashboardFilters[K]
    ) => {
        setFilters((prev) => ({
            ...prev,
            [key]: value,
        }));
    };

    const resetFilters = () => {
        setFilters(DEFAULT_FILTERS);
    };

    return (
        <FilterContext.Provider value={{ filters, setFilter, resetFilters }}>
            {children}
        </FilterContext.Provider>
    );
}

/**
 * Hook to access filter context
 * Must be used within FilterProvider
 */
export function useFilters(): FilterContextValue {
    const context = useContext(FilterContext);
    if (!context) {
        throw new Error('useFilters must be used within FilterProvider');
    }
    return context;
}

/**
 * Helper function to transform UI filters to backend API format
 * Converts our FilterContext state to the DashboardFilters expected by the API
 */
export function transformFiltersForAPI(uiFilters: DashboardFilters): {
    start_date?: string;
    end_date?: string;
    currency: string;
    comparison_mode: 'yoy' | 'prev_period' | 'none';
    anomaly_threshold: number;
    clients: string[];
    countries: string[];
    product_types: string[];
    brands: string[];
    suppliers: string[];
} {
    // Format dates as YYYY-MM-DD
    const formatDate = (date: Date) => {
        return date.toISOString().split('T')[0];
    };

    // Map display labels to database values for product types
    const productTypeMap: Record<string, string> = {
        'Gift Card': 'gift_card',
        'Merchandise': 'merchandise',
    };

    return {
        start_date: formatDate(uiFilters.dateRange.start),
        end_date: formatDate(uiFilters.dateRange.end),
        currency: uiFilters.currency,
        comparison_mode: uiFilters.comparisonMode,
        anomaly_threshold: isNaN(uiFilters.anomalyThreshold) ? 3.0 : uiFilters.anomalyThreshold,
        clients: uiFilters.selectedClients,
        countries: uiFilters.countries,
        product_types: uiFilters.productTypes.map(pt => productTypeMap[pt] || pt),
        brands: uiFilters.selectedBrands,
        suppliers: uiFilters.selectedSuppliers,
    };
}
