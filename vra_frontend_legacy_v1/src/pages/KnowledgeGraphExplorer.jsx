import React, { useState, useRef, useEffect, useMemo } from "react";
import ForceGraph2D from "react-force-graph-2d";
import useResearchStore from "../state/researchStore";
import { Search, Info, X } from "lucide-react";

const KnowledgeGraphExplorer = () => {
    const { knowledgeGraph, currentStep, submitGraphReview, query } =
        useResearchStore();
    const [selectedNode, setSelectedNode] = useState(null);
    const [searchTerm, setSearchTerm] = useState("");
    const fgRef = useRef();

    // Data Preparation
    const graphData = useMemo(() => {
        if (!knowledgeGraph?.nodes) return { nodes: [], links: [] };
        return {
            nodes: knowledgeGraph.nodes.map((n) => ({
                ...n,
                val: n.type === "concept" ? (n.paper_count ?? 1) * 2 : 1,
            })),
            links: knowledgeGraph.links || [],
        };
    }, [knowledgeGraph]);

    // Handle Search
    useEffect(() => {
        if (searchTerm && fgRef.current) {
            const node = graphData.nodes.find((n) =>
                (n.label || n.id)
                    .toLowerCase()
                    .includes(searchTerm.toLowerCase())
            );
            if (node && node.x !== undefined && node.y !== undefined) {
                fgRef.current.centerAt(node.x, node.y, 1000);
                fgRef.current.zoom(3, 2000);
                setSelectedNode(node);
            }
        }
    }, [searchTerm, graphData]);

    const handleNodeClick = (node) => {
        setSelectedNode(node);
        if (fgRef.current) {
            fgRef.current.centerAt(node.x, node.y, 1000);
            fgRef.current.zoom(4, 2000);
        }
    };

    const handleConfirmGraph = async () => {
        await submitGraphReview({ query, approved: true });
    };

    return (
        <div className="flex h-[calc(100vh-8rem)] gap-4 animate-fade-in">
            {/* Graph Area */}
            <div className="flex-1 card p-0 overflow-hidden relative border-border/50">
                <div className="absolute top-4 left-4 z-10 w-64">
                    <div className="relative">
                        <Search
                            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                            size={16}
                        />
                        <input
                            type="text"
                            placeholder="Search concepts..."
                            className="input pl-10 text-sm bg-bg-app/80 backdrop-blur"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                </div>

                <ForceGraph2D
                    ref={fgRef}
                    graphData={graphData}
                    nodeLabel="label"
                    nodeColor={(node) =>
                        node.type === "concept"
                            ? "hsl(210, 100%, 60%)"
                            : "hsl(220, 10%, 60%)"
                    }
                    nodeRelSize={6}
                    linkColor={() => "rgba(255,255,255,0.1)"}
                    backgroundColor="hsl(220, 30%, 8%)" // bg-app
                    onNodeClick={handleNodeClick}
                    cooldownTicks={100}
                />

                {/* HITL Confirm Button Overlay */}
                {currentStep === "awaiting_graph_review" && (
                    <div className="absolute bottom-4 right-4 z-10 flex gap-2">
                        <div className="bg-bg-app/90 backdrop-blur p-4 rounded-xl border border-primary/30 shadow-xl flex flex-col items-end">
                            <p className="text-sm font-medium text-white mb-2">
                                Review Graph Structure
                            </p>
                            <button
                                className="btn btn-primary btn-sm"
                                onClick={handleConfirmGraph}
                            >
                                Approve & Continue
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Side Panel */}
            <div
                className={`w-80 card flex flex-col transition-all duration-300 ${
                    selectedNode ? "translate-x-0" : "translate-x-full hidden"
                }`}
            >
                <div className="flex justify-between items-start mb-4">
                    <h2 className="text-xl font-bold text-white leading-tight">
                        {selectedNode?.label || selectedNode?.id}
                    </h2>
                    <button
                        onClick={() => setSelectedNode(null)}
                        className="text-muted-foreground hover:text-white"
                    >
                        <X size={20} />
                    </button>
                </div>

                <div className="space-y-4 flex-1 overflow-y-auto pr-2">
                    <div className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">
                        {selectedNode?.type || "Entity"}
                    </div>

                    <div className="space-y-2">
                        <div className="flex justify-between text-sm py-2 border-b border-border/50">
                            <span className="text-muted-foreground">
                                Mentions
                            </span>
                            <span className="text-white font-medium">
                                {selectedNode?.paper_count || 1} Papers
                            </span>
                        </div>
                        {/* Placeholder for more metrics if available in node data */}
                        {selectedNode?.relevance && (
                            <div className="flex justify-between text-sm py-2 border-b border-border/50">
                                <span className="text-muted-foreground">
                                    Relevance
                                </span>
                                <span className="text-white font-medium">
                                    {selectedNode.relevance}
                                </span>
                            </div>
                        )}
                    </div>

                    {selectedNode?.description && (
                        <div className="bg-primary/5 p-3 rounded-lg border border-primary/10">
                            <h4 className="text-primary text-sm font-medium mb-1 flex items-center gap-1">
                                <Info size={14} /> Description
                            </h4>
                            <p className="text-xs text-muted-foreground">
                                {selectedNode.description}
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default KnowledgeGraphExplorer;
