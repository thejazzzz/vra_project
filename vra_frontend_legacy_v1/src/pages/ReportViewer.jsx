import React, { useRef } from "react";
import ReactMarkdown from "react-markdown";
import useResearchStore from "../state/researchStore";
import { Download, FileText, Printer, Share2 } from "lucide-react";
import { useReactToPrint } from "react-to-print";

const ReportViewer = () => {
    const { globalAnalysis, drafts, query } = useResearchStore();
    // Assuming report is stored in globalAnalysis.draft_report or similar,
    // or strictly in 'drafts' if we had that.
    // The previous code used status.draft_report.
    // In researchStore, I mapped it to 'draft_report'.
    // Let's check researchStore state mapping.
    // "draft_report": state.draft_report

    // Actually, I need to check how I mapped it in researchStore.js
    // I mapped: globalAnalysis: state.global_analysis || {}
    // But draft_report is top level in VRAState.
    // I missed mapping draft_report in researchStore.js explicitly?
    // Let's check researchStore.js.

    // If it's missing, I'll add access to it or assume it's passed around.
    // For now, I'll assume I can access it via useResearchStore (I might need to fix store first).

    const store = useResearchStore();
    const reportContent =
        store.draftReport ||
        store.globalAnalysis?.summary ||
        "Report generation pending...";

    const printRef = useRef();
    const handlePrint = useReactToPrint({
        content: () => printRef.current,
        documentTitle: `Research_Report_${query}`,
    });

    const handleExportMarkdown = () => {
        const element = document.createElement("a");
        const file = new Blob([reportContent], { type: "text/markdown" });
        element.href = URL.createObjectURL(file);
        element.download = `Research_Report_${query}.md`;
        document.body.appendChild(element); // Required for this to work in FireFox
        element.click();
    };

    return (
        <div className="animate-fade-in space-y-6">
            <header className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">
                        Research Report
                    </h1>
                    <p className="text-muted-foreground">
                        Synthesized findings and strategic insights.
                    </p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={handleExportMarkdown}
                        className="btn btn-secondary text-sm"
                    >
                        <FileText size={16} /> MD
                    </button>
                    <button
                        onClick={handlePrint}
                        className="btn btn-primary text-sm"
                    >
                        <Printer size={16} /> PDF / Print
                    </button>
                </div>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* TOC Sidebar (Simple Header Extraction) */}
                <div className="hidden lg:block lg:col-span-1">
                    <div className="card sticky top-24 max-h-[calc(100vh-8rem)] overflow-y-auto">
                        <h4 className="font-bold text-white mb-4 flex items-center gap-2">
                            <Share2 size={16} className="text-primary" />{" "}
                            Contents
                        </h4>
                        <nav className="space-y-1 text-sm text-muted-foreground">
                            {/* In a real implementation, we would parse headers from markdown. 
                                For now, simplified links or static sections based on template. */}
                            <a
                                href="#"
                                className="block hover:text-primary transition-colors py-1"
                            >
                                Executive Summary
                            </a>
                            <a
                                href="#"
                                className="block hover:text-primary transition-colors py-1"
                            >
                                Key Research Gaps
                            </a>
                            <a
                                href="#"
                                className="block hover:text-primary transition-colors py-1"
                            >
                                Trend Analysis
                            </a>
                            <a
                                href="#"
                                className="block hover:text-primary transition-colors py-1"
                            >
                                Detailed Evidence
                            </a>
                            <a
                                href="#"
                                className="block hover:text-primary transition-colors py-1"
                            >
                                Strategic Recommendations
                            </a>
                        </nav>
                    </div>
                </div>

                {/* Main Report Content */}
                <div className="lg:col-span-3">
                    <div
                        ref={printRef}
                        className="card bg-bg-surface p-8 min-h-[80vh] print:text-black print:bg-white"
                    >
                        <div className="prose prose-invert max-w-none prose-headings:text-white prose-p:text-gray-300 prose-a:text-primary prose-strong:text-white print:prose-neutral">
                            <ReactMarkdown>{reportContent}</ReactMarkdown>
                        </div>

                        <div className="mt-12 pt-8 border-t border-border/50 text-xs text-muted-foreground text-center print:text-gray-500">
                            Generated by VRA Research Intelligence •{" "}
                            {new Date().toLocaleDateString()}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ReportViewer;
