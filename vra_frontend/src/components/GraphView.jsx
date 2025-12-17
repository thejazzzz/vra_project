import { useRef, useEffect, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { graphApi } from "../api";

export default function GraphView({ query, onContinue }) {
    const [data, setData] = useState({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const fgRef = useRef();

    useEffect(() => {
        let isMounted = true;
        const fetchData = async () => {
            try {
                console.log("Fetching graph data for:", query);
                const res = await graphApi.getData(query);
                const rawData = res.data;
                console.log("Graph API RAW Response:", rawData);

                // Backend returns { knowledge_graph: { nodes: [...], links: [...] }, citation_graph: ... }
                const kg = rawData.knowledge_graph;

                if (kg && kg.nodes && Array.isArray(kg.nodes)) {
                    const links = kg.links || kg.edges || [];
                    console.log(
                        `Parsing: ${kg.nodes.length} nodes, ${links.length} links`
                    );

                    if (kg.nodes.length === 0) {
                        if (isMounted)
                            setError(
                                "No concepts found in the Knowledge Graph."
                            );
                    }

                    if (isMounted) {
                        setData({
                            nodes: kg.nodes.map((n) => ({
                                ...n,
                                id: n.id,
                                // Ensure we have a valid label for the name
                                label: n.label || n.id,
                                group: n.type,
                                val: 5, // Default radius size
                            })),
                            links: links.map((e) => ({
                                source: e.source,
                                target: e.target,
                                value: 1,
                            })),
                        });
                    }
                } else {
                    console.warn(
                        "Invalid Graph Data Structure - Missing 'knowledge_graph'",
                        rawData
                    );
                    if (isMounted)
                        setError("Received invalid graph data from backend.");
                }
            } catch (err) {
                console.error("Failed to load graph data", err);
                setError(err.message || "Failed to load graph data");
            } finally {
                if (isMounted) {
                    setLoading(false);
                }
            }
        };
        fetchData();
        return () => {
            isMounted = false;
        };
    }, [query]);

    // Function to render nodes with text labels permanently visible
    const renderNode = (node, ctx, globalScale) => {
        const label = node.label || node.id;
        const fontSize = 12 / globalScale;

        // Draw Node Circle
        const r = 5;
        ctx.beginPath();
        ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
        ctx.fillStyle =
            node.color || (node.group === "concept" ? "#4ac" : "#c4a");
        ctx.fill();

        // Draw Text Label
        if (globalScale > 0.5) {
            // Only show text when zoomed in a bit to avoid clutter
            ctx.font = `${fontSize}px Sans-Serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
            ctx.fillText(label, node.x, node.y + r + fontSize); // Draw below the node
        }
    };

    return (
        <div
            style={{
                width: "100%",
                height: "600px",
                position: "relative",
                border: "1px solid hsl(var(--border))",
                borderRadius: "1rem",
                overflow: "hidden",
                background: "hsl(var(--bg-app))",
            }}
        >
            {loading && (
                <div
                    style={{
                        position: "absolute",
                        top: "50%",
                        left: "50%",
                        transform: "translate(-50%, -50%)",
                        zIndex: 10,
                        background: "rgba(0,0,0,0.5)",
                        padding: "1rem",
                        borderRadius: "8px",
                    }}
                >
                    Loading Graph...
                </div>
            )}

            {error && !loading && (
                <div
                    style={{
                        position: "absolute",
                        top: "50%",
                        left: "50%",
                        transform: "translate(-50%, -50%)",
                        zIndex: 10,
                        color: "#ff6b6b",
                        background: "rgba(0,0,0,0.8)",
                        padding: "1rem",
                        borderRadius: "8px",
                    }}
                >
                    Error: {error}
                </div>
            )}

            {!loading && !error && (
                <ForceGraph2D
                    ref={fgRef}
                    graphData={data}
                    nodeAutoColorBy="group"
                    nodeCanvasObject={renderNode}
                    nodeCanvasObjectMode={() => "replace"} // We draw everything
                    width={undefined}
                    height={600}
                    backgroundColor="#0f172a" // Dark background explicit
                    linkColor={() => "rgba(255,255,255,0.2)"}
                    linkDirectionalArrowLength={3.5}
                    linkDirectionalArrowRelPos={1}
                />
            )}

            <div
                style={{
                    position: "absolute",
                    bottom: "1rem",
                    right: "1rem",
                    display: "flex",
                    gap: "0.5rem",
                    zIndex: 10,
                }}
            >
                <button className="btn btn-primary" onClick={onContinue}>
                    Confirm & Continue
                </button>
            </div>
        </div>
    );
}
