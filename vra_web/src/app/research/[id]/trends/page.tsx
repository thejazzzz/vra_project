//vra_web/src/app/research/[id]/trends/page.tsx
"use client";

import { useResearchStore } from "@/lib/store";
import { useMemo } from "react";
import { TrendCard } from "@/components/trend-card";
import { TrendMetrics } from "@/types";

export default function TrendsPage() {
    const { trends } = useResearchStore();

    // Scientific Sorting Algorithm
    const sortedTrends = useMemo(() => {
        if (!trends) return [];
        return Object.entries(trends).sort(([, a], [, b]) => {
            const metricA = a as TrendMetrics;
            const metricB = b as TrendMetrics;

            // 1. Separate Valid vs Invalid (Invalid always last)
            if (metricA.is_trend_valid && !metricB.is_trend_valid) return -1;
            if (!metricA.is_trend_valid && metricB.is_trend_valid) return 1;

            // 2. Status Priority
            const statusPriority: Record<string, number> = {
                Emerging: 5,
                New: 4,
                Stable: 3,
                Saturated: 2,
                Declining: 1,
                Sporadic: 0,
            };

            const scoreA = statusPriority[metricA.status] || 0;
            const scoreB = statusPriority[metricB.status] || 0;

            if (scoreA !== scoreB) return scoreB - scoreA; // Descending priority

            // 3. Growth Rate (Desc)
            if (metricA.growth_rate !== metricB.growth_rate) {
                return (metricB.growth_rate || 0) - (metricA.growth_rate || 0);
            }

            // 4. Confidence (Desc)
            return (
                (metricB.trend_confidence || 0) -
                (metricA.trend_confidence || 0)
            );
        });
    }, [trends]);

    return (
        <div className="space-y-6 animate-in fade-in">
            <div className="flex flex-col gap-1">
                <h2 className="text-2xl font-bold tracking-tight">
                    Topic Evolution
                </h2>
                <p className="text-muted-foreground">
                    Analysis of concept frequency, stability, and semantic
                    evolution over time.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {sortedTrends.map(([concept, data]) => (
                    <TrendCard
                        key={concept}
                        concept={concept}
                        data={data as TrendMetrics}
                    />
                ))}
            </div>

            {sortedTrends.length === 0 && (
                <div className="text-center py-20 text-muted-foreground">
                    No trend data available. Ensure analysis phase is complete.
                </div>
            )}
        </div>
    );
}
