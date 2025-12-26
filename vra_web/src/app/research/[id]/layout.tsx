"use client";

import { useEffect, use } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { useResearchStore } from "@/lib/store";
import { Loader2 } from "lucide-react";

export default function ResearchLayout({
    children,
    params,
}: {
    children: React.ReactNode;
    params: Promise<{ id: string }>;
}) {
    const resolvedParams = use(params);
    const { syncState, isLoading, currentStep, query } = useResearchStore();
    const queryId = decodeURIComponent(resolvedParams.id);

    useEffect(() => {
        if (queryId) {
            syncState(queryId);
            // Polling disabled per user request. Use manual refresh.
            // const interval = setInterval(() => syncState(queryId), 5000);
            // return () => clearInterval(interval);
        }
    }, [queryId, syncState]);

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
                        </div>
                    </div>

                    {children}
                </div>
            </main>
        </div>
    );
}
