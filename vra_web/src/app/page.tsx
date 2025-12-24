"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useResearchStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Sparkles, ArrowRight, Loader2 } from "lucide-react";

export default function LandingPage() {
    const router = useRouter();
    const [inputQuery, setInputQuery] = useState("");
    const { startResearch, isLoading, error } = useResearchStore();

    const handleStart = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!inputQuery.trim()) return;

        try {
            const success = await startResearch(inputQuery);
            if (success) {
                router.push(`/research/${encodeURIComponent(inputQuery)}`);
            }
            // Error state will be displayed by the error UI below
        } catch (err) {
            // Error is handled by the store
            console.error("Failed to start research:", err);
        }
    };

    return (
        <div className="min-h-screen flex flex-col items-center justify-center p-4 bg-background text-foreground relative overflow-hidden">
            {/* Ambient Background */}
            <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary/20 via-background to-background -z-10" />

            <div className="max-w-2xl w-full space-y-8 animate-in fade-in slide-in-from-bottom-5 duration-700">
                <div className="text-center space-y-2">
                    <div className="inline-flex items-center justify-center p-2 bg-primary/10 rounded-full mb-4 ring-1 ring-primary/20">
                        <Sparkles className="w-5 h-5 text-primary mr-2" />
                        <span className="text-sm font-medium text-primary">
                            Virtual Research Assistant
                        </span>
                    </div>
                    <h1 className="text-4xl md:text-6xl font-bold tracking-tight">
                        Research Intelligence <br />
                        <span className="text-primary bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-500">
                            Reimagined
                        </span>
                    </h1>
                    <p className="text-muted-foreground text-lg max-w-lg mx-auto">
                        Automated multi-agent research pipelines. From query to
                        comprehensive report in minutes.
                    </p>
                </div>

                <Card className="border-primary/20 bg-card/50 backdrop-blur">
                    <CardHeader>
                        <CardTitle>Start a New Investigation</CardTitle>
                        <CardDescription>
                            Enter a research topic, question, or hypothesis.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleStart} className="flex gap-4">
                            <Input
                                placeholder="e.g., 'Impact of LLMs on Clinical Decision Support'..."
                                className="flex-1"
                                value={inputQuery}
                                onChange={(e) => setInputQuery(e.target.value)}
                                disabled={isLoading}
                                suppressHydrationWarning
                            />
                            <Button
                                type="submit"
                                disabled={isLoading}
                                className="min-w-[120px]"
                                suppressHydrationWarning
                            >
                                {isLoading ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Init...
                                    </>
                                ) : (
                                    <>
                                        Analyze{" "}
                                        <ArrowRight className="ml-2 h-4 w-4" />
                                    </>
                                )}
                            </Button>
                        </form>
                        {error && (
                            <p className="text-sm text-destructive mt-3 flex items-center">
                                <span className="w-1.5 h-1.5 rounded-full bg-destructive mr-2" />
                                {error}
                            </p>
                        )}
                    </CardContent>
                </Card>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center text-sm text-muted-foreground">
                    <div className="p-4 rounded-lg bg-secondary/20">
                        <strong className="block text-foreground mb-1">
                            Deep Search
                        </strong>
                        Aggregates papers from trusted sources.
                    </div>
                    <div className="p-4 rounded-lg bg-secondary/20">
                        <strong className="block text-foreground mb-1">
                            Graph Analysis
                        </strong>
                        Maps concepts and authors dynamically.
                    </div>
                    <div className="p-4 rounded-lg bg-secondary/20">
                        <strong className="block text-foreground mb-1">
                            Gap Identification
                        </strong>
                        Finds structural opportunities using AI.
                    </div>
                </div>
            </div>
        </div>
    );
}
