//File: src/pages/LandingPage.jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { plannerApi } from "../api";
import { Search, Sparkles } from "lucide-react";

export default function LandingPage() {
    const [query, setQuery] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setIsLoading(true);
        try {
            // Trigger the plan
            await plannerApi.plan(query);
            // Navigate to workflow page
            navigate(`/research/${encodeURIComponent(query)}`);
        } catch (error) {
            toast.error("Failed to start research. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div
            className="container"
            style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                alignItems: "center",
                paddingBottom: "10vh",
            }}
        >
            <div
                className="animate-fade-in"
                style={{
                    textAlign: "center",
                    width: "100%",
                    maxWidth: "600px",
                }}
            >
                <h1
                    style={{
                        fontSize: "3.5rem",
                        marginBottom: "1rem",
                        background:
                            "linear-gradient(135deg, hsl(var(--text-main)) 0%, hsl(var(--text-muted)) 100%)",
                        WebkitBackgroundClip: "text",
                        WebkitTextFillColor: "transparent",
                    }}
                >
                    What do you want to discover?
                </h1>

                <p
                    style={{
                        color: "hsl(var(--text-muted))",
                        fontSize: "1.125rem",
                        marginBottom: "2.5rem",
                    }}
                >
                    Automated deep research powered by multi-agent AI.
                </p>

                <form onSubmit={handleSearch} style={{ position: "relative" }}>
                    <div style={{ position: "relative" }}>
                        <Search
                            size={20}
                            style={{
                                position: "absolute",
                                left: "1.25rem",
                                top: "50%",
                                transform: "translateY(-50%)",
                                color: "hsl(var(--text-muted))",
                            }}
                        />
                        <input
                            id="search-input"
                            aria-label="Research query"
                            autoFocus
                            className="input"
                            style={{
                                paddingLeft: "3.5rem",
                                paddingRight: "8rem",
                                height: "3.5rem",
                                fontSize: "1.125rem",
                            }}
                            placeholder="e.g. Impact of AI on Radiology workflow"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            disabled={isLoading}
                        />{" "}
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={isLoading}
                            style={{
                                position: "absolute",
                                right: "0.5rem",
                                top: "0.5rem",
                                bottom: "0.5rem",
                                padding: "0 1.25rem",
                                fontSize: "0.9rem",
                            }}
                        >
                            {isLoading ? (
                                <span className="loader">Starting...</span> // Simple text loader for MVP
                            ) : (
                                <>
                                    Research <Sparkles size={16} />
                                </>
                            )}
                        </button>
                    </div>
                </form>

                <div
                    style={{
                        marginTop: "2rem",
                        display: "flex",
                        gap: "0.5rem",
                        justifyContent: "center",
                        flexWrap: "wrap",
                    }}
                >
                    {[
                        "CRISPR Applications",
                        "Quantum Computing Trends",
                        "Fusion Energy 2025",
                    ].map((tag) => (
                        <button
                            key={tag}
                            onClick={() => setQuery(tag)}
                            style={{
                                background: "hsla(var(--bg-surface))",
                                border: "1px solid hsla(var(--border))",
                                padding: "0.5rem 1rem",
                                borderRadius: "2rem",
                                color: "hsl(var(--text-muted))",
                                fontSize: "0.875rem",
                                cursor: "pointer",
                            }}
                        >
                            {tag}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}
