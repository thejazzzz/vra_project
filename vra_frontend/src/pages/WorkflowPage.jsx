//File: src/pages/WorkflowPage
import { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";
import { plannerApi, graphApi } from "../api";
import { Loader2, AlertCircle } from "lucide-react";
import PaperReview from "../components/PaperReview";
import GraphView from "../components/GraphView";
import ReportView from "../components/ReportView";

export default function WorkflowPage() {
    const { queryId } = useParams();
    if (!queryId) {
        return (
            <div
                className="container"
                style={{ textAlign: "center", marginTop: "4rem" }}
            >
                <AlertCircle
                    size={48}
                    color="red"
                    style={{ marginBottom: "1rem" }}
                />
                <h2>Invalid Request</h2>
                <p>No query ID provided in the URL.</p>
            </div>
        );
    }
    const decodedQuery = decodeURIComponent(queryId);
    const [status, setStatus] = useState(null);
    const [error, setError] = useState(null);
    const [papers, setPapers] = useState([]);

    const pollingRef = useRef(null);
    const papersFetchedRef = useRef(false);

    const fetchStatus = async () => {
        try {
            const res = await plannerApi.status(decodedQuery);
            setStatus(res.data);

            // If we need papers for the review step, we might need to fetch state fully
            // OR status endpoint should return papers.
            // plannerApi.status returns { current_step, papers_count, draft_report, error }
            // It does NOT return the list of papers.
            // We need to fetch the full state if in 'awaiting_research_review'
            // OR use /planner/plan (which returns state if already exists) to get papers.

            if (
                res.data.current_step === "awaiting_research_review" &&
                !papersFetchedRef.current
            ) {
                // Fetch full state - using /plan is safe as it returns existing state
                const planRes = await plannerApi.plan(decodedQuery);
                setPapers(planRes.data.state.collected_papers || []);
                papersFetchedRef.current = true;
            }
        } catch (err) {
            console.error("Polling error", err);
            // Don't set global error immediately on polling fail, might be transient
        }
    };

    useEffect(() => {
        fetchStatus(); // Initial fetch
        pollingRef.current = setInterval(fetchStatus, 2000); // Poll every 2s

        return () => clearInterval(pollingRef.current);
    }, [decodedQuery]);

    // Stop polling if completed or failed
    useEffect(() => {
        if (
            status?.current_step === "completed" ||
            status?.current_step === "failed" ||
            status?.error
        ) {
            clearInterval(pollingRef.current);
        }
        if (status?.error) {
            setError(status.error);
        }
    }, [status]);

    const handlePaperConfirm = async (selectedIds) => {
        try {
            setStatus((prev) => ({ ...prev, current_step: "processing" })); // Optimistic update
            await plannerApi.review({
                query: decodedQuery,
                selected_paper_ids: selectedIds,
            });
            // Polling will pick up new state
        } catch (err) {
            setError("Failed to submit paper review.");
            setStatus((prev) => ({
                ...prev,
                current_step: "awaiting_research_review",
            }));
            console.error(err);
        }
    };

    const handleGraphConfirm = async () => {
        try {
            await plannerApi.reviewGraph({
                query: decodedQuery,
                approved: true,
            });
        } catch (err) {
            setError("Failed to confirm graph.");
        }
    };

    // Render logic
    const step = status?.current_step;

    if (error) {
        return (
            <div
                className="container"
                style={{ textAlign: "center", marginTop: "4rem" }}
            >
                <AlertCircle
                    size={48}
                    color="red"
                    style={{ marginBottom: "1rem" }}
                />
                <h2>Something went wrong</h2>
                <p>{error}</p>
                <button
                    className="btn btn-secondary"
                    onClick={() => window.location.reload()}
                >
                    Retry
                </button>
            </div>
        );
    }

    if (!status) {
        return (
            <div
                className="container"
                style={{
                    display: "flex",
                    justifyContent: "center",
                    marginTop: "4rem",
                }}
            >
                <Loader2 className="spin" size={32} />
            </div>
        );
    }

    return (
        <div className="container" style={{ paddingBottom: "4rem" }}>
            {/* Progress Header */}
            <div
                style={{
                    margin: "2rem 0",
                    display: "flex",
                    gap: "1rem",
                    alignItems: "center",
                    fontSize: "0.9rem",
                    color: "hsl(var(--text-muted))",
                }}
            >
                <span
                    style={{
                        color:
                            step === "planning" || step === "researching"
                                ? "hsl(var(--primary))"
                                : "inherit",
                    }}
                >
                    Research
                </span>
                <span>→</span>
                <span
                    style={{
                        color:
                            step === "awaiting_research_review"
                                ? "hsl(var(--primary))"
                                : "inherit",
                        fontWeight:
                            step === "awaiting_research_review"
                                ? "bold"
                                : "normal",
                    }}
                >
                    Review Papers
                </span>
                <span>→</span>
                <span
                    style={{
                        color:
                            step && step.includes("analysis")
                                ? "hsl(var(--primary))"
                                : "inherit",
                    }}
                >
                    Analysis
                </span>
                <span>→</span>
                <span
                    style={{
                        color:
                            step === "awaiting_graph_review"
                                ? "hsl(var(--primary))"
                                : "inherit",
                    }}
                >
                    Graph
                </span>
                <span>→</span>
                <span
                    style={{
                        color:
                            step === "completed"
                                ? "hsl(var(--primary))"
                                : "inherit",
                    }}
                >
                    Report
                </span>
            </div>

            {/* Content Switch */}
            {(step === "planning" ||
                step === "researching" ||
                step === "processing") && (
                <div style={{ textAlign: "center", marginTop: "4rem" }}>
                    <Loader2
                        className="spin"
                        size={48}
                        color="hsl(var(--primary))"
                        style={{ margin: "0 auto 1rem" }}
                    />
                    <h2>AI Agent is working...</h2>
                    <p style={{ color: "hsl(var(--text-muted))" }}>
                        {step === "researching"
                            ? "Searching global databases for papers..."
                            : "Processing..."}
                    </p>
                </div>
            )}

            {step === "awaiting_research_review" && (
                <PaperReview papers={papers} onConfirm={handlePaperConfirm} />
            )}

            {(step === "awaiting_analysis" ||
                step === "analyzing" ||
                step === "awaiting_graphs") && (
                <div style={{ textAlign: "center", marginTop: "4rem" }}>
                    <Loader2
                        className="spin"
                        size={48}
                        color="hsl(var(--primary))"
                        style={{ margin: "0 auto 1rem" }}
                    />
                    <h2>Analyzing Research</h2>
                    <p>Extracting concepts and building knowledge graph...</p>
                </div>
            )}

            {step === "awaiting_graph_review" && (
                <div className="animate-fade-in">
                    <h2 style={{ marginBottom: "1rem" }}>Knowledge Graph</h2>
                    <GraphView
                        query={decodedQuery}
                        onContinue={handleGraphConfirm}
                    />
                </div>
            )}

            {step === "awaiting_gap_analysis" && (
                <div style={{ textAlign: "center", marginTop: "4rem" }}>
                    <Loader2
                        className="spin"
                        size={48}
                        color="hsl(var(--primary))"
                        style={{ margin: "0 auto 1rem" }}
                    />
                    <h2>Identifying Research Gaps</h2>
                </div>
            )}

            {(step === "awaiting_report" || step === "creating_report") && (
                <div style={{ textAlign: "center", marginTop: "4rem" }}>
                    <Loader2
                        className="spin"
                        size={48}
                        color="hsl(var(--primary))"
                        style={{ margin: "0 auto 1rem" }}
                    />
                    <h2>Writing Final Report</h2>
                </div>
            )}

            {(step === "completed" || step === "awaiting_final_review") && (
                <ReportView report={status.draft_report} query={decodedQuery} />
            )}
        </div>
    );
}
