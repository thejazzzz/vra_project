"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Loader2, LayoutDashboard, Clock } from "lucide-react";
import { plannerApi } from "@/lib/api";
import { NewResearchDialog } from "@/components/new-research-dialog";

interface ResearchSession {
    session_id: string;
    query: string;
    status: string;
    last_updated: string;
}

export default function DashboardPage() {
    const [sessions, setSessions] = useState<ResearchSession[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchSessions() {
            try {
                const data = await plannerApi.getSessions();
                setSessions(data.sessions);
            } catch (e) {
                console.error("Failed to fetch sessions", e);
            } finally {
                setLoading(false);
            }
        }
        fetchSessions();
    }, []);

    return (
        <div className="container mx-auto p-6 space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">
                        My Research
                    </h1>
                    <p className="text-muted-foreground">
                        Manage your research sessions and history.
                    </p>
                </div>
                <NewResearchDialog />
            </div>

            {loading ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map((i) => (
                        <Skeleton key={i} className="h-40 rounded-xl" />
                    ))}
                </div>
            ) : sessions.length === 0 ? (
                <div className="rounded-lg border border-dashed p-12 text-center">
                    <h3 className="text-lg font-medium">
                        No research sessions found
                    </h3>
                    <p className="text-sm text-muted-foreground mt-2">
                        Start your first research query to see it here.
                    </p>
                    <Link href="/" className="mt-4 inline-block">
                        <Button variant="outline">Start Research</Button>
                    </Link>
                </div>
            ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {sessions.map((session) => (
                        <Link
                            key={session.session_id}
                            href={`/research/${session.session_id}`}
                        >
                            <Card className="h-full hover:bg-muted/50 transition-colors cursor-pointer">
                                <CardHeader className="pb-2">
                                    <div className="flex justify-between items-start">
                                        <Badge
                                            variant={
                                                session.status === "running"
                                                    ? "default"
                                                    : "secondary"
                                            }
                                        >
                                            {session.status}
                                        </Badge>
                                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                                            <Clock className="h-3 w-3" />
                                            {new Date(
                                                session.last_updated
                                            ).toLocaleDateString()}
                                        </span>
                                    </div>
                                    <CardTitle className="leading-snug line-clamp-2 mt-2">
                                        {session.query}
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <p className="text-sm text-muted-foreground">
                                        Session ID:{" "}
                                        {session.session_id.substring(0, 8)}...
                                    </p>
                                </CardContent>
                            </Card>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}
