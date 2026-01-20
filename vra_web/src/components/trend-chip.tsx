import React from "react";
import { Badge } from "@/components/ui/badge";
import {
    TrendingUp,
    TrendingDown,
    Anchor,
    RefreshCw,
    Sprout,
    HelpCircle,
} from "lucide-react";

export interface TrendChipProps {
    status?: string;
    showLabel?: boolean;
    className?: string;
}

export const TrendChip: React.FC<TrendChipProps> = ({
    status,
    showLabel = true,
    className,
}) => {
    if (!status) return null;

    const lowerStatus = status.toLowerCase();

    let variant: "default" | "secondary" | "destructive" | "outline" =
        "outline";
    let icon = <HelpCircle className="h-3 w-3" />;
    let label = status;
    let styleClass = "";

    switch (lowerStatus) {
        case "rising":
        case "growth":
            variant = "default";
            icon = <TrendingUp className="h-3 w-3" />;
            styleClass =
                "bg-green-600 hover:bg-green-700 text-white border-green-600";
            label = "Rising";
            break;
        case "stable":
            variant = "secondary";
            icon = <Anchor className="h-3 w-3" />;
            styleClass =
                "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300";
            label = "Stable";
            break;
        case "declining":
            variant = "secondary";
            icon = <TrendingDown className="h-3 w-3" />;
            styleClass =
                "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400";
            label = "Declining";
            break;
        case "reemerging":
        case "re-emerging":
            variant = "default";
            icon = <RefreshCw className="h-3 w-3 animate-spin-slow" />; // animate-spin-slow needs to exist or just static
            styleClass =
                "bg-orange-500 hover:bg-orange-600 text-white border-orange-500";
            label = "Re-emerging";
            break;
        case "emerging":
            variant = "outline";
            icon = <Sprout className="h-3 w-3" />;
            styleClass =
                "border-emerald-500 text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/20";
            label = "Emerging";
            break;
        default:
            // Generic fallback
            break;
    }

    return (
        <Badge
            variant={variant}
            className={`gap-1 ${styleClass} ${className || ""}`}
        >
            {icon}
            {showLabel && <span>{label}</span>}
        </Badge>
    );
};
