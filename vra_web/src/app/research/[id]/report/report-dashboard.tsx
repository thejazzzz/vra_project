//vra_web/src/app/research/[id]/report/report-dashboard.tsx
"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { reportingApi } from "@/lib/api";
import { ReportState } from "@/types";
import { InitializationGate } from "./init-gate";
import { SectionNavigationList } from "./sidebar-nav";
import { SectionWorkspace } from "./section-workspace";
import { FullReportPreview } from "./full-preview";
import { Loader2, AlertTriangle, RefreshCw } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

interface ReportDashboardProps {
    sessionId: string;
}

export function ReportDashboard({ sessionId }: ReportDashboardProps) {
    const searchParams = useSearchParams();
    const [state, setState] = useState<ReportState | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const pollingRef = useRef<NodeJS.Timeout | null>(null);

    // URL Sync State
    const [activeSectionId, setActiveSectionId] = useState<string>(
        searchParams.get("section") || ""
    );

    const activeSection = state?.sections?.find(
        (s) => s.section_id === activeSectionId
    );

    // Determines if we should show the full preview instead of the workspace
    const showFullPreview =
        state &&
        (state.report_status === "awaiting_final_review" ||
            state.report_status === "finalizing" ||
            state.report_status === "completed");

    const fetchState = useCallback(async () => {
        try {
            const data = await reportingApi.getState(sessionId);
            // Backend might return null if not initialized, handle gracefully
            if (data) {
                setState(data);
                setError(null);
            } else {
                // If null, it means not started
            }
        } catch (err: any) {
            console.error("Failed to fetch report state:", err);

            // Handle 404 as "Not Started" -> Show Init Gate
            if (err.response && err.response.status === 404) {
                console.warn(
                    "Report state not found (404), treating as uninitialized."
                );
                setState(null);
                setError(null);
                return;
            }

            // Don't block UI on transient network errors during polling
            // We check against previous state via functional update if needed, but here simple check is fine
            // actually 'state' in closure is stale if not in dep array, but we are setting state
            if (!state) {
                setError("Failed to load report state. Please try refreshing.");
            }
        } finally {
            setIsLoading(false);
        }
    }, [sessionId, state]); // Added state to prevented stale closure

    // Auto-select Effect
    useEffect(() => {
        if (state && state.sections?.length > 0 && !activeSectionId) {
            // Check if we are in a mode where auto-select makes sense (not full preview)
            const isPreviewMode =
                state.report_status === "awaiting_final_review" ||
                state.report_status === "finalizing" ||
                state.report_status === "completed";

            if (!isPreviewMode) {
                setActiveSectionId(state.sections[0].section_id);
            }
        }
    }, [state, activeSectionId]);

    // Initial Load
    useEffect(() => {
        fetchState();
    }, [fetchState]);

    // Polling Logic
    useEffect(() => {
        const shouldPoll =
            state &&
            (state.report_status === "in_progress" ||
                state.report_status === "validating" ||
                state.report_status === "finalizing" ||
                state.sections?.some((s) => s.status === "generating"));

        if (shouldPoll) {
            pollingRef.current = setInterval(fetchState, 3000);
        } else {
            if (pollingRef.current) clearInterval(pollingRef.current);
        }

        return () => {
            if (pollingRef.current) clearInterval(pollingRef.current);
        };
    }, [state, fetchState]);

    const handleInitialized = () => {
        setIsLoading(true);
        fetchState();
    };

    if (isLoading && !state) {
        return (
            <div className="flex items-center justify-center min-h-[50vh]">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                <span className="ml-3 text-gray-500">Loading State...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-8 max-w-2xl mx-auto">
                <Alert variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
                <Button onClick={fetchState} className="mt-4" variant="outline">
                    Retry
                </Button>
            </div>
        );
    }

    // 1. Initialization Gate
    if (!state || !state.user_confirmed_start) {
        return (
            <InitializationGate
                sessionId={sessionId}
                onInitialized={handleInitialized}
            />
        );
    }

    // 2. Global Status Banner (Validating/Failed)
    const showValidating =
        state.report_status === "validating" ||
        state.report_status === "finalizing";
    const showFailed = state.report_status === "failed";

    // 3. Main Split Layout
    return (
        <div className="h-[calc(100vh-64px)] bg-black flex flex-col">
            {/* Status Banners */}
            {showValidating && (
                <div className="bg-blue-950/50 border-b border-blue-900 p-2 text-center text-blue-300 text-xs font-medium flex items-center justify-center gap-2">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    {state.report_status === "finalizing"
                        ? "Finalizing report..."
                        : "Validating report integrity..."}
                </div>
            )}

            {showFailed && (
                <div className="bg-red-950/50 border-b border-red-900 p-2 text-center text-red-400 text-xs font-medium flex items-center justify-center gap-2">
                    <AlertTriangle className="w-3 h-3" />
                    Report generation failed. Please check section errors or
                    reset.
                </div>
            )}

            <div className="flex-1 flex overflow-hidden">
                {/* Sidebar */}
                <SectionNavigationList
                    sections={state.sections}
                    activeSectionId={activeSectionId}
                    onSelect={(id) => {
                        // Update URL
                        const url = new URL(window.location.href);
                        url.searchParams.set("section", id);
                        window.history.pushState({}, "", url.toString());
                        setActiveSectionId(id);
                    }}
                />

                {/* Main Workspace OR Full Preview */}
                <main className="flex-1 overflow-hidden bg-neutral-950">
                    {showFullPreview ? (
                        <FullReportPreview
                            sessionId={sessionId}
                            state={state}
                            onRefresh={() => {
                                setIsLoading(true);
                                fetchState();
                            }}
                        />
                    ) : activeSection ? (
                        <SectionWorkspace
                            key={activeSection.section_id} // Force re-mount on change
                            section={activeSection}
                            sessionId={sessionId}
                            allSections={state.sections}
                            onRefresh={() => {
                                setIsLoading(true); // Trigger loading visual
                                fetchState();
                            }}
                        />
                    ) : (
                        <div className="h-full flex items-center justify-center text-gray-400">
                            Select a section to begin
                        </div>
                    )}
                </main>
            </div>
        </div>
    );
}
