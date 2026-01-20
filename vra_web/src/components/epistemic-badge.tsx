import React from "react";
import { Badge } from "@/components/ui/badge";
import {
    Sparkles,
    AlertTriangle,
    FlaskConical,
    ShieldCheck,
    Microscope,
} from "lucide-react";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";

export interface EpistemicProps {
    type: "node" | "link";
    data: any; // GraphNode or GraphLink
}

export const EpistemicBadge: React.FC<EpistemicProps> = ({ type, data }) => {
    if (!data) return null;

    const badges = [];

    // 1. Novelty (Links usually, but Nodes can have high novelty score too?)
    // Phase 4 Analytics puts novelty_score on Edges (Links)
    if (data.novelty_score && data.novelty_score > 50) {
        // Threshold verified in tests
        badges.push(
            <Badge
                key="novel"
                variant="outline"
                className="border-purple-500 text-purple-600 bg-purple-50 dark:bg-purple-900/20 gap-1"
            >
                <Sparkles className="h-3 w-3" />
                Novel Insight
            </Badge>,
        );
    }

    // 2. Contested (Memory Service)
    if (data.contested_count && data.contested_count > 0) {
        badges.push(
            <TooltipProvider key="contested">
                <Tooltip>
                    <TooltipTrigger>
                        <Badge variant="destructive" className="gap-1">
                            <AlertTriangle className="h-3 w-3" />
                            Contested
                        </Badge>
                    </TooltipTrigger>
                    <TooltipContent>
                        <p>
                            This relationship has been rejected by researchers{" "}
                            {data.contested_count} times.
                        </p>
                    </TooltipContent>
                </Tooltip>
            </TooltipProvider>,
        );
    }

    // 3. Hypothesis (Low Confidence / Speculative)
    if (data.is_hypothesis) {
        badges.push(
            <Badge
                key="hypo"
                variant="secondary"
                className="bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200 border-amber-200 gap-1"
            >
                <FlaskConical className="h-3 w-3" />
                Hypothesis
            </Badge>,
        );
    }

    // 4. Established (Longitudinal Memory)
    // Run count > 5 implies stability/consensus
    if (
        (data.run_count && data.run_count >= 5) ||
        (data.max_run_count && data.max_run_count >= 5)
    ) {
        badges.push(
            <Badge
                key="established"
                variant="secondary"
                className="bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200 gap-1"
            >
                <ShieldCheck className="h-3 w-3" />
                Established
            </Badge>,
        );
    }

    // 5. Causal (Strong assertion)
    if (data.causal_strength === "causal") {
        badges.push(
            <Badge
                key="causal"
                variant="outline"
                className="border-blue-500 text-blue-600 dark:text-blue-400 gap-1"
            >
                <Microscope className="h-3 w-3" />
                Causal
            </Badge>,
        );
    }

    if (badges.length === 0) return null;

    return <div className="flex flex-wrap gap-2 mt-2">{badges}</div>;
};
