import React, { useMemo } from "react";
import ForceGraph2D from "react-force-graph-2d";
import useResearchStore from "../state/researchStore";
import { Users, Crown, Award } from "lucide-react";

const AuthorNetworkView = () => {
    const { authorGraph } = useResearchStore();

    const graphData = useMemo(() => {
        if (!authorGraph?.nodes) return { nodes: [], links: [] };
        return {
            nodes: authorGraph.nodes.map((n) => ({
                ...n,
                val: (n.influence_score || 0) * 5 + 2, // Scale node size by influence
            })),
            links: authorGraph.links || [],
        };
    }, [authorGraph]);

    const topAuthors = useMemo(() => {
        if (!authorGraph?.nodes) return [];
        return [...authorGraph.nodes]
            .sort((a, b) => (b.influence_score || 0) - (a.influence_score || 0))
            .slice(0, 5);
    }, [authorGraph]);

    return (
        <div className="flex h-[calc(100vh-8rem)] gap-4 animate-fade-in">
            {/* Graph */}
            <div className="flex-1 card p-0 overflow-hidden relative border-border/50">
                <div className="absolute top-4 left-4 z-10 bg-bg-app/80 backdrop-blur p-2 rounded-lg border border-border/50">
                    <span className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                        <Users size={16} />
                        Collaboration Network
                    </span>
                </div>

                <ForceGraph2D
                    graphData={graphData}
                    nodeLabel="id"
                    nodeColor={() => "hsl(270, 80%, 60%)"} // Purple
                    nodeRelSize={6}
                    linkColor={() => "rgba(255,255,255,0.1)"}
                    backgroundColor="hsl(220, 30%, 8%)"
                />
            </div>

            {/* Right Panel: Top Influencers */}
            <div className="w-80 card flex flex-col">
                <div className="mb-4 pb-4 border-b border-border/50">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <Crown className="text-yellow-500" size={20} />
                        Key Influencers
                    </h2>
                    <p className="text-xs text-muted-foreground mt-1">
                        Based on centrality and paper count.
                    </p>
                </div>

                <div className="space-y-3 overflow-y-auto">
                    {topAuthors.length === 0 ? (
                        <div className="text-sm text-muted-foreground text-center py-4">
                            No authors analyzed yet.
                        </div>
                    ) : (
                        topAuthors.map((author, idx) => (
                            <div
                                key={idx}
                                className="flex items-center gap-3 p-3 bg-bg-surface rounded-xl border border-border/50 hover:border-primary/30 transition-colors"
                            >
                                <div className="w-8 h-8 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center font-bold text-xs ring-1 ring-purple-500/30">
                                    {idx + 1}
                                </div>
                                <div>
                                    <div className="text-sm font-bold text-white">
                                        {author.id}
                                    </div>
                                    <div className="text-xs text-muted-foreground flex items-center gap-2 mt-0.5">
                                        <Award size={12} />
                                        Score:{" "}
                                        {(author.influence_score || 0).toFixed(
                                            2
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>

                <div className="mt-auto pt-4 border-t border-border/50">
                    <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                        <h4 className="text-red-400 text-xs font-bold mb-1">
                            Diversity Check
                        </h4>
                        <p className="text-xs text-muted-foreground">
                            {authorGraph?.graph?.diversity_index < 0.3
                                ? "Low author diversity detected. Risk of echo chamber."
                                : "Healthy author diversity observed."}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AuthorNetworkView;
