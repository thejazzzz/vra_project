//vra_web/src/app/research/[id]/hypotheses/page.tsx
"use client";

import { useResearchStore } from "@/lib/store";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Check, AlertCircle, Lightbulb, Plus, Trash2 } from "lucide-react";
import { PaperLink } from "@/components/ui/paper-link";
import { extractPaperIds } from "@/lib/provenance-utils";
import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export default function HypothesesPage() {
    const { query, hypotheses, reviews, currentStep, submitHypothesisReview, isLoading } = useResearchStore();
    const [localHypotheses, setLocalHypotheses] = useState<any[]>([]);
    const hasInitialized = useRef(false);

    useEffect(() => {
        if (hypotheses && hypotheses.length > 0 && !hasInitialized.current) {
            setLocalHypotheses(structuredClone(hypotheses));
            hasInitialized.current = true;
        }
    }, [hypotheses]);

    const isReviewMode = currentStep === "awaiting_hypothesis_review";

    const getReview = (id: string) =>
        reviews?.find((r) => r.hypothesis_id === id);

    const handleUpdateStatement = (index: number, newStatement: string) => {
        const updated = [...localHypotheses];
        updated[index] = { ...updated[index], statement: newStatement };
        setLocalHypotheses(updated);
    };

    const handleDelete = (index: number) => {
        const updated = [...localHypotheses];
        updated.splice(index, 1);
        setLocalHypotheses(updated);
    };

    const handleAdd = () => {
        setLocalHypotheses([
            ...localHypotheses,
            {
                id: `HYP_${Math.random().toString(36).substring(2, 6).toUpperCase()}`,
                statement: "",
                novelty_score: 5,
                testability_score: 5,
                supporting_evidence: "Manually added by user.",
            },
        ]);
    };

    const handleApprove = async () => {
        try {
            await submitHypothesisReview({
                query: query,
                updated_hypotheses: localHypotheses,
                approved: true
            });
        } catch (error) {
            console.error("Failed to submit hypothesis review:", error);
            // TODO: Show user-facing error notification
        }
    };

    if (!hypotheses || hypotheses.length === 0) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                <Lightbulb className="mx-auto h-12 w-12 mb-4 opacity-50" />
                <h3 className="text-xl font-semibold">
                    Generating Hypotheses...
                </h3>
                <p>
                    Analyzing gaps and trends to formulate novel research
                    directions.
                </p>
            </div>
        );
    }

    return (
        <ScrollArea className="h-[calc(100vh-10rem)] pr-4">
            <div className="space-y-6 animate-in fade-in pb-10">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight">
                            Research Hypotheses
                        </h1>
                        <p className="text-muted-foreground">
                            Novel directions generated from identified gaps and
                            trends.
                        </p>
                    </div>
                    {isReviewMode && (
                        <div className="flex items-center gap-2">
                            <Button variant="outline" onClick={handleAdd}>
                                <Plus className="h-4 w-4 mr-2" />
                                Add Hypothesis
                            </Button>
                            <Button 
                                onClick={handleApprove} 
                                disabled={isLoading}
                                className="bg-primary text-primary-foreground"
                            >
                                {isLoading ? "Saving..." : "Approve & Proceed"}
                            </Button>
                        </div>
                    )}
                </div>

                <div className="grid gap-6">
                    {localHypotheses.map((hyp, index) => {
                        const review = getReview(hyp.id);
                        return (
                            <Card
                                key={hyp.id || index}
                                className="p-6 border-l-4 border-l-primary/50 relative overflow-hidden group"
                            >
                                <div className="flex justify-between items-start mb-4">
                                    <div className="flex items-center gap-2">
                                        <Badge variant="outline">
                                            {hyp.id}
                                        </Badge>
                                        <Badge
                                            variant="secondary"
                                            className="bg-blue-500/10 text-blue-500 hover:bg-blue-500/20"
                                        >
                                            Novelty: {hyp.novelty_score}/10
                                        </Badge>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {review && (
                                            <Badge
                                                variant={
                                                    review.score >= 7
                                                        ? "default"
                                                        : "destructive"
                                                }
                                            >
                                                Review Score: {review.score}/10
                                            </Badge>
                                        )}
                                        {isReviewMode && (
                                            <Button 
                                                variant="ghost" 
                                                size="icon" 
                                                className="text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                                                onClick={() => handleDelete(index)}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        )}
                                    </div>
                                </div>

                                {isReviewMode ? (
                                    <Textarea
                                        value={hyp.statement}
                                        onChange={(e) => handleUpdateStatement(index, e.target.value)}
                                        className="text-lg font-bold mb-3 italic resize-none"
                                        rows={2}
                                        placeholder="Enter hypothesis statement..."
                                    />
                                ) : (
                                    <h3 className="text-lg font-bold mb-3 italic">
                                        "{hyp.statement}"
                                    </h3>
                                )}

                                <div className="text-sm text-muted-foreground mb-4 bg-muted/50 p-3 rounded-md border">
                                    <strong className="text-foreground">
                                        Evidence Base:
                                    </strong>{" "}
                                    {(() => {
                                        const text =
                                            hyp.supporting_evidence || "";
                                        const ids = extractPaperIds(text);

                                        if (ids.length === 0) {
                                            return (
                                                <>
                                                    {text}
                                                    <span className="block mt-2 text-[10px] bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 px-2 py-1 rounded inline-block font-medium">
                                                        Conceptual Rationale (No
                                                        Direct Citation)
                                                    </span>
                                                </>
                                            );
                                        }

                                        const escapedIds = ids.map((id) =>
                                            id.replace(
                                                /[.*+?^${}()|[\]\\]/g,
                                                "\\$&"
                                            )
                                        );
                                        const splitRegex = new RegExp(
                                            `(${escapedIds.join("|")})`,
                                            "g"
                                        );
                                        const parts = text.split(splitRegex);

                                        return (
                                            <span>
                                                {parts.map((part: string, i: number) => {
                                                    if (ids.includes(part)) {
                                                        return (
                                                            <PaperLink
                                                                key={i}
                                                                paperId={part}
                                                                variant="inline"
                                                            />
                                                        );
                                                    }
                                                    return (
                                                        <span key={i}>
                                                            {part}
                                                        </span>
                                                    );
                                                })}
                                            </span>
                                        );
                                    })()}
                                </div>

                                {review && (
                                    <div className="mt-4 pt-4 border-t grid gap-4 md:grid-cols-2">
                                        <div className="text-sm">
                                            <strong className="text-red-400 flex items-center gap-1 mb-1">
                                                <AlertCircle className="h-3 w-3" />{" "}
                                                Critique
                                            </strong>
                                            <p className="opacity-90">
                                                {review.critique}
                                            </p>
                                        </div>
                                        <div className="text-sm">
                                            <strong className="text-green-400 flex items-center gap-1 mb-1">
                                                <Check className="h-3 w-3" />{" "}
                                                Suggestions
                                            </strong>
                                            <p className="opacity-90">
                                                {review.suggestions}
                                            </p>
                                        </div>
                                    </div>
                                )}
                            </Card>
                        );
                    })}
                </div>
            </div>
        </ScrollArea>
    );
}
