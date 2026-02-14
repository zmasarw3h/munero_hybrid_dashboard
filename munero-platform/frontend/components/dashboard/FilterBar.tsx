'use client';

import React, { useState, useEffect } from 'react';
import { useFilters } from './FilterContext';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { MultiSelect } from '@/components/ui/multi-select';
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@/components/ui/popover';
import { Calendar, Filter, RotateCcw, ChevronDown } from 'lucide-react';

/**
 * FilterBar Component
 * Sticky command bar for global dashboard filters with searchable multi-select dropdowns
 */
export function FilterBar() {
    const { filters, setFilter, resetFilters } = useFilters();
    const [showAdvanced, setShowAdvanced] = useState(false);

    // Filter options from database
    const [filterOptions, setFilterOptions] = useState<{
        clients: string[];
        brands: string[];
        suppliers: string[];
        countries: string[];
    }>({
        clients: [],
        brands: [],
        suppliers: [],
        countries: [],
    });

    const [loading, setLoading] = useState(true);

    // Fetch filter options on mount
    useEffect(() => {
        const fetchOptions = async () => {
            try {
                const options = await apiClient.getFilterOptions();
                setFilterOptions(options);
            } catch (error) {
                console.error('Failed to fetch filter options:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchOptions();
    }, []);

    // Format date for input
    const formatDate = (date: Date) => {
        return date.toISOString().split('T')[0];
    };

    // Parse date from input
    const parseDate = (dateString: string) => {
        return new Date(dateString);
    };

    // Count active filters
    const activeFilterCount = [
        filters.countries.length > 0,
        filters.productTypes.length > 0,
        filters.selectedClients.length > 0,
        filters.selectedBrands.length > 0,
        filters.selectedSuppliers.length > 0,
    ].filter(Boolean).length;

    return (
        <div className="border-t bg-white px-6 py-3">
            <div className="flex items-center justify-between gap-4">
                {/* Zone A: Primary Context Selectors */}
                <div className="flex items-center gap-3 flex-1">
                    {/* Date Range Picker */}
                    <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-gray-500" />
                        <Input
                            type="date"
                            value={formatDate(filters.dateRange.start)}
                            onChange={(e) =>
                                setFilter('dateRange', {
                                    ...filters.dateRange,
                                    start: parseDate(e.target.value),
                                })
                            }
                            className="h-9 w-[140px] text-sm"
                        />
                        <span className="text-gray-400">to</span>
                        <Input
                            type="date"
                            value={formatDate(filters.dateRange.end)}
                            onChange={(e) =>
                                setFilter('dateRange', {
                                    ...filters.dateRange,
                                    end: parseDate(e.target.value),
                                })
                            }
                            className="h-9 w-[140px] text-sm"
                        />
                    </div>

                    <Separator orientation="vertical" className="h-6" />

                    {/* Currency (AED-only) */}
                    <div className="flex items-center gap-2">
                        <Label className="text-sm text-gray-600">Currency:</Label>
                        <span className="text-sm font-medium text-gray-900">{filters.currency || 'AED'}</span>
                    </div>

                    {/* Country Multi-Select */}
                    <div className="flex items-center gap-2">
                        <Label className="text-sm text-gray-600">Country:</Label>
                        <MultiSelect
                            options={filterOptions.countries}
                            selected={filters.countries}
                            onChange={(selected) => setFilter('countries', selected)}
                            placeholder="All Countries"
                            className="h-9 w-[160px]"
                        />
                    </div>
                </div>

                {/* Zone B: Slicers & Actions */}
                <div className="flex items-center gap-3">
                    {/* Product Type Multi-Select */}
                    <div className="flex items-center gap-2">
                        <Label className="text-sm text-gray-600">Type:</Label>
                        <MultiSelect
                            options={['Gift Card', 'Merchandise']}
                            selected={filters.productTypes}
                            onChange={(selected) => setFilter('productTypes', selected)}
                            placeholder="All Types"
                            className="h-9 w-[140px]"
                        />
                    </div>

                    <Separator orientation="vertical" className="h-6" />

                    {/* More Filters Popover */}
                    <Popover open={showAdvanced} onOpenChange={setShowAdvanced}>
                        <PopoverTrigger asChild>
                            <Button variant="outline" size="sm" className="h-9 gap-2">
                                <Filter className="h-4 w-4" />
                                More Filters
                                {activeFilterCount > 0 && (
                                    <Badge variant="secondary" className="ml-1 h-5 px-1.5">
                                        {activeFilterCount}
                                    </Badge>
                                )}
                                <ChevronDown className="h-3 w-3 opacity-50" />
                            </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-80" align="end">
                            <div className="space-y-4">
                                <div className="space-y-2">
                                    <h4 className="font-medium text-sm">Advanced Filters</h4>
                                    <p className="text-xs text-gray-500">
                                        Select multiple entities to drill down
                                    </p>
                                </div>

                                <div className="space-y-3">
                                    {/* Client Multi-Select */}
                                    <div className="space-y-1.5">
                                        <Label htmlFor="clients" className="text-xs">
                                            Clients ({filterOptions.clients.length} available)
                                        </Label>
                                        <MultiSelect
                                            options={filterOptions.clients}
                                            selected={filters.selectedClients}
                                            onChange={(selected) => setFilter('selectedClients', selected)}
                                            placeholder="Search clients..."
                                            className="h-9"
                                        />
                                    </div>

                                    {/* Brand Multi-Select */}
                                    <div className="space-y-1.5">
                                        <Label htmlFor="brands" className="text-xs">
                                            Brands ({filterOptions.brands.length} available)
                                        </Label>
                                        <MultiSelect
                                            options={filterOptions.brands}
                                            selected={filters.selectedBrands}
                                            onChange={(selected) => setFilter('selectedBrands', selected)}
                                            placeholder="Search brands..."
                                            className="h-9"
                                        />
                                    </div>

                                    {/* Supplier Multi-Select */}
                                    <div className="space-y-1.5">
                                        <Label htmlFor="suppliers" className="text-xs">
                                            Suppliers ({filterOptions.suppliers.length} available)
                                        </Label>
                                        <MultiSelect
                                            options={filterOptions.suppliers}
                                            selected={filters.selectedSuppliers}
                                            onChange={(selected) => setFilter('selectedSuppliers', selected)}
                                            placeholder="Search suppliers..."
                                            className="h-9"
                                        />
                                    </div>

                                    <Separator />

                                    {/* Anomaly Threshold */}
                                    <div className="space-y-1.5">
                                        <Label htmlFor="threshold" className="text-xs">
                                            Anomaly Threshold (Z-Score)
                                        </Label>
                                        <Input
                                            id="threshold"
                                            type="number"
                                            step="0.1"
                                            min="1"
                                            max="5"
                                            value={isNaN(filters.anomalyThreshold) ? 3.0 : filters.anomalyThreshold}
                                            onChange={(e) => {
                                                const value = parseFloat(e.target.value);
                                                // Only update if we have a valid number within bounds
                                                if (!isNaN(value) && value >= 1 && value <= 5) {
                                                    setFilter('anomalyThreshold', value);
                                                }
                                            }}
                                            className="h-8 text-sm"
                                        />
                                    </div>
                                </div>

                                <div className="flex justify-between">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => {
                                            setFilter('selectedClients', []);
                                            setFilter('selectedBrands', []);
                                            setFilter('selectedSuppliers', []);
                                        }}
                                    >
                                        Clear Advanced
                                    </Button>
                                    <Button
                                        variant="default"
                                        size="sm"
                                        onClick={() => setShowAdvanced(false)}
                                    >
                                        Apply
                                    </Button>
                                </div>
                            </div>
                        </PopoverContent>
                    </Popover>

                    {/* Reset Button */}
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={resetFilters}
                        className="h-9 gap-2"
                    >
                        <RotateCcw className="h-4 w-4" />
                        Reset
                    </Button>
                </div>
            </div>

            {/* Loading indicator */}
            {loading && (
                <div className="text-xs text-gray-500 mt-2">
                    Loading filter options...
                </div>
            )}
        </div>
    );
}
