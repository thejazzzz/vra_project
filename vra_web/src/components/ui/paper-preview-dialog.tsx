//vra_web/src/components/ui/paper-preview-dialog.tsx
"use client";

import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
    ExternalLink,
    AlertTriangle,
    ShieldCheck,
    FileText,
    Calendar,
    BarChart3,
    BookOpen,
} from "lucide-react"; // Added Icons
import { getPaperUrl, identifySourceType } from "@/lib/provenance-utils";
import { useResearchStore } from "@/lib/store";
import { Badge } from "@/components/ui/badge";

interface PaperPreviewDialogProps {
    paperId: string;
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
}

export function PaperPreviewDialog({
    paperId,
    isOpen,
    onOpenChange,
}: PaperPreviewDialogProps) {
    const { papers } = useResearchStore();
    const paper = papers.find(
        (p) =>
            p.canonical_id === paperId ||
            p.paper_id === paperId ||
            p.id === paperId,
    );

    // Fallbacks if paper not found in store (legacy behavior)
    const type = identifySourceType(paperId);
    const sourceUrl = getPaperUrl(paperId); // Fallback source URL

    // Metadata from store
    const pdfUrl =
        paper?.pdf_url || (paper?.metadata as any)?.openAccessPdf?.url;
    const citationCount =
        (paper?.metadata as any)?.citationCount || paper?.citation_count || 0;
    const year = paper?.year || (paper?.metadata as any)?.year;
    const abstract =
        paper?.summary || paper?.abstract || (paper?.metadata as any)?.abstract;
    const title = paper?.title || paperId;

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-2xl">
                <DialogHeader>
                    <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2 text-muted-foreground">
                            <ShieldCheck className="h-4 w-4 text-green-500" />
                            <span className="text-xs uppercase tracking-wider font-semibold">
                                Evidence Inspection
                            </span>
                        </div>

                        {/* Impact Badge */}
                        {citationCount > 100 && (
                            <Badge
                                variant="secondary"
                                className="bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100 border-amber-200 dark:border-amber-800 gap-1"
                            >
                                <BarChart3 className="h-3 w-3" />
                                High Impact
                            </Badge>
                        )}
                    </div>

                    <DialogTitle className="text-xl leading-tight pr-8">
                        {title}
                    </DialogTitle>

                    {/* Metadata Row */}
                    <div className="flex flex-wrap gap-2 mt-3 text-sm text-muted-foreground">
                        {/* Source Type */}
                        <div className="flex items-center gap-1.5 bg-secondary/50 px-2 py-1 rounded text-xs">
                            <BookOpen className="h-3 w-3" />
                            <span>{type}</span>
                        </div>

                        {/* Year */}
                        {year && (
                            <div className="flex items-center gap-1.5 bg-secondary/50 px-2 py-1 rounded text-xs">
                                <Calendar className="h-3 w-3" />
                                <span>{year}</span>
                            </div>
                        )}

                        {/* Citations */}
                        {citationCount > 0 && (
                            <div className="flex items-center gap-1.5 bg-secondary/50 px-2 py-1 rounded text-xs">
                                <BarChart3 className="h-3 w-3" />
                                <span>{citationCount} Citations</span>
                            </div>
                        )}
                    </div>
                </DialogHeader>

                {/* Abstract / Summary */}
                {abstract && (
                    <div className="my-2 p-4 rounded-md bg-muted/30 text-sm leading-relaxed max-h-60 overflow-y-auto border">
                        <p className="text-muted-foreground">{abstract}</p>
                    </div>
                )}

                {/* Disclaimer */}
                <div className="bg-amber-50 dark:bg-amber-950/30 p-4 rounded-md border border-amber-200 dark:border-amber-900/50 flex gap-3 mt-2">
                    <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0" />
                    <div className="space-y-1">
                        <h4 className="text-sm font-semibold text-amber-900 dark:text-amber-200">
                            Scientific Disclaimer
                        </h4>
                        <p className="text-xs text-amber-800 dark:text-amber-300 leading-relaxed">
                            This citation supports the claim but does not
                            establish causal proof. The system categorizes this
                            as retrieved evidence, not verified fact.
                        </p>
                    </div>
                </div>

                <DialogFooter className="sm:justify-between flex-row gap-2 mt-6">
                    <Button
                        type="button"
                        variant="ghost"
                        onClick={() => onOpenChange(false)}
                    >
                        Close
                    </Button>

                    <div className="flex gap-2">
                        {/* Source Link */}
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => window.open(sourceUrl, "_blank")}
                            disabled={!sourceUrl}
                            className="gap-2"
                        >
                            View Source
                            <ExternalLink className="h-4 w-4" />
                        </Button>

                        {/* PDF Button (Primary if available) */}
                        {pdfUrl ? (
                            <Button
                                type="button"
                                onClick={() => window.open(pdfUrl, "_blank")}
                                className="gap-2"
                            >
                                <FileText className="h-4 w-4" />
                                Open PDF
                            </Button>
                        ) : // Fallback if no PDF but we have a source URL, make Source primary?
                        // No, keep consistent layout.
                        null}
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
