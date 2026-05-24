import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

/**
 * GET /api/auth/callback/google?code=...
 * This path must match GOOGLE_REDIRECT_URI exactly.
 * Exchanges the Google auth code for tokens via Flask backend,
 * sets httpOnly session cookies, then redirects to onboarding.
 */
export async function GET(req: NextRequest) {
  const code = req.nextUrl.searchParams.get("code");

  if (!code) {
    return NextResponse.redirect(new URL("/?error=missing_code", req.url));
  }

  const res = await fetch(`${API_BASE}/auth/google/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });

  if (!res.ok) {
    console.error("Token exchange failed:", await res.text());
    return NextResponse.redirect(new URL("/?error=exchange_failed", req.url));
  }

  const { pm_id, session_token } = await res.json();

  const cookieStore = await cookies();
  cookieStore.set("session_token", session_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 30,
    path: "/",
  });
  // pm_id is a non-sensitive UUID; keep it readable by JS so onboarding/training pages can use it
  cookieStore.set("pm_id", pm_id, {
    httpOnly: false,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 30,
    path: "/",
  });

  // ?google=done tells the onboarding page to mark step 2 complete.
  // All scopes (gmail.compose + calendar.readonly) are requested in the
  // initial sign-in, so step 2 is always done after any successful exchange.
  return NextResponse.redirect(new URL("/dashboard/onboarding?google=done", req.url));
}
