//File: src/components/Navbar.jsx
import { BrainCircuit } from "lucide-react";
import { Link } from "react-router-dom";

export default function Navbar() {
    return (
        <nav
            style={{
                borderBottom: "1px solid hsl(var(--border))",
                padding: "1rem 2rem",
                background: "hsla(var(--bg-app) / 0.8)",
                backdropFilter: "blur(var(--blur))",
                position: "sticky",
                top: 0,
                zIndex: 100,
            }}
        >
            <div
                className="container"
                style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                }}
            >
                <Link
                    to="/"
                    style={{
                        textDecoration: "none",
                        color: "inherit",
                        display: "flex",
                        alignItems: "center",
                        gap: "0.75rem",
                    }}
                >
                    <BrainCircuit size={32} color="hsl(var(--primary))" />
                    <span
                        style={{
                            fontSize: "1.25rem",
                            fontWeight: "bold",
                            letterSpacing: "-0.01em",
                        }}
                    >
                        VRA{" "}
                        <span style={{ opacity: 0.5, fontWeight: 400 }}>
                            Research Assistant
                        </span>
                    </span>
                </Link>

                <div style={{ display: "flex", gap: "1rem" }}>
                    {/* Future: User Profile */}
                    <div
                        style={{
                            width: 32,
                            height: 32,
                            borderRadius: "50%",
                            background: "hsl(var(--bg-surface))",
                        }}
                    ></div>
                </div>
            </div>
        </nav>
    );
}
