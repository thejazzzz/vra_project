//vra_web/src/app/research/[id]/report/sidebar-nav.tsx
"use client";

import { ReportSection, SectionStatus } from "@/types";
import {
    CheckCircle,
    Circle,
    Loader2,
    Lock,
    AlertCircle,
    FileText,
} from "lucide-react";
import { cn } from "@/lib/utils"; // Assuming strict CSS/Tailwind hybrid uses generic cn utility

interface SectionNavigationListProps {
    sections: ReportSection[];
    activeSectionId: string;
    onSelect: (id: string) => void;
}

const StatusIcon = ({ status }: { status: SectionStatus }) => {
    switch (status) {
        case "accepted":
            return <CheckCircle className="w-4 h-4 text-green-500" />;
        case "review":
            return <AlertCircle className="w-4 h-4 text-orange-500" />;
        case "generating":
            return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
        case "error":
            return <AlertCircle className="w-4 h-4 text-red-500" />;
        case "planned":
        default:
            return <Circle className="w-4 h-4 text-gray-300" />;
    }
};

export function SectionNavigationList({
    sections,
    activeSectionId,
    onSelect,
}: SectionNavigationListProps) {
    const acceptedCount = sections.filter(
        (s) => s.status === "accepted"
    ).length;

    return (
        <div className="w-72 border-r bg-white flex flex-col h-full">
            <div className="p-4 border-b">
                <h3 className="font-semibold text-gray-900">Report Sections</h3>
                <p className="text-xs text-gray-500 mt-1">
                    {acceptedCount} / {sections.length} Accepted
                </p>
                {/* Progress Bar */}
                <div className="w-full bg-gray-100 h-1.5 mt-3 rounded-full overflow-hidden">
                    <div
                        className="bg-green-500 h-full transition-all duration-500"
                        style={{
                            width: `${
                                sections.length
                                    ? (acceptedCount / sections.length) * 100
                                    : 0
                            }%`,
                        }}
                    />
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-1">
                {sections.map((section) => {
                    const isActive = section.section_id === activeSectionId;

                    // Client-side visual dependency check to warn user
                    // (Backend enforcement is source of truth, but UI should hint)
                    const unresolvedDeps = section.depends_on.filter(
                        (depId) => {
                            const dep = sections.find(
                                (s) => s.section_id === depId
                            );
                            return dep?.status !== "accepted";
                        }
                    );
                    const isLocked =
                        unresolvedDeps.length > 0 &&
                        section.status === "planned";

                    return (
                        <button
                            key={section.section_id}
                            onClick={() => onSelect(section.section_id)}
                            className={cn(
                                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-left transition-colors",
                                isActive
                                    ? "bg-blue-50 text-blue-700 font-medium"
                                    : "text-gray-600 hover:bg-gray-50",
                                isLocked ? "opacity-70" : ""
                            )}
                        >
                            {isLocked ? (
                                <Lock className="w-4 h-4 text-gray-300" />
                            ) : (
                                <StatusIcon status={section.status} />
                            )}
                            <span className="truncate flex-1">
                                {section.title}
                            </span>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}
