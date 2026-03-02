"use client";

import dynamic from "next/dynamic";
import { useMemo, useRef, useState, useEffect } from "react";
import * as d3 from "d3";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
    ssr: false,
});

const CURRENT_YEAR = new Date().getFullYear();

export interface CitationGraphViewProps {
    graphData: { nodes: any[]; links: any[] };
    showCommunities: boolean;
    highlightBridges: boolean;
    highlightEmerging: boolean;
    sizeMode: "pagerank" | "age" | "default";
    onNodeSelect?: (node: any) => void;
    focusedCommunity?: string | number | null;
    searchMatchNodeId?: string | null;
}

export function CitationGraphView({
    graphData,
    showCommunities,
    highlightBridges,
    highlightEmerging,
    sizeMode,
    onNodeSelect,
    focusedCommunity,
    searchMatchNodeId,
}: CitationGraphViewProps) {
    const fgRef = useRef<any>(null);

    // Color scale for communities
    const colorScale = useMemo(() => d3.scaleOrdinal(d3.schemeCategory10), []);

    // Adjust forces to spread nodes nicely
    useEffect(() => {
        if (fgRef.current) {
            fgRef.current.d3Force("charge")?.strength(-150);
            fgRef.current.d3Force("link")?.distance(60);
        }
    }, [graphData]);

    const handleNodeClick = (node: any) => {
        if (onNodeSelect) {
            onNodeSelect(node);
        }
    };

    return (
        <ForceGraph2D
            ref={fgRef}
            graphData={graphData}
            cooldownTicks={100}
            backgroundColor="#09090b"
            onNodeClick={handleNodeClick}
            nodeLabel={(node: any) => {
                return `
                    <div style="background: rgba(0,0,0,0.8); padding: 8px; border-radius: 4px; border: 1px solid #333; font-family: sans-serif; font-size: 12px; max-width: 250px;">
                        <strong style="display:block; margin-bottom: 4px; color: #fff;">${node.title || node.id}</strong>
                        <div style="color: #bbb; display: grid; grid-template-columns: 1fr 1fr; gap: 4px;">
                            <span>Year: ${node.year || "N/A"}</span>
                            <span>Citations: ${node.citation_count || 0}</span>
                            <span>Community: ${node.community ?? "N/A"}</span>
                            <span>PageRank: ${(node.pagerank || 0).toFixed(4)}</span>
                            <span>Betweenness: ${(node.betweenness || 0).toFixed(4)}</span>
                            <span>Velocity: ${(node.citation_velocity || 0).toFixed(2)}</span>
                        </div>
                    </div>
                `;
            }}
            nodeCanvasObject={(node: any, ctx, globalScale) => {
                let size = 4;
                if (sizeMode === "pagerank") {
                    size = node.display_size || 4;
                } else if (sizeMode === "age") {
                    size =
                        ((node.pagerank || 0) * 100) /
                        Math.log1p(
                            Math.max(
                                CURRENT_YEAR - (node.year || CURRENT_YEAR - 1),
                                1,
                            ),
                        );
                    size = Math.max(3, size);
                }

                const isBridged = node.betweenness > 0.05; // threshold
                const isEmerging =
                    (node.citation_velocity || 0) > 2.0 &&
                    CURRENT_YEAR - (node.year || CURRENT_YEAR - 1) < 5;

                const isDimmed =
                    focusedCommunity !== null &&
                    focusedCommunity !== undefined &&
                    node.community !== focusedCommunity;

                ctx.beginPath();
                ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);

                if (showCommunities && node.community !== undefined) {
                    ctx.fillStyle = colorScale(node.community.toString());
                } else {
                    ctx.fillStyle = "#3b82f6";
                }

                if (isDimmed) {
                    // override fill with very low opacity
                    ctx.fillStyle = "rgba(100, 100, 100, 0.2)";
                }

                ctx.fill();

                // Draw outlines for special highlights
                if (
                    (highlightBridges && isBridged) ||
                    (highlightEmerging && isEmerging) ||
                    searchMatchNodeId === node.id
                ) {
                    ctx.lineWidth = 1.5 / globalScale;
                    if (searchMatchNodeId === node.id) {
                        ctx.strokeStyle = "#fff";
                        ctx.lineWidth = 3 / globalScale;
                    } else if (highlightBridges && isBridged) {
                        ctx.strokeStyle = "#FFD700"; // Gold
                    } else if (highlightEmerging && isEmerging) {
                        ctx.strokeStyle = "#10b981"; // Emerald green
                        // Glow effect using display_glow
                        ctx.shadowBlur = (node.display_glow || 2) * 2;
                        ctx.shadowColor = "#10b981";
                    }
                    ctx.stroke();
                    // Reset shadow for next node
                    ctx.shadowBlur = 0;
                }
            }}
            linkDirectionalArrowLength={3.5}
            linkDirectionalArrowRelPos={1}
            linkWidth={(link: any) => {
                const sourceDimmed =
                    focusedCommunity !== null &&
                    focusedCommunity !== undefined &&
                    link.source.community !== focusedCommunity;
                const targetDimmed =
                    focusedCommunity !== null &&
                    focusedCommunity !== undefined &&
                    link.target.community !== focusedCommunity;

                if (sourceDimmed && targetDimmed) return 0.5;
                if (
                    focusedCommunity !== null &&
                    focusedCommunity !== undefined &&
                    (!sourceDimmed || !targetDimmed)
                ) {
                    return 2;
                }
                return 1.2;
            }}
            linkColor={(link: any) => {
                const sourceDimmed =
                    focusedCommunity !== null &&
                    focusedCommunity !== undefined &&
                    link.source.community !== focusedCommunity;
                const targetDimmed =
                    focusedCommunity !== null &&
                    focusedCommunity !== undefined &&
                    link.target.community !== focusedCommunity;

                if (sourceDimmed && targetDimmed) {
                    return "rgba(255, 255, 255, 0.05)";
                }
                if (
                    focusedCommunity !== null &&
                    focusedCommunity !== undefined &&
                    (!sourceDimmed || !targetDimmed)
                ) {
                    return "rgba(255, 255, 255, 0.6)";
                }
                return "rgba(255, 255, 255, 0.35)"; // Increased default visibility
            }}
        />
    );
}
