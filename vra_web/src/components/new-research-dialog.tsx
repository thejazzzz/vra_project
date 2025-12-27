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

export function NewResearchDialog({
    children,
}: {
    children?: React.ReactNode;
}) {
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const router = useRouter();

    const handleStart = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setError(null);
        try {
            const response = await plannerApi.plan(query);
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
            setError(
                err.response?.data?.detail ||
                    "Failed to start research. Please try again."
            );
        } finally {
            setLoading(false);
        }
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
