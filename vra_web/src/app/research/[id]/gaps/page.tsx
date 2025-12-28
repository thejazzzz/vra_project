//vra_web/src/app/research/[id]/gaps/page.tsx
"use client";

import { useResearchStore } from "@/lib/store";
import { ResearchGap } from "@/types";
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription,
    CardFooter,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ThumbsUp, ThumbsDown, Check, ArrowRight } from "lucide-react";
import { PaperLink } from "@/components/ui/paper-link";
import { isPaperId, extractPaperIds } from "@/lib/provenance-utils";

export default function ResearchGapsPage() {
    const { gaps } = useResearchStore();

    // Helper to render Evidence Value
    const renderEvidenceValue = (key: string, value: any) => {
        if (Array.isArray(value)) {
            return (
                <div className="flex flex-wrap gap-1 mt-1">
                    {value.map((v, i) => (
                        <span
                            key={i}
                            className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono"
                        >
                            {isPaperId(String(v)) ? (
                                <PaperLink
                                    paperId={String(v)}
                                    variant="inline"
                                />
                            ) : (
                                String(v)
                            )}
                        </span>
                    ))}
                </div>
            );
        }
        if (isPaperId(String(value))) {
            return (
                <PaperLink
                    paperId={String(value)}
                    variant="inline"
                    className="text-sm"
                />
            );
        }
        return <span className="text-foreground">{String(value)}</span>;
    };

    return (
        <div className="space-y-6 animate-in fade-in">
            <div className="flex flex-col gap-1">
                <h2 className="text-2xl font-bold tracking-tight">
                    Identified Research Gaps
                </h2>
                <p className="text-muted-foreground">
                    Structural holes and unexplored connections in the
                    literature.
                </p>
            </div>

            <div className="grid gap-6">
                {gaps?.map((gap: ResearchGap, idx: number) => (
                    <Card
                        key={idx}
                        className="bg-card/50 border-border/50 hover:border-primary/30 transition-all"
                    >
                        <CardHeader>
                            <div className="flex justify-between items-start gap-4">
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Badge
                                            variant="outline"
                                            className="text-primary border-primary/20"
                                        >
                                            {gap.gap_id || `GAP-${idx + 1}`}
                                        </Badge>
                                        <Badge
                                            variant="secondary"
                                            className="capitalize"
                                        >
                                            {gap.type || "Structural"}
                                        </Badge>
                                        {gap.confidence && (
                                            <span className="text-xs text-green-500 font-medium">
                                                {Math.round(
                                                    gap.confidence * 100
                                                )}
                                                % Confidence
                                            </span>
                                        )}
                                    </div>
                                    <CardTitle className="text-xl leading-tight">
                                        {gap.description ||
                                            "Unexplored Connection"}
                                    </CardTitle>
                                </div>
                                <div className="flex gap-1">
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="hover:text-green-500"
                                    >
                                        <ThumbsUp className="h-4 w-4" />
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="hover:text-red-500"
                                    >
                                        <ThumbsDown className="h-4 w-4" />
                                    </Button>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="grid md:grid-cols-2 gap-6">
                            <div className="space-y-2">
                                <h4 className="text-sm font-semibold flex items-center gap-2">
                                    <Check className="h-3 w-3 text-primary" />{" "}
                                    Rationale
                                </h4>
                                <p className="text-sm text-muted-foreground leading-relaxed">
                                    {gap.rationale ||
                                        "No detailed rationale provided."}
                                </p>
                            </div>
                            <div className="space-y-2">
                                <h4 className="text-sm font-semibold flex items-center gap-2">
                                    <ArrowRight className="h-3 w-3 text-primary" />{" "}
                                    Evidence
                                </h4>
                                <div className="bg-secondary/20 rounded-md p-3 text-sm border border-border/50">
                                    {/* PROVENANCE FIX: Structured List */}
                                    {typeof gap.evidence === "object" &&
                                    gap.evidence !== null ? (
                                        <ul className="space-y-2">
                                            {Object.entries(gap.evidence).map(
                                                ([key, val]) => (
                                                    <li
                                                        key={key}
                                                        className="flex flex-col"
                                                    >
                                                        <span className="text-[10px] uppercase text-muted-foreground font-semibold tracking-wider">
                                                            {key.replace(
                                                                /_/g,
                                                                " "
                                                            )}
                                                        </span>
                                                        <div className="text-sm">
                                                            {renderEvidenceValue(
                                                                key,
                                                                val
                                                            )}
                                                        </div>
                                                    </li>
                                                )
                                            )}
                                        </ul>
                                    ) : (
                                        <p className="italic text-muted-foreground">
                                            {gap.evidence ||
                                                "Derived from system analysis."}
                                        </p>
                                    )}
                                </div>
                            </div>
                        </CardContent>
                        <CardFooter className="justify-end border-t bg-secondary/10 py-3">
                            <Button
                                variant="link"
                                size="sm"
                                className="text-muted-foreground hover:text-primary transition-colors"
                                onClick={() => {
                                    // EXTRACT IDS using centralized utils
                                    const ids = extractPaperIds(gap.evidence);

                                    // Log to console
                                    console.info("Related papers:", ids);

                                    // Explicit failure-mode / status feedback
                                    alert(
                                        `Preview related evidence (filtering not yet applied)\n\nFound ${
                                            ids.length
                                        } papers linked in evidence:\n${ids.join(
                                            ", "
                                        )}`
                                    );
                                }}
                            >
                                View Related Papers
                            </Button>
                        </CardFooter>
                    </Card>
                ))}

                {(!gaps || gaps.length === 0) && (
                    <div className="text-center py-20 text-muted-foreground border rounded-xl border-dashed">
                        No gaps identified yet. Wait for graph analysis to
                        complete.
                    </div>
                )}
            </div>
        </div>
    );
}
