"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { AlertCircle, Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

export default function LoginPage() {
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        if (!email || !email.includes("@")) {
            setError("Please enter a valid email address.");
            setIsLoading(false);
            return;
        }

        try {
            const response = await authApi.login(email);
            if (response.access_token) {
                // Manual Cookie Stamping to fix Localhost Middleware visibility issues
                document.cookie = `vra_auth_token=${response.access_token}; path=/; max-age=3600; samesite=Lax`;
                // Redundancy: Store in LocalStorage for API Client Interceptor
                localStorage.setItem("vra_auth_token", response.access_token);
            }
            router.push("/dashboard"); // Redirect to dashboard
        } catch (err: any) {
            console.error("Login failed", err);
            const detail = err.response?.data?.detail;
            let message = "Login failed. Please try again.";

            if (detail) {
                if (typeof detail === "string") {
                    message = detail;
                } else if (Array.isArray(detail)) {
                    message = detail
                        .map((e: any) => e.msg || JSON.stringify(e))
                        .join("; ");
                } else {
                    message = JSON.stringify(detail);
                }
            }
            setError(message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-background p-4">
            <Card className="w-full max-w-sm">
                <CardHeader className="space-y-1">
                    <CardTitle className="text-2xl font-bold">
                        Sign In
                    </CardTitle>
                    <CardDescription>
                        Enter your email to access the VRA platform.
                        <br />
                        <span className="text-xs text-muted-foreground">
                            (Demo Mode: No password required)
                        </span>
                    </CardDescription>
                </CardHeader>
                <form onSubmit={handleLogin}>
                    <CardContent className="space-y-4">
                        {error && (
                            <Alert variant="destructive">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{error}</AlertDescription>
                            </Alert>
                        )}
                        <div className="space-y-2">
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="name@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                disabled={isLoading}
                                required
                            />
                        </div>
                    </CardContent>
                    <CardFooter>
                        <Button
                            className="w-full"
                            type="submit"
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Signing In...
                                </>
                            ) : (
                                "Sign In"
                            )}
                        </Button>
                    </CardFooter>
                </form>
            </Card>
        </div>
    );
}
