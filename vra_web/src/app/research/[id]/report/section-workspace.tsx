"use client";

import { useState } from "react";
import { ReportSection } from "@/types";
import { reportingApi } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import {
    Loader2,
    Lock,
    RefreshCw,
    Check,
    ArrowRight,
    AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import { useToast } from "@/components/ui/use-toast";

interface SectionWorkspaceProps {
    section: ReportSection;
    sessionId: string;
    allSections: ReportSection[]; // For dependency checking
    onRefresh: () => void;
}

export function SectionWorkspace({
    section,
    sessionId,
    allSections,
    onRefresh,
}: SectionWorkspaceProps) {
    const [isActionLoading, setIsActionLoading] = useState(false);
    const [feedback, setFeedback] = useState("");
    const [showActionPanel, setShowActionPanel] = useState(false);

    // --- Hooks ---
    const { toast } = useToast(); // Added hook initialization

    // Dependency Check
    const unresolvedDeps = section.depends_on.filter((depId) => {
        const dep = allSections.find((s) => s.section_id === depId);
        return dep?.status !== "accepted";
    });
    const isLocked = unresolvedDeps.length > 0;

    const handleGenerate = async () => {
        setIsActionLoading(true);
        try {
            await reportingApi.generateSection(sessionId, section.section_id);
            // Polling will pick up the 'generating' status
            onRefresh();
        } catch (err: any) {
            console.error(err);
            const status = err.response?.status;
            if (status === 423 || status === 409) {
                toast({
                    title: "Generation Queued",
                    description:
                        "This section is locked or being processed. Please wait.",
                    variant: "default",
                });
            } else {
                toast({
                    title: "Generation Failed",
                    description:
                        err.response?.data?.detail ||
                        "An unexpected error occurred.",
                    variant: "destructive",
                });
            }
        } finally {
            setIsActionLoading(false);
        }
    };

    const handleSubmitReview = async (accepted: boolean) => {
        setIsActionLoading(true);
        try {
            await reportingApi.submitReview(sessionId, section.section_id, {
                accepted,
                feedback: accepted ? undefined : feedback,
            });
            setFeedback("");
            onRefresh();
            if (accepted) {
                // Added default toast for accepted
                toast({
                    title: "Section Approved",
                    description: "Section marked as complete.",
                    variant: "default",
                });
            }
        } catch (err: any) {
            console.error(err);
            toast({
                title: "Review Failed",
                description:
                    err.response?.data?.detail || "Failed to submit review.",
                variant: "destructive",
            });
        } finally {
            setIsActionLoading(false);
        }
    };

    const handleReset = async () => {
        if (
            !confirm(
                "Are you sure? This will delete the current content and history."
            )
        )
            return;
        setIsActionLoading(true);
        try {
            // Force true acts as "Safe Reset & Regenerate" in our UX context
            // Backend auth will block if user doesnt have permission, but for now we follow req.
            await reportingApi.resetSection(
                sessionId,
                section.section_id,
                true
            ); // Added 'true' parameter
            onRefresh();
            toast({
                title: "Section Reset",
                description: "Content has been cleared.",
            }); // Added success toast
        } catch (err: any) {
            // Modified error type and added error toast
            console.error(err);
            toast({
                title: "Reset Failed",
                description:
                    err.response?.data?.detail || "Failed to reset section.",
                variant: "destructive",
            });
        } finally {
            setIsActionLoading(false);
        }
    };

    // --- RENDER STATES ---

    // 1. Locked / Planned (Empty)
    if (
        section.status === "planned" ||
        (section.status === "error" && !section.content)
    ) {
        return (
            <div className="h-full flex flex-col items-center justify-center text-center p-12 text-gray-400 bg-neutral-950">
                {isLocked ? (
                    <div className="max-w-md bg-neutral-900 p-6 rounded-xl border border-neutral-800">
                        <Lock className="w-8 h-8 mx-auto mb-4 text-gray-500" />
                        <h3 className="text-lg font-semibold text-gray-100 mb-2">
                            Section Locked
                        </h3>
                        <p className="text-sm">
                            Waiting for dependencies to be accepted:
                        </p>
                        <div className="flex flex-wrap gap-2 justify-center mt-3">
                            {unresolvedDeps.map((dep) => (
                                <span
                                    key={dep}
                                    className="px-2 py-1 bg-neutral-800 border-neutral-700 border rounded text-xs font-mono text-gray-300"
                                >
                                    {dep}
                                </span>
                            ))}
                        </div>
                    </div>
                ) : (
                    <div className="max-w-md">
                        <div className="w-12 h-12 bg-blue-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                            <ArrowRight className="w-6 h-6 text-blue-400" />
                        </div>
                        <h3 className="text-lg font-semibold text-gray-100 mb-2">
                            Ready to Draft
                        </h3>
                        <p className="text-sm text-gray-400 mb-6">
                            {section.description}
                        </p>
                        <Button
                            onClick={handleGenerate}
                            disabled={isActionLoading}
                            className="bg-blue-600 hover:bg-blue-700 text-white"
                        >
                            {isActionLoading ? (
                                <Loader2 className="animate-spin mr-2 h-4 w-4" />
                            ) : null}
                            Generate Draft
                        </Button>
                        {section.status === "error" && (
                            <p className="text-red-400 text-sm mt-4">
                                Previous generation failed. Please try again.
                            </p>
                        )}
                    </div>
                )}
            </div>
        );
    }

    // 2. Generating
    if (section.status === "generating") {
        return (
            <div className="h-full flex flex-col items-center justify-center p-12 bg-neutral-950">
                <Loader2 className="w-10 h-10 text-blue-500 animate-spin mb-4" />
                <h3 className="text-lg font-medium text-gray-100">
                    Writing Draft...
                </h3>
                <p className="text-sm text-gray-400 mt-2">
                    Using{" "}
                    {section.history[section.history.length - 1]?.model_name ||
                        "AI Model"}
                </p>
            </div>
        );
    }

    // 3. Review & Accepted (Content View)
    return (
        <div className="h-full flex flex-col bg-neutral-950">
            {/* Header / Meta */}
            <div className="border-b border-neutral-800 px-6 py-4 flex justify-between items-center bg-neutral-900 sticky top-0 z-10">
                <div>
                    <h2 className="text-xl font-bold text-gray-100">
                        {section.title}
                    </h2>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                        <span>
                            Revision {section.revision} /{" "}
                            {section.max_revisions}
                        </span>
                        {section.history.length > 0 &&
                            section.history[section.history.length - 1]
                                .model_name && (
                                <>
                                    <span>•</span>
                                    <span>
                                        {
                                            section.history[
                                                section.history.length - 1
                                            ].model_name
                                        }
                                    </span>
                                </>
                            )}
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    {section.status === "accepted" ? (
                        <div className="flex items-center gap-3">
                            <span className="px-3 py-1 bg-green-900/30 text-green-400 rounded-full text-sm font-medium flex items-center gap-2 border border-green-800">
                                <Check className="w-4 h-4" /> Accepted
                            </span>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={handleReset}
                                className="text-gray-400 hover:text-red-400 hover:bg-red-950/30"
                            >
                                Reset
                            </Button>
                        </div>
                    ) : (
                        <div className="flex items-center gap-2">
                            <Button
                                variant="outline"
                                onClick={() =>
                                    setShowActionPanel(!showActionPanel)
                                }
                                disabled={isActionLoading}
                                className="border-neutral-700 text-gray-300 hover:bg-neutral-800 hover:text-white"
                            >
                                Request Changes
                            </Button>
                            <Button
                                className="bg-green-600 hover:bg-green-700 text-white"
                                onClick={() => handleSubmitReview(true)}
                                disabled={isActionLoading}
                            >
                                {isActionLoading ? (
                                    <Loader2 className="animate-spin mr-2 h-4 w-4" />
                                ) : (
                                    <Check className="mr-2 h-4 w-4" />
                                )}
                                Approve
                            </Button>
                        </div>
                    )}
                </div>
            </div>

            {/* Content Body */}
            <div className="flex-1 overflow-y-auto p-6 lg:p-10 bg-neutral-950">
                <div className="max-w-4xl mx-auto prose prose-invert prose-blue prose-lg">
                    <ReactMarkdown>{section.content || ""}</ReactMarkdown>
                </div>
            </div>

            {/* Action Panel (Feedback) */}
            {showActionPanel && section.status === "review" && (
                <div className="border-t border-neutral-800 p-6 bg-neutral-900">
                    <div className="max-w-2xl mx-auto space-y-4">
                        <h4 className="font-semibold text-gray-100">
                            Request Changes
                        </h4>
                        <Textarea
                            placeholder="Describe what needs to be improved..."
                            value={feedback}
                            onChange={(e) => setFeedback(e.target.value)}
                            maxLength={500}
                            className="bg-neutral-950 border-neutral-800 text-gray-100 placeholder:text-gray-600 focus:border-blue-600"
                        />
                        <div className="flex justify-between items-center text-sm text-gray-500">
                            <span>{feedback.length} / 500 characters</span>
                            <div className="flex gap-2">
                                <Button
                                    variant="ghost"
                                    onClick={() => setShowActionPanel(false)}
                                    className="text-gray-400 hover:text-white hover:bg-neutral-800"
                                >
                                    Cancel
                                </Button>
                                <Button
                                    variant="default" // Orange-ish for regen?
                                    className="bg-orange-600 hover:bg-orange-700 text-white"
                                    onClick={() => handleSubmitReview(false)}
                                    disabled={
                                        !feedback.trim() ||
                                        isActionLoading ||
                                        section.revision >=
                                            section.max_revisions
                                    }
                                >
                                    {section.revision >= section.max_revisions
                                        ? "Max Revisions Reached"
                                        : "Regenerate"}
                                </Button>
                            </div>
                        </div>
                        {section.revision >= section.max_revisions && (
                            <Alert
                                variant="destructive"
                                className="bg-red-950/20 border-red-900"
                            >
                                <AlertTriangle className="h-4 w-4" />
                                <AlertTitle>Limit Reached</AlertTitle>
                                <AlertDescription>
                                    You have reached the maximum number of
                                    revisions for this section. Please reset if
                                    you need to start over.
                                </AlertDescription>
                            </Alert>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
