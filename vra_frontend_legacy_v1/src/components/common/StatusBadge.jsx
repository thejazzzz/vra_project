// src/components/common/StatusBadge.jsx
import React from "react";
import { cn } from "../../utils"; // Assuming utils exists or I will create it? Use clsx/tailwind-merge directly if not.
// Let's use clsx directly for now if utils not present, or create utils.
import clsx from "clsx";
import { twMerge } from "tailwind-merge";

const variants = {
    emerging: "bg-green-500/10 text-green-400 border-green-500/20",
    stable: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    saturated: "bg-red-500/10 text-red-400 border-red-500/20",
    neutral: "bg-slate-500/10 text-slate-400 border-slate-500/20",
    concept: "bg-blue-500/10 text-blue-400 border-blue-500/20",
};

export const StatusBadge = ({ status, label, className }) => {
    const variant = variants[status?.toLowerCase()] || variants.neutral;

    return (
        <span
            className={cn(
                "px-2.5 py-0.5 rounded-full text-xs font-medium border",
                variant,
                className
            )}
        >
            {label || status}
        </span>
    );
};
