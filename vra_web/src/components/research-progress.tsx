import { useEffect, useState, useRef } from "react";
import { researchApi } from "@/lib/api";
import { Progress } from "@/components/ui/progress";
import { Card } from "@/components/ui/card";
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface ResearchProgressProps {
    taskId: string;
    onComplete: (status: string, data: any) => void;
    onError?: (error: any) => void;
}

const TERMINAL_PHASES = ["COMPLETED", "FAILED"];

const PHASE_MAPPING: Record<string, { percent: number; label: string }> = {
    INITIALIZING: { percent: 10, label: "Initializing research agents..." },
    EXPANDING_QUERIES: { percent: 30, label: "Expanding research queries..." },
    FETCHING_PAPERS: {
        percent: 60,
        label: "Fetching papers from trusted sources...",
    },
    MERGING_RESULTS: {
        percent: 85,
        label: "Merging and deduplicating results...",
    },
    COMPLETED: { percent: 100, label: "Research completed." },
    FAILED: { percent: 100, label: "Research failed." },
};

export function ResearchProgress({
    taskId,
    onComplete,
    onError,
}: ResearchProgressProps) {
    const [progressData, setProgressData] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const pollingRef = useRef<NodeJS.Timeout | null>(null);

    // Polling logic
    useEffect(() => {
        let isMounted = true;

        const poll = async () => {
            try {
                const data = await researchApi.getProgress(taskId);
                if (!isMounted) return;

                setProgressData(data);

                const phase = data.phase;

                if (TERMINAL_PHASES.includes(phase)) {
                    // Stop polling
                    if (pollingRef.current) {
                        clearInterval(pollingRef.current);
                        pollingRef.current = null;
                    }

                    if (phase === "FAILED") {
                        setError("Research task failed. Please try again.");
                        if (onError) onError(new Error("Task failed"));
                    } else {
                        // Completed successfully
                        // Add a small delay for UI smoothness before unmounting/redirecting
                        setTimeout(() => {
                            onComplete(phase, data);
                        }, 800);
                    }
                }
            } catch (err) {
                console.error("Polling error:", err);
                // Don't stop polling immediately on transient network errors,
                // but maybe track failure count? for now just log.
            }
        };

        // Start polling
        // Adaptive interval: 1s usually.
        pollingRef.current = setInterval(poll, 1000);

        // Immediate first check
        poll();

        return () => {
            isMounted = false;
            if (pollingRef.current) {
                clearInterval(pollingRef.current);
            }
        };
    }, [taskId, onComplete, onError]);

    if (error) {
        return (
            <div className="p-4 rounded-md bg-destructive/10 text-destructive flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                <span>{error}</span>
            </div>
        );
    }

    if (!progressData) {
        return (
            <div className="space-y-4 py-4 animate-pulse">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Initializing connection...
                </div>
                <Progress value={5} className="h-2" />
            </div>
        );
    }

    const currentPhase = progressData.phase || "INITIALIZING";
    const phaseInfo = PHASE_MAPPING[currentPhase] || PHASE_MAPPING.INITIALIZING;

    // If fetching, show detailed counts
    let detailText = phaseInfo.label;
    if (currentPhase === "FETCHING_PAPERS" && progressData.queries_total > 1) {
        detailText = `Fetching sources (Query ${progressData.queries_completed}/${progressData.queries_total}). Found ${progressData.papers_found} papers.`;
    } else if (currentPhase === "MERGING_RESULTS") {
        detailText = `Processing ${progressData.papers_found} papers...`;
    }

    return (
        <div className="space-y-4 py-2">
            <div className="flex justify-between items-center text-sm">
                <div className="flex items-center gap-2 font-medium">
                    {currentPhase !== "COMPLETED" && (
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    )}
                    {currentPhase === "COMPLETED" && (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                    )}
                    <span className="capitalize">
                        {currentPhase.replace(/_/g, " ").toLowerCase()}
                    </span>
                </div>
                <span className="text-muted-foreground text-xs">
                    {progressData.papers_found > 0
                        ? `${progressData.papers_found} papers found`
                        : ""}
                </span>
            </div>

            <Progress
                value={phaseInfo.percent}
                className="h-2 transition-all duration-500"
            />

            <p className="text-xs text-muted-foreground text-center animate-in fade-in">
                {detailText}
            </p>
        </div>
    );
}
