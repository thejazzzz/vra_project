import React, { useMemo } from "react";
import useResearchStore from "../state/researchStore";
import { StatusBadge } from "../components/common/StatusBadge";
import { TrendingUp, Minus, ArrowDown } from "lucide-react";

const TrendChart = ({ years }) => {
    // years: { "2020": 4, "2021": 6 ... }
    const sortedYears = Object.keys(years).sort();
    if (sortedYears.length === 0) return null;

    const maxCount = Math.max(...Object.values(years));

    return (
        <div className="flex items-end gap-2 h-24 mt-4 border-b border-border/50 pb-1">
            {sortedYears.map((year) => {
                const count = years[year];
                const height = maxCount > 0 ? (count / maxCount) * 100 : 0;
                return (
                    <div
                        key={year}
                        className="flex flex-col items-center gap-1 group w-8"
                    >
                        <div
                            className="bg-primary/50 group-hover:bg-primary rounded-t w-full transition-all"
                            style={{ height: `${height}%` }}
                        ></div>
                        <span className="text-[10px] text-muted-foreground">
                            {year.slice(2)}
                        </span>
                    </div>
                );
            })}
        </div>
    );
};

const TrendsDashboard = () => {
    const { trends } = useResearchStore();

    const sortedTrends = useMemo(() => {
        if (!trends) return [];
        // Sort by total count descending
        return Object.entries(trends).sort(
            ([, a], [, b]) => (b.total_count || 0) - (a.total_count || 0)
        );
    }, [trends]);

    return (
        <div className="animate-fade-in space-y-6">
            <header className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">
                        Topic Trends
                    </h1>
                    <p className="text-muted-foreground">
                        Evolution of key concepts over time.
                    </p>
                </div>
            </header>

            {sortedTrends.length === 0 ? (
                <div className="card text-center py-12 text-muted-foreground">
                    No trend data available. Complete the analysis phase first.
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {sortedTrends.map(([concept, data]) => (
                        <div
                            key={concept}
                            className="card hover:border-primary/30 transition-colors"
                        >
                            <div className="flex justify-between items-start mb-2">
                                <h3 className="text-lg font-bold text-white capitalize">
                                    {concept}
                                </h3>
                                <StatusBadge
                                    status={data.status || "neutral"}
                                />
                            </div>

                            <div className="flex items-center gap-4 text-sm text-muted-foreground mb-4">
                                <div>
                                    <span className="text-white font-bold">
                                        {data.total_count || 0}
                                    </span>{" "}
                                    Papers
                                </div>
                                <div className="flex items-center gap-1">
                                    {data.growth_rate > 0 ? (
                                        <TrendingUp
                                            size={14}
                                            className="text-green-500"
                                        />
                                    ) : data.growth_rate < 0 ? (
                                        <ArrowDown
                                            size={14}
                                            className="text-red-500"
                                        />
                                    ) : (
                                        <Minus
                                            size={14}
                                            className="text-yellow-500"
                                        />
                                    )}
                                    <span>
                                        {(data.growth_rate || 0).toFixed(1)}{" "}
                                        Growth
                                    </span>
                                </div>
                            </div>

                            <TrendChart years={data.years || {}} />
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default TrendsDashboard;
