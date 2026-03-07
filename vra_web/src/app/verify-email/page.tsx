"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";

function VerifyEmailContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const token = searchParams.get("token");

    const [status, setStatus] = useState<"loading" | "success" | "error">(
        "loading",
    );
    const [message, setMessage] = useState("Verifying your email address...");

    useEffect(() => {
        if (!token) {
            setStatus("error");
            setMessage("Invalid or missing verification token.");
            return;
        }

        const verify = async () => {
            try {
                await authApi.verifyEmail(token);
                setStatus("success");
                setMessage("Your email has been verified successfully!");
            } catch (err: any) {
                console.error("Email verification failed", err);
                setStatus("error");
                const detail = err.response?.data?.detail;
                setMessage(
                    detail ||
                        "Failed to verify email. The link may have expired or is invalid.",
                );
            }
        };

        verify();
    }, [token]);

    if (status === "loading") {
        return (
            <Card className="w-full max-w-md">
                <CardHeader>
                    <div className="flex justify-center mb-4">
                        <Loader2 className="h-12 w-12 text-primary animate-spin" />
                    </div>
                    <CardTitle className="text-2xl font-bold text-center">
                        Verifying Email
                    </CardTitle>
                    <CardDescription className="text-center">
                        Please wait while we confirm your email address.
                    </CardDescription>
                </CardHeader>
            </Card>
        );
    }

    if (status === "success") {
        return (
            <Card className="w-full max-w-md">
                <CardHeader>
                    <div className="flex justify-center mb-4">
                        <CheckCircle2 className="h-12 w-12 text-primary" />
                    </div>
                    <CardTitle className="text-2xl font-bold text-center">
                        Email Verified
                    </CardTitle>
                    <CardDescription className="text-center">
                        {message}
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

    return (
        <Card className="w-full max-w-md">
            <CardHeader>
                <div className="flex justify-center mb-4">
                    <XCircle className="h-12 w-12 text-destructive" />
                </div>
                <CardTitle className="text-2xl font-bold text-center">
                    Verification Failed
                </CardTitle>
                <CardDescription className="text-center">
                    {message}
                </CardDescription>
            </CardHeader>
            <CardFooter>
                <Link href="/login" className="w-full">
                    <Button className="w-full" variant="outline">
                        Back to Sign In
                    </Button>
                </Link>
            </CardFooter>
        </Card>
    );
}

export default function VerifyEmailPage() {
    return (
        <div className="flex min-h-screen items-center justify-center bg-background p-4 text-foreground">
            <Suspense
                fallback={
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                }
            >
                <VerifyEmailContent />
            </Suspense>
        </div>
    );
}
