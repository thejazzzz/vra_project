import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
    const path = request.nextUrl.pathname;

    // Public paths that don't require authentication
    if (
        path === "/" ||
        path === "/login" ||
        path === "/terms" ||
        path === "/privacy" ||
        path.startsWith("/_next") ||
        path === "/favicon.ico" ||
        path.startsWith("/api/") // If we decide to proxy, or if these are Next.js API routes (unlikely for now)
    ) {
        return NextResponse.next();
    }

    // Check for auth token
    const token = request.cookies.get("vra_auth_token")?.value;

    // NOTE: We only check for the *presence* of the token here for efficient client-side routing.
    // Full cryptographic verification (signature, expiry, revocation) is performed by the backend API
    // on every protected request. This split architecture ensures the Edge middleware stays fast
    // while the Backend maintains strict security.

    if (!token) {
        // Redirect to login if no token found
        const url = new URL("/login", request.url);
        // Optional: Add return URL logic here
        // url.searchParams.set('from', path)
        return NextResponse.redirect(url);
    }

    return NextResponse.next();
}

export const config = {
    matcher: [
        /*
         * Match all request paths except for the ones starting with:
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         */
        "/((?!_next/static|_next/image|favicon.ico).*)",
    ],
};
