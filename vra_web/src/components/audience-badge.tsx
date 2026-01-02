import { Badge } from "@/components/ui/badge";

interface AudienceBadgeProps {
    audience: string;
}

export function AudienceBadge({ audience }: AudienceBadgeProps) {
    const map: Record<string, string> = {
        phd: "Academic / PhD",
        rd: "R&D / Engineering",
        industry: "Industry / Business",
        general: "General Audience",
    };

    const label = map[audience] || audience;

    return (
        <Badge variant="outline" className="text-xs bg-muted/50 font-normal">
            Audience: <span className="font-semibold ml-1">{label}</span>
        </Badge>
    );
}
