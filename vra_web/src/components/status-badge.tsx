import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
    status: string;
    className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
    let variant: "default" | "secondary" | "destructive" | "outline" =
        "outline";
    let colorClass = "";

    const nStatus = status?.toLowerCase() || "unknown";

    if (["completed", "stable", "verified"].includes(nStatus)) {
        variant = "default"; // Usually black/white, but we can override
        colorClass =
            "bg-green-500/10 text-green-500 border-green-500/20 hover:bg-green-500/20";
    } else if (["processing", "emerging", "active"].includes(nStatus)) {
        variant = "secondary";
        colorClass =
            "bg-blue-500/10 text-blue-500 border-blue-500/20 hover:bg-blue-500/20";
    } else if (["error", "saturated", "rejected"].includes(nStatus)) {
        variant = "destructive";
    } else if (["awaiting", "pending"].includes(nStatus)) {
        colorClass =
            "bg-yellow-500/10 text-yellow-500 border-yellow-500/20 hover:bg-yellow-500/20";
    }

    return (
        <Badge
            variant={variant}
            className={cn("capitalize", colorClass, className)}
        >
            {status?.replace(/_/g, " ") || "Unknown"}
        </Badge>
    );
}
