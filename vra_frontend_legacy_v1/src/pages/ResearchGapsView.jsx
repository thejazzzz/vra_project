import React from "react";
import useResearchStore from "../state/researchStore";
import {
    AlertTriangle,
    Check,
    ThumbsDown,
    ThumbsUp,
    ArrowRight,
} from "lucide-react";

const ResearchGapsView = () => {
    const { gaps } = useResearchStore();

    if (!gaps || gaps.length === 0) {
        return (
            <div className="flex h-[50vh] items-center justify-center text-muted-foreground animate-fade-in">
                <div className="text-center">
                    <AlertTriangle
                        size={48}
                        className="mx-auto mb-4 opacity-50"
                    />
                    <p>No research gaps identified yet.</p>
                    <p className="text-xs">
                        Complete the graph analysis phase to generate insights.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="animate-fade-in space-y-6">
            <header>
                <h1 className="text-3xl font-bold text-white mb-2">
                    Research Gaps
                </h1>
                <p className="text-muted-foreground">
                    High-potential areas for new contributions.
                </p>
            </header>

            <div className="grid gap-6">
                {gaps.map((gap, idx) => (
                    <div
                        key={idx}
                        className="card bg-bg-card border-border hover:border-primary/50 transition-all"
                    >
                        <div className="flex justify-between items-start mb-4">
                            <div>
                                <div className="flex items-center gap-3 mb-2">
                                    <span className="text-xs font-bold uppercase tracking-wider text-primary bg-primary/10 px-2 py-1 rounded">
                                        {gap.gap_id || `GAP-${idx + 1}`}
                                    </span>
                                    <span className="text-xs font-medium text-muted-foreground border border-border px-2 py-1 rounded capitalize">
                                        {gap.type || "Structural"}
                                    </span>
                                    {gap.confidence && (
                                        <span className="text-xs font-medium text-green-400 bg-green-500/10 px-2 py-1 rounded">
                                            {Math.round(gap.confidence * 100)}%
                                            Confidence
                                        </span>
                                    )}
                                </div>
                                <h3 className="text-xl font-bold text-white">
                                    {gap.description || "Unexplored Connection"}
                                </h3>
                            </div>

                            {/* HITL Controls (Placeholder for now) */}
                            <div className="flex gap-2">
                                <button
                                    className="p-2 hover:bg-green-500/20 text-muted-foreground hover:text-green-500 rounded-lg transition-colors"
                                    title="Mark Relevant"
                                >
                                    <ThumbsUp size={18} />
                                </button>
                                <button
                                    className="p-2 hover:bg-red-500/20 text-muted-foreground hover:text-red-500 rounded-lg transition-colors"
                                    title="Mark Irrelevant"
                                >
                                    <ThumbsDown size={18} />
                                </button>
                            </div>
                        </div>

                        <div className="grid md:grid-cols-2 gap-6 bg-bg-surface/50 rounded-lg p-4 mb-4">
                            <div>
                                <h4 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                                    <Check size={14} className="text-primary" />{" "}
                                    Rationale
                                </h4>
                                <p className="text-sm text-muted-foreground leading-relaxed">
                                    {gap.rationale ||
                                        "No detailed rationale provided."}
                                </p>
                            </div>
                            <div>
                                <h4 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                                    <ArrowRight
                                        size={14}
                                        className="text-primary"
                                    />{" "}
                                    Evidence
                                </h4>
                                <p className="text-sm text-muted-foreground leading-relaxed italic">
                                    "
                                    {gap.evidence ||
                                        "Derived from graph structural holes."}
                                    "
                                </p>
                            </div>
                        </div>

                        <div className="flex justify-end">
                            <button className="btn btn-secondary text-sm py-1.5 h-auto">
                                View Related Papers
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default ResearchGapsView;
