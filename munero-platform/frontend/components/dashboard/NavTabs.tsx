'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { BarChart3, TrendingUp, Package } from 'lucide-react';

const navItems = [
    {
        label: 'Executive Overview',
        href: '/dashboard/overview',
        icon: BarChart3,
    },
    {
        label: 'Market Analysis',
        href: '/dashboard/market',
        icon: TrendingUp,
    },
    {
        label: 'Catalog Performance',
        href: '/dashboard/catalog',
        icon: Package,
    },
];

/**
 * NavTabs Component
 * Tab-style navigation for dashboard sections
 */
export function NavTabs() {
    const pathname = usePathname();

    return (
        <nav className="flex items-center gap-1">
            {navItems.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;

                return (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                            'flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors rounded-t-md',
                            'hover:bg-gray-100',
                            isActive
                                ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                                : 'text-gray-600 border-b-2 border-transparent'
                        )}
                    >
                        <Icon className="h-4 w-4" />
                        {item.label}
                    </Link>
                );
            })}
        </nav>
    );
}
