//vra_web/src/app/research/[id]/report/full-preview.tsx
"use client";

import { ReportState } from "@/types";
import { reportingApi } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { Download, CheckCircle, Loader2 } from "lucide-react";
import { useState } from "react";

interface FullReportPreviewProps {
    sessionId: string;
    state: ReportState;
    onRefresh: () => void;
}

export function FullReportPreview({
    sessionId,
    state,
    onRefresh,
}: FullReportPreviewProps) {
    const [isFinalizing, setIsFinalizing] = useState(false);

    const handleFinalize = async () => {
        if (
            !confirm(
                "Are you sure you want to finalize the report? This will lock all sections."
            )
        )
            return;
        setIsFinalizing(true);
        try {
            await reportingApi.finalize(sessionId);
            onRefresh();
        } catch (err) {
            console.error(err);
            alert("Failed to finalize report.");
        } finally {
            setIsFinalizing(false);
        }
    };

    const handleExport = async (format: "pdf" | "docx" | "markdown") => {
        try {
            const blob = await reportingApi.exportReport(sessionId, format);
            // Create a link and click it to download
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.setAttribute(
                "download",
                `research-report.${format === "markdown" ? "md" : format}`
            );
            document.body.appendChild(link);
            link.click();

            // Clean up
            setTimeout(() => {
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);
            }, 100);
        } catch (err) {
            console.error(err);
            alert("Failed to export report.");
        }
    };

    const isCompleted = state.report_status === "completed";

    return (
        <div className="h-full flex flex-col bg-black">
            {/* Header */}
            <div className="bg-neutral-900 border-b border-neutral-800 px-8 py-4 flex justify-between items-center sticky top-0 z-10 shadow-sm">
                <div>
                    <h2 className="text-xl font-bold text-gray-100">
                        Final Report Preview
                    </h2>
                    <p className="text-sm text-gray-400">
                        {isCompleted
                            ? "Report finalized and ready for export."
                            : "Review the full report before finalizing."}
                    </p>
                </div>
                <div className="flex gap-2">
                    {isCompleted ? (
                        <>
                            <Button
                                variant="outline"
                                onClick={() => handleExport("markdown")}
                                className="border-neutral-700 text-gray-300 hover:bg-neutral-800 hover:text-white"
                            >
                                <Download className="w-4 h-4 mr-2" />
                                Markdown
                            </Button>
                            {/* PDF/DOCX are stubs in backend, but UI is ready */}
                            <Button
                                variant="outline"
                                onClick={() => handleExport("docx")}
                                className="border-neutral-700 text-gray-300 hover:bg-neutral-800 hover:text-white"
                            >
                                <Download className="w-4 h-4 mr-2" />
                                DOCX
                            </Button>
                            <Button
                                variant="outline"
                                onClick={() => handleExport("pdf")}
                                className="border-neutral-700 text-gray-300 hover:bg-neutral-800 hover:text-white"
                            >
                                <Download className="w-4 h-4 mr-2" />
                                PDF
                            </Button>
                        </>
                    ) : (
                        <Button
                            className="bg-green-600 hover:bg-green-700 text-white"
                            onClick={handleFinalize}
                            disabled={isFinalizing}
                        >
                            {isFinalizing ? (
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            ) : (
                                <CheckCircle className="w-4 h-4 mr-2" />
                            )}
                            Finalize Report
                        </Button>
                    )}
                </div>
            </div>

            {/* Scrolling Preview */}
            <div className="flex-1 overflow-auto p-8 lg:p-12">
                <div className="max-w-4xl mx-auto bg-neutral-900 shadow-lg rounded-xl min-h-full p-12 print:shadow-none print:p-0 border border-neutral-800">
                    <div className="prose prose-invert prose-blue prose-lg max-w-none">
                        <h1>Research Report</h1>
                        {state.sections.map((section) => (
                            <div
                                key={section.section_id}
                                className="mb-12 border-b pb-8 last:border-0"
                            >
                                {/* We render the content directly, or if it's empty, a placeholder */}
                                <ReactMarkdown>
                                    {section.content ||
                                        `*${section.title} content missing*`}
                                </ReactMarkdown>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
