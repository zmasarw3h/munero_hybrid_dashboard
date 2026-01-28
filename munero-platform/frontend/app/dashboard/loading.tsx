export default function Loading() {
    return (
        <div className="space-y-6 animate-pulse">
            {/* Header skeleton */}
            <div className="h-8 w-64 bg-gray-200 rounded"></div>

            {/* KPI Grid skeleton */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
                {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-32 bg-gray-200 rounded-lg"></div>
                ))}
            </div>

            {/* Charts skeleton */}
            <div className="grid gap-6 md:grid-cols-2">
                {[...Array(2)].map((_, i) => (
                    <div key={i} className="h-80 bg-gray-200 rounded-lg"></div>
                ))}
            </div>
        </div>
    );
}
