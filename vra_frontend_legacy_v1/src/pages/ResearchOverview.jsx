import React, { useState } from "react";
import useResearchStore from "../state/researchStore";
import { StatCard } from "../components/common/StatCard";
import {
    Activity,
    BookOpen,
    GitGraph,
    FileText,
    AlertTriangle,
    CheckCircle,
} from "lucide-react";
import PaperReview from "../components/PaperReview";
import { useNavigate } from "react-router-dom";

const ResearchOverview = () => {
    const {
        query,
        currentStep,
        papers,
        knowledgeGraph,
        gaps,
        globalAnalysis,
        submitReview,
        isLoading,
    } = useResearchStore();

    const navigate = useNavigate();
    const [isReviewOpen, setIsReviewOpen] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Derived Stats
    const paperCount = papers?.length || 0;
    const conceptCount = knowledgeGraph?.nodes?.length || 0;
    const gapCount = gaps?.length || 0;

    const handlePaperConfirm = async (ids) => {
        try {
            setIsSubmitting(true);
            await submitReview({ query, selected_paper_ids: ids });
            setIsReviewOpen(false);
        } catch (error) {
            console.error("Failed to submit review:", error);
            // Consider showing a toast notification or error message to the user
        } finally {
            setIsSubmitting(false);
        }
    };

    const isWaitingForReview = currentStep === "awaiting_research_review";
    const isWaitingForGraph = currentStep === "awaiting_graph_review";

    return (
        <div className="space-y-8 animate-fade-in">
            <header className="flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">
                        Research Overview
                    </h1>
                    <p className="text-muted-foreground">
                        Query:{" "}
                        <span className="text-primary font-medium">
                            "{query}"
                        </span>
                    </p>
                </div>
                <div className="text-right">
                    <span className="text-xs text-muted-foreground uppercase tracking-wider block mb-1">
                        Status
                    </span>
                    <span
                        className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium border ${
                            isWaitingForReview || isWaitingForGraph
                                ? "bg-yellow-500/10 text-yellow-500 border-yellow-500/20"
                                : "bg-green-500/10 text-green-500 border-green-500/20"
                        }`}
                    >
                        {isLoading
                            ? "Updates in progress..."
                            : currentStep?.replace(/_/g, " ") || "Unknown"}
                    </span>
                </div>
            </header>

            {/* ACTION REQUIRED BANNER */}
            {isWaitingForReview && (
                <div className="bg-primary/10 border border-primary/20 rounded-xl p-6 flex items-center justify-between">
                    <div>
                        <h3 className="text-lg font-bold text-white flex items-center gap-2">
                            <AlertTriangle className="text-primary" size={20} />
                            Action Required: Review Papers
                        </h3>
                        <p className="text-muted-foreground text-sm mt-1">
                            The agent has collected {paperCount} papers. Please
                            verify which ones to analyze.
                        </p>
                    </div>
                    <button
                        onClick={() => setIsReviewOpen(!isReviewOpen)}
                        className="btn btn-primary"
                        disabled={isSubmitting}
                    >
                        {isReviewOpen ? "Close Review" : "Start Review"}
                    </button>
                </div>
            )}

            {isWaitingForGraph && (
                <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-6 flex items-center justify-between">
                    <div>
                        <h3 className="text-lg font-bold text-white flex items-center gap-2">
                            <GitGraph className="text-purple-400" size={20} />
                            Action Required: Verify Knowledge Graph
                        </h3>
                        <p className="text-muted-foreground text-sm mt-1">
                            The knowledge graph has been constructed. Please
                            review it before gap analysis.
                        </p>
                    </div>
                    <button
                        onClick={() => navigate("knowledge")}
                        className="btn btn-primary bg-purple-600 hover:bg-purple-700 border-transparent text-white"
                    >
                        Go to Graph Explorer
                    </button>
                </div>
            )}

            {/* INLINE PAPER REVIEW COMPONENT */}
            {isWaitingForReview && isReviewOpen && (
                <div className="border border-border rounded-xl p-4 bg-card/50">
                    <PaperReview
                        papers={papers}
                        onConfirm={handlePaperConfirm}
                    />
                </div>
            )}

            {/* STAT CARDS */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                    title="Papers Analyzed"
                    value={paperCount}
                    subtext={
                        isWaitingForReview ? "Pending Selection" : "Analyzed"
                    }
                    icon={BookOpen}
                    delay={0.1}
                />
                <StatCard
                    title="Concepts Mapped"
                    value={conceptCount}
                    subtext="Key research topics"
                    icon={GitGraph}
                    delay={0.2}
                />
                <StatCard
                    title="Research Gaps"
                    value={gapCount}
                    subtext="Identified opportunities"
                    icon={Activity}
                    delay={0.3}
                />
                <StatCard
                    title="System Status"
                    value={currentStep === "completed" ? "Ready" : "Active"}
                    subtext="Workflow Progress"
                    icon={FileText}
                    delay={0.4}
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Global Summary */}
                <div className="lg:col-span-2 card">
                    <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                        <BookOpen size={18} className="text-primary" />
                        Executive Summary
                    </h3>
                    <div className="prose prose-invert max-w-none text-muted-foreground text-sm">
                        {globalAnalysis?.summary ||
                            "No summary available yet. Analysis is pending..."}
                    </div>
                </div>

                {/* Evidence Provenance */}
                <div className="card">
                    <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                        <CheckCircle size={18} className="text-green-500" />
                        Evidence Provenance
                    </h3>
                    <div className="space-y-4">
                        <div className="flex justify-between text-sm py-2 border-b border-border/50">
                            <span className="text-muted-foreground">
                                Source Coverage
                            </span>
                            <span className="text-white font-medium">
                                {paperCount} Papers
                            </span>
                        </div>
                        <div className="flex justify-between text-sm py-2 border-b border-border/50">
                            <span className="text-muted-foreground">
                                Entity Integrity
                            </span>
                            <span className="text-white font-medium">
                                {conceptCount} Concepts
                            </span>
                        </div>
                        <div className="flex justify-between text-sm py-2 border-b border-border/50">
                            <span className="text-muted-foreground">
                                Trend Signals
                            </span>
                            <span className="text-white font-medium">
                                {globalAnalysis?.trendStatus || "Pending"}
                            </span>
                        </div>
                        <div className="mt-4 p-3 bg-bg-surface rounded-lg text-xs text-muted-foreground">
                            System confidence Level:{" "}
                            <span
                                className={`font-bold ${
                                    globalAnalysis?.confidence === "high"
                                        ? "text-green-400"
                                        : globalAnalysis?.confidence ===
                                          "medium"
                                        ? "text-yellow-400"
                                        : "text-red-400"
                                }`}
                            >
                                {globalAnalysis?.confidence || "Unknown"}
                            </span>
                            <br />
                            Data provenance trail established.
                        </div>
                    </div>

                    {/* Manual Notes Section */}
                    <div className="mt-6 pt-6 border-t border-border/50">
                        <h4 className="text-sm font-bold text-white mb-2">
                            Researcher Notes
                        </h4>
                        <textarea
                            className="input min-h-[100px] text-sm"
                            placeholder="Add your observations here..."
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ResearchOverview;
