"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Clock, Trash2 } from "lucide-react";
import { plannerApi } from "@/lib/api";
import { NewResearchDialog } from "@/components/new-research-dialog";
import { DashboardHeader } from "@/components/dashboard-header";

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
                setSessions(data.sessions || []);
            } catch (e) {
                console.error("Failed to fetch sessions", e);
            } finally {
                setLoading(false);
            }
        }
        fetchSessions();
    }, []);

    const performDelete = async (sessionId: string, force: boolean) => {
        try {
            const response = await plannerApi.deleteSession(sessionId, force);
            
            if (response.status === "cancelling") {
                alert("Session cancellation requested. Background tasks are halting. You can force delete it now or wait a moment.");
                setSessions((prev) => 
                    prev.map((s) => s.session_id === sessionId ? { ...s, status: "CANCELLING" } : s)
                );
            } else {
                setSessions((prev) =>
                    prev.filter((s) => s.session_id !== sessionId),
                );
            }
        } catch (error: any) {
            console.error("Failed to delete session", error);
            const errorMsg = error.response?.data?.detail || "Failed to delete session.";
            
            if (error.response?.status === 409 || errorMsg.toLowerCase().includes("conflict") || errorMsg.toLowerCase().includes("running")) {
                if (window.confirm(`${errorMsg}\n\nWould you like to FORCE delete this session anyway?`)) {
                    performDelete(sessionId, true);
                }
            } else {
                alert(`${errorMsg} Please try again.`);
            }
        }
    };

    const handleDelete = async (e: React.MouseEvent, sessionId: string, force: boolean = false) => {
        e.preventDefault(); 
        e.stopPropagation();

        const message = force 
            ? "Are you sure you want to FORCE delete this session? This action cannot be undone."
            : "Are you sure you want to permanently delete this research session?";

        if (window.confirm(message)) {
            performDelete(sessionId, force);
        }
    };

    return (
        <div className="flex min-h-screen flex-col">
            <DashboardHeader />
            <main className="flex-1 container mx-auto p-6 space-y-8">
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
                        <NewResearchDialog>
                            <Button variant="outline" className="mt-4">
                                Start Research
                            </Button>
                        </NewResearchDialog>
                    </div>
                ) : (
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {sessions.map((session) => (
                            <div
                                key={session.session_id}
                                className="relative group"
                            >
                                <Link
                                    href={`/research/${session.session_id}`}
                                    className="block h-full"
                                >
                                    <Card className="h-full hover:bg-muted/50 transition-colors cursor-pointer border">
                                        <CardHeader className="pb-2">
                                            <div className="flex justify-between items-start">
                                                <Badge
                                                    variant={
                                                        session.status?.toLowerCase() === "running"
                                                            ? "default"
                                                            : session.status?.toLowerCase() === "cancelling"
                                                            ? "destructive"
                                                            : "secondary"
                                                    }
                                                >
                                                    {session.status?.toLowerCase()}
                                                </Badge>
                                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                                    <Clock className="h-3 w-3" />
                                                    {new Date(
                                                        session.last_updated,
                                                    ).toLocaleDateString()}
                                                </span>
                                            </div>
                                            <CardTitle className="leading-snug line-clamp-2 mt-2 pr-8">
                                                {session.query}
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <p className="text-sm text-muted-foreground">
                                                Session ID:{" "}
                                                {session.session_id.substring(
                                                    0,
                                                    8,
                                                )}
                                                ...
                                            </p>
                                        </CardContent>
                                    </Card>
                                </Link>

                                <Button
                                    variant="destructive"
                                    size="icon"
                                    className="absolute bottom-4 right-4 h-8 w-8 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity"
                                    aria-label="Delete session"
                                    onClick={(e) =>
                                        handleDelete(e, session.session_id)
                                    }
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </div>
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
}
