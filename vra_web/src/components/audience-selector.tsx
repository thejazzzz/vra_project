import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { GraduationCap, Briefcase, Factory, Users } from "lucide-react";

interface AudienceSelectorProps {
    audience: string;
    setAudience: (audience: string) => void;
}

export function AudienceSelector({
    audience,
    setAudience,
}: AudienceSelectorProps) {
    const options = [
        {
            id: "general",
            label: "General Audience",
            icon: Users,
            description: "Broad, accessible, overview-focused",
        },
        {
            id: "phd",
            label: "PhD / Academic",
            icon: GraduationCap,
            description: "Formal, detailed, citation-heavy",
        },
        {
            id: "rd",
            label: "R&D / Engineering",
            icon: Factory,
            description: "Technical, implementation-focused",
        },
        {
            id: "industry",
            label: "Industry / Business",
            icon: Briefcase,
            description: "Strategic, ROI-focused, concise",
        },
    ];

    return (
        <div
            className="space-y-3"
            role="radiogroup"
            aria-label="Target Audience"
        >
            <Label>Target Audience</Label>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {options.map((opt, index) => {
                    const Icon = opt.icon;
                    const isSelected = audience === opt.id;
                    const isFocusable =
                        isSelected || (!audience && index === 0);
                    return (
                        <button
                            type="button"
                            key={opt.id}
                            role="radio"
                            aria-checked={isSelected}
                            tabIndex={isFocusable ? 0 : -1}
                            onClick={() => setAudience(opt.id)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                    e.preventDefault();
                                    setAudience(opt.id);
                                }
                            }}
                            className={cn(
                                "cursor-pointer rounded-lg border p-3 flex flex-col items-center gap-2 text-center transition-all hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                                isSelected
                                    ? "border-primary bg-primary/5 ring-1 ring-primary"
                                    : "border-muted bg-background"
                            )}
                        >
                            <Icon
                                className={cn(
                                    "h-5 w-5",
                                    isSelected
                                        ? "text-primary"
                                        : "text-muted-foreground"
                                )}
                            />
                            <div className="space-y-1">
                                <div className="font-medium text-sm leading-none">
                                    {opt.label}
                                </div>
                                <div className="text-[10px] text-muted-foreground">
                                    {opt.description}
                                </div>
                            </div>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}
