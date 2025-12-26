"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
    ArrowRight,
    BrainCircuit,
    Network,
    BookOpen,
    Layers,
} from "lucide-react";

export default function LandingPage() {
    return (
        <div className="flex min-h-screen flex-col bg-background">
            <header className="px-4 lg:px-6 h-14 flex items-center border-b">
                <Link className="flex items-center justify-center" href="/">
                    <BrainCircuit className="h-6 w-6 text-primary" />
                    <span className="ml-2 text-lg font-bold">VRA</span>
                </Link>
                <nav className="ml-auto flex gap-4 sm:gap-6">
                    <Link
                        className="text-sm font-medium hover:underline underline-offset-4"
                        href="#features"
                    >
                        Features
                    </Link>
                    <Link
                        className="text-sm font-medium hover:underline underline-offset-4"
                        href="/login"
                    >
                        Sign In
                    </Link>
                </nav>
            </header>
            <main className="flex-1">
                <section className="w-full py-12 md:py-24 lg:py-32 xl:py-48 flex flex-col items-center text-center px-4 md:px-6">
                    <div className="container max-w-4xl space-y-6">
                        <div className="space-y-2">
                            <h1 className="text-4xl font-extrabold tracking-tighter sm:text-5xl md:text-6xl lg:text-7xl bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-500">
                                Virtual Research Assistant
                            </h1>
                            <p className="mx-auto max-w-[700px] text-gray-400 md:text-xl">
                                Accelerate your academic research with AI-driven
                                insights, automated gap analysis, and
                                interactive knowledge graphs.
                            </p>
                        </div>
                        <div className="space-x-4">
                            <Link href="/login">
                                <Button size="lg" className="h-12 px-8">
                                    Start a New Research Session
                                    <ArrowRight className="ml-2 h-4 w-4" />
                                </Button>
                            </Link>
                        </div>
                    </div>
                </section>

                <section
                    id="features"
                    className="w-full py-12 md:py-24 lg:py-32 bg-muted/20"
                >
                    <div className="container px-4 md:px-6 mx-auto">
                        <h2 className="text-3xl font-bold tracking-tighter text-center mb-12">
                            Key Capabilities
                        </h2>
                        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
                            <div className="flex flex-col items-center space-y-3 p-6 border rounded-lg bg-background/50">
                                <Network className="h-12 w-12 text-primary mb-2" />
                                <h3 className="text-xl font-bold">
                                    Knowledge Graphs
                                </h3>
                                <p className="text-muted-foreground text-center">
                                    Visualize connections between papers,
                                    authors, and concepts to find hidden
                                    relationships.
                                </p>
                            </div>
                            <div className="flex flex-col items-center space-y-3 p-6 border rounded-lg bg-background/50">
                                <Layers className="h-12 w-12 text-primary mb-2" />
                                <h3 className="text-xl font-bold">
                                    Gap Analysis
                                </h3>
                                <p className="text-muted-foreground text-center">
                                    Automatically identify unexplored areas and
                                    structural gaps in the current literature.
                                </p>
                            </div>
                            <div className="flex flex-col items-center space-y-3 p-6 border rounded-lg bg-background/50">
                                <BookOpen className="h-12 w-12 text-primary mb-2" />
                                <h3 className="text-xl font-bold">
                                    Automated Reporting
                                </h3>
                                <p className="text-muted-foreground text-center">
                                    Generate comprehensive literature reviews
                                    and research proposals in minutes.
                                </p>
                            </div>
                        </div>
                    </div>
                </section>
            </main>
            <footer className="flex flex-col gap-2 sm:flex-row py-6 w-full shrink-0 items-center px-4 md:px-6 border-t">
                <p className="text-xs text-muted-foreground">
                    © 2024 VRA Project. All rights reserved.
                </p>
                <nav className="sm:ml-auto flex gap-4 sm:gap-6">
                    <Link
                        className="text-xs hover:underline underline-offset-4"
                        href="/terms"
                    >
                        Terms of Service
                    </Link>
                    <Link
                        className="text-xs hover:underline underline-offset-4"
                        href="/privacy"
                    >
                        Privacy
                    </Link>
                </nav>
            </footer>
        </div>
    );
}
