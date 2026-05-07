"use client";

import { motion } from "framer-motion";
import { Network, Layers, BookOpen, Search, Workflow, ShieldCheck } from "lucide-react";

const features = [
    {
        title: "Knowledge Graphs",
        description: "Visualize connections between papers, authors, and concepts to find hidden relationships and academic voids.",
        icon: Network,
    },
    {
        title: "Gap Analysis",
        description: "Automatically identify unexplored territories and structural weaknesses in current literature.",
        icon: Search,
    },
    {
        title: "Automated Reporting",
        description: "Generate comprehensive literature reviews, abstracts, and proposals backed by strict citations.",
        icon: BookOpen,
    },
    {
        title: "Multi-Agent Orchestration",
        description: "Utilizes specialized agents for planning, deep-dive research, and rigorous peer-review logic.",
        icon: Workflow,
    },
    {
        title: "Structural Integrity",
        description: "Ensures every generated insight is logically sound and directly traceable to uploaded source documents.",
        icon: Layers,
    },
    {
        title: "Data Privacy",
        description: "Your proprietary research is kept secure in private vector databases, never used to train public models.",
        icon: ShieldCheck,
    },
];

const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
        opacity: 1,
        transition: {
            staggerChildren: 0.1,
        },
    },
};

const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
        y: 0,
        opacity: 1,
        transition: { type: "spring" as const, stiffness: 100 },
    },
};

export function FeatureSection() {
    return (
        <section id="features" className="w-full py-24 lg:py-32 relative z-10">
            <div className="container px-4 md:px-6 mx-auto">
                <div className="text-center mb-16">
                    <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl md:text-5xl bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-400">
                        Accelerate Discovery
                    </h2>
                    <p className="mt-4 max-w-[700px] mx-auto text-muted-foreground md:text-xl">
                        A complete suite of AI-driven tools designed specifically for rigorous academic research.
                    </p>
                </div>

                <motion.div
                    className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3"
                    variants={containerVariants}
                    initial="hidden"
                    whileInView="visible"
                    viewport={{ once: true, margin: "-100px" }}
                >
                    {features.map((feature, index) => {
                        const Icon = feature.icon;
                        return (
                            <motion.div
                                key={index}
                                variants={itemVariants}
                                className="group relative overflow-hidden rounded-xl border bg-background/40 backdrop-blur-md p-8 hover:bg-background/60 transition-colors"
                            >
                                <div className="absolute inset-0 bg-gradient-to-b from-primary/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                                <div className="relative z-10 flex flex-col items-start space-y-4">
                                    <div className="p-3 rounded-lg bg-primary/10 text-primary">
                                        <Icon className="h-8 w-8" />
                                    </div>
                                    <h3 className="text-xl font-bold">{feature.title}</h3>
                                    <p className="text-muted-foreground leading-relaxed">
                                        {feature.description}
                                    </p>
                                </div>
                            </motion.div>
                        );
                    })}
                </motion.div>
            </div>
        </section>
    );
}
