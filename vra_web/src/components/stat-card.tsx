import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
    title: string;
    value: string | number;
    subtext?: string;
    icon: LucideIcon;
    className?: string;
}

export function StatCard({
    title,
    value,
    subtext,
    icon: Icon,
    className,
}: StatCardProps) {
    return (
        <Card className={cn("hover:bg-accent/50 transition-colors", className)}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                    {title}
                </CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
                <div className="text-2xl font-bold">{value}</div>
                {subtext && (
                    <p className="text-xs text-muted-foreground mt-1">
                        {subtext}
                    </p>
                )}
            </CardContent>
        </Card>
    );
}
