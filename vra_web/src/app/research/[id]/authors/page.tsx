//vra_web/src/app/research/[id]/authors/page.tsx
"use client";

import dynamic from "next/dynamic";
import { useResearchStore } from "@/lib/store";
import { useMemo, useState, useRef, useCallback } from "react";
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription,
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
    Crown,
    Users,
    Award,
    AlertTriangle,
    Info,
    FileText,
    Share2,
    X,
} from "lucide-react";
import { PaperLink } from "@/components/ui/paper-link";
import { cn } from "@/lib/utils";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
    ssr: false,
});

interface SelectionState {
    type: "node" | "link";
    data: any;
    papers?: any[]; // Only for node
    neighbors?: any[]; // Only for node
    source?: string; // Only for link
    target?: string; // Only for link
}

export default function AuthorNetworkPage() {
    const { authorGraph, papers } = useResearchStore();
    const fgRef = useRef<any>(null);

    // Selection State
    const [selectedNode, setSelectedNode] = useState<any>(null);
    const [selectedLink, setSelectedLink] = useState<any>(null);

    // Graph Data Memoization
    const graphData = useMemo(() => {
        if (!authorGraph?.nodes) return { nodes: [], links: [] };
        return {
            nodes: authorGraph.nodes.map((n: any) => ({
                ...n,
                // Ensure name/id consistency
                label: n.id,
            })),
            links: (authorGraph.links || []).map((l: any) => ({
                ...l,
                // Ensure source/target are preserved
            })),
        };
    }, [authorGraph]);

    // Data Validity Signals
    const meta = authorGraph?.meta;
    const isGraphValid = meta?.edges_present === true;
    const metricsValid = meta?.metrics_valid === true;

    // Heuristic: Warn if connectivity is very sparse (less than 0.5 edges per node average)
    const lowConnectivity = useMemo(() => {
        if (!authorGraph?.nodes || !authorGraph?.links) return false;
        return (
            authorGraph.links.length > 0 &&
            authorGraph.links.length < authorGraph.nodes.length / 2
        );
    }, [authorGraph]);

    // Helper: Find papers for a specific author
    const getAuthorPapers = useCallback(
        (authorName: string) => {
            // Simple normalization match: exact or clean string
            const target = authorName.toLowerCase().replace(/\s+/g, " ").trim();
            return papers.filter((p) =>
                p.authors?.some((a) => {
                    const name = typeof a === "string" ? a : (a as any).name;
                    return (
                        name?.toLowerCase().replace(/\s+/g, " ").trim() ===
                        target
                    );
                })
            );
        },
        [papers]
    );

    // Helper: Safe node ID extraction handling D3 mutability
    const getNodeId = (node: any): string =>
        typeof node === "object" ? node.id : String(node);

    // Derived Selection Data
    const selectionDetails: SelectionState | null = useMemo(() => {
        if (selectedNode) {
            const authoredPapers = getAuthorPapers(selectedNode.id);
            // Find neighbors
            const neighbors = graphData.links.reduce(
                (acc: any[], link: any) => {
                    // Safe ID extraction
                    const sId = getNodeId(link.source);
                    const tId = getNodeId(link.target);

                    if (sId === selectedNode.id) acc.push({ id: tId, ...link });
                    if (tId === selectedNode.id) acc.push({ id: sId, ...link });
                    return acc;
                },
                []
            );

            return {
                type: "node",
                data: selectedNode,
                papers: authoredPapers,
                neighbors,
            };
        }
        if (selectedLink) {
            const sId = getNodeId(selectedLink.source);
            const tId = getNodeId(selectedLink.target);
            return {
                type: "link",
                data: selectedLink,
                source: sId,
                target: tId,
            };
        }
        return null;
    }, [selectedNode, selectedLink, graphData, getAuthorPapers]);

    // Handlers
    const handleNodeClick = (node: any) => {
        setSelectedLink(null);
        setSelectedNode(node);
        // Center view on node
        if (fgRef.current) {
            fgRef.current.centerAt(node.x, node.y, 1000);
            fgRef.current.zoom(3, 2000);
        }
    };

    const handleLinkClick = (link: any) => {
        setSelectedNode(null);
        setSelectedLink(link);
    };

    const handleBackgroundClick = () => {
        setSelectedNode(null);
        setSelectedLink(null);
    };

    const handleInfluencerClick = (authorId: string) => {
        // Find node in graph data
        const node = graphData.nodes.find((n) => n.id === authorId);
        if (node) handleNodeClick(node);
    };

    // Sorted Top Authors
    const topAuthors = useMemo(() => {
        if (!authorGraph?.nodes) return [];
        return [...authorGraph.nodes]
            .sort(
                (a: any, b: any) =>
                    (b.influence_score || 0) - (a.influence_score || 0)
            )
            .slice(0, 10);
    }, [authorGraph]);

    return (
        <div className="flex h-[calc(100vh-12rem)] gap-4 animate-in fade-in relative">
            {/* Main Graph Area */}
            <div className="flex-1 border rounded-xl overflow-hidden bg-zinc-950 relative flex flex-col">
                {/* Header / Legend */}
                <div className="absolute top-4 left-4 z-10 flex flex-col gap-2 pointer-events-none">
                    <div className="bg-background/80 backdrop-blur p-2 rounded-lg border w-fit pointer-events-auto">
                        <span className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                            <Users className="h-4 w-4" />
                            Collaboration Network
                        </span>
                    </div>
                </div>

                {/* Warnings / Banners */}
                <div className="absolute top-4 right-4 z-10 max-w-md flex flex-col gap-2 pointer-events-none">
                    {!isGraphValid &&
                        selectedNode === null &&
                        selectedLink === null && (
                            <Alert
                                variant="default"
                                className="bg-amber-950/50 border-amber-900 text-amber-200 pointer-events-auto"
                            >
                                <AlertTriangle className="h-4 w-4" />
                                <AlertTitle>Disconnected Graph</AlertTitle>
                                <AlertDescription className="text-xs">
                                    No co-authorship edges found within this
                                    paper set. Authors are displayed
                                    independently.
                                </AlertDescription>
                            </Alert>
                        )}
                    {isGraphValid && !metricsValid && (
                        <Alert
                            variant="default"
                            className="bg-blue-950/50 border-blue-900 text-blue-200 pointer-events-auto"
                        >
                            <Info className="h-4 w-4" />
                            <AlertTitle>Limited Data</AlertTitle>
                            <AlertDescription className="text-xs">
                                {meta?.warning ||
                                    "Influence scores are indicative only due to limited collaboration data."}
                            </AlertDescription>
                        </Alert>
                    )}
                    {lowConnectivity && metricsValid && (
                        <Alert
                            variant="default"
                            className="bg-zinc-800/80 border-zinc-700 text-zinc-300 pointer-events-auto"
                        >
                            <Info className="h-4 w-4" />
                            <AlertTitle>Sparse Network</AlertTitle>
                            <AlertDescription className="text-xs">
                                Collaboration network is sparse; influence
                                rankings may be unstable.
                            </AlertDescription>
                        </Alert>
                    )}
                </div>

                <ForceGraph2D
                    ref={fgRef}
                    graphData={graphData}
                    nodeLabel="id"
                    nodeColor={
                        (node: any) =>
                            node.id === selectedNode?.id
                                ? "#facc15" // Yellow selected
                                : "#a855f7" // Purple default
                    }
                    // Clamped scaling: (score * 3) + 4, max 20
                    nodeVal={(n: any) =>
                        Math.min((n.influence_score || 0) * 3 + 4, 20)
                    }
                    nodeRelSize={6}
                    linkColor={() => "rgba(255,255,255,0.15)"}
                    linkWidth={(link: any) =>
                        link.weight ? Math.sqrt(link.weight) : 1
                    }
                    // linkDirectionalParticles={(link: any) => selectedNode && (link.source.id === selectedNode.id || link.target.id === selectedNode.id) ? 2 : 0}
                    // linkDirectionalParticleSpeed={0.005}
                    backgroundColor="#09090b"
                    onNodeClick={handleNodeClick}
                    onLinkClick={handleLinkClick}
                    onBackgroundClick={handleBackgroundClick}
                    cooldownTicks={100}
                />
            </div>

            {/* Right Side Panel - Conditional: Details vs Key Influencers */}
            <Card className="w-80 flex flex-col h-full overflow-hidden shrink-0 transition-all duration-300">
                {selectionDetails ? (
                    // ---------------- DETAILS PANEL ----------------
                    <>
                        <CardHeader className="pb-2 bg-secondary/10 shrink-0 relative">
                            <button
                                onClick={() => {
                                    setSelectedNode(null);
                                    setSelectedLink(null);
                                }}
                                className="absolute right-4 top-4 hover:bg-secondary rounded-full p-1 transition-colors"
                            >
                                <X className="h-4 w-4 text-muted-foreground" />
                            </button>
                            <CardTitle className="text-base flex items-center gap-2 pr-6">
                                {selectionDetails.type === "node" ? (
                                    <>
                                        <Users className="h-4 w-4 text-primary" />{" "}
                                        Author Details
                                    </>
                                ) : (
                                    <>
                                        <Share2 className="h-4 w-4 text-primary" />{" "}
                                        Collaboration
                                    </>
                                )}
                            </CardTitle>
                        </CardHeader>
                        <ScrollArea className="flex-1">
                            <CardContent className="space-y-6 pt-4">
                                {selectionDetails.type === "node" && (
                                    <>
                                        <div>
                                            <h3 className="text-xl font-bold text-foreground mb-1">
                                                {selectionDetails.data.id}
                                            </h3>
                                            <div className="flex flex-wrap gap-2 mt-2">
                                                <Badge
                                                    variant="outline"
                                                    className="gap-1"
                                                >
                                                    <Award className="h-3 w-3" />
                                                    Base:{" "}
                                                    {selectionDetails.data
                                                        .paper_count || 0}
                                                </Badge>
                                                <Badge
                                                    variant="outline"
                                                    className="gap-1 cursor-help"
                                                    title="Influence is a heuristic metric combining publication volume and network connectivity. Scores are comparative, not absolute."
                                                >
                                                    <Crown className="h-3 w-3" />
                                                    Inf:{" "}
                                                    {(
                                                        selectionDetails.data
                                                            .influence_score ||
                                                        0
                                                    ).toFixed(2)}
                                                </Badge>
                                            </div>
                                        </div>

                                        {/* Paper List */}
                                        <div>
                                            <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                                                <FileText className="h-4 w-4 text-muted-foreground" />
                                                Authored Papers (
                                                {selectionDetails.papers
                                                    ?.length || 0}
                                                )
                                            </h4>
                                            {(selectionDetails.papers?.length ||
                                                0) > 0 ? (
                                                <div className="space-y-1">
                                                    {selectionDetails.papers?.map(
                                                        (p, idx) => (
                                                            <PaperLink
                                                                key={`${p.id}-${idx}`}
                                                                paperId={
                                                                    p.canonical_id ||
                                                                    p.id
                                                                }
                                                                variant="list-item"
                                                            >
                                                                {p.title}
                                                            </PaperLink>
                                                        )
                                                    )}
                                                </div>
                                            ) : (
                                                <div className="text-xs text-muted-foreground italic">
                                                    No papers found in active
                                                    session.
                                                </div>
                                            )}
                                        </div>

                                        {/* Neighbors */}
                                        <div>
                                            <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                                                <Share2 className="h-4 w-4 text-muted-foreground" />
                                                Collaborators (
                                                {
                                                    (
                                                        selectionDetails.neighbors ||
                                                        []
                                                    ).length
                                                }
                                                )
                                            </h4>
                                            <div className="flex flex-wrap gap-2">
                                                {selectionDetails.neighbors?.map(
                                                    (n: any, idx: number) => (
                                                        <Badge
                                                            key={`${n.id}-${idx}`}
                                                            variant="secondary"
                                                            className="cursor-pointer hover:bg-primary/20"
                                                            onClick={() =>
                                                                handleInfluencerClick(
                                                                    n.id
                                                                )
                                                            }
                                                        >
                                                            {n.id}
                                                        </Badge>
                                                    )
                                                )}
                                                {(selectionDetails.neighbors
                                                    ?.length || 0) === 0 && (
                                                    <span className="text-xs text-muted-foreground">
                                                        None found
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </>
                                )}

                                {selectionDetails.type === "link" && (
                                    <>
                                        <div className="flex items-center gap-2 justify-center py-4 bg-muted/20 rounded-lg">
                                            <span className="font-semibold text-sm">
                                                {selectionDetails.source}
                                            </span>
                                            <span className="text-muted-foreground">
                                                ↔
                                            </span>
                                            <span className="font-semibold text-sm">
                                                {selectionDetails.target}
                                            </span>
                                        </div>

                                        <div>
                                            <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                                                <FileText className="h-4 w-4 text-muted-foreground" />
                                                Shared Papers (
                                                {
                                                    (
                                                        selectionDetails.data
                                                            .shared_papers || []
                                                    ).length
                                                }
                                                )
                                            </h4>
                                            <div className="space-y-1">
                                                {(
                                                    selectionDetails.data
                                                        .shared_papers || []
                                                ).map(
                                                    (
                                                        pid: string,
                                                        idx: number
                                                    ) => (
                                                        <PaperLink
                                                            key={`${pid}-${idx}`}
                                                            paperId={pid}
                                                            variant="list-item"
                                                        />
                                                    )
                                                )}
                                            </div>
                                        </div>
                                    </>
                                )}
                            </CardContent>
                        </ScrollArea>
                    </>
                ) : (
                    // ---------------- KEY INFLUENCERS LIST ----------------
                    <>
                        <CardHeader className="pb-2 text-primary shrink-0">
                            <CardTitle className="flex items-center gap-2 text-lg">
                                <Crown className="text-yellow-500 h-5 w-5" />{" "}
                                Key Influencers
                            </CardTitle>
                        </CardHeader>
                        <ScrollArea className="flex-1 h-full">
                            <CardContent className="space-y-2 pt-0">
                                {topAuthors.map((author: any, idx: number) => (
                                    <div
                                        key={`${author.id}-${idx}`}
                                        onClick={() => handleNodeClick(author)}
                                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-secondary/50 transition-colors cursor-pointer group"
                                    >
                                        <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary shrink-0">
                                            {idx + 1}
                                        </div>
                                        <div className="min-w-0">
                                            <div className="text-sm font-medium leading-none truncate pr-2">
                                                {author.id}
                                            </div>
                                            <div className="text-xs text-muted-foreground flex items-center gap-2 mt-1">
                                                <span className="flex items-center gap-1">
                                                    <Award className="h-3 w-3" />
                                                    {(
                                                        author.influence_score ||
                                                        0
                                                    ).toFixed(2)}
                                                </span>
                                                <span className="w-1 h-1 rounded-full bg-muted-foreground/50" />
                                                <span className="text-[10px]">
                                                    {author.paper_count} papers
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                                {topAuthors.length === 0 && (
                                    <div className="text-center text-muted-foreground py-8 text-sm px-4">
                                        No metrics available. <br />
                                        <span className="text-xs opacity-70">
                                            Try adding more connected papers.
                                        </span>
                                    </div>
                                )}
                            </CardContent>
                        </ScrollArea>
                    </>
                )}
            </Card>
        </div>
    );
}
