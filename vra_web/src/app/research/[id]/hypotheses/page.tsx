"use client";

import { useResearchStore } from "@/lib/store";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Check, AlertCircle, Lightbulb } from "lucide-react";

export default function HypothesesPage() {
    const { hypotheses, reviews } = useResearchStore();
    
    const getReview = (id: string) =>
        reviews?.find((r) => r.hypothesis_id === id);

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
            <div className="space-y-6 animate-in fade-in">
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
                </div>

                <div className="grid gap-6">
                    {hypotheses.map((hyp) => {
                        const review = getReview(hyp.id);
                        return (
                            <Card
                                key={hyp.id}
                                className="p-6 border-l-4 border-l-primary/50 relative overflow-hidden"
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
                                </div>

                                <h3 className="text-lg font-bold mb-3 italic">
                                    "{hyp.statement}"
                                </h3>

                                <p className="text-sm text-muted-foreground mb-4 bg-muted/50 p-3 rounded-md border">
                                    <strong className="text-foreground">
                                        Evidence Base:
                                    </strong>{" "}
                                    {hyp.supporting_evidence}
                                </p>

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
