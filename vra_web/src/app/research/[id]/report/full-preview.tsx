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
                "Are you sure you want to finalize the report? This will lock all sections.",
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

    const [isExporting, setIsExporting] = useState(false);

    const handleExport = async (
        format: "pdf" | "docx" | "markdown" | "latex",
    ) => {
        // Guard: Check completion
        if (state.report_status !== "completed") {
            alert("Please finalize the report before exporting.");
            return;
        }

        // Guard: Runtime format check
        const allowed = ["pdf", "docx", "markdown", "latex"];
        if (!allowed.includes(format)) {
            alert("Invalid export format requested.");
            return;
        }

        // Guard: Loading
        if (isExporting) return;

        setIsExporting(true);
        try {
            const blob = await reportingApi.exportReport(sessionId, format);
            // Create a link and click it to download
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;

            let ext: string = format;
            if (format === "markdown") ext = "md";
            if (format === "latex") ext = "tex";

            // Improved File Naming with Sanity Check
            // @ts-ignore - query/title might be missing from strict type but available at runtime or we use fallback
            const title =
                (state as any).title ||
                (state as any).query ||
                "research-report";
            const safeTitle = title.replace(/[^a-z0-9]/gi, "_").toLowerCase();
            const filename = `${safeTitle}-${sessionId.substring(0, 8)}.${ext}`;

            link.setAttribute("download", filename);
            document.body.appendChild(link);
            link.click();

            // Clean up
            setTimeout(() => {
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);
            }, 100);
        } catch (err: any) {
            console.error(err);
            const msg =
                err?.response?.data?.detail || "Failed to export report.";
            alert(msg);
        } finally {
            setIsExporting(false);
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
                            ? "Report finalized. Preview shows content only; structure applied on export."
                            : "Review and finalize to enable export options."}
                    </p>
                </div>
                <div className="flex gap-2">
                    {isCompleted ? (
                        <>
                            <Button
                                variant="outline"
                                onClick={() => handleExport("markdown")}
                                disabled={isExporting}
                                className="border-neutral-700 text-gray-300 hover:bg-neutral-800 hover:text-white"
                            >
                                {isExporting ? (
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                ) : (
                                    <Download className="w-4 h-4 mr-2" />
                                )}
                                Markdown
                            </Button>
                            <Button
                                variant="outline"
                                onClick={() => handleExport("docx")}
                                disabled={isExporting}
                                className="border-neutral-700 text-gray-300 hover:bg-neutral-800 hover:text-white"
                            >
                                {isExporting ? (
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                ) : (
                                    <Download className="w-4 h-4 mr-2" />
                                )}
                                DOCX
                            </Button>
                            <Button
                                variant="outline"
                                onClick={() => handleExport("pdf")}
                                disabled={isExporting}
                                className="border-neutral-700 text-gray-300 hover:bg-neutral-800 hover:text-white"
                            >
                                {isExporting ? (
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                ) : (
                                    <Download className="w-4 h-4 mr-2" />
                                )}
                                PDF
                            </Button>
                            <Button
                                variant="outline"
                                onClick={() => handleExport("latex")}
                                disabled={isExporting}
                                className="border-neutral-700 text-gray-300 hover:bg-neutral-800 hover:text-white"
                            >
                                {isExporting ? (
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                ) : (
                                    <Download className="w-4 h-4 mr-2" />
                                )}
                                LaTeX
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
                        <div className="mb-8 p-4 bg-yellow-900/20 border border-yellow-800 rounded text-yellow-200 text-sm">
                            <strong>Note:</strong> This is a content preview.
                            NUMBERING, TABLE OF CONTENTS, and ABSTRACT will be
                            generated in the exported file.
                        </div>
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
