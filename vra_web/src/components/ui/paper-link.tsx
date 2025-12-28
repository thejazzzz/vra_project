//vra_web/src/components/ui/paper-link.tsx
"use client";

import { useUIStore } from "@/lib/ui-store";
import { FileText, ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface PaperLinkProps {
    paperId: string;
    variant?: "inline" | "badge" | "list-item";
    className?: string;
    children?: React.ReactNode;
}

export function PaperLink({
    paperId,
    variant = "inline",
    className,
    children,
}: PaperLinkProps) {
    // Safe store access
    const ui = useUIStore();
    const openPaperPreview = ui?.openPaperPreview;

    const handleClick = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (!paperId || !openPaperPreview) return; // Guard
        openPaperPreview(paperId);
    };

    if (!paperId) {
        return (
            <span
                className={cn(
                    "text-xs text-muted-foreground italic",
                    className
                )}
            >
                [missing source]
            </span>
        );
    }

    if (!openPaperPreview) {
        // Optional: Log missing handler
        // console.warn("PaperLink: openPaperPreview handler missing");
        return (
            <span
                className={cn(
                    "text-xs text-muted-foreground italic",
                    className
                )}
            >
                [preview unavailable]
            </span>
        );
    }

    return (
        <>
            {variant === "inline" && (
                <button
                    type="button"
                    onClick={handleClick}
                    className={cn(
                        "text-primary hover:underline font-mono inline-flex items-center gap-0.5 align-baseline cursor-pointer",
                        className
                    )}
                    title={`Inspect evidence: ${paperId}`}
                    aria-label={`Inspect evidence: ${paperId}`}
                >
                    {children || paperId}
                    <ArrowUpRight className="h-3 w-3 opacity-50" />
                </button>
            )}

            {variant === "badge" && (
                <button
                    type="button"
                    onClick={handleClick}
                    className={cn(
                        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-secondary text-secondary-foreground hover:bg-secondary/80 text-xs font-mono transition-colors border border-transparent hover:border-border cursor-pointer",
                        className
                    )}
                    title={`Inspect evidence: ${paperId}`}
                    aria-label={`Inspect evidence: ${paperId}`}
                >
                    <FileText className="h-3 w-3 text-muted-foreground" />
                    <span>{children || paperId}</span>
                </button>
            )}

            {variant === "list-item" && (
                <button
                    type="button"
                    onClick={handleClick}
                    className={cn(
                        "flex w-full items-center gap-2 p-1.5 rounded hover:bg-muted/50 group text-left transition-colors cursor-pointer",
                        className
                    )}
                    title={`Open paper ${paperId}`}
                    aria-label={`Open paper ${paperId}`}
                >
                    <FileText className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                    <span className="flex-1 font-mono text-xs text-muted-foreground group-hover:text-primary group-hover:underline truncate">
                        {children || paperId}
                    </span>
                    <ArrowUpRight className="h-3 w-3 opacity-0 group-hover:opacity-100 text-muted-foreground" />
                </button>
            )}
        </>
    );
}
