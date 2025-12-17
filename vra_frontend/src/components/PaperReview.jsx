//File: src/components/PaperReview.jsx
import { useState, useEffect } from "react";
import { CheckCircle, Circle, ExternalLink, X, BookOpen } from "lucide-react";

export default function PaperReview({ papers = [], onConfirm }) {
    const [selected, setSelected] = useState(new Set());
    const [expandedPaper, setExpandedPaper] = useState(null); // Paper to show in modal

    // Select all papers by default when papers change
    useEffect(() => {
        const newIds = new Set(papers.map((p) => p.canonical_id));
        setSelected((prev) => {
            if (
                prev.size === 0 ||
                prev.size !== newIds.size ||
                ![...prev].every((id) => newIds.has(id))
            ) {
                return newIds;
            }
            return prev;
        });
    }, [papers]);

    const toggle = (id) => {
        setSelected((prev) => {
            const next = new Set(prev);
            next.has(id) ? next.delete(id) : next.add(id);
            return next;
        });
    };

    const handleCardClick = (e, paper) => {
        // If clicking checkbox area or external link, don't open modal
        // But the checkbox is a separate clickable div.
        // We will make the text area trigger the modal.
        setExpandedPaper(paper);
    };

    return (
        <div
            className="animate-fade-in"
            style={{ width: "100%", maxWidth: "900px", margin: "0 auto" }}
        >
            {/* Header */}
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "2rem",
                }}
            >
                <div>
                    <h2>Review Sources</h2>
                    <p style={{ color: "hsl(var(--text-muted))" }}>
                        We found {papers.length} papers. Review details and
                        uncheck irrelevant ones.
                    </p>
                </div>
                <button
                    className="btn btn-primary"
                    onClick={() => onConfirm(Array.from(selected))}
                    disabled={selected.size === 0}
                >
                    Analyze {selected.size} Papers
                </button>
            </div>

            {/* Paper list */}
            <div style={{ display: "grid", gap: "1rem" }}>
                {papers.map((paper) => {
                    const isSelected = selected.has(paper.canonical_id);
                    return (
                        <div
                            key={paper.canonical_id}
                            className="card"
                            style={{
                                display: "flex",
                                gap: "1rem",
                                borderColor: isSelected
                                    ? "hsl(var(--primary))"
                                    : undefined,
                                opacity: isSelected ? 1 : 0.7,
                                position: "relative",
                            }}
                        >
                            {/* Checkbox (Clickable independent of modal) */}
                            <div
                                onClick={(e) => {
                                    e.stopPropagation();
                                    toggle(paper.canonical_id);
                                }}
                                style={{
                                    cursor: "pointer",
                                    paddingTop: "0.25rem",
                                    display: "flex",
                                    alignItems: "flex-start",
                                }}
                            >
                                {isSelected ? (
                                    <CheckCircle color="hsl(var(--primary))" />
                                ) : (
                                    <Circle color="hsl(var(--text-muted))" />
                                )}
                            </div>

                            {/* Content Area (Triggers Modal) */}
                            <div
                                style={{ flex: 1, cursor: "pointer" }}
                                onClick={(e) => handleCardClick(e, paper)}
                            >
                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        marginBottom: "0.5rem",
                                    }}
                                >
                                    <h3
                                        style={{
                                            fontSize: "1.1rem",
                                            margin: 0,
                                            fontWeight: 600,
                                        }}
                                    >
                                        {paper.title}
                                    </h3>
                                    <span
                                        style={{
                                            fontSize: "0.85rem",
                                            color: "hsl(var(--text-muted))",
                                            whiteSpace: "nowrap",
                                            marginLeft: "1rem",
                                        }}
                                    >
                                        {paper.year || "N/A"}
                                    </span>
                                </div>

                                <p
                                    style={{
                                        fontSize: "0.9rem",
                                        color: "hsl(var(--text-muted))",
                                        margin: 0,
                                        lineHeight: 1.5,
                                    }}
                                >
                                    {paper.abstract
                                        ? paper.abstract.length > 180
                                            ? paper.abstract.slice(0, 180) + "..."
                                            : paper.abstract
                                        : "No abstract available."}
                                    {paper.abstract && paper.abstract.length > 180 && (
                                        <span
                                            style={{
                                                color: "hsl(var(--primary))",
                                                marginLeft: "0.5rem",
                                                fontSize: "0.85rem",
                                                fontWeight: 500,
                                            }}
                                        >
                                            Read more
                                        </span>
                                    )}
                                </p>

                                <div
                                    style={{
                                        marginTop: "0.75rem",
                                        display: "flex",
                                        gap: "1rem",
                                        fontSize: "0.85rem",
                                        alignItems: "center",
                                    }}
                                >

                                    <span
                                        style={{
                                            background:
                                                "hsla(var(--bg-surface))",
                                            padding: "0.2rem 0.6rem",
                                            borderRadius: "4px",
                                            color: "hsl(var(--text-muted))",
                                        }}
                                    >
                                        Citations: {paper.citation_count || 0}
                                    </span>
                                    {paper.venue && (
                                        <span
                                            style={{
                                                color: "hsl(var(--text-muted))",
                                            }}
                                        >
                                            {paper.venue}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Modal */}
            {expandedPaper && (
                <div
                    style={{
                        position: "fixed",
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        background: "rgba(0,0,0,0.7)",
                        backdropFilter: "blur(5px)",
                        zIndex: 1000,
                        display: "flex",
                        justifyContent: "center",
                        alignItems: "center",
                        padding: "2rem",
                    }}
                    onClick={() => setExpandedPaper(null)} // Click outside to close
                >
                    <div
                        className="card"
                        style={{
                            width: "100%",
                            maxWidth: "800px",
                            maxHeight: "90vh",
                            overflowY: "auto",
                            position: "relative",
                            background: "hsl(var(--bg-card))",
                            boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
                        }}
                        onClick={(e) => e.stopPropagation()} // Don't close when clicking inside
                    >
                        <button
                            onClick={() => setExpandedPaper(null)}
                            style={{
                                position: "absolute",
                                top: "1rem",
                                right: "1rem",
                                background: "none",
                                border: "none",
                                cursor: "pointer",
                                color: "hsl(var(--text-muted))",
                            }}
                        >
                            <X size={24} />
                        </button>

                        <div style={{ paddingRight: "2rem" }}>
                            <h2
                                style={{
                                    fontSize: "1.5rem",
                                    marginBottom: "0.5rem",
                                    lineHeight: 1.3,
                                }}
                            >
                                {expandedPaper.title}
                            </h2>
                            <div
                                style={{
                                    display: "flex",
                                    gap: "1rem",
                                    color: "hsl(var(--text-muted))",
                                    fontSize: "0.9rem",
                                    marginBottom: "1.5rem",
                                }}
                            >
                                <span>{expandedPaper.year || "N/A"}</span>                                <span>•</span>
                                <span>
                                    {expandedPaper.authors
                                        ? expandedPaper.authors
                                              .map((a) => a.name)
                                              .join(", ")
                                        : "Unknown Authors"}
                                </span>
                                <span>•</span>
                                <span>
                                    {expandedPaper.venue || "Unknown Venue"}
                                </span>
                            </div>

                            <div style={{ marginBottom: "2rem" }}>
                                <h4
                                    style={{
                                        fontSize: "1rem",
                                        textTransform: "uppercase",
                                        letterSpacing: "0.05em",
                                        color: "hsl(var(--text-muted))",
                                        marginBottom: "0.5rem",
                                    }}
                                >
                                    Abstract
                                </h4>
                                <p
                                    style={{
                                        lineHeight: 1.7,
                                        fontSize: "1rem",
                                    }}
                                >
                                    {expandedPaper.abstract ||
                                        "No abstract available."}
                                </p>
                            </div>

                            <div style={{ display: "flex", gap: "1rem" }}>
                                <button
                                    className="btn btn-primary"
                                    onClick={() => {
                                        if (
                                            !selected.has(
                                                expandedPaper.canonical_id
                                            )
                                        )
                                            toggle(expandedPaper.canonical_id);
                                        setExpandedPaper(null);
                                    }}
                                >
                                    {selected.has(expandedPaper.canonical_id)
                                        ? "Keep Selected"
                                        : "Select This Paper"}
                                </button>

                                {expandedPaper.url && (
                                    <a
                                        href={expandedPaper.url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="btn btn-secondary"
                                        style={{ textDecoration: "none" }}
                                    >
                                        Open Original <ExternalLink size={16} />
                                    </a>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
