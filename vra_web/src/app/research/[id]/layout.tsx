"use client";

import { useEffect, use } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { useResearchStore } from "@/lib/store";
import { Loader2 } from "lucide-react";
import { AudienceBadge } from "@/components/audience-badge";

export default function ResearchLayout({
    children,
    params,
}: {
    children: React.ReactNode;
    params: Promise<{ id: string }>;
}) {
    const resolvedParams = use(params);
    const { syncState, isLoading, currentStep, query, audience } =
        useResearchStore();
    const queryId = decodeURIComponent(resolvedParams.id);

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

    useEffect(() => {
        let isMounted = true;
        let timeoutId: NodeJS.Timeout;

        // Initial sync on mount or queryId change
        if (queryId) {
            syncState(queryId);
        }

        const poll = async () => {
            if (!shouldPoll || !isMounted) return;
            try {
                await syncState(queryId);
            } catch (e) {
                console.error("Polling error:", e);
            } finally {
                if (isMounted && shouldPoll) {
                    timeoutId = setTimeout(poll, 10000);
                }
            }
        };

        if (shouldPoll) {
            timeoutId = setTimeout(poll, 10000);
        }

        return () => {
            isMounted = false;
            clearTimeout(timeoutId);
        };
    }, [queryId, syncState, shouldPoll]);

    return (
        <div className="flex min-h-screen bg-background text-foreground">
            <Sidebar params={resolvedParams} />
            <main className="flex-1 md:ml-64 transition-all duration-300">
                <div className="container p-8 max-w-7xl mx-auto space-y-6">
                    {/* Header / Breadcrumb placeholder */}
                    <div className="flex justify-between items-center pb-6 border-b">
                        <h1
                            className="text-2xl font-bold truncate max-w-xl"
                            title={query || queryId}
                        >
                            {query || queryId}
                        </h1>
                        <div className="flex items-center gap-2">
                            {isLoading && (
                                <Loader2 className="animate-spin text-muted-foreground w-4 h-4" />
                            )}
                            <span className="text-xs uppercase tracking-wider text-muted-foreground border px-2 py-1 rounded">
                                {currentStep?.replace(/_/g, " ") ||
                                    "Initializing"}
                            </span>
                            {audience && <AudienceBadge audience={audience} />}
                        </div>
                    </div>

                    {children}
                </div>
            </main>
        </div>
    );
}
