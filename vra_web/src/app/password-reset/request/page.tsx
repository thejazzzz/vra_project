"use client";

import { useState } from "react";
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

export default function PasswordResetRequestPage() {
    const [email, setEmail] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isSuccess, setIsSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        if (!email || !email.includes("@")) {
            setError("Please enter a valid email address.");
            setIsLoading(false);
            return;
        }

        try {
            await authApi.requestPasswordReset(email);
            setIsSuccess(true);
        } catch (err: any) {
            console.error("Password reset request failed", err);
            // We show success even if email not found to prevent enumeration
            setIsSuccess(true);
        } finally {
            setIsLoading(false);
        }
    };

    if (isSuccess) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-background p-4 text-foreground">
                <Card className="w-full max-w-md">
                    <CardHeader>
                        <div className="flex justify-center mb-4">
                            <CheckCircle2 className="h-12 w-12 text-primary" />
                        </div>
                        <CardTitle className="text-2xl font-bold text-center">
                            Check Your Email
                        </CardTitle>
                        <CardDescription className="text-center">
                            If an account exists for <strong>{email}</strong>,
                            you will receive a password reset link shortly.
                        </CardDescription>
                    </CardHeader>
                    <CardFooter className="flex flex-col gap-4">
                        <Link href="/login" className="w-full">
                            <Button className="w-full" variant="outline">
                                Back to Sign In
                            </Button>
                        </Link>
                    </CardFooter>
                </Card>
            </div>
        );
    }

    return (
        <div className="flex min-h-screen items-center justify-center bg-background p-4 text-foreground">
            <Card className="w-full max-w-md">
                <CardHeader className="space-y-1">
                    <CardTitle className="text-2xl font-bold">
                        Reset Password
                    </CardTitle>
                    <CardDescription>
                        Enter your email address and we&apos;ll send you a link
                        to reset your password.
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
                    <CardFooter className="flex flex-col gap-4">
                        <Button
                            className="w-full"
                            type="submit"
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Sending Link...
                                </>
                            ) : (
                                "Send Reset Link"
                            )}
                        </Button>
                        <div className="text-center text-sm text-muted-foreground">
                            Remember your password?{" "}
                            <Link
                                href="/login"
                                className="text-primary hover:underline underline-offset-4"
                            >
                                Sign In
                            </Link>
                        </div>
                    </CardFooter>
                </form>
            </Card>
        </div>
    );
}
