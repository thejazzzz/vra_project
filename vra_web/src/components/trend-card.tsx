//vra_web/src/components/trend-card.tsx
"use client";

import { useMemo, useState } from "react";
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription,
    CardFooter,
} from "@/components/ui/card";
import { StatusBadge } from "@/components/status-badge";
import {
    ResponsiveContainer,
    BarChart,
    Bar,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import {
    ArrowUpRight,
    ArrowDownRight,
    Minus,
    Globe,
    Target,
    Pin,
    Activity,
    Anchor,
    Zap,
    Info,
    ChevronDown,
    ChevronUp,
    FileText,
    AlertTriangle,
} from "lucide-react";
import { TrendMetrics } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Tooltip as UITooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";

interface TrendCardProps {
    concept: string;
    data: TrendMetrics;
}

export function TrendCard({ concept, data }: TrendCardProps) {
    const [showPapers, setShowPapers] = useState(false);
    const [useNormFreq, setUseNormFreq] = useState(true);

    const growth = data.growth_rate || 0;
    const isValid = data.is_trend_valid;
    const confidence = (data.trend_confidence || 0) * 100;

    // Prepare chart data with context
    const chartData = useMemo(() => {
        return (data.trend_vector || [])
            .map((tv) => ({
                year: tv.year,
                value: useNormFreq ? tv.norm_freq : tv.count,
                raw_count: tv.count,
                top_related: tv.top_related || [], // Context Exposure
            }))
            .sort((a, b) => a.year - b.year);
    }, [data.trend_vector, useNormFreq]);

    // Scope Icon Logic
    const ScopeIcon = useMemo(() => {
        switch (data.scope?.toLowerCase()) {
            case "global":
                return Globe;
            case "subfield":
                return Target;
            case "niche":
                return Pin;
            default:
                return Target;
        }
    }, [data.scope]);

    // Stability Icon Logic
    const StabilityIcon = useMemo(() => {
        switch (data.stability?.toLowerCase()) {
            case "stable":
                return Anchor;
            case "volatile":
                return Activity;
            case "transient":
                return Zap;
            default:
                return Activity;
        }
    }, [data.stability]);

    // Drift Color Logic
    const driftColor = useMemo(() => {
        switch (data.semantic_drift?.toLowerCase()) {
            case "low":
                return "text-green-500";
            case "moderate":
                return "text-yellow-500";
            case "high":
                return "text-red-500";
            default:
                return "text-muted-foreground";
        }
    }, [data.semantic_drift]);

    // Micro-Explanation Generator
    const rationale = useMemo(() => {
        let text = `Classified as ${data.status}`;
        if (data.status === "Emerging") {
            text += ` with ${(growth * 100).toFixed(0)}% growth since ${
                chartData[0]?.year || "start"
            }.`;
        } else if (data.status === "Saturated") {
            text += ` (high volume, low growth).`;
        } else if (data.status === "Declining") {
            text += ` due to falling frequency.`;
        } else if (data.status === "Stable") {
            text += ` showing consistent presence.`;
        } else {
            text += `.`;
        }

        if (data.semantic_drift === "Low") {
            text += " Meaning matches early usage.";
        } else if (data.semantic_drift === "High") {
            text += " Warning: Meaning has shifted significantly.";
        }
        return text;
    }, [data.status, growth, chartData, data.semantic_drift]);

    // Collect all paper IDs
    const paperIds = useMemo(() => {
        const ids = new Set<string>();
        data.trend_vector?.forEach((tv) =>
            tv.paper_ids?.forEach((id) => ids.add(id))
        );
        return Array.from(ids);
    }, [data.trend_vector]);

    return (
        <Card
            className={`flex flex-col transition-opacity duration-200 ${
                !isValid
                    ? "opacity-75 border-yellow-200 dark:border-yellow-900"
                    : ""
            }`}
        >
            <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                    <div className="space-y-1">
                        <CardTitle className="capitalize flex items-center gap-2">
                            {concept}
                            {!isValid && (
                                <Badge
                                    variant="outline"
                                    className="text-yellow-600 border-yellow-200 bg-yellow-50 text-[10px] h-5"
                                >
                                    <AlertTriangle className="h-3 w-3 mr-1" />{" "}
                                    Insufficient Evidence
                                </Badge>
                            )}
                        </CardTitle>
                        <CardDescription className="flex items-center gap-3 text-xs">
                            <TooltipProvider>
                                <UITooltip>
                                    <TooltipTrigger className="flex items-center gap-1 cursor-help">
                                        <ScopeIcon className="h-3 w-3" />
                                        {data.scope || "Unknown Scope"}
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        Scope based on corpus share
                                    </TooltipContent>
                                </UITooltip>

                                <UITooltip>
                                    <TooltipTrigger className="flex items-center gap-1 cursor-help">
                                        <StabilityIcon className="h-3 w-3" />
                                        {data.stability || "Unknown Stability"}
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        {/* Improved Stability Explanation */}
                                        {data.stability === "Volatile"
                                            ? "High variance in normalized frequency"
                                            : data.stability === "Stable"
                                            ? "Consistent frequency over time"
                                            : "Based on NCF variance analysis"}
                                    </TooltipContent>
                                </UITooltip>
                            </TooltipProvider>
                        </CardDescription>
                    </div>
                    <StatusBadge status={data.status} />
                </div>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col">
                <div className="flex items-center justify-between mb-4 text-sm">
                    <div className="flex items-center gap-2">
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
                            {(growth * 100).toFixed(1)}% Growth
                        </span>
                    </div>
                    {/* Toggle Switch */}
                    <div className="flex items-center text-[10px] border rounded-md overflow-hidden">
                        <button
                            onClick={() => setUseNormFreq(true)}
                            className={`px-2 py-1 ${
                                useNormFreq
                                    ? "bg-primary text-primary-foreground"
                                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                            }`}
                        >
                            Norm
                        </button>
                        <button
                            onClick={() => setUseNormFreq(false)}
                            className={`px-2 py-1 ${
                                !useNormFreq
                                    ? "bg-primary text-primary-foreground"
                                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                            }`}
                        >
                            Raw
                        </button>
                    </div>
                </div>

                <div className="h-32 w-full mt-auto relative">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData}>
                            <XAxis
                                dataKey="year"
                                fontSize={10}
                                stroke="hsl(var(--muted-foreground))"
                            />
                            <YAxis
                                fontSize={10}
                                stroke="hsl(var(--muted-foreground))"
                                width={30}
                            />
                            <Tooltip
                                content={({ active, payload, label }) => {
                                    if (active && payload && payload.length) {
                                        const dataPoint = payload[0].payload;
                                        return (
                                            <div className="bg-popover border border-border p-2 rounded shadow-lg text-xs">
                                                <p className="font-bold mb-1">
                                                    {label}
                                                </p>
                                                <p>
                                                    {useNormFreq
                                                        ? "Norm Freq"
                                                        : "Count"}
                                                    :{" "}
                                                    {Number(
                                                        payload[0].value
                                                    ).toFixed(
                                                        useNormFreq ? 3 : 0
                                                    )}
                                                </p>
                                                {/* DATA EXPOSURE: Top Related Concepts */}
                                                {dataPoint.top_related &&
                                                    dataPoint.top_related
                                                        .length > 0 && (
                                                        <div className="mt-2 text-[10px] text-muted-foreground border-t pt-1">
                                                            <strong>
                                                                Co-occurs with:
                                                            </strong>
                                                            <div className="flex flex-wrap gap-1 mt-0.5">
                                                                {dataPoint.top_related
                                                                    .slice(0, 3)
                                                                    .map(
                                                                        (
                                                                            c: string
                                                                        ) => (
                                                                            <span
                                                                                key={
                                                                                    c
                                                                                }
                                                                                className="bg-secondary px-1 rounded"
                                                                            >
                                                                                {
                                                                                    c
                                                                                }
                                                                            </span>
                                                                        )
                                                                    )}
                                                            </div>
                                                        </div>
                                                    )}
                                            </div>
                                        );
                                    }
                                    return null;
                                }}
                                cursor={{ fill: "hsl(var(--primary)/0.1)" }}
                            />
                            <Bar
                                dataKey="value"
                                fill={
                                    isValid
                                        ? "hsl(var(--primary))"
                                        : "hsl(var(--muted-foreground))"
                                }
                                radius={[4, 4, 0, 0]}
                                barSize={20}
                            />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                {/* Footer Metrics */}
                <div className="mt-4 pt-4 border-t grid grid-cols-2 gap-2 text-xs">
                    <div className="flex flex-col">
                        <span className="text-muted-foreground">Drift</span>
                        <span
                            className={`font-medium flex items-center gap-1 ${driftColor}`}
                        >
                            {data.semantic_drift || "Unknown"}
                        </span>
                    </div>
                    <div className="flex flex-col items-end">
                        <span className="text-muted-foreground flex items-center gap-1">
                            Confidence
                            <TooltipProvider>
                                <UITooltip>
                                    <TooltipTrigger>
                                        <Info className="h-3 w-3" />
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        Based on volume, consistency, and
                                        evidence
                                    </TooltipContent>
                                </UITooltip>
                            </TooltipProvider>
                        </span>
                        <span className="font-medium">
                            {confidence.toFixed(0)}%
                        </span>
                    </div>
                </div>

                {/* Micro-Explanation */}
                <div className="mt-3 text-[10px] text-muted-foreground bg-muted/30 p-2 rounded italic border border-transparent hover:border-border transition-colors">
                    {rationale}
                </div>
            </CardContent>

            <CardFooter className="pt-0">
                <div className="w-full">
                    <Button
                        variant="ghost"
                        size="sm"
                        className="w-full text-xs h-8 flex justify-between group"
                        onClick={() => setShowPapers(!showPapers)}
                    >
                        <span>Evidence ({paperIds.length} papers)</span>
                        {showPapers ? (
                            <ChevronUp className="h-3 w-3" />
                        ) : (
                            <ChevronDown className="h-3 w-3 text-muted-foreground group-hover:text-foreground" />
                        )}
                    </Button>

                    {showPapers && (
                        <div className="mt-2 text-xs space-y-1 max-h-40 overflow-y-auto pl-1 pr-1 border-t pt-2 scrollbar-thin scrollbar-thumb-muted-foreground/20">
                            {paperIds.length > 0 ? (
                                paperIds.map((pid) => (
                                    <a
                                        key={pid}
                                        href={`https://arxiv.org/abs/${pid}`} // PROVENANCE FIX: Direct Link
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-center gap-2 p-1 hover:bg-muted/50 rounded group/link transition-colors"
                                    >
                                        <FileText className="h-3 w-3 text-muted-foreground group-hover/link:text-primary" />
                                        <span className="truncate flex-1 font-mono text-[10px] text-muted-foreground group-hover/link:text-primary group-hover/link:underline">
                                            {pid}
                                        </span>
                                        <ArrowUpRight className="h-3 w-3 opacity-0 group-hover/link:opacity-100" />
                                    </a>
                                ))
                            ) : (
                                <span className="text-muted-foreground italic">
                                    No linked papers found.
                                </span>
                            )}
                        </div>
                    )}
                </div>
            </CardFooter>
        </Card>
    );
}
