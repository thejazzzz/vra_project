"use client";

import { useUIStore } from "@/lib/ui-store";
import { PaperPreviewDialog } from "@/components/ui/paper-preview-dialog";

export function GlobalPaperDialog() {
    const { previewPaperId, closePaperPreview } = useUIStore();

    return (
        <PaperPreviewDialog
            paperId={previewPaperId || ""}
            isOpen={!!previewPaperId}
            onOpenChange={(open) => {
                if (!open) closePaperPreview();
            }}
        />
    );
}
