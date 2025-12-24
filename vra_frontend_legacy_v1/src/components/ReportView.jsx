//File: src/components/ReportView.jsx
import ReactMarkdown from "react-markdown";

export default function ReportView({ report, query }) {
    if (!report) return <div>No report generated yet.</div>;

    return (
        <div className="container" style={{ padding: "2rem 0" }}>
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "2rem",
                }}
            >
                <h1 style={{ fontSize: "2rem" }}>Research Report: {query}</h1>
                <button
                    className="btn btn-secondary"
                    onClick={() => window.print()}
                >
                    Print PDF
                </button>
            </div>

            <div
                className="card"
                style={{
                    background: "hsla(var(--bg-surface))",
                    padding: "3rem",
                    minHeight: "80vh",
                }}
            >
                <article
                    className="prose"
                    style={{ color: "hsl(var(--text-main))", maxWidth: "none" }}
                >
                    <ReactMarkdown>{report}</ReactMarkdown>
                </article>
            </div>
        </div>
    );
}
