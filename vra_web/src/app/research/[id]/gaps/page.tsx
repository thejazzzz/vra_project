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

export default function ResearchGapsPage() {
    const { gaps } = useResearchStore();

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
                                <p className="text-sm text-muted-foreground leading-relaxed italic border-l-2 pl-3">
                                    " "
                                    {typeof gap.evidence === "object" &&
                                    gap.evidence !== null &&
                                    !Array.isArray(gap.evidence)
                                        ? Object.entries(gap.evidence)
                                              .map(
                                                  ([k, v]) =>
                                                      `${k.replace(
                                                          /_/g,
                                                          " "
                                                      )}: ${
                                                          typeof v === "string"
                                                              ? v
                                                              : JSON.stringify(
                                                                    v
                                                                )
                                                      }`
                                              )
                                              .join(", ")
                                        : gap.evidence ||
                                          "Derived from graph structural holes."}
                                    " "
                                </p>
                            </div>
                        </CardContent>
                        <CardFooter className="justify-end border-t bg-secondary/10 py-3">
                            <Button
                                variant="link"
                                size="sm"
                                className="text-muted-foreground"
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
