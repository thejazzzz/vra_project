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
        return Object.entries(trends)
            .filter(([, data]) => (data as TrendMetrics).is_trend_valid)
            .sort(([, a], [, b]) => {
                const metricA = a as TrendMetrics;
                const metricB = b as TrendMetrics;

                // 1. Status Priority
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

                // 2. Growth Rate (Desc)
                if (metricA.growth_rate !== metricB.growth_rate) {
                    return (
                        (metricB.growth_rate || 0) - (metricA.growth_rate || 0)
                    );
                }

                // 3. Confidence (Desc)
                return (
                    (metricB.trend_confidence || 0) -
                    (metricA.trend_confidence || 0)
                );
            });
    }, [trends]);

    // Quick Stats
    const stats = useMemo(() => {
        if (!sortedTrends.length)
            return { emerging: 0, stable: 0, declining: 0 };
        return {
            emerging: sortedTrends.filter(
                ([, d]) => (d as TrendMetrics).status === "Emerging",
            ).length,
            stable: sortedTrends.filter(
                ([, d]) => (d as TrendMetrics).status === "Stable",
            ).length,
            declining: sortedTrends.filter(
                ([, d]) => (d as TrendMetrics).status === "Declining",
            ).length,
        };
    }, [sortedTrends]);

    return (
        <div className="space-y-6 animate-in fade-in">
            <div className="flex flex-col gap-1">
                <h2 className="text-2xl font-bold tracking-tight">
                    Topic Evolution
                </h2>
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <p className="text-muted-foreground">
                        Analysis of concept frequency, stability, and semantic
                        evolution over time. Filtered to display only
                        cross-paper trends.
                    </p>
                    {sortedTrends.length > 0 && (
                        <div className="flex gap-3 text-sm">
                            <div className="bg-green-500/10 text-green-500 px-3 py-1 rounded-full border border-green-500/20">
                                {stats.emerging} Emerging
                            </div>
                            <div className="bg-blue-500/10 text-blue-500 px-3 py-1 rounded-full border border-blue-500/20">
                                {stats.stable} Stable
                            </div>
                            <div className="bg-red-500/10 text-red-500 px-3 py-1 rounded-full border border-red-500/20">
                                {stats.declining} Declining
                            </div>
                        </div>
                    )}
                </div>
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
