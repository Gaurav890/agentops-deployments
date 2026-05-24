import { NextRequest, NextResponse } from "next/server";

/**
 * Protect all /dashboard/* routes.
 * If session_token cookie is missing → redirect to landing page.
 */
export function middleware(req: NextRequest) {
  const sessionToken = req.cookies.get("session_token")?.value;
  if (!sessionToken) {
    return NextResponse.redirect(new URL("/", req.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*"],
};
