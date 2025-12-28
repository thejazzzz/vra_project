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
import { ExternalLink, AlertTriangle, ShieldCheck } from "lucide-react";
import { getPaperUrl, identifySourceType } from "@/lib/provenance-utils";

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
    const type = identifySourceType(paperId);
    const url = getPaperUrl(paperId);

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <div className="flex items-center gap-2 text-muted-foreground mb-2">
                        <ShieldCheck className="h-4 w-4 text-green-500" />
                        <span className="text-xs uppercase tracking-wider font-semibold">
                            Evidence Inspection
                        </span>
                    </div>
                    <DialogTitle className="flex items-center gap-2 pr-8">
                        <span
                            className="truncate min-w-0 flex-1 max-w-[320px]"
                            title={paperId}
                        >
                            {paperId || "Unknown ID"}
                        </span>
                        {type && (
                            <span className="text-xs font-normal text-muted-foreground bg-secondary px-2 py-0.5 rounded-full border shrink-0">
                                {type}
                            </span>
                        )}
                    </DialogTitle>
                    <DialogDescription className="pt-2">
                        You are about to view an external source cited as
                        supporting evidence.
                    </DialogDescription>
                </DialogHeader>

                <div className="bg-amber-50 dark:bg-amber-950/30 p-4 rounded-md border border-amber-200 dark:border-amber-900/50 flex gap-3">
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

                <DialogFooter className="sm:justify-between flex-row gap-2 mt-4">
                    <Button
                        type="button"
                        variant="secondary"
                        onClick={() => onOpenChange(false)}
                    >
                        Close
                    </Button>
                    <Button
                        type="button"
                        onClick={() => {
                            if (url) {
                                window.open(url, "_blank");
                                onOpenChange(false);
                            }
                        }}
                        disabled={!url}
                        className="gap-2"
                    >
                        Open External Source
                        <ExternalLink className="h-4 w-4" />
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
