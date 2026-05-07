"use client";

import dynamic from "next/dynamic";
import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import { useTheme } from "next-themes";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
    ssr: false,
});

// Generate some dummy data for the graph
const gData = {
    nodes: [...Array(30).keys()].map((i) => ({ id: i, group: i % 3 })),
    links: [...Array(40).keys()].map(() => ({
        source: Math.floor(Math.random() * 30),
        target: Math.floor(Math.random() * 30),
    })),
};

export function HeroGraph() {
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
    const containerRef = useRef<HTMLDivElement>(null);
    const { theme } = useTheme();

    useEffect(() => {
        const updateDimensions = () => {
            if (containerRef.current) {
                setDimensions({
                    width: containerRef.current.offsetWidth,
                    height: containerRef.current.offsetHeight,
                });
            }
        };

        window.addEventListener("resize", updateDimensions);
        updateDimensions();

        return () => window.removeEventListener("resize", updateDimensions);
    }, []);

    const nodeColor = theme === "dark" ? "#4b2bee" : "#4b2bee";
    const linkColor = theme === "dark" ? "rgba(255,255,255,0.1)" : "rgba(0,0,0,0.1)";
    const bgCol = "transparent";

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1.5 }}
            ref={containerRef}
            className="w-full h-full absolute inset-0 -z-10 overflow-hidden opacity-50 dark:opacity-40"
        >
            {dimensions.width > 0 && (
                <ForceGraph2D
                    width={dimensions.width}
                    height={dimensions.height}
                    graphData={gData}
                    nodeColor={(node: any) =>
                        node.group === 0 ? nodeColor : node.group === 1 ? "#8b5cf6" : "#6366f1"
                    }
                    linkColor={() => linkColor}
                    backgroundColor={bgCol}
                    nodeRelSize={4}
                    linkWidth={1.5}
                    enableZoomInteraction={false}
                    enablePanInteraction={false}
                    enableNodeDrag={true}
                    d3AlphaDecay={0.01}
                    d3VelocityDecay={0.2}
                />
            )}
            
            {/* Soft gradient overlay to blend edges */}
            <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-transparent z-0" />
            <div className="absolute inset-0 bg-gradient-to-r from-background via-transparent to-transparent z-0" />
        </motion.div>
    );
}
