'use client';

import React from 'react';
import { TrendPoint } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, TrendingUp, TrendingDown, CheckCircle } from 'lucide-react';

interface AnomalyCardProps {
  trendData: TrendPoint[];
  threshold: number;
  height?: number;
}

interface AnomalyItem {
  date: string;
  metric: 'Revenue' | 'Orders';
  change: number;
  isPositive: boolean;
}

/**
 * AnomalyCard Component
 *
 * Displays the top 3 most significant anomalies from trend data.
 * Shows: Date, Metric type (Revenue/Orders), % change
 * Header shows the current Z-score threshold being used.
 */
export function AnomalyCard({ trendData, threshold, height = 280 }: AnomalyCardProps) {
  // Extract and sort anomalies by significance (absolute % change)
  const anomalies = React.useMemo(() => {
    if (!trendData || trendData.length === 0) return [];

    const anomalyList: AnomalyItem[] = [];

    trendData.forEach((point) => {
      // Check for revenue anomaly
      if (point.is_revenue_anomaly) {
        anomalyList.push({
          date: point.date_label,
          metric: 'Revenue',
          change: point.revenue_growth,
          isPositive: point.revenue_growth > 0,
        });
      }
      // Check for order anomaly
      if (point.is_order_anomaly) {
        anomalyList.push({
          date: point.date_label,
          metric: 'Orders',
          change: point.orders_growth,
          isPositive: point.orders_growth > 0,
        });
      }
    });

    // Sort by absolute change (most significant first)
    anomalyList.sort((a, b) => Math.abs(b.change) - Math.abs(a.change));

    // Return top 3
    return anomalyList.slice(0, 3);
  }, [trendData]);

  const hasAnomalies = anomalies.length > 0;

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            Recent Anomalies
          </CardTitle>
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
            Z &gt; {threshold}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div
          className="flex flex-col justify-center"
          style={{ height: height - 80 }}
        >
          {hasAnomalies ? (
            <div className="space-y-3">
              {anomalies.map((anomaly, index) => (
                <div
                  key={`${anomaly.date}-${anomaly.metric}-${index}`}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    {/* Trend Icon */}
                    {anomaly.isPositive ? (
                      <TrendingUp className="h-5 w-5 text-green-500" />
                    ) : (
                      <TrendingDown className="h-5 w-5 text-red-500" />
                    )}
                    {/* Date and Metric */}
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {anomaly.date}
                      </p>
                      <p className="text-xs text-gray-500">{anomaly.metric}</p>
                    </div>
                  </div>
                  {/* Change Percentage */}
                  <div
                    className={`text-sm font-semibold ${
                      anomaly.isPositive ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    {anomaly.isPositive ? '+' : ''}
                    {anomaly.change.toFixed(1)}%
                  </div>
                </div>
              ))}

              {/* Subtle hint if there are more anomalies */}
              {trendData.filter(
                (p) => p.is_revenue_anomaly || p.is_order_anomaly
              ).length > 3 && (
                <p className="text-xs text-gray-400 text-center pt-2">
                  +{' '}
                  {trendData.filter(
                    (p) => p.is_revenue_anomaly || p.is_order_anomaly
                  ).length - 3}{' '}
                  more anomalies detected
                </p>
              )}
            </div>
          ) : (
            // No anomalies state
            <div className="flex flex-col items-center justify-center text-center py-6">
              <CheckCircle className="h-12 w-12 text-green-500 mb-3" />
              <p className="text-sm font-medium text-gray-700">
                No Anomalies Detected
              </p>
              <p className="text-xs text-gray-500 mt-1">
                All metrics are within normal range
              </p>
              <p className="text-xs text-gray-400 mt-2">
                (Z-score threshold: {threshold})
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
