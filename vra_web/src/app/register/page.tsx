"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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

export default function RegisterPage() {
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isSuccess, setIsSuccess] = useState(false);

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        // Basic validation
        if (!email || !email.includes("@")) {
            setError("Please enter a valid email address.");
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
            await authApi.register(email, password);
            setIsSuccess(true);
        } catch (err: any) {
            console.error("Registration failed", err);
            const detail = err.response?.data?.detail;
            let message = "Registration failed. Please try again.";

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

    if (isSuccess) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-background p-4">
                <Card className="w-full max-w-md">
                    <CardHeader>
                        <div className="flex justify-center mb-4">
                            <CheckCircle2 className="h-12 w-12 text-primary" />
                        </div>
                        <CardTitle className="text-2xl font-bold text-center">
                            Registration Successful
                        </CardTitle>
                        <CardDescription className="text-center">
                            We've sent a verification link to{" "}
                            <strong>{email}</strong>. Please check your inbox to
                            activate your account.
                        </CardDescription>
                    </CardHeader>
                    <CardFooter className="flex flex-col gap-4">
                        <Link href="/login" className="w-full">
                            <Button className="w-full">
                                Return to Sign In
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
                        Create an Account
                    </CardTitle>
                    <CardDescription>
                        Enter your email and a strong password to get started.
                    </CardDescription>
                </CardHeader>
                <form onSubmit={handleRegister}>
                    <CardContent className="space-y-4">
                        {error && (
                            <Alert variant="destructive">
                                <AlertCircle className="h-4 w-4" />
                                <AlertTitle>Registration Error</AlertTitle>
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

                        <div className="space-y-2">
                            <Label htmlFor="password">Password</Label>
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
                            <p className="text-xs text-muted-foreground">
                                Must be at least 8 characters.
                            </p>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="confirm-password">
                                Confirm Password
                            </Label>
                            <Input
                                id="confirm-password"
                                type="password"
                                placeholder="••••••••"
                                value={confirmPassword}
                                onChange={(e) =>
                                    setConfirmPassword(e.target.value)
                                }
                                disabled={isLoading}
                                minLength={8}
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
                                    Creating Account...
                                </>
                            ) : (
                                "Sign Up"
                            )}
                        </Button>
                        <div className="text-center text-sm text-muted-foreground">
                            Already have an account?{" "}
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
