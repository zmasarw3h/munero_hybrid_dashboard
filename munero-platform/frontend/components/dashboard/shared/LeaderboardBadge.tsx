'use client';

import { Badge } from '@/components/ui/badge';
import { ReactNode } from 'react';

// ============================================================================
// TYPES
// ============================================================================

export interface LeaderboardBadgeProps {
    /** Text content of the badge */
    children: ReactNode;
    /** Variant determines the color scheme */
    variant?: 'default' | 'gift_card' | 'merchandise' | 'segment' | 'success' | 'warning' | 'error';
    /** Custom background color (overrides variant) */
    bgColor?: string;
    /** Custom text color (overrides variant) */
    textColor?: string;
    /** Additional className */
    className?: string;
}

// ============================================================================
// VARIANT STYLES
// ============================================================================

const VARIANT_STYLES: Record<string, { bg: string; text: string; border?: string }> = {
    default: {
        bg: 'bg-gray-100',
        text: 'text-gray-800',
        border: 'border-gray-200',
    },
    gift_card: {
        bg: 'bg-blue-100',
        text: 'text-blue-800',
        border: 'border-blue-200',
    },
    merchandise: {
        bg: 'bg-purple-100',
        text: 'text-purple-800',
        border: 'border-purple-200',
    },
    segment: {
        bg: '', // Uses custom color
        text: 'text-white',
    },
    success: {
        bg: 'bg-green-100',
        text: 'text-green-800',
        border: 'border-green-200',
    },
    warning: {
        bg: 'bg-amber-100',
        text: 'text-amber-800',
        border: 'border-amber-200',
    },
    error: {
        bg: 'bg-red-100',
        text: 'text-red-800',
        border: 'border-red-200',
    },
};

// ============================================================================
// COMPONENT
// ============================================================================

export function LeaderboardBadge({
    children,
    variant = 'default',
    bgColor,
    textColor,
    className = '',
}: LeaderboardBadgeProps) {
    const styles = VARIANT_STYLES[variant] || VARIANT_STYLES.default;

    // Use custom colors if provided, otherwise use variant styles
    const finalBgColor = bgColor || styles.bg;
    const finalTextColor = textColor || styles.text;
    const borderClass = styles.border || '';

    // If custom bgColor is provided, use inline style
    if (bgColor) {
        return (
            <Badge
                className={`${finalTextColor} ${borderClass} ${className} text-xs`}
                style={{ backgroundColor: bgColor }}
            >
                {children}
            </Badge>
        );
    }

    return (
        <Badge
            className={`${finalBgColor} ${finalTextColor} ${borderClass} ${className} text-xs`}
        >
            {children}
        </Badge>
    );
}

// ============================================================================
// PRESET BADGES
// ============================================================================

/**
 * Badge for product type (Gift Card / Merchandise)
 */
export function ProductTypeBadge({ type }: { type: 'gift_card' | 'merchandise' | string }) {
    const isGiftCard = type === 'gift_card';
    return (
        <LeaderboardBadge variant={isGiftCard ? 'gift_card' : 'merchandise'}>
            {isGiftCard ? 'Gift Card' : 'Merchandise'}
        </LeaderboardBadge>
    );
}

/**
 * Badge for client segments with dynamic color
 */
export function SegmentBadge({
    label,
    color
}: {
    label: string;
    color: string;
}) {
    return (
        <LeaderboardBadge variant="segment" bgColor={color}>
            {label}
        </LeaderboardBadge>
    );
}

/**
 * Badge for status indicators
 */
export function StatusBadge({
    status
}: {
    status: 'healthy' | 'warning' | 'critical';
}) {
    const variantMap = {
        healthy: 'success',
        warning: 'warning',
        critical: 'error',
    } as const;

    const labelMap = {
        healthy: 'Healthy',
        warning: 'At Risk',
        critical: 'Critical',
    };

    return (
        <LeaderboardBadge variant={variantMap[status]}>
            {labelMap[status]}
        </LeaderboardBadge>
    );
}

export default LeaderboardBadge;
