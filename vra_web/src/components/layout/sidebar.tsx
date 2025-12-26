"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
    LayoutDashboard,
    Network,
    Users,
    TrendingUp,
    AlertTriangle,
    FileText,
    Lightbulb,
} from "lucide-react";
import { useResearchStore } from "@/lib/store";

interface SidebarProps {
    params: { id: string };
}

export function Sidebar({ params }: SidebarProps) {
    const pathname = usePathname();
    const { query } = useResearchStore();
    const baseUrl = `/research/${params.id}`;

    const navItems = [
        { name: "Overview", href: baseUrl, icon: LayoutDashboard },
        {
            name: "Knowledge Graph",
            href: `${baseUrl}/knowledge`,
            icon: Network,
        },
        { name: "Author Network", href: `${baseUrl}/authors`, icon: Users },
        { name: "Trends", href: `${baseUrl}/trends`, icon: TrendingUp },
        { name: "Research Gaps", href: `${baseUrl}/gaps`, icon: AlertTriangle },
        { name: "Hypotheses", href: `${baseUrl}/hypotheses`, icon: Lightbulb },
        { name: "Report", href: `${baseUrl}/report`, icon: FileText },
    ];

    return (
        <div className="pb-12 w-64 border-r min-h-screen bg-card/50 hidden md:block fixed left-0 top-0 h-full overflow-y-auto">
            <div className="space-y-4 py-4">
                <div className="px-4 py-2">
                    <h2 className="mb-2 px-2 text-lg font-semibold tracking-tight text-primary">
                        <Link href="/dashboard" className="hover:underline">
                            VRA Dashboard
                        </Link>
                    </h2>
                    <p
                        className="px-2 text-xs text-muted-foreground truncate"
                        title={query}
                    >
                        {query || "No Active Query"}
                    </p>
                </div>
                <div className="px-3 py-2">
                    <div className="space-y-1">
                        {navItems.map((item) => (
                            <Button
                                key={item.href}
                                variant={
                                    pathname === item.href ||
                                    (item.href !== baseUrl &&
                                        pathname.startsWith(item.href))
                                        ? "secondary"
                                        : "ghost"
                                }
                                className={cn(
                                    "w-full justify-start",
                                    (pathname === item.href ||
                                        (item.href !== baseUrl &&
                                            pathname.startsWith(item.href))) &&
                                        "bg-secondary"
                                )}
                                asChild
                            >
                                <Link href={item.href}>
                                    <item.icon className="mr-2 h-4 w-4" />
                                    {item.name}
                                </Link>
                            </Button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
