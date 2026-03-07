"use client";

import { useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
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
import { AlertCircle, Loader2, CheckCircle2 } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

function PasswordResetConfirmForm() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const token = searchParams.get("token");

    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isSuccess, setIsSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        if (!token) {
            setError("Invalid or missing reset token.");
            setIsLoading(false);
            return;
        }

        if (password.length < 8) {
            setError("Password must be at least 8 characters.");
            setIsLoading(false);
            return;
        }

        if (password !== confirmPassword) {
            setError("Passwords do not match.");
            setIsLoading(false);
            return;
        }

        try {
            await authApi.resetPassword(token, password);
            setIsSuccess(true);
        } catch (err: any) {
            console.error("Password reset failed", err);
            const detail = err.response?.data?.detail;
            setError(
                detail ||
                    "Failed to reset password. The link may have expired.",
            );
        } finally {
            setIsLoading(false);
        }
    };

    if (isSuccess) {
        return (
            <Card className="w-full max-w-md">
                <CardHeader>
                    <div className="flex justify-center mb-4">
                        <CheckCircle2 className="h-12 w-12 text-primary" />
                    </div>
                    <CardTitle className="text-2xl font-bold text-center">
                        Password Reset
                    </CardTitle>
                    <CardDescription className="text-center">
                        Your password has been successfully reset. You can now
                        sign in with your new credentials.
                    </CardDescription>
                </CardHeader>
                <CardFooter>
                    <Link href="/login" className="w-full">
                        <Button className="w-full">Go to Sign In</Button>
                    </Link>
                </CardFooter>
            </Card>
        );
    }

    if (!token) {
        return (
            <Card className="w-full max-w-md">
                <CardHeader>
                    <CardTitle className="text-destructive font-bold">
                        Invalid Link
                    </CardTitle>
                    <CardDescription>
                        This password reset link is invalid or has expired.
                    </CardDescription>
                </CardHeader>
                <CardFooter>
                    <Link href="/password-reset/request" className="w-full">
                        <Button className="w-full" variant="outline">
                            Request New Link
                        </Button>
                    </Link>
                </CardFooter>
            </Card>
        );
    }

    return (
        <Card className="w-full max-w-md">
            <CardHeader className="space-y-1">
                <CardTitle className="text-2xl font-bold">
                    New Password
                </CardTitle>
                <CardDescription>
                    Please enter your new password below.
                </CardDescription>
            </CardHeader>
            <form onSubmit={handleSubmit}>
                <CardContent className="space-y-4">
                    {error && (
                        <Alert variant="destructive">
                            <AlertCircle className="h-4 w-4" />
                            <AlertTitle>Error</AlertTitle>
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}

                    <div className="space-y-2">
                        <Label htmlFor="password">New Password</Label>
                        <Input
                            id="password"
                            type="password"
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            disabled={isLoading}
                            minLength={8}
                            required
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="confirm-password">
                            Confirm New Password
                        </Label>
                        <Input
                            id="confirm-password"
                            type="password"
                            placeholder="••••••••"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            disabled={isLoading}
                            minLength={8}
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
                                Resetting Password...
                            </>
                        ) : (
                            "Reset Password"
                        )}
                    </Button>
                </CardFooter>
            </form>
        </Card>
    );
}

export default function PasswordResetConfirmPage() {
    return (
        <div className="flex min-h-screen items-center justify-center bg-background p-4 text-foreground">
            <Suspense
                fallback={
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                }
            >
                <PasswordResetConfirmForm />
            </Suspense>
        </div>
    );
}
