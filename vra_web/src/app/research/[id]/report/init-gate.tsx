//vra_web/src/app/research/[id]/report/init-gate.tsx
"use client";

import { useState } from "react";
import { reportingApi } from "@/lib/api";
import { Loader2, FileText, CheckCircle, PenTool } from "lucide-react";
import { Button } from "@/components/ui/button";

interface InitializationGateProps {
    sessionId: string;
    onInitialized: () => void;
}

export function InitializationGate({
    sessionId,
    onInitialized,
}: InitializationGateProps) {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleInit = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const AUTO_CONFIRM = true;
            await reportingApi.init(sessionId, AUTO_CONFIRM);
            onInitialized();
        } catch (err: unknown) {
            console.error(err);
            const detail = (err as any)?.response?.data?.detail;
            let message = "Failed to initialize report.";

            if (detail) {
                if (typeof detail === "string") {
                    message = detail;
                } else if (Array.isArray(detail)) {
                    message = detail
                        .map((e: any) => e.msg || JSON.stringify(e))
                        .join("; ");
                } else {
                    message = JSON.stringify(detail);
                }
            }
            setError(message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-8 max-w-2xl mx-auto">
            <div className="bg-white p-8 rounded-2xl shadow-xl border border-gray-100">
                <div className="bg-blue-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6">
                    <FileText className="w-8 h-8 text-blue-600" />
                </div>

                <h1 className="text-2xl font-bold text-gray-900 mb-4">
                    Ready to Generate Research Report
                </h1>

                <p className="text-gray-600 mb-8 leading-relaxed">
                    The agent will now analyze all collected papers, trends, and
                    gaps to structure a comprehensive report. This process
                    involves multiple steps of generation, review, and
                    refinement.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8 text-left">
                    <div className="p-4 bg-gray-50 rounded-lg">
                        <div className="flex items-center gap-2 mb-2 font-semibold text-gray-900">
                            <PenTool className="w-4 h-4 text-purple-500" />
                            <span>1. Draft</span>
                        </div>
                        <p className="text-xs text-gray-500">
                            AI generates content section by section.
                        </p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg">
                        <div className="flex items-center gap-2 mb-2 font-semibold text-gray-900">
                            <CheckCircle className="w-4 h-4 text-orange-500" />
                            <span>2. Review</span>
                        </div>
                        <p className="text-xs text-gray-500">
                            You review, edit, or regenerate each part.
                        </p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg">
                        <div className="flex items-center gap-2 mb-2 font-semibold text-gray-900">
                            <FileText className="w-4 h-4 text-green-500" />
                            <span>3. Finalize</span>
                        </div>
                        <p className="text-xs text-gray-500">
                            Export to PDF, DOCX, or Markdown.
                        </p>
                    </div>
                </div>

                {error && (
                    <div className="mb-6 p-3 bg-red-50 text-red-600 text-sm rounded-md">
                        Error: {error}
                    </div>
                )}

                <Button
                    size="lg"
                    onClick={handleInit}
                    disabled={isLoading}
                    className="w-full sm:w-auto"
                >
                    {isLoading ? (
                        <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Initializing...
                        </>
                    ) : (
                        "Start Report Generation"
                    )}
                </Button>
            </div>
        </div>
    );
}
