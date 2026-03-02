"use client";

import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export interface CitationIntelligencePanelProps {
    showCommunities: boolean;
    setShowCommunities: (v: boolean) => void;
    highlightBridges: boolean;
    setHighlightBridges: (v: boolean) => void;
    highlightEmerging: boolean;
    setHighlightEmerging: (v: boolean) => void;
    sizeMode: "pagerank" | "age" | "default";
    setSizeMode: (v: "pagerank" | "age" | "default") => void;
    emergingPapers: any[];
    onNodeSelect: (node: any) => void;
    focusedCommunity: string | number | null;
    setFocusedCommunity: (v: string | number | null) => void;
    communityStats: { id: string | number; count: number; avgPr: number }[];
}

export function CitationIntelligencePanel({
    showCommunities,
    setShowCommunities,
    highlightBridges,
    setHighlightBridges,
    highlightEmerging,
    setHighlightEmerging,
    sizeMode,
    setSizeMode,
    emergingPapers,
    onNodeSelect,
    focusedCommunity,
    setFocusedCommunity,
    communityStats,
}: CitationIntelligencePanelProps) {
    return (
        <Card className="w-80 h-full flex flex-col bg-zinc-950/50 border-l border-zinc-800 rounded-none rounded-r-xl">
            <div className="p-4 border-b border-zinc-800">
                <h2 className="font-bold text-lg text-primary">
                    Intelligence Controls
                </h2>
            </div>

            <ScrollArea className="flex-1 p-4">
                <div className="space-y-6">
                    {/* Visual Encoding Toggles */}
                    <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                            Metrics Overlay
                        </h3>

                        <div className="flex items-center justify-between">
                            <Label htmlFor="comm-toggle" className="text-sm">
                                Show Communities
                            </Label>
                            <Switch
                                id="comm-toggle"
                                checked={showCommunities}
                                onCheckedChange={setShowCommunities}
                            />
                        </div>

                        <div className="flex items-center justify-between">
                            <Label htmlFor="bridge-toggle" className="text-sm">
                                Highlight Bridges (Gold)
                            </Label>
                            <Switch
                                id="bridge-toggle"
                                checked={highlightBridges}
                                onCheckedChange={setHighlightBridges}
                            />
                        </div>

                        <div className="flex items-center justify-between">
                            <Label
                                htmlFor="emerging-toggle"
                                className="text-sm"
                            >
                                Highlight Emerging (Green)
                            </Label>
                            <Switch
                                id="emerging-toggle"
                                checked={highlightEmerging}
                                onCheckedChange={setHighlightEmerging}
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                            Node Sizing
                        </h3>
                        <div className="flex gap-2 text-xs">
                            <Button
                                size="sm"
                                variant={
                                    sizeMode === "default"
                                        ? "default"
                                        : "outline"
                                }
                                onClick={() => setSizeMode("default")}
                                className="flex-1 h-8"
                            >
                                Uniform
                            </Button>
                            <Button
                                size="sm"
                                variant={
                                    sizeMode === "pagerank"
                                        ? "default"
                                        : "outline"
                                }
                                onClick={() => setSizeMode("pagerank")}
                                className="flex-1 h-8"
                            >
                                PageRank
                            </Button>
                            <Button
                                size="sm"
                                variant={
                                    sizeMode === "age" ? "default" : "outline"
                                }
                                onClick={() => setSizeMode("age")}
                                className="flex-1 h-8"
                            >
                                Age-Norm
                            </Button>
                        </div>
                    </div>

                    {/* Community Exploration Phase 5 */}
                    {showCommunities && communityStats.length > 0 && (
                        <div className="space-y-3">
                            <div className="flex justify-between items-center">
                                <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                                    Clusters
                                </h3>
                                {focusedCommunity !== null && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-4 text-[10px] px-1"
                                        onClick={() =>
                                            setFocusedCommunity(null)
                                        }
                                    >
                                        Clear Focus
                                    </Button>
                                )}
                            </div>
                            <div className="flex flex-wrap gap-1">
                                {communityStats.slice(0, 10).map((c) => (
                                    <Badge
                                        key={c.id}
                                        className={`cursor-pointer text-xs ${focusedCommunity === c.id ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground hover:bg-secondary/80"}`}
                                        onClick={() =>
                                            setFocusedCommunity(
                                                c.id === focusedCommunity
                                                    ? null
                                                    : c.id,
                                            )
                                        }
                                    >
                                        C{c.id} ({c.count})
                                    </Badge>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Emerging Papers Phase 4 */}
                    {emergingPapers.length > 0 && (
                        <div className="space-y-3 pt-2 border-t border-zinc-800/50">
                            <h3 className="text-sm font-semibold text-emerald-500 uppercase tracking-wider">
                                Emerging Signals
                            </h3>
                            <ul className="space-y-2">
                                {emergingPapers.slice(0, 5).map((paper) => (
                                    <li
                                        key={paper.id}
                                        className="text-xs p-2 rounded bg-zinc-900 border border-zinc-800 cursor-pointer hover:border-emerald-500/50 transition-colors"
                                        onClick={() => onNodeSelect(paper)}
                                    >
                                        <div
                                            className="font-medium text-zinc-200 line-clamp-2"
                                            title={paper.title || paper.id}
                                        >
                                            {paper.title || paper.id}
                                        </div>
                                        <div className="flex justify-between mt-1 text-emerald-500/80">
                                            <span>
                                                v:{" "}
                                                {paper.citation_velocity?.toFixed(
                                                    1,
                                                ) || 0}
                                            </span>
                                            <span>
                                                Year: {paper.year || "N/A"}
                                            </span>
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            </ScrollArea>
        </Card>
    );
}
