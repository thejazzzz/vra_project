import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import { Providers } from "@/components/session-provider";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
    title: "VRA - Research Intelligence",
    description: "Advanced Research Assistant Dashboard",
};

import AuthGuard from "@/components/auth-guard";

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className="dark">
            <body
                className={cn(
                    "min-h-screen bg-background font-sans antialiased",
                    inter.variable
                )}
            >
                <Providers>
                    <AuthGuard>{children}</AuthGuard>
                </Providers>
            </body>
        </html>
    );
}
