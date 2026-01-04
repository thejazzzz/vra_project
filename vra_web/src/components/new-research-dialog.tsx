"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { plannerApi } from "@/lib/api";
import { Loader2, Plus } from "lucide-react";
import { AudienceSelector } from "./audience-selector";
import { LocalPaperUpload } from "./local-paper-upload";
import { LocalPaperList } from "./local-paper-list";
import { LocalPaper, UploadPaperResponse } from "@/types";

export function NewResearchDialog({
    children,
}: {
    children?: React.ReactNode;
}) {
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState("");
    const [audience, setAudience] = useState("general");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [localPapers, setLocalPapers] = useState<LocalPaper[]>([]);
    const router = useRouter();

    const handleStart = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setError(null);
        try {
            // Collect included paper IDs
            const includeIds = localPapers
                .filter((p) => p.included)
                .map((p) => String(p.paper_id));

            const response = await plannerApi.plan(query, includeIds, audience);
            // Redirect to the new research session
            if (response.session_id) {
                setOpen(false); // Only close on success
                router.push(`/research/${response.session_id}`);
            } else {
                console.error("No session ID returned", response);
                setError("Failed to start session: No ID returned.");
            }
        } catch (err: any) {
            console.error("Failed to start research", err);
            const detail = err.response?.data?.detail;
            let errorMessage = "Failed to start research. Please try again.";

            if (detail) {
                if (Array.isArray(detail)) {
                    if (detail.length > 0) {
                        errorMessage = detail
                            .map((e: any) => e.msg || JSON.stringify(e))
                            .join("; ");
                    }
                    // else: length 0 array -> keep default errorMessage
                } else if (typeof detail === "string") {
                    errorMessage = detail;
                } else {
                    errorMessage = JSON.stringify(detail);
                }
            }
            setError(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    const handleUploadSuccess = (paper: UploadPaperResponse) => {
        setLocalPapers((prev) => [
            ...prev,
            {
                paper_id: String(paper.paper_id), // Ensure string
                canonical_id: paper.canonical_id,
                title: paper.title,
                source: paper.source,
                included: true,
            },
        ]);
    };

    const handleTogglePaper = (id: string, checked: boolean) => {
        setLocalPapers((prev) =>
            prev.map((p) =>
                p.canonical_id === id ? { ...p, included: checked } : p
            )
        );
    };

    const handleRemovePaper = (id: string) => {
        setLocalPapers((prev) => prev.filter((p) => p.canonical_id !== id));
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                {children || (
                    <Button className="gap-2">
                        <Plus className="h-4 w-4" /> New Research
                    </Button>
                )}
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
                <form onSubmit={handleStart}>
                    <DialogHeader>
                        <DialogTitle>Start New Research</DialogTitle>
                        <DialogDescription>
                            Enter your research topic or question to begin a new
                            session.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        {error && (
                            <div className="text-sm text-red-500 font-medium px-1">
                                {error}
                            </div>
                        )}
                        <div className="grid grid-cols-4 items-center gap-4">
                            <Label htmlFor="query" className="text-right">
                                Topic
                            </Label>
                            <Input
                                id="query"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="e.g. Battery optimization for EV"
                                className="col-span-3"
                                autoFocus
                            />
                        </div>

                        <AudienceSelector
                            audience={audience}
                            setAudience={setAudience}
                        />

                        <div className="grid grid-cols-4 items-start gap-4">
                            <Label className="text-right pt-2">
                                Local Docs
                            </Label>
                            <div className="col-span-3">
                                <LocalPaperUpload
                                    onUploadSuccess={handleUploadSuccess}
                                />
                                <LocalPaperList
                                    papers={localPapers}
                                    onToggle={handleTogglePaper}
                                    onRemove={handleRemovePaper}
                                />
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        {loading ? (
                            <Button disabled>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Starting...
                            </Button>
                        ) : (
                            <Button type="submit">Start Research</Button>
                        )}
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
