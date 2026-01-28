'use client';

/**
 * GeographyMap - Interactive choropleth map showing revenue by country
 * 
 * Zone 4A component using react-simple-maps to display a world map
 * with countries colored by revenue intensity. Supports hover tooltips
 * and click-to-filter functionality.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import {
    ComposableMap,
    Geographies,
    Geography,
    ZoomableGroup,
} from 'react-simple-maps';
import { scaleLinear } from 'd3-scale';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';
import { useFilters, transformFiltersForAPI } from '@/components/dashboard/FilterContext';
import { CountryData } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

// World map TopoJSON URL (Natural Earth 110m)
const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

interface GeographyMapProps {
    /** Map height in pixels */
    height?: number;
    /** Optional className */
    className?: string;
    /** Click handler for country selection */
    onCountryClick?: (countryName: string) => void;
}

// ISO country code to name mapping for matching with TopoJSON
const COUNTRY_NAME_MAP: Record<string, string> = {
    'AE': 'United Arab Emirates',
    'SA': 'Saudi Arabia',
    'KW': 'Kuwait',
    'QA': 'Qatar',
    'BH': 'Bahrain',
    'OM': 'Oman',
    'EG': 'Egypt',
    'JO': 'Jordan',
    'LB': 'Lebanon',
    'US': 'United States of America',
    'GB': 'United Kingdom',
    'DE': 'Germany',
    'FR': 'France',
    'IN': 'India',
    'PK': 'Pakistan',
};

function formatRevenue(value: number): string {
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(0)}K`;
    return value.toFixed(0);
}

export function GeographyMap({
    height = 280,
    className,
    onCountryClick,
}: GeographyMapProps) {
    const { filters } = useFilters();
    const [countryData, setCountryData] = useState<CountryData[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [hoveredCountry, setHoveredCountry] = useState<CountryData | null>(null);
    const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

    // Zoom and pan state
    const [zoom, setZoom] = useState(1);

    // Zoom constraints
    const MIN_ZOOM = 1;
    const MAX_ZOOM = 8;
    const ZOOM_STEP = 1.5;

    // Zoom handlers
    const handleZoomIn = useCallback(() => {
        setZoom((prev) => Math.min(prev * ZOOM_STEP, MAX_ZOOM));
    }, []);

    const handleZoomOut = useCallback(() => {
        setZoom((prev) => Math.max(prev / ZOOM_STEP, MIN_ZOOM));
    }, []);

    const handleReset = useCallback(() => {
        setZoom(1);
    }, []);

    // Fetch geography data
    useEffect(() => {
        async function fetchData() {
            setIsLoading(true);
            try {
                const apiFilters = transformFiltersForAPI(filters);
                const response = await apiClient.getGeographyData(apiFilters);
                setCountryData(response.data);
            } catch (error) {
                console.error('Failed to fetch geography data:', error);
                setCountryData([]);
            } finally {
                setIsLoading(false);
            }
        }
        fetchData();
    }, [filters]);

    // Create lookup map and color scale
    const { countryLookup, colorScale, maxRevenue } = useMemo(() => {
        const lookup = new Map<string, CountryData>();
        let max = 0;

        for (const data of countryData) {
            // Store by both country_code and country_name for flexible matching
            lookup.set(data.country_code, data);
            lookup.set(data.country_name, data);
            if (data.revenue > max) max = data.revenue;
        }

        const scale = scaleLinear<string>()
            .domain([0, max || 1])
            .range(['#dbeafe', '#1d4ed8']); // Light blue to dark blue

        return { countryLookup: lookup, colorScale: scale, maxRevenue: max };
    }, [countryData]);

    // Get country data by name (matching TopoJSON properties)
    const getCountryData = (geoName: string): CountryData | undefined => {
        return countryLookup.get(geoName);
    };

    // Handle mouse move for tooltip positioning
    const handleMouseMove = (event: React.MouseEvent) => {
        setTooltipPos({ x: event.clientX + 10, y: event.clientY - 10 });
    };

    if (isLoading) {
        return (
            <Card className={className}>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base">Revenue by Geography</CardTitle>
                </CardHeader>
                <CardContent>
                    <div
                        className="flex items-center justify-center bg-muted/50 rounded animate-pulse"
                        style={{ height }}
                    >
                        <span className="text-sm text-muted-foreground">Loading map...</span>
                    </div>
                </CardContent>
            </Card>
        );
    }

    // Total card height = height + 90 to match TopPerformers
    const cardHeight = height + 90;
    // Map container: subtract header (~45px) and legend area (~45px)
    const mapHeight = cardHeight - 100;

    return (
        <Card className={cn('relative overflow-hidden', className)} style={{ height: cardHeight }}>
            <CardHeader className="pb-1 pt-3 flex flex-row items-center justify-between">
                <CardTitle className="text-base">Revenue by Geography</CardTitle>
                {/* Zoom Controls */}
                <div className="flex items-center gap-1">
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-7 w-7"
                        onClick={handleZoomIn}
                        disabled={zoom >= MAX_ZOOM}
                        title="Zoom In"
                    >
                        <ZoomIn className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-7 w-7"
                        onClick={handleZoomOut}
                        disabled={zoom <= MIN_ZOOM}
                        title="Zoom Out"
                    >
                        <ZoomOut className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                        variant="outline"
                        size="icon"
                        className="h-7 w-7"
                        onClick={handleReset}
                        disabled={zoom === 1}
                        title="Reset View"
                    >
                        <RotateCcw className="h-3.5 w-3.5" />
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="relative p-2 pt-0" onMouseMove={handleMouseMove}>
                <div style={{ height: mapHeight }} className="rounded overflow-hidden bg-slate-50 dark:bg-slate-900">
                    <ComposableMap
                        projection="geoMercator"
                        projectionConfig={{
                            scale: 110,
                            center: [0, 20],
                        }}
                        style={{ width: '100%', height: '100%' }}
                    >
                        <ZoomableGroup
                            zoom={zoom}
                            minZoom={MIN_ZOOM}
                            maxZoom={MAX_ZOOM}
                        >
                            <Geographies geography={GEO_URL}>
                                {({ geographies }) =>
                                    geographies.map((geo) => {
                                        const geoName = geo.properties.name;
                                        const data = getCountryData(geoName);
                                        const hasData = !!data;
                                        const fillColor = hasData
                                            ? colorScale(data.revenue)
                                            : '#e5e7eb'; // Gray for no data

                                        return (
                                            <Geography
                                                key={geo.rsmKey}
                                                geography={geo}
                                                onMouseEnter={() => {
                                                    if (data) setHoveredCountry(data);
                                                }}
                                                onMouseLeave={() => setHoveredCountry(null)}
                                                onClick={() => {
                                                    if (data && onCountryClick) {
                                                        onCountryClick(data.country_name);
                                                    }
                                                }}
                                                style={{
                                                    default: {
                                                        fill: fillColor,
                                                        stroke: '#fff',
                                                        strokeWidth: 0.5,
                                                        outline: 'none',
                                                    },
                                                    hover: {
                                                        fill: hasData ? '#2563eb' : '#d1d5db',
                                                        stroke: '#fff',
                                                        strokeWidth: 0.75,
                                                        outline: 'none',
                                                        cursor: hasData ? 'pointer' : 'default',
                                                    },
                                                    pressed: {
                                                        fill: '#1e40af',
                                                        stroke: '#fff',
                                                        strokeWidth: 0.75,
                                                        outline: 'none',
                                                    },
                                                }}
                                            />
                                        );
                                    })
                                }
                            </Geographies>
                        </ZoomableGroup>
                    </ComposableMap>
                </div>

                {/* Tooltip */}
                {hoveredCountry && (
                    <div
                        className="fixed z-50 bg-background border rounded-lg shadow-lg p-3 text-sm pointer-events-none"
                        style={{ left: tooltipPos.x, top: tooltipPos.y }}
                    >
                        <p className="font-medium mb-1">{hoveredCountry.country_name}</p>
                        <div className="space-y-0.5 text-muted-foreground">
                            <p>Revenue: <span className="text-foreground font-medium">{filters.currency} {formatRevenue(hoveredCountry.revenue)}</span></p>
                            <p>Orders: <span className="text-foreground">{hoveredCountry.orders.toLocaleString()}</span></p>
                            <p>Clients: <span className="text-foreground">{hoveredCountry.clients.toLocaleString()}</span></p>
                        </div>
                        <p className="text-xs text-primary mt-1">Click to filter</p>
                    </div>
                )}

                {/* Legend */}
                <div className="absolute bottom-4 left-4 bg-background/90 rounded px-2 py-1.5 text-xs">
                    <div className="flex items-center gap-2">
                        <div
                            className="w-16 h-2 rounded"
                            style={{
                                background: 'linear-gradient(to right, #dbeafe, #1d4ed8)',
                            }}
                        />
                        <span className="text-muted-foreground">
                            0 - {formatRevenue(maxRevenue)}
                        </span>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

export default GeographyMap;
