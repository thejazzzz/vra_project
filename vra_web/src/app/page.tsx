"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowRight, BrainCircuit, CheckCircle2 } from "lucide-react";
import { HeroGraph } from "@/components/landing/HeroGraph";
import { FeatureSection } from "@/components/landing/FeatureSection";
import { AgentSection } from "@/components/landing/AgentSection";
import { motion } from "framer-motion";

export default function LandingPage() {
    return (
        <div className="flex min-h-screen flex-col bg-background relative overflow-hidden">
            {/* Header */}
            <header className="px-4 lg:px-6 h-16 flex items-center border-b border-border/40 bg-background/60 backdrop-blur-md fixed top-0 w-full z-50">
                <Link className="flex items-center justify-center group" href="/">
                    <div className="bg-primary/10 p-2 rounded-lg group-hover:bg-primary/20 transition-colors">
                        <BrainCircuit className="h-6 w-6 text-primary" />
                    </div>
                    <span className="ml-3 text-xl font-extrabold tracking-tight">VRA</span>
                </Link>
                <nav className="ml-auto flex items-center gap-4 sm:gap-6">
                    <Link
                        className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                        href="#features"
                    >
                        Capabilities
                    </Link>
                    <Link
                        className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors hidden sm:block"
                        href="/login"
                    >
                        Sign In
                    </Link>
                    <Link href="/register">
                        <Button className="rounded-full px-6">
                            Get Started
                        </Button>
                    </Link>
                </nav>
            </header>

            <main className="flex-1 pt-16">
                {/* Hero Section */}
                <section className="relative w-full py-20 md:py-32 lg:py-48 flex flex-col items-center justify-center min-h-[90vh]">
                    <HeroGraph />
                    <div className="container relative z-10 px-4 md:px-6 text-center space-y-8">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.8 }}
                            className="inline-flex items-center rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-sm text-primary mb-4"
                        >
                            <span className="flex h-2 w-2 rounded-full bg-primary mr-2 animate-pulse"></span>
                            VRA 2.0 - Powered by Multi-Agent Architecture
                        </motion.div>
                        
                        <motion.div 
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.8, delay: 0.1 }}
                            className="space-y-4 max-w-4xl mx-auto"
                        >
                            <h1 className="text-5xl font-extrabold tracking-tighter sm:text-6xl md:text-7xl lg:text-8xl bg-clip-text text-transparent bg-gradient-to-br from-foreground via-foreground to-muted-foreground">
                                Bridge the Gap in Your <br className="hidden md:block"/>
                                <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-purple-400">
                                    Academic Research
                                </span>
                            </h1>
                            <p className="mx-auto max-w-[700px] text-muted-foreground md:text-xl lg:text-2xl font-medium">
                                Upload papers. Map the landscape. Let autonomous AI agents discover unexplored territories and draft rigorous literature reviews.
                            </p>
                        </motion.div>
                        
                        <motion.div 
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.8, delay: 0.2 }}
                            className="flex flex-col sm:flex-row justify-center gap-4 pt-4"
                        >
                            <Link href="/register">
                                <Button size="lg" className="h-14 px-8 text-lg rounded-full shadow-lg shadow-primary/25 hover:shadow-primary/40 transition-shadow">
                                    Start Researching Free
                                    <ArrowRight className="ml-2 h-5 w-5" />
                                </Button>
                            </Link>
                        </motion.div>

                        <motion.div 
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 1, delay: 0.5 }}
                            className="pt-12 text-sm text-muted-foreground flex items-center justify-center gap-8 opacity-70"
                        >
                            <div className="flex items-center gap-2">
                                <CheckCircle2 className="h-4 w-4 text-primary" />
                                <span>Powered by Finite State Machine</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <CheckCircle2 className="h-4 w-4 text-primary" />
                                <span>ChromaDB Vector Search</span>
                            </div>
                        </motion.div>
                    </div>
                </section>

                <FeatureSection />
                
                <AgentSection />

                {/* Final CTA Section */}
                <section className="w-full py-24 lg:py-32 relative z-10 border-t border-border/50 bg-background/50">
                    <div className="absolute inset-0 bg-primary/5 blur-3xl -z-10" />
                    <div className="container px-4 md:px-6 mx-auto text-center space-y-8">
                        <h2 className="text-4xl font-extrabold tracking-tighter md:text-5xl lg:text-6xl">
                            Ready to accelerate your discovery?
                        </h2>
                        <p className="mx-auto max-w-[600px] text-muted-foreground md:text-xl">
                            Join researchers mapping the future of human knowledge with VRA.
                        </p>
                        <Link href="/register" className="inline-block mt-8">
                            <Button size="lg" className="h-14 px-10 text-lg rounded-full">
                                Create Your First Project
                            </Button>
                        </Link>
                    </div>
                </section>
            </main>

            <footer className="relative z-10 flex flex-col gap-4 sm:flex-row py-8 w-full shrink-0 items-center px-4 md:px-6 border-t border-border/40 bg-background">
                <p className="text-sm text-muted-foreground">
                    © {new Date().getFullYear()} VRA Project. All rights reserved.
                </p>
                <nav className="sm:ml-auto flex gap-4 sm:gap-6">
                    <Link className="text-sm text-muted-foreground hover:text-foreground transition-colors" href="/terms">
                        Terms of Service
                    </Link>
                    <Link className="text-sm text-muted-foreground hover:text-foreground transition-colors" href="/privacy">
                        Privacy
                    </Link>
                </nav>
            </footer>
        </div>
    );
}
