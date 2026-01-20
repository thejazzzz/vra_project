//vra_web/src/app/research/[id]/knowledge/page.tsx
"use client";

import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useResearchStore } from "@/lib/store";
import { graphApi } from "@/lib/api";
import { useMemo, useState, useRef, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, Info, X, Check } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { PaperLink } from "@/components/ui/paper-link";
import { ScopeGuardBanner } from "@/components/scope-guard-banner";
import { EpistemicBadge } from "@/components/epistemic-badge";
import { TrendChip } from "@/components/trend-chip";
import { useToast } from "@/components/ui/use-toast";

// Dynamic import for Force Graph (Client Side Only)
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
    ssr: false,
});

export default function KnowledgeGraphPage() {
    const { knowledgeGraph, query, currentStep } = useResearchStore();
    const { toast } = useToast();

    const [selectedNode, setSelectedNode] = useState<any>(null);
    const [searchTerm, setSearchTerm] = useState("");
    const [hasMatch, setHasMatch] = useState(false);
    const fgRef = useRef<any>(null);

    // Prepare Data
    const graphData = useMemo(() => {
        if (!knowledgeGraph?.nodes) return { nodes: [], links: [] };
        return {
            nodes: knowledgeGraph.nodes.map((n: any) => ({
                ...n,
                val: n.type === "concept" ? (n.paper_count || 1) * 2 : 1,
            })),
            links: knowledgeGraph.links || [],
        };
    }, [knowledgeGraph]);

    // Force Graph Configuration for Readability
    useEffect(() => {
        if (fgRef.current) {
            // Increase repulsion to reduce clustering
            fgRef.current.d3Force("charge").strength(-400);
            // Increase link distance to spread out connected nodes
            fgRef.current.d3Force("link").distance(70);
        }
    }, [graphData]); // Re-run when graph data loads

    const [contextLoading, setContextLoading] = useState(false);
    const [contextSnippets, setContextSnippets] = useState<
        Array<{ document: string; metadata?: { canonical_id?: string } }>
    >([]);

    // Fetch context on node selection
    useEffect(() => {
        if (selectedNode && selectedNode.type === "concept") {
            setContextLoading(true);
            const conceptId = selectedNode.label || selectedNode.id;
            graphApi
                .getConceptContext(conceptId)
                .then((res) => {
                    setContextSnippets(res.data.snippets || []);
                })
                .catch(() => setContextSnippets([]))
                .finally(() => setContextLoading(false));
        } else {
            setContextSnippets([]);
        }
    }, [selectedNode]);

    // Search Handler
    useEffect(() => {
        if (searchTerm && fgRef.current) {
            const node = graphData.nodes.find((n: any) =>
                (n.label || n.id)
                    .toLowerCase()
                    .includes(searchTerm.toLowerCase()),
            );

            // Explicitly track match status
            setHasMatch(!!node);

            if (node) {
                fgRef.current.centerAt(node.x, node.y, 1000);
                fgRef.current.zoom(3, 2000);
                setSelectedNode(node);
            }
        } else {
            setHasMatch(false);
        }
    }, [searchTerm, graphData]);

    const handleNodeClick = (node: any) => {
        setSelectedNode(node);
        fgRef.current?.centerAt(node.x, node.y, 1000);
        fgRef.current?.zoom(4, 2000);
    };

    const handleLinkClick = (link: any) => {
        setSelectedNode({ ...link, type: "link" }); // Treat link as node for panel
        // Center on link midpoint
        if (link.source.x != null && link.target.x != null) {
            const mx = (link.source.x + link.target.x) / 2;
            const my = (link.source.y + link.target.y) / 2;
            fgRef.current?.centerAt(mx, my, 1000);
            fgRef.current?.zoom(4, 2000);
        }
    };

    const params = useParams();
    const id = useMemo(() => {
        const rawId = params?.id;
        if (!rawId || typeof rawId !== "string") {
            return "";
        }
        try {
            return decodeURIComponent(rawId);
        } catch (error) {
            console.error("Failed to decode URL parameter:", error);
            return rawId; // Fallback to raw value
        }
    }, [params?.id]);

    const handleApprove = async () => {
        if (!id) return;
        try {
            // Phase 4: Validated Approval Trigger
            await graphApi.approve(id, "current-user"); // TODO: Use real user ID
            toast({
                title: "Graph Approved",
                description:
                    "This research run has been integrated into Global Memory.",
            });
        } catch (error) {
            console.error("Failed to approve graph:", error);
            toast({
                title: "Approval Failed",
                description: "Could not update global memory.",
                variant: "destructive",
            });
        }
    };

    // Derived Selection State
    const isLink = selectedNode?.type === "link";
    const selectionLabel = isLink
        ? `${selectedNode.source.label || selectedNode.source.id} → ${selectedNode.target.label || selectedNode.target.id}`
        : selectedNode?.label || selectedNode?.id;

    return (
        <div className="flex flex-col h-[calc(100vh-10rem)] gap-4 animate-in fade-in">
            {/* Phase 5: Scope Guard Banner */}
            <ScopeGuardBanner graph={knowledgeGraph} />

            <div className="flex flex-1 gap-4 overflow-hidden">
                {/* Graph Container */}
                <div className="flex-1 relative border rounded-xl overflow-hidden bg-zinc-950">
                    <div className="absolute top-4 left-4 z-10 w-72">
                        <div className="relative">
                            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                                suppressHydrationWarning
                                placeholder="Search concepts..."
                                className="pl-8 bg-background/80 backdrop-blur"
                                value={searchTerm}
                                onChange={(
                                    e: React.ChangeEvent<HTMLInputElement>,
                                ) => setSearchTerm(e.target.value)}
                            />
                            {searchTerm && !hasMatch && (
                                <div className="absolute right-3 top-2.5 text-xs text-red-500 font-medium">
                                    No match
                                </div>
                            )}
                        </div>
                    </div>

                    {currentStep === "awaiting_graph_review" && (
                        <div className="absolute bottom-4 right-4 z-10">
                            <Card className="p-4 bg-background/90 backdrop-blur border-primary/30 flex flex-col gap-2 shadow-xl">
                                <p className="text-sm font-semibold">
                                    Review Graph Structure
                                </p>
                                <Button
                                    onClick={handleApprove}
                                    size="sm"
                                    className="w-full"
                                >
                                    <Check className="mr-2 h-4 w-4" /> Approve &
                                    Continue
                                </Button>
                            </Card>
                        </div>
                    )}

                    <ForceGraph2D
                        ref={fgRef}
                        graphData={graphData}
                        nodeLabel="label"
                        nodeColor={(node: any) =>
                            node.type === "concept" ? "#3b82f6" : "#64748b"
                        }
                        nodeRelSize={6}
                        // Phase 5: Edge Styling (Research-Grade)
                        linkColor={(link: any) => {
                            if (
                                link.contested_count &&
                                link.contested_count > 0
                            )
                                return "#ef4444"; // Red for Contested
                            if (link.is_hypothesis) return "#f59e0b"; // Amber for Hypothesis
                            if (link.causal_strength === "causal")
                                return "#3b82f6"; // Blue for Causal
                            return "rgba(255,255,255,0.1)"; // Default
                        }}
                        linkLineDash={(link: any) =>
                            link.is_hypothesis ? [5, 5] : null
                        } // Dashed for Hypothesis
                        linkWidth={(link: any) =>
                            link.causal_strength === "causal" ? 2 : 1
                        }
                        linkDirectionalArrowLength={3.5}
                        linkDirectionalArrowRelPos={1}
                        backgroundColor="#09090b" // zinc-950
                        onNodeClick={handleNodeClick}
                        onLinkClick={handleLinkClick}
                        cooldownTicks={100}
                        nodeCanvasObject={(node: any, ctx, globalScale) => {
                            const label = node.label || node.id;
                            const fontSize = 12 / globalScale;
                            ctx.font = `${fontSize}px Sans-Serif`;
                            const textWidth = ctx.measureText(label).width;
                            const bckgDimensions = [textWidth, fontSize].map(
                                (n) => n + fontSize * 0.2,
                            ); // some padding

                            // Draw Node
                            const color =
                                node.type === "concept" ? "#3b82f6" : "#64748b";
                            ctx.fillStyle = color;
                            ctx.beginPath();
                            ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false);
                            ctx.fill();

                            // Draw Text
                            ctx.textAlign = "center";
                            ctx.textBaseline = "middle";
                            ctx.fillStyle = "rgba(255, 255, 255, 0.8)";
                            ctx.fillText(label, node.x, node.y + 8);

                            node.__bckgDimensions = bckgDimensions; // to re-use in nodePointerAreaPaint
                        }}
                        nodePointerAreaPaint={(node: any, color, ctx) => {
                            ctx.fillStyle = color;
                            const bckgDimensions = node.__bckgDimensions;
                            bckgDimensions &&
                                ctx.fillRect(
                                    node.x - bckgDimensions[0] / 2,
                                    node.y - bckgDimensions[1] / 2,
                                    bckgDimensions[0],
                                    bckgDimensions[1],
                                );

                            // Also paint the node circle for pointer detection
                            ctx.beginPath();
                            ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false);
                            ctx.fill();
                        }}
                    />
                </div>

                {/* Side Panel */}
                <Card
                    className={`w-80 h-full flex flex-col transition-all duration-300 ${
                        selectedNode
                            ? "translate-x-0"
                            : "translate-x-full hidden"
                    }`}
                >
                    <div className="p-4 flex items-center justify-between border-b">
                        <h2
                            className="font-bold truncate pr-2"
                            title={selectionLabel}
                        >
                            {selectionLabel}
                        </h2>
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setSelectedNode(null)}
                        >
                            <X className="h-4 w-4" />
                        </Button>
                    </div>
                    <ScrollArea className="flex-1 p-4">
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <div className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">
                                    {selectedNode?.type || "Entity"}
                                </div>
                                {/* Trend Chip for Concepts */}
                                {selectedNode?.type === "concept" &&
                                    selectedNode.trend_state && (
                                        <TrendChip
                                            status={selectedNode.trend_state}
                                        />
                                    )}
                            </div>

                            {/* Epistemic Badges (Both Nodes and Links) */}
                            <EpistemicBadge
                                type={isLink ? "link" : "node"}
                                data={selectedNode}
                            />

                            {!isLink && (
                                <div className="space-y-2">
                                    <div className="flex justify-between text-sm py-2 border-b">
                                        <span className="text-muted-foreground">
                                            Mentions
                                        </span>
                                        <span className="font-medium">
                                            {selectedNode?.paper_count || 1}{" "}
                                            Papers
                                        </span>
                                    </div>
                                </div>
                            )}

                            {!isLink && (
                                <div className="bg-secondary/50 p-3 rounded-lg text-xs text-muted-foreground">
                                    <h4 className="font-semibold mb-2 flex items-center">
                                        <Info className="h-3 w-3 inline mr-1" />
                                        Evidence Context
                                    </h4>
                                    <div className="max-h-60 overflow-y-auto pr-2 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-muted-foreground/20 hover:[&::-webkit-scrollbar-thumb]:bg-muted-foreground/40">
                                        {contextLoading ? (
                                            <div className="text-center py-2">
                                                Loading context...
                                            </div>
                                        ) : contextSnippets.length > 0 ? (
                                            <ul className="space-y-3">
                                                {contextSnippets.map(
                                                    (snip, i) => (
                                                        <li
                                                            key={i}
                                                            className="leading-snug bg-background/50 p-2 rounded border border-border/50"
                                                        >
                                                            <p className="italic mb-1">
                                                                "
                                                                {snip.document.slice(
                                                                    0,
                                                                    150,
                                                                )}
                                                                ..."
                                                            </p>
                                                            {/* PROVENANCE FIX: Attribute Source */}
                                                            {snip.metadata
                                                                ?.canonical_id ? (
                                                                <div className="flex justify-end mt-1">
                                                                    <PaperLink
                                                                        paperId={
                                                                            snip
                                                                                .metadata
                                                                                .canonical_id
                                                                        }
                                                                        variant="inline"
                                                                        className="text-[10px]"
                                                                    />
                                                                </div>
                                                            ) : (
                                                                <span className="flex justify-end text-[10px] text-muted-foreground mt-1">
                                                                    — System
                                                                    Context
                                                                </span>
                                                            )}
                                                        </li>
                                                    ),
                                                )}
                                            </ul>
                                        ) : (
                                            <p>
                                                No direct context found in
                                                papers.
                                            </p>
                                        )}

                                        {/* FALSE AUTHORITY BADGE */}
                                        <div className="mt-4 pt-3 border-t border-border/50">
                                            <div className="text-[10px] text-muted-foreground flex gap-2 items-start bg-yellow-500/10 p-2 rounded">
                                                <Info className="h-3 w-3 shrink-0 translate-y-0.5 text-yellow-500" />
                                                <span>
                                                    Context snippets represent
                                                    retrieved evidence, not
                                                    system facts.
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </ScrollArea>
                </Card>
            </div>
        </div>
    );
}
