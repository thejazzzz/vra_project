"use client";

import Link from "next/link";
import { BrainCircuit } from "lucide-react";
import { UserNav } from "./user-nav";

export function DashboardHeader() {
    return (
        <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="container flex h-14 items-center justify-between">
                <div className="flex items-center gap-2 md:gap-4">
                    <Link
                        href="/dashboard"
                        className="flex items-center space-x-2"
                    >
                        <BrainCircuit className="h-6 w-6 text-primary" />
                        <span className="hidden font-bold sm:inline-block">
                            VRA Dashboard
                        </span>
                    </Link>
                </div>
                <div className="flex flex-1 items-center justify-end space-x-4">
                    <nav className="flex items-center space-x-2">
                        <UserNav />
                    </nav>
                </div>
            </div>
        </header>
    );
}
