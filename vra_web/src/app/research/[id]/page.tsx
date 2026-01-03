"use client";

import { use, useEffect, useRef } from "react";
import { useResearchStore } from "@/lib/store";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
    BookOpen,
    GitGraph,
    Activity,
    FileText,
    AlertTriangle,
    CheckCircle,
    RefreshCw,
    Play,
} from "lucide-react";
import Link from "next/link";
import { PaperReviewDialog } from "@/components/paper-review-dialog";

export default function ResearchOverviewPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const resolvedParams = use(params);
    const {
        papers,
        knowledgeGraph,
        gaps,
        currentStep,
        globalAnalysis,
        syncState,
        isLoading,
    } = useResearchStore();

    const id = decodeURIComponent(resolvedParams.id);
    const paperCount = papers?.length || 0;
    const conceptCount = knowledgeGraph?.nodes?.length || 0;
    const gapCount = gaps?.length || 0;

    const isPaperReviewNeeded = currentStep === "awaiting_research_review";
    const isGraphReviewNeeded = currentStep === "awaiting_graph_review";
    const isReportReady = currentStep === "awaiting_report_start";

    const computeConfidence = () => {
        if (paperCount >= 10 && conceptCount >= 20) {
            return { level: "High", color: "text-green-500" };
        }
        if (paperCount >= 5) {
            return { level: "Medium", color: "text-yellow-500" };
        }
        return { level: "Low", color: "text-red-500" };
    };

    const confidence = computeConfidence();

    // Polling Logic: Check status every 4 seconds if in an intermediate step
    const INTERMEDIATE_STEPS = [
        "awaiting_analysis",
        "awaiting_paper_summaries",
        "awaiting_graphs",
        "awaiting_gap_analysis",
        "awaiting_hypothesis",
        "reviewing_hypotheses",
        "awaiting_report",
    ];

    const shouldPoll = INTERMEDIATE_STEPS.includes(currentStep || "");
    const pollingRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        if (shouldPoll) {
            pollingRef.current = setInterval(() => {
                syncState(id);
            }, 4000);
        } else {
            if (pollingRef.current) clearInterval(pollingRef.current);
        }

        return () => {
            if (pollingRef.current) clearInterval(pollingRef.current);
        };
    }, [shouldPoll, id, syncState]);

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex justify-between items-center">
                <h1 className="text-3xl font-bold tracking-tight">
                    Research Overview
                </h1>
                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => syncState(id)}
                        disabled={isLoading}
                    >
                        <RefreshCw
                            className={`h-4 w-4 mr-2 ${
                                isLoading ? "animate-spin" : ""
                            }`}
                        />
                        Refresh Status
                    </Button>
                </div>
            </div>

            {/* Action Alerts */}
            {isPaperReviewNeeded && (
                <Alert
                    variant="default"
                    className="border-primary/50 bg-primary/10"
                >
                    <AlertTriangle className="h-4 w-4 text-primary" />
                    <AlertTitle className="text-primary font-bold">
                        Action Required: Paper Review
                    </AlertTitle>
                    <AlertDescription className="flex justify-between items-center mt-2">
                        <span>
                            The agent has collected {paperCount} papers. Please
                            verify which ones to analyze.
                        </span>
                        <PaperReviewDialog query={id} />
                    </AlertDescription>
                </Alert>
            )}

            {isGraphReviewNeeded && (
                <Alert className="border-purple-500/50 bg-purple-500/10">
                    <GitGraph className="h-4 w-4 text-purple-500" />
                    <AlertTitle className="text-purple-500 font-bold">
                        Action Required: Verify Knowledge Graph
                    </AlertTitle>
                    <AlertDescription className="flex justify-between items-center mt-2">
                        <span>
                            The knowledge graph has been constructed. Please
                            review structure.
                        </span>
                        <Button
                            size="sm"
                            className="bg-purple-600 hover:bg-purple-700"
                            asChild
                        >
                            <Link href={`/research/${id}/knowledge`}>
                                Review Graph
                            </Link>
                        </Button>
                    </AlertDescription>
                </Alert>
            )}

            {isReportReady && (
                <Alert className="border-green-500/50 bg-green-500/10">
                    <Play className="h-4 w-4 text-green-500" />
                    <AlertTitle className="text-green-500 font-bold">
                        Report Planning Complete
                    </AlertTitle>
                    <AlertDescription className="flex justify-between items-center mt-2">
                        <span>
                            The research report structure is ready. You can now
                            generate the full report.
                        </span>
                        <Button
                            size="sm"
                            className="bg-green-600 hover:bg-green-700"
                            asChild
                        >
                            <Link href={`/research/${id}/report`}>
                                Go to Report
                            </Link>
                        </Button>
                    </AlertDescription>
                </Alert>
            )}

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                    title="Papers Analyzed"
                    value={paperCount}
                    subtext="From trusted sources"
                    icon={BookOpen}
                />
                <StatCard
                    title="Concepts Mapped"
                    value={conceptCount}
                    subtext="Key research topics"
                    icon={GitGraph}
                />
                <StatCard
                    title="Research Gaps"
                    value={gapCount}
                    subtext="Identified opportunities"
                    icon={Activity}
                />
                <StatCard
                    title="Status"
                    value={currentStep?.replace(/_/g, " ") || "Active"}
                    subtext="Workflow Progress"
                    icon={FileText}
                />
            </div>

            {/* Analysis & Provenance */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <Card className="lg:col-span-2">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <BookOpen className="w-5 h-5 text-primary" />{" "}
                            Executive Summary
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="prose prose-invert prose-sm max-w-none text-muted-foreground">
                            {globalAnalysis?.summary || "Analysis pending..."}
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <CheckCircle className="w-5 h-5 text-green-500" />{" "}
                            Provenance
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex justify-between text-sm py-2 border-b">
                            <span className="text-muted-foreground">
                                Source Coverage
                            </span>
                            <span className="font-medium">
                                {paperCount} Papers
                            </span>
                        </div>
                        <div className="flex justify-between text-sm py-2 border-b">
                            <span className="text-muted-foreground">
                                Entity Integrity
                            </span>
                            <span className="font-medium">
                                {conceptCount} Concepts
                            </span>
                        </div>
                        <div className="p-3 bg-secondary/30 rounded-lg text-xs text-muted-foreground mt-4">
                            System confidence:{" "}
                            <span className={`font-bold ${confidence.color}`}>
                                {confidence.level}
                            </span>
                            <br />
                            Data provenance verified.
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
