// src/components/common/StatCard.jsx
import React from "react";
import { motion } from "framer-motion";

export const StatCard = ({ title, value, subtext, icon: Icon, delay = 0 }) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay, duration: 0.3 }}
            className="card flex items-start justify-between min-h-[120px]"
        >
            <div>
                <h3 className="text-muted-foreground text-sm font-medium mb-1">
                    {title}
                </h3>
                <div className="text-3xl font-bold text-white mb-2">
                    {value}
                </div>
                {subtext && (
                    <p className="text-xs text-muted-foreground">{subtext}</p>
                )}
            </div>
            {Icon && (
                <div className="p-2 bg-primary/10 rounded-lg text-primary">
                    <Icon size={24} />
                </div>
            )}
        </motion.div>
    );
};
