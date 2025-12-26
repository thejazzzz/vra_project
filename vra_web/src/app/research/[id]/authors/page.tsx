"use client";

import dynamic from "next/dynamic";
import { useResearchStore } from "@/lib/store";
import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Crown, Users, Award } from "lucide-react";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
    ssr: false,
});

export default function AuthorNetworkPage() {
    const { authorGraph } = useResearchStore();

    const graphData = useMemo(() => {
        if (!authorGraph?.nodes) return { nodes: [], links: [] };
        return {
            nodes: authorGraph.nodes.map((n: any) => ({
                ...n,
                val: (n.influence_score || 0) * 10 + 2,
            })),
            links: authorGraph.links || [],
        };
    }, [authorGraph]);

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
        <div className="flex h-[calc(100vh-12rem)] gap-4 animate-in fade-in">
            <div className="flex-1 border rounded-xl overflow-hidden bg-zinc-950 relative">
                <div className="absolute top-4 left-4 z-10 bg-background/80 backdrop-blur p-2 rounded-lg border">
                    <span className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                        <Users className="h-4 w-4" />
                        Collaboration Network
                    </span>
                </div>
                <ForceGraph2D
                    graphData={graphData}
                    nodeLabel="id"
                    nodeColor={() => "#a855f7"} // Purple-500
                    nodeRelSize={6}
                    linkColor={() => "rgba(255,255,255,0.1)"}
                    backgroundColor="#09090b"
                />
            </div>

            <Card className="w-80 flex flex-col h-full overflow-hidden">
                <CardHeader className="pb-2 text-primary shrink-0">
                    <CardTitle className="flex items-center gap-2 text-lg">
                        <Crown className="text-yellow-500 h-5 w-5" /> Key
                        Influencers
                    </CardTitle>
                </CardHeader>
                <div className="flex-1 min-h-0 bg-transparent">
                    <ScrollArea className="h-full">
                        <CardContent className="space-y-2">
                            {topAuthors.map((author: any, idx: number) => (
                                <div
                                    key={author.id}
                                    className="flex items-center gap-3 p-2 rounded-lg hover:bg-secondary/50 transition-colors cursor-default group"
                                >
                                    <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary">
                                        {idx + 1}
                                    </div>
                                    <div>
                                        <div className="text-sm font-medium leading-none">
                                            {author.id}
                                        </div>
                                        <div className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                                            <Award className="h-3 w-3" />
                                            {(
                                                author.influence_score || 0
                                            ).toFixed(2)}
                                        </div>
                                    </div>
                                </div>
                            ))}
                            {topAuthors.length === 0 && (
                                <div className="text-center text-muted-foreground py-8 text-sm">
                                    No data available
                                </div>
                            )}
                        </CardContent>
                    </ScrollArea>
                </div>
            </Card>
        </div>
    );
}
