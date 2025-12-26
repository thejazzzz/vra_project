"use client";

import { useEffect, useState } from "react";
import { useResearchStore } from "@/lib/store";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Checkbox } from "@/components/ui/checkbox";
import { Card } from "@/components/ui/card";
import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, ChevronDown, ChevronUp, FileText, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

interface PaperReviewDialogProps {
    query: string;
}

export function PaperReviewDialog({ query }: PaperReviewDialogProps) {
    const { papers, submitReview, addPaper, isLoading } = useResearchStore();
    const [selectedIds, setSelectedIds] = useState<string[]>([]);
    const [isOpen, setIsOpen] = useState(false);
    const [activeTab, setActiveTab] = useState("review");

    // Manual Entry State
    const [newPaper, setNewPaper] = useState({
        title: "",
        abstract: "",
        url: "",
        year: new Date().getFullYear().toString(),
        authors: "",
    });

    /** Select all papers by default when papers load */
    useEffect(() => {
        if (papers?.length) {
            setSelectedIds(papers.map((p) => p.canonical_id || p.id));
        }
    }, [papers]);

    const handleToggle = (id: string, checked: boolean) => {
        setSelectedIds((prev) =>
            checked ? [...prev, id] : prev.filter((x) => x !== id)
        );
    };

    const handleSubmit = async () => {
        try {
            await submitReview({
                query,
                selected_paper_ids: selectedIds,
                audience: "general",
            });
            setIsOpen(false);
        } catch (error) {
            console.error("Failed to submit review:", error);
        }
    };

    const handleAddPaper = async () => {
        if (!newPaper.title || !newPaper.abstract) return;

        try {
            await addPaper({
                query,
                title: newPaper.title,
                abstract: newPaper.abstract,
                url: newPaper.url,
                year: newPaper.year,
                authors: newPaper.authors
                    .split(",")
                    .map((a) => a.trim())
                    .filter((a) => a),
                source: "user_upload",
            });

            // Reset and switch back only on success
            setNewPaper({
                title: "",
                abstract: "",
                url: "",
                year: new Date().getFullYear().toString(),
                authors: "",
            });
            setActiveTab("review");
        } catch (error) {
            console.error("Failed to add paper:", error);
            // Consider adding user-facing error notification here
        }
    };
    return (
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
            <DialogTrigger asChild>
                <Button size="sm">Start Review</Button>
            </DialogTrigger>
            <DialogContent className="max-w-3xl h-[85vh] flex flex-col gap-0 p-0 overflow-hidden">
                <Tabs
                    value={activeTab}
                    onValueChange={setActiveTab}
                    className="flex flex-col h-full"
                >
                    {/* Header Section */}
                    <div className="p-6 pb-2 border-b bg-background z-10">
                        <DialogHeader className="mb-4">
                            <DialogTitle>Research Material</DialogTitle>
                            <DialogDescription>
                                Review retrieved papers or add your own sources
                                manually.
                            </DialogDescription>
                        </DialogHeader>
                        <TabsList className="grid w-full grid-cols-2">
                            <TabsTrigger value="review">
                                Review Collected ({papers?.length || 0})
                            </TabsTrigger>
                            <TabsTrigger value="add">
                                Add Manual Entry
                            </TabsTrigger>
                        </TabsList>
                    </div>

                    {/* Review Tab Content */}
                    <TabsContent
                        value="review"
                        className="flex-1 min-h-0 flex flex-col m-0 data-[state=inactive]:hidden"
                    >
                        <div className="flex-1 min-h-0 w-full relative">
                            <ScrollArea className="h-full w-full">
                                <div className="p-6 pt-4 space-y-4">
                                    {papers?.map((paper) => {
                                        const pid =
                                            paper.canonical_id || paper.id;
                                        const selected =
                                            selectedIds.includes(pid);

                                        return (
                                            <Collapsible
                                                key={pid}
                                                className="group"
                                            >
                                                <Card
                                                    className={cn(
                                                        "flex flex-col bg-secondary/20 transition-all border-l-4",
                                                        selected
                                                            ? "border-l-primary"
                                                            : "border-l-transparent"
                                                    )}
                                                >
                                                    <div className="flex gap-4 p-4 items-start">
                                                        <Checkbox
                                                            checked={selected}
                                                            onCheckedChange={(
                                                                c
                                                            ) =>
                                                                handleToggle(
                                                                    pid,
                                                                    c === true
                                                                )
                                                            }
                                                            className="mt-1"
                                                        />

                                                        <div className="flex-1 space-y-1">
                                                            <div className="flex justify-between gap-2">
                                                                <h4 className="text-sm font-semibold leading-tight">
                                                                    {
                                                                        paper.title
                                                                    }
                                                                </h4>

                                                                <CollapsibleTrigger
                                                                    asChild
                                                                >
                                                                    <Button
                                                                        variant="ghost"
                                                                        size="sm"
                                                                        className="h-6 w-6 p-0"
                                                                    >
                                                                        <ChevronDown className="h-4 w-4 transition-transform group-data-[state=open]:rotate-180" />
                                                                        <span className="sr-only">
                                                                            Toggle
                                                                            details
                                                                        </span>
                                                                    </Button>
                                                                </CollapsibleTrigger>
                                                            </div>

                                                            <div className="text-xs text-muted-foreground">
                                                                {paper.authors
                                                                    ?.slice(
                                                                        0,
                                                                        3
                                                                    )
                                                                    .join(
                                                                        ", "
                                                                    )}{" "}
                                                                •{" "}
                                                                {paper.year ||
                                                                    "N/A"}
                                                                {paper.venue &&
                                                                    ` • ${paper.venue}`}
                                                            </div>

                                                            <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                                                                {paper.summary ||
                                                                    paper.abstract?.slice(
                                                                        0,
                                                                        150
                                                                    ) + "..." ||
                                                                    "No summary available."}
                                                            </p>
                                                        </div>
                                                    </div>

                                                    <CollapsibleContent>
                                                        <div className="px-4 pb-4 pl-12">
                                                            <div className="bg-background/50 border rounded-md p-3 text-xs text-muted-foreground">
                                                                <h5 className="font-semibold flex items-center gap-2 mb-1 text-foreground">
                                                                    <FileText className="h-3 w-3" />{" "}
                                                                    Full
                                                                    Abstract
                                                                </h5>
                                                                {paper.abstract ||
                                                                    "No abstract available."}
                                                            </div>
                                                        </div>
                                                    </CollapsibleContent>
                                                </Card>
                                            </Collapsible>
                                        );
                                    })}
                                </div>
                            </ScrollArea>
                        </div>

                        <div className="p-6 pt-4 border-t mt-auto text-right flex items-center justify-between bg-background z-10">
                            <span className="text-sm text-muted-foreground">
                                {selectedIds.length} of {papers?.length || 0}{" "}
                                selected
                            </span>
                            <div className="flex gap-2">
                                <Button
                                    variant="outline"
                                    onClick={() => setIsOpen(false)}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    onClick={handleSubmit}
                                    disabled={
                                        isLoading || selectedIds.length === 0
                                    }
                                >
                                    {isLoading && (
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    )}
                                    Confirm Selection
                                </Button>
                            </div>
                        </div>
                    </TabsContent>

                    {/* Add Manual Tab Content */}
                    <TabsContent
                        value="add"
                        className="flex-1 min-h-0 flex flex-col m-0 p-0 overflow-hidden data-[state=inactive]:hidden"
                    >
                        <ScrollArea className="h-full w-full">
                            <div className="p-6 pt-4 grid gap-4">
                                <div className="grid gap-2">
                                    <Label htmlFor="title">Paper Title *</Label>
                                    <Input
                                        id="title"
                                        placeholder="e.g. Attention Is All You Need"
                                        value={newPaper.title}
                                        onChange={(e) =>
                                            setNewPaper({
                                                ...newPaper,
                                                title: e.target.value,
                                            })
                                        }
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="grid gap-2">
                                        <Label htmlFor="author">
                                            Authors (comma separated)
                                        </Label>
                                        <Input
                                            id="author"
                                            placeholder="Vaswani, Shazeer, et al."
                                            value={newPaper.authors}
                                            onChange={(e) =>
                                                setNewPaper({
                                                    ...newPaper,
                                                    authors: e.target.value,
                                                })
                                            }
                                        />
                                    </div>
                                    <div className="grid gap-2">
                                        <Label htmlFor="year">Year</Label>
                                        <Input
                                            id="year"
                                            type="number"
                                            placeholder="2017"
                                            value={newPaper.year}
                                            onChange={(e) =>
                                                setNewPaper({
                                                    ...newPaper,
                                                    year: e.target.value,
                                                })
                                            }
                                        />
                                    </div>
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="url">URL (Optional)</Label>
                                    <Input
                                        id="url"
                                        placeholder="https://arxiv.org/..."
                                        value={newPaper.url}
                                        onChange={(e) =>
                                            setNewPaper({
                                                ...newPaper,
                                                url: e.target.value,
                                            })
                                        }
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="abstract">
                                        Abstract / Summary *
                                    </Label>
                                    <Textarea
                                        id="abstract"
                                        placeholder="Paste the abstract here..."
                                        className="min-h-[150px]"
                                        value={newPaper.abstract}
                                        onChange={(e) =>
                                            setNewPaper({
                                                ...newPaper,
                                                abstract: e.target.value,
                                            })
                                        }
                                    />
                                </div>
                                <div className="flex justify-end pt-4">
                                    <Button
                                        onClick={handleAddPaper}
                                        disabled={
                                            !newPaper.title ||
                                            !newPaper.abstract ||
                                            isLoading
                                        }
                                    >
                                        {isLoading && (
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        )}
                                        <Plus className="mr-2 h-4 w-4" /> Add
                                        Paper to List
                                    </Button>
                                </div>
                            </div>
                        </ScrollArea>
                    </TabsContent>
                </Tabs>
            </DialogContent>
        </Dialog>
    );
}
