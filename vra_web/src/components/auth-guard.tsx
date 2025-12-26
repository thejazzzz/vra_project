"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { authApi } from "@/lib/api";
import { Loader2 } from "lucide-react";

const logger = console;

export default function AuthGuard({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const [isLoading, setIsLoading] = useState(true);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [shouldRender, setShouldRender] = useState(false);

    useEffect(() => {
        let isMounted = true;

        const checkAuth = async () => {
            // Public routes that don't need auth
            if (pathname === "/login" || pathname === "/") {
                if (isMounted) {
                    setShouldRender(true);
                    setIsLoading(false);
                }
                return;
            }

            // Cookie-based check: We cannot check for token presence client-side.
            // We rely on authApi.me() to validate the session.

            try {
                // Verify token validity with backend
                await authApi.me();
                if (isMounted) {
                    setIsAuthenticated(true);
                    setShouldRender(true);
                }
            } catch (error) {
                logger.error("Auth check failed:", error);

                if (isMounted) {
                    setIsLoading(false);
                    router.push("/login");
                }
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        };

        checkAuth();

        return () => {
            isMounted = false;
        };
    }, [pathname, router]);

    // Show loading spinner while checking auth
    if (isLoading) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-background">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    // If on a public route or authenticated, render children
    if (!isAuthenticated && !shouldRender) {
        return null;
    }

    return <>{children}</>;
}
