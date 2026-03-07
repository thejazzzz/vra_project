"use client";

import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { LogOut, User, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { UserResponse } from "@/types";

export function UserNav() {
    const router = useRouter();
    const [user, setUser] = useState<UserResponse | null>(null);

    useEffect(() => {
        authApi.me().then(setUser).catch(console.error);
    }, []);

    const handleLogout = async () => {
        try {
            await authApi.logout();
            router.push("/login");
        } catch (error) {
            console.error("Logout failed", error);
            // Force redirect even if API fails
            localStorage.removeItem("vra_auth_token");
            document.cookie =
                "vra_auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;";
            router.push("/login");
        }
    };

    if (!user) return null;

    const initials = user.email
        ? user.email.substring(0, 2).toUpperCase()
        : "U";

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button
                    variant="ghost"
                    className="relative h-8 w-8 rounded-full"
                >
                    <Avatar className="h-8 w-8">
                        <AvatarFallback>{initials}</AvatarFallback>
                    </Avatar>
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end" forceMount>
                <DropdownMenuLabel className="font-normal">
                    <div className="flex flex-col space-y-1">
                        <p className="text-sm font-medium leading-none">
                            {user.email}
                        </p>
                        <p className="text-xs leading-none text-muted-foreground">
                            {user.role}
                        </p>
                    </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => router.push("/dashboard")}>
                    <User className="mr-2 h-4 w-4" />
                    <span>My Research</span>
                </DropdownMenuItem>
                <DropdownMenuItem disabled>
                    <ShieldCheck className="mr-2 h-4 w-4" />
                    <span>Security (MFA)</span>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                    onClick={handleLogout}
                    className="text-destructive"
                >
                    <LogOut className="mr-2 h-4 w-4" />
                    <span>Log out</span>
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
