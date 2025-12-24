"use client";

import { useResearchStore } from "@/lib/store";
import { useMemo } from "react";
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription,
} from "@/components/ui/card";
import { StatusBadge } from "@/components/status-badge";
import {
    ResponsiveContainer,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    Tooltip,
} from "recharts";
import { TrendingUp, ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";

export default function TrendsPage() {
    const { trends } = useResearchStore();

    const sortedTrends = useMemo(() => {
        if (!trends) return [];
        return Object.entries(trends).sort(
            ([, a]: any, [, b]: any) =>
                (b.total_count || 0) - (a.total_count || 0)
        );
    }, [trends]);

    return (
        <div className="space-y-6 animate-in fade-in">
            <div className="flex flex-col gap-1">
                <h2 className="text-2xl font-bold tracking-tight">
                    Topic Evolution
                </h2>
                <p className="text-muted-foreground">
                    Analysis of concept frequency and growth over time.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {sortedTrends.map(([concept, data]: any) => {
                    const chartData = Object.entries(data.years || {})
                        .map(([year, count]) => ({ year, count }))
                        .sort((a: any, b: any) => a.year - b.year);

                    const growth = data.growth_rate || 0;

                    return (
                        <Card key={concept} className="flex flex-col">
                            <CardHeader className="pb-2">
                                <div className="flex justify-between items-start">
                                    <div>
                                        <CardTitle className="capitalize">
                                            {concept}
                                        </CardTitle>
                                        <CardDescription>
                                            {data.total_count} Mentions
                                        </CardDescription>
                                    </div>
                                    <StatusBadge status={data.status} />
                                </div>
                            </CardHeader>
                            <CardContent className="flex-1 flex flex-col justify-end">
                                <div className="flex items-center gap-2 mb-4 text-sm">
                                    {growth > 0 ? (
                                        <ArrowUpRight className="text-green-500 h-4 w-4" />
                                    ) : growth < 0 ? (
                                        <ArrowDownRight className="text-red-500 h-4 w-4" />
                                    ) : (
                                        <Minus className="text-yellow-500 h-4 w-4" />
                                    )}
                                    <span
                                        className={
                                            growth > 0
                                                ? "text-green-500 font-bold"
                                                : "text-muted-foreground"
                                        }
                                    >
                                        {growth.toFixed(1)} Growth
                                    </span>
                                </div>

                                <div className="h-24 w-full mt-auto">
                                    <ResponsiveContainer
                                        width="100%"
                                        height="100%"
                                    >
                                        <BarChart data={chartData}>
                                            <Tooltip
                                                contentStyle={{
                                                    backgroundColor:
                                                        "hsl(var(--card))",
                                                    border: "1px solid hsl(var(--border))",
                                                }}
                                                itemStyle={{
                                                    color: "hsl(var(--foreground))",
                                                }}
                                                cursor={{
                                                    fill: "hsl(var(--primary)/0.1)",
                                                }}
                                            />
                                            <Bar
                                                dataKey="count"
                                                fill="hsl(var(--primary))"
                                                radius={[4, 4, 0, 0]}
                                            />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </CardContent>
                        </Card>
                    );
                })}
            </div>

            {sortedTrends.length === 0 && (
                <div className="text-center py-20 text-muted-foreground">
                    No trend data available. Ensure analysis phase is complete.
                </div>
            )}
        </div>
    );
}
