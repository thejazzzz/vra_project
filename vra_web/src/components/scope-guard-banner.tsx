import React from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertTriangle } from "lucide-react";
import { GraphNode, GraphLink } from "@/types";

interface ScopeGuardBannerProps {
    graph?: {
        nodes: GraphNode[];
        links: GraphLink[];
        graph?: {
            scope_limited?: boolean;
            meta?: any;
        };
    };
    reportStatus?: string;
}

export const ScopeGuardBanner: React.FC<ScopeGuardBannerProps> = ({
    graph,
    reportStatus,
}) => {
    // Check 1: Explicit Flag from Graph Builder (backend)
    const isLimited = graph?.graph?.scope_limited === true;

    // Check 2: Report Status from Analytics
    const isInsufficient = reportStatus === "INSUFFICIENT_DATA";

    if (!isLimited && !isInsufficient) return null;

    return (
        <Alert
            variant="destructive"
            className="mb-4 border-l-4 border-orange-500 bg-orange-50 dark:bg-orange-950/20"
        >
            <AlertTriangle className="h-5 w-5 text-orange-600 dark:text-orange-400" />
            <AlertTitle className="text-orange-800 dark:text-orange-300 font-semibold flex items-center gap-2">
                Research Scope Limited
                <span className="text-xs bg-orange-200 dark:bg-orange-900 px-2 py-0.5 rounded-full text-orange-800 dark:text-orange-200 uppercase tracking-wide">
                    Safety Guard Active
                </span>
            </AlertTitle>
            <AlertDescription className="text-orange-700 dark:text-orange-400 mt-2">
                <p className="mb-2">
                    This knowledge graph has insufficient evidence (
                    <b>{graph?.nodes?.length || 0} nodes</b>,{" "}
                    <b>{graph?.links?.length || 0} edges</b>) to support
                    high-confidence research claims.
                </p>
                <div className="flex flex-col gap-1 text-sm bg-white/50 dark:bg-black/20 p-2 rounded">
                    <strong>Constraints Applied:</strong>
                    <ul className="list-disc list-inside opacity-90">
                        <li>
                            Novelty & Conflict Analytics: <b>Disabled</b>
                        </li>
                        <li>
                            Report Generation: <b>Blocked</b>
                        </li>
                        <li>
                            Export: <b>Restricted</b>
                        </li>
                    </ul>
                </div>
            </AlertDescription>
        </Alert>
    );
};
