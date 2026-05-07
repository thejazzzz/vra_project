"use client";

import { motion } from "framer-motion";
import { BrainCircuit, Cpu, ShieldAlert, ArrowRight } from "lucide-react";

export function AgentSection() {
    return (
        <section className="w-full py-24 lg:py-32 bg-secondary/5 relative z-10 overflow-hidden">
            <div className="container px-4 md:px-6 mx-auto">
                <div className="flex flex-col lg:flex-row gap-16 items-center">
                    <div className="flex-1 space-y-8">
                        <div>
                            <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl md:text-5xl mb-4">
                                The Multi-Agent Advantage
                            </h2>
                            <p className="text-muted-foreground md:text-xl max-w-[600px] leading-relaxed">
                                VRA doesn&apos;t just summarize text. It employs a team of specialized AI agents that collaborate to ensure deep analysis, structural logic, and academic rigor.
                            </p>
                        </div>
                        
                        <div className="space-y-6">
                            <div className="flex items-start gap-4">
                                <div className="p-3 bg-primary/20 text-primary rounded-xl shrink-0 mt-1">
                                    <BrainCircuit className="h-6 w-6" />
                                </div>
                                <div>
                                    <h4 className="text-lg font-bold">1. The Planner Agent</h4>
                                    <p className="text-muted-foreground">Architects the research strategy, breaks down complex topics, and outlines the required hypotheses.</p>
                                </div>
                            </div>
                            
                            <div className="flex items-start gap-4">
                                <div className="p-3 bg-chart-2/20 text-chart-2 rounded-xl shrink-0 mt-1">
                                    <Cpu className="h-6 w-6" />
                                </div>
                                <div>
                                    <h4 className="text-lg font-bold">2. The Researcher Agent</h4>
                                    <p className="text-muted-foreground">Executes the plan by diving deep into the ChromaDB vector store, extracting precise citations and uncovering hidden gaps.</p>
                                </div>
                            </div>

                            <div className="flex items-start gap-4">
                                <div className="p-3 bg-chart-1/20 text-chart-1 rounded-xl shrink-0 mt-1">
                                    <ShieldAlert className="h-6 w-6" />
                                </div>
                                <div>
                                    <h4 className="text-lg font-bold">3. The Reviewer Agent</h4>
                                    <p className="text-muted-foreground">Acts as a peer-reviewer. It challenges the generated hypotheses, flags logical inconsistencies, and ensures high-fidelity outputs.</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="flex-1 w-full max-w-md lg:max-w-none relative">
                        {/* Visual representation of the agent loop */}
                        <div className="relative aspect-square md:aspect-video lg:aspect-square max-w-[500px] mx-auto">
                            <div className="absolute inset-0 bg-primary/5 rounded-full blur-3xl" />
                            
                            <motion.div 
                                className="absolute top-10 left-1/2 -translate-x-1/2 p-6 bg-background border rounded-2xl shadow-xl z-20 flex flex-col items-center gap-2"
                                animate={{ y: [0, -10, 0] }}
                                transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
                            >
                                <BrainCircuit className="h-10 w-10 text-primary" />
                                <span className="font-bold text-sm">Planner</span>
                            </motion.div>

                            <motion.div 
                                className="absolute bottom-20 left-4 md:left-10 p-6 bg-background border rounded-2xl shadow-xl z-20 flex flex-col items-center gap-2"
                                animate={{ y: [0, 10, 0] }}
                                transition={{ repeat: Infinity, duration: 5, ease: "easeInOut", delay: 1 }}
                            >
                                <Cpu className="h-10 w-10 text-chart-2" />
                                <span className="font-bold text-sm">Researcher</span>
                            </motion.div>

                            <motion.div 
                                className="absolute bottom-20 right-4 md:right-10 p-6 bg-background border rounded-2xl shadow-xl z-20 flex flex-col items-center gap-2"
                                animate={{ y: [0, -10, 0] }}
                                transition={{ repeat: Infinity, duration: 4.5, ease: "easeInOut", delay: 2 }}
                            >
                                <ShieldAlert className="h-10 w-10 text-chart-1" />
                                <span className="font-bold text-sm">Reviewer</span>
                            </motion.div>

                            {/* Connecting lines SVG */}
                            <svg className="absolute inset-0 w-full h-full z-10 pointer-events-none text-border opacity-50">
                                <path d="M 250 120 L 120 300" stroke="currentColor" strokeWidth="2" strokeDasharray="5,5" fill="none" />
                                <path d="M 250 120 L 380 300" stroke="currentColor" strokeWidth="2" strokeDasharray="5,5" fill="none" />
                                <path d="M 150 330 L 350 330" stroke="currentColor" strokeWidth="2" strokeDasharray="5,5" fill="none" />
                            </svg>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
