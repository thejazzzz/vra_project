//vra_web/src/app/research/[id]/knowledge/page.tsx
"use client";

import dynamic from "next/dynamic";
import { useParams, useRouter } from "next/navigation";
import { useResearchStore } from "@/lib/store";
import { graphApi, plannerApi } from "@/lib/api";
import { useMemo, useState, useRef, useEffect, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
    Search,
    Info,
    X,
    Check,
    Loader2,
    Pencil,
    Plus,
    Trash2,
    GitBranch,
    ArrowLeft,
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { PaperLink } from "@/components/ui/paper-link";
import { ScopeGuardBanner } from "@/components/scope-guard-banner";
import { EpistemicBadge } from "@/components/epistemic-badge";
import { TrendChip } from "@/components/trend-chip";
import { useToast } from "@/components/ui/use-toast";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CitationGraphView } from "@/components/CitationGraphView";
import { CitationIntelligencePanel } from "@/components/CitationIntelligencePanel";

// Lightweight styled native select for dark UI (no extra shadcn dep needed)
const NativeSelect = ({
    value,
    onChange,
    options,
}: {
    value: string;
    onChange: (v: string) => void;
    options: string[];
}) => (
    <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-8 w-full rounded-md border border-input bg-background px-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
    >
        {options.map((o) => (
            <option key={o} value={o}>
                {o.replace(/_/g, " ")}
            </option>
        ))}
    </select>
);

// Dynamic import for Force Graph (Client Side Only)
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
    ssr: false,
});

const RELATION_OPTIONS = [
    "related_to",
    "extends",
    "used_in",
    "supports",
    "contradicts",
    "causes",
    "evaluates",
    "proposes",
    "depends_on",
    "improves",
];

const NODE_TYPE_OPTIONS = ["concept", "method", "dataset", "metric", "system"];

export default function KnowledgeGraphPage() {
    const { knowledgeGraph, citationGraph, query, currentStep, syncState } =
        useResearchStore();
    const { toast } = useToast();

    const [selectedNode, setSelectedNode] = useState<any>(null);
    const [searchTerm, setSearchTerm] = useState("");
    const [hasMatch, setHasMatch] = useState(false);
    const fgRef = useRef<any>(null);

    // ---------------------------------------------------------------
    //  EDIT MODE STATE
    // ---------------------------------------------------------------
    const [editMode, setEditMode] = useState(false);
    const [isEditing, setIsEditing] = useState(false);

    // -- Add Node form
    const [newNodeLabel, setNewNodeLabel] = useState("");
    const [newNodeType, setNewNodeType] = useState("concept");

    // -- Add Edge (draw mode): click source → click target
    const [drawEdgeMode, setDrawEdgeMode] = useState(false);
    const [pendingSource, setPendingSource] = useState<any>(null);
    const [newEdgeRelation, setNewEdgeRelation] = useState("related_to");

    // ---------------------------------------------------------------
    //  DERIVED GRAPH DATA
    // ---------------------------------------------------------------
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

    // ---------------------------------------------------------------
    //  CITATION GRAPH STATE
    // ---------------------------------------------------------------
    const [showCommunities, setShowCommunities] = useState(true);
    const [highlightBridges, setHighlightBridges] = useState(false);
    const [highlightEmerging, setHighlightEmerging] = useState(false);
    const [sizeMode, setSizeMode] = useState<"pagerank" | "age" | "default">(
        "pagerank",
    );
    const [focusedCommunity, setFocusedCommunity] = useState<
        string | number | null
    >(null);
    const [selectedCitationNode, setSelectedCitationNode] = useState<any>(null);

    const emergingPapers = useMemo(() => {
        if (!citationGraph?.nodes) return [];
        return citationGraph.nodes
            .filter(
                (n: any) =>
                    (n.citation_velocity || 0) > 2.0 &&
                    2025 - (n.year || 2024) < 5,
            )
            .sort(
                (a: any, b: any) =>
                    (b.citation_velocity || 0) - (a.citation_velocity || 0),
            );
    }, [citationGraph]);

    const communityStats = useMemo(() => {
        if (!citationGraph?.nodes) return [];
        const stats: Record<string, { count: number; prSum: number }> = {};
        citationGraph.nodes.forEach((n: any) => {
            if (n.community !== undefined) {
                const c = n.community.toString();
                if (!stats[c]) stats[c] = { count: 0, prSum: 0 };
                stats[c].count++;
                stats[c].prSum += n.pagerank || 0;
            }
        });
        return Object.entries(stats)
            .map(([communityId, data]) => ({
                id: communityId,
                count: data.count,
                avgPr: data.prSum / data.count,
            }))
            .sort((a, b) => b.count - a.count);
    }, [citationGraph]);

    // ---------------------------------------------------------------
    //  FORCE GRAPH CONFIG
    // ---------------------------------------------------------------
    useEffect(() => {
        if (fgRef.current) {
            fgRef.current.d3Force("charge").strength(-400);
            fgRef.current.d3Force("link").distance(70);
        }
    }, [graphData]);

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

    // ---------------------------------------------------------------
    //  SEARCH HANDLER
    // ---------------------------------------------------------------
    useEffect(() => {
        if (searchTerm && fgRef.current) {
            const node = graphData.nodes.find((n: any) =>
                (n.label || n.id)
                    .toLowerCase()
                    .includes(searchTerm.toLowerCase()),
            );
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

    // ---------------------------------------------------------------
    //  NODE / LINK CLICK HANDLERS
    // ---------------------------------------------------------------
    const handleNodeClick = (node: any) => {
        if (editMode && drawEdgeMode) {
            if (!pendingSource) {
                // First click: set source
                setPendingSource(node);
                setSelectedNode(node);
                toast({
                    title: "Source selected",
                    description: `Now click a target node to connect "${node.label || node.id}"`,
                });
            } else if (pendingSource.id !== node.id) {
                // Second click: add edge
                handleEditAction("add_edge", {
                    source: pendingSource.id,
                    target: node.id,
                    relation: newEdgeRelation,
                });
                setPendingSource(null);
                setDrawEdgeMode(false);
            }
            return;
        }
        // Normal mode
        setSelectedNode(node);
        fgRef.current?.centerAt(node.x, node.y, 1000);
        fgRef.current?.zoom(4, 2000);
    };

    const handleLinkClick = (link: any) => {
        setSelectedNode({ ...link, type: "link" });
        if (link.source.x != null && link.target.x != null) {
            const mx = (link.source.x + link.target.x) / 2;
            const my = (link.source.y + link.target.y) / 2;
            fgRef.current?.centerAt(mx, my, 1000);
            fgRef.current?.zoom(4, 2000);
        }
    };

    const handleAddNode = () => {
        if (!newNodeLabel.trim()) {
            toast({
                title: "Please enter a node label",
                description: "Type a concept name before adding.",
                variant: "destructive",
            });
            return;
        }
        handleEditAction("add_node", {
            node_id: newNodeLabel.trim().toLowerCase().replace(/\s+/g, "_"),
            node_label: newNodeLabel.trim(),
            node_type: newNodeType,
        });
        setNewNodeLabel("");
    };

    const handleDeleteNode = () => {
        if (!selectedNode?.id) return;
        handleEditAction("remove_node", { node_id: selectedNode.id });
        setSelectedNode(null);
    };

    const handleDeleteEdge = () => {
        if (!selectedNode) return;
        const src =
            typeof selectedNode.source === "object"
                ? selectedNode.source.id
                : selectedNode.source;
        const tgt =
            typeof selectedNode.target === "object"
                ? selectedNode.target.id
                : selectedNode.target;
        handleEditAction("remove_edge", { source: src, target: tgt });
        setSelectedNode(null);
    };

    // ---------------------------------------------------------------
    //  ROUTER & APPROVAL
    // ---------------------------------------------------------------
    const params = useParams();
    const router = useRouter();
    const id = useMemo(() => {
        const rawId = params?.id;
        if (!rawId || typeof rawId !== "string") return "";
        try {
            return decodeURIComponent(rawId);
        } catch {
            return rawId as string;
        }
    }, [params?.id]);

    // ---------------------------------------------------------------
    //  EDIT ACTION HANDLER
    // ---------------------------------------------------------------
    const handleEditAction = useCallback(
        async (action: string, payload: Record<string, any>) => {
            if (!id) return;
            setIsEditing(true);
            try {
                await graphApi.editGraph(id, { action, ...payload });
                await syncState(id);
                toast({
                    title: "Graph Updated ✓",
                    description: `Action: ${action.replace(/_/g, " ")}`,
                });
            } catch (e: any) {
                console.error("Graph edit failed:", e);
                toast({
                    title: "Edit Failed",
                    description:
                        e?.response?.data?.detail || "Could not apply edit.",
                    variant: "destructive",
                });
            } finally {
                setIsEditing(false);
            }
        },
        [id, syncState, toast],
    );

    const [isAdvancing, setIsAdvancing] = useState(false);

    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (isAdvancing && id) {
            interval = setInterval(() => syncState(id), 5000);
        }
        return () => clearInterval(interval);
    }, [isAdvancing, id, syncState]);

    useEffect(() => {
        if (!currentStep) return;
        const gapSteps = [
            "gap_analysis",
            "review_gaps",
            "awaiting_gap_review",
            "awaiting_hypothesis",
            "reviewing_hypotheses",
        ];
        const reportSteps = [
            "awaiting_report_start",
            "awaiting_report",
            "awaiting_final_review",
            "completed",
        ];
        if (gapSteps.includes(currentStep)) {
            router.push(`/research/${id}/gaps`);
        } else if (reportSteps.includes(currentStep)) {
            router.push(`/research/${id}/report`);
        }
    }, [currentStep, id, router]);

    const handleApprove = async () => {
        if (!id) return;
        setIsAdvancing(true);
        try {
            await graphApi.approve(id, "current-user");
            await plannerApi.continue(id);
            toast({
                title: "Graph Approved",
                description: "Research continuing to Gap Analysis...",
            });
        } catch (error) {
            console.error("Failed to approve graph:", error);
            setIsAdvancing(false);
            toast({
                title: "Approval Failed",
                description: "Could not update global memory.",
                variant: "destructive",
            });
        }
    };

    // ---------------------------------------------------------------
    //  DERIVED SELECTION STATE
    // ---------------------------------------------------------------
    const isLink = selectedNode?.type === "link";
    const selectionLabel = isLink
        ? `${selectedNode.source.label || selectedNode.source.id} → ${selectedNode.target.label || selectedNode.target.id}`
        : selectedNode?.label || selectedNode?.id;

    const isReviewStep = currentStep === "awaiting_graph_review";

    // ---------------------------------------------------------------
    //  NODE RENDERING (with pending source highlight)
    // ---------------------------------------------------------------
    const nodeCanvasObject = (
        node: any,
        ctx: CanvasRenderingContext2D,
        globalScale: number,
    ) => {
        const label = node.label || node.id;
        const fontSize = 12 / globalScale;
        ctx.font = `${fontSize}px Sans-Serif`;
        const textWidth = ctx.measureText(label).width;
        const bckgDimensions = [textWidth, fontSize].map(
            (n) => n + fontSize * 0.2,
        );

        const isPendingSource = pendingSource?.id === node.id;
        const isManual = node.is_manual;

        // Node colour
        let color = node.type === "concept" ? "#3b82f6" : "#64748b";
        if (isManual) color = "#10b981"; // emerald for manually added

        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false);
        ctx.fill();

        // Pending source: gold pulsing ring
        if (isPendingSource) {
            ctx.strokeStyle = "#f59e0b";
            ctx.lineWidth = 2.5;
            ctx.beginPath();
            ctx.arc(node.x, node.y, 9, 0, 2 * Math.PI, false);
            ctx.stroke();
        }

        // Manual node: green outline
        if (isManual && !isPendingSource) {
            ctx.strokeStyle = "#10b981";
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.arc(node.x, node.y, 7, 0, 2 * Math.PI, false);
            ctx.stroke();
        }

        // Label
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = "rgba(255, 255, 255, 0.8)";
        ctx.fillText(label, node.x, node.y + 8);

        node.__bckgDimensions = bckgDimensions;
    };

    // ---------------------------------------------------------------
    //  RENDER
    // ---------------------------------------------------------------
    return (
        <div className="flex flex-col h-[calc(100vh-10rem)] gap-4 animate-in fade-in relative">
            {/* Loading Overlay */}
            {isAdvancing && (
                <div className="absolute inset-0 z-50 bg-background/80 backdrop-blur-sm flex flex-col items-center justify-center text-center p-4">
                    <div className="bg-card border shadow-xl p-8 rounded-xl max-w-md w-full space-y-4">
                        <Loader2 className="h-10 w-10 animate-spin text-primary mx-auto" />
                        <div className="space-y-2">
                            <h3 className="font-semibold text-lg">
                                Analyzing Research Gaps
                            </h3>
                            <p className="text-sm text-muted-foreground">
                                The system is now running deep analysis on the
                                Knowledge Graph to find novel gaps and generate
                                hypotheses.
                            </p>
                            <p className="text-xs text-muted-foreground pt-2 font-mono">
                                Estimated time: 1-2 minutes
                            </p>
                        </div>
                    </div>
                </div>
            )}

            <ScopeGuardBanner graph={knowledgeGraph} />

            <Tabs
                defaultValue="knowledge"
                className="flex flex-col flex-1 overflow-hidden"
            >
                <TabsList className="w-full justify-start rounded-none border-b bg-transparent p-0 z-10 px-4">
                    <TabsTrigger
                        value="knowledge"
                        className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-6 font-semibold"
                    >
                        Knowledge Graph
                    </TabsTrigger>
                    <TabsTrigger
                        value="citation"
                        className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent px-6 font-semibold flex items-center gap-2"
                    >
                        Citation Intelligence
                        <span className="bg-primary/20 text-primary text-[10px] px-2 py-0.5 rounded-full font-bold">
                            BETA
                        </span>
                    </TabsTrigger>
                </TabsList>

                {/* --- KNOWLEDGE GRAPH TAB --- */}
                <TabsContent
                    value="knowledge"
                    className="flex-1 mt-0 gap-4 overflow-hidden outline-none data-[state=active]:flex pt-4"
                >
                    {/* Graph Container */}
                    <div className="flex-1 relative border rounded-xl overflow-hidden bg-zinc-950 flex flex-col">
                        {/* Search Bar */}
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

                        {/* Edit Mode Status Banner */}
                        {editMode && (
                            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10">
                                <div
                                    className={`px-4 py-2 rounded-full text-xs font-semibold flex items-center gap-2 shadow-lg border ${
                                        drawEdgeMode
                                            ? "bg-amber-500/20 border-amber-500/50 text-amber-400"
                                            : "bg-emerald-500/20 border-emerald-500/50 text-emerald-400"
                                    }`}
                                >
                                    {drawEdgeMode ? (
                                        <>
                                            <GitBranch className="h-3 w-3" />
                                            {pendingSource
                                                ? `Source: "${pendingSource.label || pendingSource.id}" — click target node`
                                                : "Draw Edge Mode — click source node"}
                                        </>
                                    ) : (
                                        <>
                                            <Pencil className="h-3 w-3" />
                                            Edit Mode Active — click nodes to
                                            select
                                        </>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Legend (bottom-left) */}
                        <div className="absolute bottom-4 left-4 z-10 text-[10px] text-muted-foreground flex flex-col gap-1 bg-black/60 p-2 rounded-lg border border-white/10">
                            <div className="flex items-center gap-1.5">
                                <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block" />{" "}
                                Auto-extracted
                            </div>
                            <div className="flex items-center gap-1.5">
                                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />{" "}
                                Manually added
                            </div>
                            <div className="flex items-center gap-1.5">
                                <span className="w-2.5 h-2.5 border border-amber-500 rounded-full inline-block" />{" "}
                                Hypothesis (low conf.)
                            </div>
                        </div>

                        {/* Review / Edit Control Card (bottom-right) */}
                        {isReviewStep && !isAdvancing && (
                            <div className="absolute bottom-4 right-4 z-10">
                                <Card className="p-4 bg-background/90 backdrop-blur border-primary/30 flex flex-col gap-3 shadow-xl w-72">
                                    <p className="text-sm font-semibold">
                                        Review Graph Structure
                                    </p>

                                    {/* Edit Mode Toggle */}
                                    <Button
                                        variant={
                                            editMode ? "secondary" : "outline"
                                        }
                                        size="sm"
                                        className="w-full"
                                        onClick={() => {
                                            setEditMode((v) => !v);
                                            setDrawEdgeMode(false);
                                            setPendingSource(null);
                                            setSelectedNode(null);
                                        }}
                                        disabled={isEditing}
                                    >
                                        {editMode ? (
                                            <>
                                                <X className="mr-2 h-4 w-4" />{" "}
                                                Exit Edit Mode
                                            </>
                                        ) : (
                                            <>
                                                <Pencil className="mr-2 h-4 w-4" />{" "}
                                                Edit Graph
                                            </>
                                        )}
                                    </Button>

                                    {/* Edit mode sub-controls */}
                                    {editMode && (
                                        <div className="flex flex-col gap-2 pt-1 border-t border-border/50">
                                            {/* ---- Add Node ---- */}
                                            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                                                Add Node
                                            </p>
                                            <Input
                                                placeholder="Node label..."
                                                value={newNodeLabel}
                                                onChange={(e) =>
                                                    setNewNodeLabel(
                                                        e.target.value,
                                                    )
                                                }
                                                className="h-8 text-sm"
                                                onKeyDown={(e) => {
                                                    if (e.key === "Enter")
                                                        handleAddNode();
                                                }}
                                            />
                                            <NativeSelect
                                                value={newNodeType}
                                                onChange={setNewNodeType}
                                                options={NODE_TYPE_OPTIONS}
                                            />
                                            <Button
                                                size="sm"
                                                className="w-full"
                                                onClick={handleAddNode}
                                                disabled={
                                                    isEditing ||
                                                    !newNodeLabel.trim()
                                                }
                                            >
                                                {isEditing ? (
                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                ) : (
                                                    <>
                                                        <Plus className="mr-2 h-4 w-4" />{" "}
                                                        Add Node
                                                    </>
                                                )}
                                            </Button>

                                            {/* ---- Draw Edge ---- */}
                                            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider pt-1 border-t border-border/50">
                                                Add Edge
                                            </p>
                                            <NativeSelect
                                                value={newEdgeRelation}
                                                onChange={setNewEdgeRelation}
                                                options={RELATION_OPTIONS}
                                            />
                                            <Button
                                                size="sm"
                                                variant={
                                                    drawEdgeMode
                                                        ? "secondary"
                                                        : "outline"
                                                }
                                                className="w-full"
                                                onClick={() => {
                                                    setDrawEdgeMode((v) => !v);
                                                    setPendingSource(null);
                                                }}
                                                disabled={isEditing}
                                            >
                                                {drawEdgeMode ? (
                                                    <>
                                                        <ArrowLeft className="mr-2 h-4 w-4" />{" "}
                                                        Cancel Draw
                                                    </>
                                                ) : (
                                                    <>
                                                        <GitBranch className="mr-2 h-4 w-4" />{" "}
                                                        Draw Edge
                                                    </>
                                                )}
                                            </Button>
                                        </div>
                                    )}

                                    {/* Approve Button */}
                                    <Button
                                        onClick={handleApprove}
                                        size="sm"
                                        className="w-full"
                                        disabled={isAdvancing}
                                    >
                                        <Check className="mr-2 h-4 w-4" />{" "}
                                        Approve & Continue
                                    </Button>
                                </Card>
                            </div>
                        )}

                        <ForceGraph2D
                            ref={fgRef}
                            graphData={graphData}
                            nodeLabel="label"
                            nodeColor={(node: any) =>
                                node.is_manual
                                    ? "#10b981"
                                    : node.type === "concept"
                                      ? "#3b82f6"
                                      : "#64748b"
                            }
                            nodeRelSize={6}
                            linkColor={(link: any) => {
                                if (
                                    link.contested_count &&
                                    link.contested_count > 0
                                )
                                    return "#ef4444";
                                if (link.is_hypothesis) return "#f59e0b";
                                if (link.is_manual) return "#10b981";
                                if (link.causal_strength === "causal")
                                    return "#3b82f6";
                                return "rgba(255,255,255,0.1)";
                            }}
                            linkLineDash={(link: any) =>
                                link.is_hypothesis ? [5, 5] : null
                            }
                            linkWidth={(link: any) =>
                                link.causal_strength === "causal" ? 2 : 1
                            }
                            linkDirectionalArrowLength={3.5}
                            linkDirectionalArrowRelPos={1}
                            backgroundColor="#09090b"
                            onNodeClick={handleNodeClick}
                            onLinkClick={handleLinkClick}
                            cooldownTicks={100}
                            nodeCanvasObject={nodeCanvasObject}
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
                                ctx.beginPath();
                                ctx.arc(
                                    node.x,
                                    node.y,
                                    5,
                                    0,
                                    2 * Math.PI,
                                    false,
                                );
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
                                    {selectedNode?.type === "concept" &&
                                        selectedNode.trend_state && (
                                            <TrendChip
                                                status={
                                                    selectedNode.trend_state
                                                }
                                            />
                                        )}
                                </div>

                                {/* Manual badge */}
                                {selectedNode?.is_manual && (
                                    <div className="flex items-center gap-1.5 text-xs text-emerald-500 bg-emerald-500/10 px-2 py-1 rounded">
                                        <Pencil className="h-3 w-3" />
                                        Manually added by reviewer
                                    </div>
                                )}

                                {/* Epistemic Badges */}
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

                                {/* ---- EDIT CONTROLS in side panel ---- */}
                                {editMode && isReviewStep && (
                                    <div className="pt-2 border-t border-border/50 space-y-2">
                                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                                            Edit Actions
                                        </p>
                                        {isLink ? (
                                            <Button
                                                variant="destructive"
                                                size="sm"
                                                className="w-full"
                                                onClick={handleDeleteEdge}
                                                disabled={isEditing}
                                            >
                                                {isEditing ? (
                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                ) : (
                                                    <>
                                                        <Trash2 className="mr-2 h-4 w-4" />{" "}
                                                        Delete Edge
                                                    </>
                                                )}
                                            </Button>
                                        ) : (
                                            <>
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    className="w-full"
                                                    onClick={() => {
                                                        setPendingSource(
                                                            selectedNode,
                                                        );
                                                        setDrawEdgeMode(true);
                                                        setSelectedNode(null);
                                                        toast({
                                                            title: "Source set",
                                                            description: `Now click target node to add "${newEdgeRelation}" edge`,
                                                        });
                                                    }}
                                                    disabled={isEditing}
                                                >
                                                    <GitBranch className="mr-2 h-4 w-4" />
                                                    Connect From Here
                                                </Button>
                                                <Button
                                                    variant="destructive"
                                                    size="sm"
                                                    className="w-full"
                                                    onClick={handleDeleteNode}
                                                    disabled={isEditing}
                                                >
                                                    {isEditing ? (
                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                    ) : (
                                                        <>
                                                            <Trash2 className="mr-2 h-4 w-4" />{" "}
                                                            Delete Node
                                                        </>
                                                    )}
                                                </Button>
                                            </>
                                        )}
                                    </div>
                                )}

                                {!isLink && (
                                    <div className="bg-secondary/50 p-3 rounded-lg text-xs text-muted-foreground">
                                        <h4 className="font-semibold mb-2 flex items-center">
                                            <Info className="h-3 w-3 inline mr-1" />
                                            Evidence Context
                                        </h4>
                                        <div className="mt-2">
                                            {contextLoading ? (
                                                <div className="text-center py-2">
                                                    Loading context...
                                                </div>
                                            ) : contextSnippets.length > 0 ? (
                                                <ScrollArea className="h-72 rounded-md border bg-background/40 p-1">
                                                    <ul className="space-y-3 p-2 pb-8">
                                                        {contextSnippets.map(
                                                            (snip, i) => (
                                                                <li
                                                                    key={i}
                                                                    className="leading-snug bg-background/80 p-3 rounded border border-border/50 shadow-sm relative"
                                                                >
                                                                    <p className="italic mb-2 text-[11px] text-foreground/90">
                                                                        "
                                                                        {snip.document.slice(
                                                                            0,
                                                                            200,
                                                                        )}
                                                                        ..."
                                                                    </p>
                                                                    <div className="flex justify-end pt-2 border-t border-dashed border-border/50">
                                                                        {snip
                                                                            .metadata
                                                                            ?.canonical_id ? (
                                                                            <PaperLink
                                                                                paperId={
                                                                                    snip
                                                                                        .metadata
                                                                                        .canonical_id
                                                                                }
                                                                                variant="inline"
                                                                                className="text-[10px] font-medium text-primary hover:text-primary/80 z-10 relative"
                                                                            />
                                                                        ) : (
                                                                            <span className="text-[10px] text-muted-foreground">
                                                                                —
                                                                                System
                                                                                Context
                                                                            </span>
                                                                        )}
                                                                    </div>
                                                                </li>
                                                            ),
                                                        )}
                                                    </ul>
                                                </ScrollArea>
                                            ) : (
                                                <p className="p-2 text-xs italic">
                                                    No direct context found in
                                                    papers.
                                                </p>
                                            )}
                                            <div className="mt-3 pt-2 border-t border-border/50">
                                                <div className="text-[10px] text-muted-foreground flex gap-2 items-start bg-yellow-500/10 p-2 rounded">
                                                    <Info className="h-3 w-3 shrink-0 translate-y-0.5 text-yellow-500" />
                                                    <span>
                                                        Context snippets
                                                        represent retrieved
                                                        evidence, not system
                                                        facts.
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </ScrollArea>
                    </Card>
                </TabsContent>

                {/* --- CITATION GRAPH TAB --- */}
                <TabsContent
                    value="citation"
                    className="flex-1 mt-0 outline-none data-[state=active]:flex bg-zinc-950 border rounded-xl overflow-hidden shadow mt-4"
                >
                    <div className="flex-1 relative overflow-hidden bg-black/20">
                        {!citationGraph?.nodes ||
                        citationGraph.nodes.length === 0 ? (
                            <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
                                No structural citation data extracted yet.
                            </div>
                        ) : (
                            <CitationGraphView
                                graphData={citationGraph}
                                showCommunities={showCommunities}
                                highlightBridges={highlightBridges}
                                highlightEmerging={highlightEmerging}
                                sizeMode={sizeMode}
                                onNodeSelect={(n) => {
                                    setSelectedCitationNode(n);
                                    if (
                                        n.community !== undefined &&
                                        showCommunities
                                    ) {
                                        setFocusedCommunity(n.community);
                                    }
                                }}
                                focusedCommunity={focusedCommunity}
                                searchMatchNodeId={selectedCitationNode?.id}
                            />
                        )}
                    </div>
                    <CitationIntelligencePanel
                        showCommunities={showCommunities}
                        setShowCommunities={setShowCommunities}
                        highlightBridges={highlightBridges}
                        setHighlightBridges={setHighlightBridges}
                        highlightEmerging={highlightEmerging}
                        setHighlightEmerging={setHighlightEmerging}
                        sizeMode={sizeMode}
                        setSizeMode={setSizeMode}
                        emergingPapers={emergingPapers}
                        onNodeSelect={(n) => setSelectedCitationNode(n)}
                        focusedCommunity={focusedCommunity}
                        setFocusedCommunity={setFocusedCommunity}
                        communityStats={communityStats}
                    />
                </TabsContent>
            </Tabs>
        </div>
    );
}
