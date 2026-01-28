// Type declarations for react-simple-maps
declare module 'react-simple-maps' {
    import { ComponentType, ReactNode, CSSProperties } from 'react';

    interface ComposableMapProps {
        projection?: string;
        projectionConfig?: {
            scale?: number;
            center?: [number, number];
            rotate?: [number, number, number];
        };
        width?: number;
        height?: number;
        style?: CSSProperties;
        children?: ReactNode;
    }

    interface ZoomableGroupProps {
        zoom?: number;
        center?: [number, number];
        minZoom?: number;
        maxZoom?: number;
        children?: ReactNode;
    }

    interface GeographiesProps {
        geography: string | object;
        children: (data: { geographies: Geography[] }) => ReactNode;
    }

    interface Geography {
        rsmKey: string;
        properties: {
            name: string;
            [key: string]: unknown;
        };
        geometry: object;
    }

    interface GeographyProps {
        geography: Geography;
        onMouseEnter?: () => void;
        onMouseLeave?: () => void;
        onClick?: () => void;
        style?: {
            default?: CSSProperties;
            hover?: CSSProperties;
            pressed?: CSSProperties;
        };
    }

    export const ComposableMap: ComponentType<ComposableMapProps>;
    export const ZoomableGroup: ComponentType<ZoomableGroupProps>;
    export const Geographies: ComponentType<GeographiesProps>;
    export const Geography: ComponentType<GeographyProps>;
}
